# Gets todays cricket score world wide and formats them in Markdown then posts them
import requests
import datetime
from zoneinfo import ZoneInfo
import argparse
import re
from collections import defaultdict

# -----------------------
# CONFIGURATION
# -----------------------
RAPIDAPI_KEY = "ApiKeyRequired"
RAPIDAPI_URLS = [
    "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live",
    "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/recent"
]

DISCUIT_BASE = "https://discuit.org"
USERNAME = "username"
PASSWORD = "password"
COMMUNITY = "community"

# -----------------------
# ARGPARSE: --live flag
# -----------------------
parser = argparse.ArgumentParser(description="Post completed cricket matches to Discuit.")
parser.add_argument("--live", action="store_true", help="Actually post (default is dry-run)")
args = parser.parse_args()
LIVE_POST = args.live

# -----------------------
# HELPER: parse timezone like '+02:30' or '-05:45'
# -----------------------
def parse_timezone(tz_str):
    match = re.match(r'([+-])(\d{2}):(\d{2})', tz_str)
    if not match:
        return datetime.timezone.utc
    sign, hours, minutes = match.groups()
    delta = datetime.timedelta(hours=int(hours), minutes=int(minutes))
    if sign == "-":
        delta = -delta
    return datetime.timezone(delta)

# -----------------------
# STEP 1: FETCH MATCHES
# -----------------------
headers = {
    "x-rapidapi-host": "cricbuzz-cricket.p.rapidapi.com",
    "x-rapidapi-key": RAPIDAPI_KEY,
}

all_matches = []

for url in RAPIDAPI_URLS:
    response = requests.get(url, headers=headers)
    data = response.json()
    for type_match in data.get("typeMatches", []):
        for series_wrapper in type_match.get("seriesMatches", []):
            series = series_wrapper.get("seriesAdWrapper") or {}
            for match in series.get("matches", []):
                info = match.get("matchInfo", {})
                # Only completed or stumps
                if info.get("stateTitle") not in ["Complete", "Stumps"]:
                    continue
                all_matches.append(match)

# Remove duplicates by matchId
unique_matches = {}
for m in all_matches:
    mid = m.get("matchInfo", {}).get("matchId")
    if mid:
        unique_matches[mid] = m

matches_sorted = list(unique_matches.values())

# -----------------------
# STEP 2: FILTER BY TODAY (Europe/London)
# -----------------------
today_local = datetime.datetime.now(ZoneInfo("Europe/London")).date()
matches_today = []

for match in matches_sorted:
    info = match.get("matchInfo", {})
    start_ts = int(info.get("startDate"))
    tz = parse_timezone(info.get("venueInfo", {}).get("timezone", "+00:00"))
    match_local_dt = datetime.datetime.fromtimestamp(start_ts / 1000, tz=datetime.timezone.utc).astimezone(tz)
    match_date = match_local_dt.date()
    if match_date == today_local:
        matches_today.append(match)

# -----------------------
# STEP 3: GROUP BY matchFormat
# -----------------------
format_groups = defaultdict(list)
for match in matches_today:
    info = match.get("matchInfo", {})
    match_format = info.get("matchFormat", "Unknown")
    if match_format == "HUN":
        match_format = "Hundred"
    if match_format == "ODI":
        match_format = "50 Over"
    format_groups[match_format].append(match)

format_order = ["TEST", "50 Over", "T20", "Hundred", "Unknown"]
sorted_formats = sorted(format_groups.keys(), key=lambda f: format_order.index(f) if f in format_order else len(format_order))

# -----------------------
# STEP 4: BUILD POST BODY
# -----------------------
title = f"Worldwide Cricket Scores for {today_local.strftime('%d/%m/%Y')}"
lines = [f"# {title}\n"]

if not matches_today:
    lines.append("_No completed matches today._")
else:
    for fmt in sorted_formats:
        lines.append(f"## {fmt} Matches\n")
        for match in format_groups[fmt]:
            info = match.get("matchInfo", {})
            team1 = info.get("team1", {}).get("teamName", "Team1")
            team2 = info.get("team2", {}).get("teamName", "Team2")
            match_desc = info.get("matchDesc", "")
            result = info.get("status", "")
            ground = info.get("venueInfo", {}).get("ground", "Unknown Ground")

            lines.append(f"**{team1} vs {team2}, {match_desc} at {ground}: {result}**")
            lines.append("```")
            lines.append("Innings                               - Runs/Wickets    Overs")
            lines.append("--------------------------------------------------------------")
            score = match.get("matchScore", {})
            for team_key, team_name in [("team1Score", team1), ("team2Score", team2)]:
                team_score = score.get(team_key, {})
                for inn_key in sorted(team_score.keys(), key=lambda x: int(x[-1])):
                    inn = team_score.get(inn_key, {})
                    runs = inn.get("runs", 0)
                    wickets = inn.get("wickets", 0)
                    overs = inn.get("overs", 0)
                    lines.append(f"{(team_name + ' Inning ' + inn_key[-1]).ljust(35)}   - {runs}/{wickets}           {overs}")
            lines.append("```")

body = "\n".join(lines)

# -----------------------
# STEP 5: LOGIN TO DISCUIT
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
# STEP 6: CHECK DUPLICATES
# -----------------------
posts_resp = session.get(f"{DISCUIT_BASE}/api/_community/{COMMUNITY}/posts")
posts = posts_resp.json().get("data", [])
already_posted = any(title in p.get("title", "") for p in posts)

# -----------------------
# STEP 7: POST OR DRY-RUN
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
