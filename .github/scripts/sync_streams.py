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

BAD_URL_PATTERNS = ["service-stitcher.clusters.pluto.tv"]

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

def get_sha(path):
    try:
        return api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/" + path).get("sha")
    except:
        return None

def is_tubi(s):
    name = s.get("name", "")
    desc = s.get("description", "")
    url = s.get("url", "")
    return name == "Tubi" or desc == "TB" or "tubi" in url.lower()

def is_clean_stream(s):
    url = s.get("url", "")
    if not url:
        return False
    if "tvpass" in url.lower():
        return False
    if is_tubi(s):
        return False
    if any(p in url for p in BAD_URL_PATTERNS):
        return False
    return True

def channel_is_tubi(streams):
    # a channel is Tubi if ALL its streams are Tubi
    if not streams:
        return False
    return all(is_tubi(s) for s in streams)

print("Fetching your catalog ...")
cat_url = "https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/catalog/tv/all.json"
cat_file = api_get(cat_url)
cat_sha = cat_file["sha"]
your_metas = json.loads(base64.b64decode(cat_file["content"]).decode()).get("metas", [])
your_name_set = set(m.get("name", "").lower().strip() for m in your_metas)

print("Fetching your stream files ...")
your_stream_files = api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/stream/tv")
your_stream_map = {f["name"].replace(".json", ""): f for f in your_stream_files}

print("Fetching original catalog ...")
orig_cat = api_get("https://api.github.com/repos/" + ORIGINAL_OWNER + "/" + ORIGINAL_REPO + "/contents/catalog/tv/all.json")
orig_metas = json.loads(base64.b64decode(orig_cat["content"]).decode()).get("metas", [])

print("Fetching original stream files ...")
orig_stream_files = api_get("https://api.github.com/repos/" + ORIGINAL_OWNER + "/" + ORIGINAL_REPO + "/contents/stream/tv")
orig_stream_map = {f["name"].replace(".json", ""): f for f in orig_stream_files}

print("Fetching original meta files ...")
orig_meta_files = api_get("https://api.github.com/repos/" + ORIGINAL_OWNER + "/" + ORIGINAL_REPO + "/contents/meta/tv")
orig_meta_map = {f["name"].replace(".json", ""): f for f in orig_meta_files}

orig_name_to_id = {m.get("name", "").lower().strip(): m["id"] for m in orig_metas}

updated = 0
added = 0
skipped = 0
new_catalog_entries = []

for orig_m in orig_metas:
    name = orig_m.get("name", "").lower().strip()
    orig_id = orig_m["id"]

    if orig_id not in orig_stream_map:
        skipped += 1
        continue

    try:
        orig = api_get(orig_stream_map[orig_id]["url"])
        orig_content = json.loads(base64.b64decode(orig["content"]).decode())
        orig_streams = orig_content.get("streams", [])

        # skip if this is a Tubi channel
        if channel_is_tubi(orig_streams):
            skipped += 1
            continue

        new_clean = [s for s in orig_streams if is_clean_stream(s)]
        if not new_clean:
            skipped += 1
            continue

        if name in your_name_set:
            # existing channel - update streams
            your_id = orig_name_to_id.get(name)
            matching = [m for m in your_metas if m.get("name","").lower().strip() == name]
            if not matching:
                skipped += 1
                continue
            your_id = matching[0]["id"]
            if your_id in your_stream_map:
                your = api_get(your_stream_map[your_id]["url"])
                your_content = json.loads(base64.b64decode(your["content"]).decode())
                your_urls = set(s.get("url", "") for s in your_content.get("streams", []))
                add_streams = [s for s in new_clean if s.get("url", "") not in your_urls]
                if not add_streams:
                    skipped += 1
                    continue
                merged = your_content.get("streams", []) + add_streams
                sha = your_stream_map[your_id]["sha"]
            else:
                merged = new_clean
                sha = None
            encoded = base64.b64encode(json.dumps({"streams": merged}, indent=2).encode()).decode()
            url = "https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/stream/tv/" + your_id + ".json"
            data = {"message": "sync streams: " + orig_m["name"], "content": encoded}
            if sha:
                data["sha"] = sha
            body = json.dumps(data).encode()
            req = urllib.request.Request(url, data=body, headers=HEADERS, method="PUT")
            req.add_header("Content-Type", "application/json")
            urllib.request.urlopen(req)
            updated += 1
            time.sleep(0.3)
        else:
            # new non-Tubi channel - add it
            encoded = base64.b64encode(json.dumps({"streams": new_clean}, indent=2).encode()).decode()
            url = "https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/stream/tv/" + orig_id + ".json"
            data = {"message": "add new channel: " + orig_m["name"], "content": encoded}
            body = json.dumps(data).encode()
            req = urllib.request.Request(url, data=body, headers=HEADERS, method="PUT")
            req.add_header("Content-Type", "application/json")
            urllib.request.urlopen(req)

            # copy meta file
            if orig_id in orig_meta_map:
                meta = api_get(orig_meta_map[orig_id]["url"])
                meta_content = base64.b64decode(meta["content"]).decode()
                encoded_meta = base64.b64encode(meta_content.encode()).decode()
                meta_url = "https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/meta/tv/" + orig_id + ".json"
                data = {"message": "add meta: " + orig_m["name"], "content": encoded_meta}
                body = json.dumps(data).encode()
                req = urllib.request.Request(meta_url, data=body, headers=HEADERS, method="PUT")
                req.add_header("Content-Type", "application/json")
                urllib.request.urlopen(req)

            new_catalog_entries.append(orig_m)
            added += 1
            print("Added new channel: " + orig_m["name"])
            time.sleep(0.3)

    except Exception as e:
        print("Error on " + orig_m.get("name", orig_id) + ": " + str(e))

# update catalog with new channels
if new_catalog_entries:
    cat_file = api_get(cat_url)
    cat_sha = cat_file["sha"]
    your_metas = json.loads(base64.b64decode(cat_file["content"]).decode()).get("metas", [])
    your_metas.extend(new_catalog_entries)
    encoded = base64.b64encode(json.dumps({"metas": your_metas}, indent=2).encode()).decode()
    data = {"message": "add " + str(len(new_catalog_entries)) + " new channels to catalog", "content": encoded, "sha": cat_sha}
    body = json.dumps(data).encode()
    req = urllib.request.Request(cat_url, data=body, headers=HEADERS, method="PUT")
    req.add_header("Content-Type", "application/json")
    urllib.request.urlopen(req)

# regenerate m3u
print("Regenerating m3u ...")
cat_file = api_get(cat_url)
all_metas = json.loads(base64.b64decode(cat_file["content"]).decode()).get("metas", [])
your_stream_files2 = api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/stream/tv")
your_stream_map2 = {f["name"].replace(".json", ""): f for f in your_stream_files2}

lines = ["#EXTM3U"]
for m in all_metas:
    cid = m["id"]
    name = m.get("name", "")
    logo = m.get("poster", "")
    genres = m.get("genres", ["Entertainment"])
    group = genres[0] if genres else "Entertainment"
    if cid not in your_stream_map2:
        continue
    try:
        sf = api_get(your_stream_map2[cid]["url"])
        content = json.loads(base64.b64decode(sf["content"]).decode())
        streams = content.get("streams", [])
        if not streams:
            continue
        stream_url = streams[0].get("url", "")
        if not stream_url:
            continue
        lines.append("#EXTINF:-1 tvg-id=\"" + cid + "\" tvg-name=\"" + name + "\" tvg-logo=\"" + logo + "\" group-title=\"" + group + "\"," + name)
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
print("Streams synced: " + str(updated))
print("New channels added: " + str(added))
print("Skipped: " + str(skipped))
