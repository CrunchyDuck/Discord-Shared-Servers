GET_MUTUAL_FRIENDS = True
GET_MUTUAL_SERVERS = True

import requests
import json
import re
import time
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass(order=True)
class User:
    uid: int = field(hash=True, compare=False)
    common_guilds: list[int] = field(hash=False, compare=False)
    guild_count: int = field(hash=False, compare=False)

    mutual_friends: list[str] = field(hash=False, compare=False)
    mutual_friends_count: int = field(hash=False, compare=False)


class GuildGetter:
    # Normal UID
    r_get_uid1 = re.compile(r'https://cdn\.discordapp\.com/avatars/(\d+)')
    # User has a custom PFP for this server.
    r_get_uid2 = re.compile(r'https://cdn\.discordapp\.com/guilds/\d+/users/(\d+)/avatars')
    r_get_auth = re.compile(r'"name": "Authorization",.+?"value": "(.+?)"', flags=re.DOTALL)

    def __init__(self):
        self.auth = None
        self.matched_ids = []
        self.users = []
        self.id_lookup = {}

    def parse_har(self):
        print("Parsing HAR file.")
        with open("requests.har", encoding='utf-8') as f:
            file = f.read()
        # Get auth token
        self.auth = self.r_get_auth.search(file).group(1)

        discord_requests = json.loads(file)
        # Get all IDs.
        for entry in discord_requests["log"]["entries"]:
            r = entry["request"]
            url = r["url"]
            match = self.r_get_uid1.match(url)
            if not match:
                match = self.r_get_uid2.match(url)

            if match:
                self.matched_ids.append(match.group(1))

        self.matched_ids = list(set(self.matched_ids))

    def fetch_uids(self):
        print("Fetching shared servers.")
        num_done = 0
        for uid in self.matched_ids:
            if num_done % 5 == 0:
                percent = round(num_done / len(self.matched_ids), 2) * 100
                time_remaining = (len(self.matched_ids) - num_done) * 2
                print(
                    f"Currently {num_done}/{len(self.matched_ids)} ({percent}%) done. Estimated time remaining: {time_remaining} seconds")

            while True:
                time.sleep(2)
                user_response = self.get_user(uid)
                if user_response.user is not None:
                    self.users.append(user_response.user)
                    break
                elif user_response.rate_limited:
                    percent = round(num_done / len(self.matched_ids), 2) * 100
                    print(
                        f"Rate limited for {user_response.rate_limit}. Currently {num_done}/{len(self.matched_ids)} ({percent}%) done.")
                    time.sleep(user_response.rate_limit)
                else:
                    print(f"Unknown error on uid {uid}")
                    break

            num_done += 1

    def display_results(self):
        # Create or clear file
        with open("results.txt", mode="w"):
            pass

        # Display shared guilds.
        print("People with more than 1 shared servers:")
        shared_servers = defaultdict(list)
        for u in self.users:
            name = self.id_to_username(u.uid)
            shared_servers[u.guild_count] += [name]

        sorted_keys = sorted(shared_servers.keys(), reverse=True)
        with open("results.txt", mode="a", encoding="utf-8") as f:
            f.write("Shared servers:\n")
            for k in sorted_keys:
                line = f"{k}: {shared_servers[k]}\n"
                if int(k) >= 2:
                    print(line, end="")
                f.write(line)
            f.write("\n")
        print()

        # Display shared friends
        print("People with shared friends:")
        shared_friends = defaultdict(list)
        for u in self.users:
            name = self.id_to_username(u.uid)
            shared_friends[u.mutual_friends_count] += [name]

        sorted_keys = sorted(shared_friends.keys(), reverse=True)
        with open("results.txt", mode="a", encoding="utf-8") as f:
            f.write("Shared friends:\n")
            for k in sorted_keys:
                line = f"{k}: {shared_friends[k]}\n"
                if int(k) >= 1:
                    print(line, end="")
                f.write(line)
            f.write("\n")
        print()

        with open("results.txt", mode="a", encoding="utf-8") as f:
            f.write("Individual user data (probably use ctrl+f here):\n")
            for u in self.users:
                name = self.id_to_username(u.uid)
                f.write(f"{name}:\n")
                f.write(f"Shared friends: ")
                for uid in u.mutual_friends:
                    name = self.id_to_username(uid)
                    f.write(f"{name}, ")
                f.write("\n\n")
                #f.write(f"Shared servers: {u.common_guilds}\n")

        print("Finished! This data, as well as a bit more, is in results.txt")

    def id_to_username(self, uid: str) -> str:
        if uid in self.id_lookup:
            return self.id_lookup[uid]
        else:
            return uid

    def get_user(self, user_id) -> 'GetUserResponse':
        friends = []
        guilds = []
        params = {"with_mutual_guilds": True}
        headers = {"Authorization": self.auth,
                   "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:103.0) Gecko/20100101 Firefox/103.0",
                   "Referer": "https://discord.com/"}

        if GET_MUTUAL_SERVERS:
            r = requests.get(url=f"https://discord.com/api/v9/users/{user_id}/profile", params=params, headers=headers)
            try:
                j = r.json()
            except Exception as e:
                raise e
            # Rate limited
            if "retry_after" in j:
                return self.GetUserResponse(rate_limited=True, rate_limit=j["retry_after"])

            # Shares server.
            if not ("code" in j and j["code"] == 50001):
                guilds = j["mutual_guilds"]
                self.id_lookup[user_id] = j["user"]["username"]

        if GET_MUTUAL_FRIENDS:
            r = requests.get(url=f"https://discord.com/api/v9/users/{user_id}/relationships", headers=headers)
            try:
                j = r.json()
            except Exception as e:
                raise e
            # Rate limited
            if "retry_after" in j:
                print("limited on friends")
                return self.GetUserResponse(rate_limited=True, rate_limit=j["retry_after"])

            # Share amigos.
            if not ("code" in j and j["code"] == 50001):
                for friend in j:
                    friends.append(friend["username"])
                    self.id_lookup[friend["id"]] = friend["username"]

        user = User(user_id, guilds, len(guilds), friends, len(friends))
        return self.GetUserResponse(user=user)

    class GetUserResponse:
        def __init__(self, user=None, rate_limit=0, rate_limited=False):
            self.rate_limit = rate_limit
            self.user = user
            self.rate_limited = rate_limited


gg = GuildGetter()
gg.parse_har()
gg.fetch_uids()
gg.display_results()
