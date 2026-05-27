import urllib.request
import json
import base64
import time
import os

TOKEN = os.environ["GITHUB_TOKEN"]
OWNER = "hotwheelz3000"
REPO = "usa-tv-next"
TIMEOUT = 5

HEADERS = {
    "Authorization": "token " + TOKEN,
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "sort-streams-action"
}

def api_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())

def test_stream_speed(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        start = time.time()
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            r.read(1024)
        return time.time() - start
    except:
        return 999

print("Fetching stream files ...")
ref_data = api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/git/ref/heads/main")
tree_sha = ref_data["object"]["sha"]
commit_data = api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/git/commits/" + tree_sha)
root_tree_sha = commit_data["tree"]["sha"]
tree_data = api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/git/trees/" + root_tree_sha + "?recursive=1")
all_files = tree_data.get("tree", [])
stream_files = [f for f in all_files if f["path"].startswith("stream/tv/") and f["path"].endswith(".json")]

multi_stream = []
for f in stream_files:
    blob = api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/git/blobs/" + f["sha"])
    content = json.loads(base64.b64decode(blob["content"]).decode())
    streams = content.get("streams", [])
    if len(streams) > 1:
        multi_stream.append((f, content, streams))

print("Channels with multiple streams: " + str(len(multi_stream)))

updated = 0
failed = 0

for i, (f, content, streams) in enumerate(multi_stream):
    channel_id = f["path"].replace("stream/tv/", "").replace(".json", "")
    timed = []
    for s in streams:
        url = s.get("url", "")
        speed = test_stream_speed(url) if url else 999
        timed.append((speed, s))

    timed.sort(key=lambda x: x[0])
    sorted_streams = [s for _, s in timed]

    if [s.get("url") for s in sorted_streams] == [s.get("url") for s in streams]:
        continue

    try:
        content["streams"] = sorted_streams
        current = api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/" + f["path"])
        current_sha = current["sha"]
        encoded = base64.b64encode(json.dumps(content, indent=2).encode()).decode()
        data = {"message": "sort streams by speed: " + channel_id, "content": encoded, "sha": current_sha}
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            "https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/" + f["path"],
            data=body, headers=HEADERS, method="PUT"
        )
        req.add_header("Content-Type", "application/json")
        urllib.request.urlopen(req)
        updated += 1
        time.sleep(0.2)
    except Exception as e:
        print("Error: " + str(e))
        failed += 1

print("Reordered: " + str(updated))
print("Failed: " + str(failed))
