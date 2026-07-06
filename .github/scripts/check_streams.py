import urllib.request
import json
import base64
import os
import time

TOKEN = os.environ["GITHUB_TOKEN"]
OWNER = "hotwheelz3000"
REPO = "usa-tv-next"
TIMEOUT = 10

HEADERS = {
    "Authorization": "token " + TOKEN,
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "stream-checker"
}

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

def test_stream(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            r.read(2048)
        return True
    except:
        return False

print("Fetching catalog ...")
cat_file = api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/catalog/tv/all.json")
metas = json.loads(base64.b64decode(cat_file["content"]).decode()).get("metas", [])

print("Fetching stream files ...")
stream_files = api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/stream/tv")
stream_map = {f["name"].replace(".json", ""): f for f in stream_files}

dead_report = []
checked = 0

for m in metas:
    cid = m["id"]
    if cid not in stream_map:
        continue
    try:
        sf = api_get(stream_map[cid]["url"])
        content = json.loads(base64.b64decode(sf["content"]).decode())
        streams = content.get("streams", [])
        if not streams:
            dead_report.append(m["name"] + ": NO STREAMS")
            continue
        all_dead = True
        dead_urls = []
        for s in streams:
            url = s.get("url", "")
            if url and test_stream(url):
                all_dead = False
            elif url:
                dead_urls.append(url[:60])
        checked += 1
        if all_dead:
            dead_report.append(m["name"] + ": ALL " + str(len(streams)) + " STREAMS DEAD")
        elif dead_urls:
            dead_report.append(m["name"] + ": " + str(len(dead_urls)) + "/" + str(len(streams)) + " streams dead")
    except Exception as e:
        pass
    time.sleep(0.2)

print("Checked: " + str(checked) + " channels")
print("Issues found: " + str(len(dead_report)))

if dead_report:
    # check if an open issue already exists
    issues = api_get("https://api.github.com/repos/" + OWNER + "/" + REPO + "/issues?state=open&labels=dead-streams")
    body_text = "Weekly stream check found issues:\n\n" + "\n".join("- " + r for r in dead_report)
    if issues:
        # update existing issue
        issue_num = issues[0]["number"]
        url = "https://api.github.com/repos/" + OWNER + "/" + REPO + "/issues/" + str(issue_num) + "/comments"
        api_post(url, {"body": body_text})
        print("Updated existing issue #" + str(issue_num))
    else:
        api_post("https://api.github.com/repos/" + OWNER + "/" + REPO + "/issues", {
            "title": "Dead streams detected (" + str(len(dead_report)) + " channels affected)",
            "body": body_text,
            "labels": ["dead-streams"]
        })
        print("Created new issue")
else:
    print("All streams healthy!")
