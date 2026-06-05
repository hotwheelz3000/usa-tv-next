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

def api_post(url, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=HEADERS, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())

def api_put(url, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=HEADERS, method="PUT")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())

def get_sha(path):
    try:
        return api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/" + path).get("sha")
    except:
        return None

def is_bad_stream(s):
    desc = s.get("description", "")
    url = s.get("url", "")
    return any(p in desc for p in BAD_DESC) or any(p in url for p in BAD_URL)

def is_good_stream(s):
    return "[DEAD]" not in str(s.get("name", "")) and not is_bad_stream(s)

# step 1: sync streams
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

# step 2: regenerate m3u
print("Regenerating m3u ...")
cat_file = api_get(cat_url)
cat_content = json.loads(base64.b64decode(cat_file["content"]).decode())
all_metas = cat_content.get("metas", [])

your_stream_files = api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/stream/tv")
your_stream_map = {f["name"].replace(".json", ""): f for f in your_stream_files}

lines = ["#EXTM3U"]
for m in all_metas:
    cid = m["id"]
    name = m.get("name", "")
    logo = m.get("poster", "")
    genres = m.get("genres", ["Entertainment"])
    group = genres[0] if genres else "Entertainment"
    if cid not in your_stream_map:
        continue
    try:
        stream_file = api_get(your_stream_map[cid]["url"])
        content = json.loads(base64.b64decode(stream_file["content"]).decode())
        streams = content.get("streams", [])
        if not streams:
            continue
        if streams[0].get("name") == "Tubi" or streams[0].get("description") == "TB":
            continue
        stream_url = streams[0].get("url", "")
        if not stream_url:
            continue
        extinf = "#EXTINF:-1 tvg-id=\"" + cid + "\" tvg-name=\"" + name + "\" tvg-logo=\"" + logo + "\" group-title=\"" + group + "\"," + name
        lines.append(extinf)
        lines.append(stream_url)
    except:
        pass

m3u_content = "\n".join(lines)
sha = get_sha("usa-tv-next.m3u")
encoded = base64.b64encode(m3u_content.encode("utf-8")).decode()
data = {"message": "update m3u playlist", "content": encoded}
if sha:
    data["sha"] = sha
body = json.dumps(data).encode()
req = urllib.request.Request("https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/usa-tv-next.m3u", data=body, headers=HEADERS, method="PUT")
req.add_header("Content-Type", "application/json")
urllib.request.urlopen(req)
print("M3U updated!")
