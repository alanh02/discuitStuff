import urllib.request
import xml.etree.ElementTree as ET
import datetime
import requests
import argparse
from email.utils import parsedate_to_datetime

# -----------------------
# CONFIGURATION
# -----------------------
RSS_URL = "http://www.espncricinfo.com/rss/content/story/feeds/0.xml"

DISCUIT_BASE = "https://discuit.org"
USERNAME = "username"
PASSWORD = "password"
COMMUNITY = "Cricket"

# -----------------------
# ARGPARSE: --live flag
# -----------------------
parser = argparse.ArgumentParser(description="Post ESPNcricinfo news to Discuit.")
parser.add_argument("--live", action="store_true", help="Actually post (default is dry-run)")
args = parser.parse_args()
LIVE_POST = args.live

# -----------------------
# STEP 1: FETCH ESPNCRICINFO RSS
# -----------------------
with urllib.request.urlopen(RSS_URL) as response:
    data = response.read()

root = ET.fromstring(data)

today = datetime.datetime.utcnow().date()
title = f"ESPNcricinfo News Summary — {today}"

lines = []

for item in root.findall(".//item"):
    headline = item.find("title").text
    link = item.find("link").text
    pub_date_text = item.find("pubDate").text
    pub_date = parsedate_to_datetime(pub_date_text).date()

    if pub_date != today:
        continue

    lines.append(f"### [{headline}]({link})\n")
    lines.append("---\n")

if not lines:
    lines.append("_No new articles today._")

# Add credit/link to ESPNcricinfo
lines.append("\n*Thanks to [ESPNcricinfo](https://www.espncricinfo.com/cricket-news) for the news feed.*")

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
