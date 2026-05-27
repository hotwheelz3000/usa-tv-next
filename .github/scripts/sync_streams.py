import urllib.request
import json
import base64
import os
import time

TOKEN = os.environ["GITHUB_TOKEN"]
OWNER = "hotwheelz3000"
REPO = "usa-tv-next"
ORIGINAL_OWNER = "yowmamasita"
ORIGINAL_REPO = "usa-tv-next"

HEADERS = {
    "Authorization": "token " + TOKEN,
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "sync-action"
}

BAD_DESC = ["HV:SERVICE-STIT", "HV:"]
BAD_URL = ["service-stitcher.clusters.pluto.tv"]

def api_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())

def is_bad_stream(s):
    desc = s.get("description", "")
    url = s.get("url", "")
    return any(p in desc for p in BAD_DESC) or any(p in url for p in BAD_URL)

def is_good_stream(s):
    return "[DEAD]" not in str(s.get("name", "")) and not is_bad_stream(s)

print("Fetching catalog ...")
cat_url = "https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/catalog/tv/all.json"
cat_file = api_get(cat_url)
cat_content = json.loads(base64.b64decode(cat_file["content"]).decode())
all_metas = cat_content.get("metas", [])
your_ids = set(m["id"] for m in all_metas)

orig_stream_files = api_get("https://api.github.com/repos/" + ORIGINAL_OWNER + "/" + ORIGINAL_REPO + "/contents/stream/tv")
orig_stream_map = {f["name"].replace(".json", ""): f for f in orig_stream_files}

your_stream_files = api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/stream/tv")
your_stream_map = {f["name"].replace(".json", ""): f for f in your_stream_files}

updated = 0
for channel_id in orig_stream_map:
    if channel_id not in your_ids:
        continue
    try:
        orig = api_get(orig_stream_map[channel_id]["url"])
        orig_content = json.loads(base64.b64decode(orig["content"]).decode())
        live = [s for s in orig_content.get("streams", []) if is_good_stream(s)]
        if not live:
            continue
        if channel_id in your_stream_map:
            your = api_get(your_stream_map[channel_id]["url"])
            your_content = json.loads(base64.b64decode(your["content"]).decode())
            your_urls = set(s.get("url", "") for s in your_content.get("streams", []))
            new = [s for s in live if s.get("url", "") not in your_urls]
            if not new:
                continue
            merged = your_content.get("streams", []) + new
            new_content = {"streams": merged}
            sha = your_stream_map[channel_id]["sha"]
        else:
            new_content = {"streams": live}
            sha = None
        encoded = base64.b64encode(json.dumps(new_content, indent=2).encode()).decode()
        url = "https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/stream/tv/" + channel_id + ".json"
        data = {"message": "sync streams: " + channel_id, "content": encoded}
        if sha:
            data["sha"] = sha
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body, headers=HEADERS, method="PUT")
        req.add_header("Content-Type", "application/json")
        urllib.request.urlopen(req)
        updated += 1
        time.sleep(0.3)
    except Exception as e:
        print("Error: " + str(e))

print("Streams synced: " + str(updated))
