# Pulls info from CricBuzz RapidAPI via API

import requests
import datetime
import argparse

# -----------------------
# CONFIGURATION
# -----------------------
RAPIDAPI_KEY = "aKeyIsRequired"
RAPIDAPI_URL = "https://cricbuzz-cricket.p.rapidapi.com/news/v1/index"

DISCUIT_BASE = "https://discuit.org"
USERNAME = "username"
PASSWORD = "password"
COMMUNITY = "community"

# In this case the community is Cricket

# -----------------------
# ARGPARSE: --live flag
# -----------------------
parser = argparse.ArgumentParser(description="Post CricBuzz news to Discuit.")
parser.add_argument("--live", action="store_true", help="Actually post (default is dry-run)")
args = parser.parse_args()
LIVE_POST = args.live

# -----------------------
# STEP 1: FETCH CRICBUZZ NEWS
# -----------------------
headers = {
    "x-rapidapi-host": "cricbuzz-cricket.p.rapidapi.com",
    "x-rapidapi-key": RAPIDAPI_KEY,
}
response = requests.get(RAPIDAPI_URL, headers=headers)
data = response.json()

cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

title = f"CricBuzz News Summary — {today}"

lines = []

for story in data.get("storyList", []):
    story_data = story.get("story")
    if not story_data:
        continue

    pub_time = story_data.get("pubTime")
    if not pub_time:
        continue

    pub_dt = datetime.datetime.utcfromtimestamp(int(pub_time) / 1000)
    if pub_dt < cutoff:
        continue

    headline = story_data.get("hline", "No Title")
    intro = story_data.get("intro", "").strip()
    caption = story_data.get("coverImage", {}).get("caption", "").strip()
    topic = story_data.get("context", "")

    lines.append(f"### {headline}")
    if intro:
        lines.append(f"{intro}\n")
    if caption:
        lines.append(f"> *{caption}*\n")
    if topic:
        lines.append(f"`{topic}`\n")
    lines.append("---\n")

web_url = data.get("appIndex", {}).get("webURL", "")
if web_url:
    lines.append(f"[Full story list on CricBuzz]({web_url})")

body = "\n".join(lines)

# -----------------------
# STEP 2: LOGIN TO DISCUIT
# -----------------------
session = requests.Session()
initial_resp = session.get(f"{DISCUIT_BASE}/api/_initial")
csrf = initial_resp.headers.get("csrf-token")

login_resp = session.post(
    f"{DISCUIT_BASE}/api/_login",
    headers={"X-Csrf-Token": csrf},
    json={"username": USERNAME, "password": PASSWORD},
)

if login_resp.status_code != 200:
    print("Login failed:", login_resp.text)
    exit(1)

# -----------------------
# STEP 3: CHECK DUPLICATES
# -----------------------
posts_resp = session.get(f"{DISCUIT_BASE}/api/_community/{COMMUNITY}/posts")
posts = posts_resp.json().get("data", [])

already_posted = any(title in p.get("title", "") for p in posts)

# -----------------------
# STEP 4: POST OR DRY-RUN
# -----------------------
if already_posted:
    print(f"A post with title '{title}' already exists. Skipping.")
else:
    if LIVE_POST:
        post_resp = session.post(
            f"{DISCUIT_BASE}/api/posts",
            headers={"X-Csrf-Token": csrf},
            json={
                "type": "text",
                "title": title,
                "body": body,
                "community": COMMUNITY,
            },
        )
        print("✅ Post sent. Response:", post_resp.json())
    else:
        print("💡 Dry run enabled. Post not sent.")
        print("Post title:", title)
        print("Post body preview:\n", body)
