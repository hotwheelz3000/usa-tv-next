import urllib.request
import json
import base64
import uuid
import re
import os
import time

TOKEN = os.environ["GITHUB_TOKEN"]
OWNER = "hotwheelz3000"
REPO = "usa-tv-next"

HEADERS = {
    "Authorization": "token " + TOKEN,
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "catalog-update-action"
}

PINNED = ["abc", "cbs", "cw", "fox", "nbc", "pbs"]
EXCLUDE_GROUPS = ["movie", "movies", "film", "films", "cinema", "vod", "radio", "podcast", "audio", "xxx", "adult", "18+"]

PLAYLISTS = [
    ("Pluto TV", "PT", "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/refs/heads/main/playlists/plutotv_us.m3u"),
    ("Tubi", "TB", "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/refs/heads/main/playlists/tubi_all.m3u"),
]

def api_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())

def get_sha(path):
    try:
        return api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/" + path).get("sha")
    except:
        return None

def fetch_m3u(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="ignore")

def parse_m3u(content):
    channels = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            name = ""
            group = ""
            logo = ""
            nm = re.search(r",(.+)$", line)
            if nm:
                name = nm.group(1).strip()
            gm = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
            if gm:
                group = gm.group(1).strip()
            lm = re.search(r'tvg-logo="([^"]*)"', line, re.IGNORECASE)
            if lm:
                logo = lm.group(1).strip()
            i += 1
            while i < len(lines) and (lines[i].strip() == "" or lines[i].strip().startswith("#")):
                i += 1
            if i < len(lines):
                su = lines[i].strip()
                if su and not su.startswith("#"):
                    channels.append({"name": name, "url": su, "group": group, "logo": logo})
        i += 1
    return channels

def is_live_tv(ch):
    return not any(ex in ch.get("group", "").lower() for ex in EXCLUDE_GROUPS)


def is_bad_name(name):
    bad_keywords = ["tvg-logo=", "group-title=", "tvg-id=", "#EXTINF"]
    return any(kw in name for kw in bad_keywords)

def map_genre(group):
    g = group.lower()
    if any(x in g for x in ["sport", "espn", "nfl", "nba"]):
        return "Sports"
    if any(x in g for x in ["news", "weather"]):
        return "News"
    if any(x in g for x in ["kids", "child", "family", "cartoon"]):
        return "Kids"
    if any(x in g for x in ["music"]):
        return "Music"
    if any(x in g for x in ["doc", "nature", "history"]):
        return "Documentaries"
    if any(x in g for x in ["lifestyle", "food", "travel"]):
        return "Lifestyle"
    if any(x in g for x in ["latino", "spanish"]):
        return "Latino"
    return "Entertainment"

cat_url = "https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/catalog/tv/all.json"
cat_file = api_get(cat_url)
cat_sha = cat_file["sha"]
cat_content = json.loads(base64.b64decode(cat_file["content"]).decode())
all_metas = cat_content.get("metas", [])

existing_names = set()
meta_files = api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/meta/tv")
for f in meta_files:
    if f["name"].endswith(".json"):
        try:
            d = api_get(f["url"])
            c = json.loads(base64.b64decode(d["content"]).decode())
            n = c.get("meta", {}).get("name", "")
            if n:
                existing_names.add(n.lower().strip())
        except:
            pass

stream_files = api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/stream/tv")
pluto_ids = set()
tubi_ids = set()
for f in stream_files:
    cid = f["name"].replace(".json", "")
    try:
        d = api_get(f["url"])
        c = json.loads(base64.b64decode(d["content"]).decode())
        streams = c.get("streams", [])
        if streams:
            name = streams[0].get("name", "")
            desc = streams[0].get("description", "")
            if name == "Pluto TV" or desc == "PT":
                pluto_ids.add(cid)
            elif name == "Tubi" or desc == "TB":
                tubi_ids.add(cid)
    except:
        pass

original = [m for m in all_metas if m["id"] not in pluto_ids and m["id"] not in tubi_ids]
pluto_metas = [m for m in all_metas if m["id"] in pluto_ids]
tubi_metas = [m for m in all_metas if m["id"] in tubi_ids]

total_added = 0
seen_names = set(existing_names)

for source_name, desc_code, playlist_url in PLAYLISTS:
    print("Processing " + source_name + " ...")
    try:
        content = fetch_m3u(playlist_url)
        channels = parse_m3u(content)
    except Exception as e:
        print("Error: " + str(e))
        continue

    new_channels = [ch for ch in channels if ch["name"] and ch["url"] and ch["name"].lower().strip() not in seen_names and is_live_tv(ch) and not is_bad_name(ch["name"])]
    for ch in new_channels:
        seen_names.add(ch["name"].lower().strip())
    print("New: " + str(len(new_channels)))

    for ch in new_channels:
        cid = "ustv-" + str(uuid.uuid4())
        name = ch["name"]
        logo = ch.get("logo", "")
        genre = map_genre(ch.get("group", ""))
        stream_data = {"streams": [{"url": ch["url"], "behaviorHints": {"notWebReady": True}, "name": source_name, "description": desc_code}]}
        meta_data = {"meta": {"id": cid, "type": "tv", "name": name, "genres": [genre], "poster": logo, "background": logo, "logo": logo, "description": name + " - " + genre}}
        catalog_entry = {"id": cid, "type": "tv", "name": name, "genres": [genre], "poster": logo}

        for path, data in [("stream/tv/" + cid + ".json", stream_data), ("meta/tv/" + cid + ".json", meta_data)]:
            sha = get_sha(path)
            enc = base64.b64encode(json.dumps(data, indent=2).encode()).decode()
            d = {"message": "add: " + name, "content": enc}
            if sha:
                d["sha"] = sha
            body = json.dumps(d).encode()
            req = urllib.request.Request("https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/" + path, data=body, headers=HEADERS, method="PUT")
            req.add_header("Content-Type", "application/json")
            urllib.request.urlopen(req)
            time.sleep(0.3)

        if source_name == "Pluto TV":
            pluto_metas.append(catalog_entry)
        else:
            tubi_metas.append(catalog_entry)
        total_added += 1

pluto_sorted = sorted(pluto_metas, key=lambda m: m.get("name", "").lower())
tubi_sorted = sorted(tubi_metas, key=lambda m: m.get("name", "").lower())
pinned = sorted([m for m in original if m.get("name", "").lower().strip() in PINNED], key=lambda m: PINNED.index(m.get("name", "").lower().strip()) if m.get("name", "").lower().strip() in PINNED else 99)
rest = sorted([m for m in original if m.get("name", "").lower().strip() not in PINNED], key=lambda m: m.get("name", "").lower())
new_metas = pinned + rest + pluto_sorted + tubi_sorted

enc = base64.b64encode(json.dumps({"metas": new_metas}, indent=2).encode()).decode()
data = {"message": "weekly update: +" + str(total_added) + " channels", "content": enc, "sha": cat_sha}
body = json.dumps(data).encode()
req = urllib.request.Request(cat_url, data=body, headers=HEADERS, method="PUT")
req.add_header("Content-Type", "application/json")
urllib.request.urlopen(req)

print("Added: " + str(total_added))
print("Total: " + str(len(new_metas)))
