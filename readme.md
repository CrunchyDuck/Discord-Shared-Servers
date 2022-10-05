## What's this?
This program searches through all the members of a server/your DMs, checks how many servers they have in common with you, and reports that information back to you!
It does this by getting their user IDs from their profile pictures, meaning any profile picture you load will be included in the list.

## Why's this?
I wanted to find new friends, and common interests is a good start :)

## How's this?
To do this, my program needs to get a list of user IDs you share a server with, and also get your account's token to form a request.
Both can be gotten by parsing the Discord network traffic.

### Recording network traffic
These instructions are for Firefox, but can be modified for other browsers.
1. Open your web browser in incognito/private mode.
1. Open Inspect Element with ctrl + shift + I.
1. Click the Network tab. Do not close this until told to.
1. On the network tab there should be a list of filters (HTML, CSS, JS...). Click "All"
1. Log into Discord on your browser.

Firefox will now start recording any data from Discord. We'll be using this to get the IDs of the people you want to check.
To get these IDs, while the Network tab is open:
1. Click on a server you want to search for new friends in.
1. Scroll through the list of members on the right until you reach the bottom.
1. Repeat for any other servers you wish to search.
1. Click the cog at the top right of the Inspect Element window to open Network Settings, and click "Save All As HAR".
1. Navigate to the folder discord_yoink.py is in, and name the file "requests.har"
1. You can now close Inspect Element/Discord

After this has been done, you merely run discord_yoink.py. Due to Discord's rate limiting, it will take **quite a while** to sort through them all - 1 user every 2 seconds.
The program will update you on how it's doing, and you can just leave it running in the background.
Once it has finished, it will print the information to the console, and also to a file called "results.txt"
