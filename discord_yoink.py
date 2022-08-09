import requests
import json
import re
import time
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass(order=True)
class User:
    uid: int = field(hash=True, compare=False)
    username: str = field(compare=False)
    common_guilds: list[int] = field(compare=False)
    guild_count: int = field(hash=False, compare=True)


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
            while True:
                if num_done % 15 == 0:
                    percent = round(num_done / len(self.matched_ids), 2) * 100
                    time_remaining = (len(self.matched_ids) - num_done) * 2
                    print(f"Currently {num_done}/{len(self.matched_ids)} ({percent}%) done. Estimated time remaining: {time_remaining} seconds")

                time.sleep(2)
                user_response = self.get_user(uid)
                if user_response.user is not None:
                    self.users.append(user_response.user)
                    break
                elif user_response.no_shared_guild:
                    break
                elif user_response.rate_limited:
                    percent = round(num_done / len(self.matched_ids), 2) * 100
                    print(f"Rate limited for {user_response.rate_limit}. Currently {num_done}/{len(self.matched_ids)} ({percent}%) done.")
                    time.sleep(user_response.rate_limit)
                else:
                    print(f"Unknown error on uid {uid}")
                    break
            num_done += 1

        self.display_results()

    def display_results(self):
        shared_servers = defaultdict(list)
        for u in self.users:
            shared_servers[u.guild_count] += [u.username]

        sorted_keys = sorted(shared_servers.keys(), reverse=True)
        with open("results.txt", mode="w", encoding="utf-8") as f:
            for k in sorted_keys:
                line = f"{k}: {shared_servers[k]}\n"
                print(line, end="")
                f.write(line)
        print()

    def get_user(self, user_id) -> 'GetUserResponse':
        params = {"with_mutual_guilds": True}
        headers = {"Authorization": self.auth,
                   "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:103.0) Gecko/20100101 Firefox/103.0",
                    "Referer": "https://discord.com/"}
        r = requests.get(url=f"https://discord.com/api/v9/users/{user_id}/profile", params=params, headers=headers)
        try:
            j = r.json()
        except Exception as e:
            raise e

        # Don't share server.
        if "code" in j and j["code"] == 50001:
            return self.GetUserResponse(no_shared_guild=True)
        # Rate limited
        if "retry_after" in j:
            return self.GetUserResponse(rate_limited=True, rate_limit=j["retry_after"])

        guilds = j["mutual_guilds"]
        user = User(int(user_id), j["user"]["username"], guilds, len(guilds))
        return self.GetUserResponse(user=user)

    class GetUserResponse:
        def __init__(self, user=None, rate_limit=0, no_shared_guild=False, rate_limited=False):
            self.rate_limit = rate_limit
            self.user = user
            self.no_shared_guild = no_shared_guild
            self.rate_limited = rate_limited


gg = GuildGetter()
gg.parse_har()
gg.fetch_uids()
