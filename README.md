import urllib.request
import json
import base64

GITHUB_TOKEN = input('Paste your GitHub token: ').strip()
OWNER = 'hotwheelz3000'
REPO = 'usa-tv-next'

HEADERS = {
    'Authorization': 'token ' + GITHUB_TOKEN,
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'update-readme'
}

README = '''# USA TV Next

295 live TV channels across 10 genres: Sports, Entertainment, News, Premium, Kids, Lifestyle, Documentaries, Local, Music, Latino.

Sources include major US networks and Tubi. Static Stremio addon hosted entirely on GitHub using raw URLs — no server required. Catalog auto-updates every Monday via GitHub Actions.

## Install

```
stremio://raw.githubusercontent.com/hotwheelz3000/usa-tv-next/main/manifest.json
```

Install via [Stremio Web](https://web.stremio.com/#/?addon=https://raw.githubusercontent.com/hotwheelz3000/usa-tv-next/main/manifest.json)

## Sources

| Source | Channels |
|---|---|
| Major US Networks | ABC, CBS, CW, Fox, NBC, PBS + more |
| Tubi | 124 channels |

## Genres

Local, News, Sports, Entertainment, Premium, Lifestyle, Kids, Documentaries, Music, Latino

## Routes

| Stremio Resource | URL Path |
|---|---|
| Manifest | `/manifest.json` |
| Catalog | `/catalog/tv/all.json` |
| Catalog (genre) | `/catalog/tv/all/genre={Genre}.json` |
| Meta | `/meta/tv/{id}.json` |
| Stream | `/stream/tv/{id}.json` |

## Structure

```
manifest.json
catalog/tv/all.json
catalog/tv/all/genre={Genre}.json
meta/tv/ustv-{uuid}.json
stream/tv/ustv-{uuid}.json
public/logo.png
public/background.jpg
public/logos/usa/{channel}.png
public/posters/usa/{channel}.png
```
'''

def api_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())

print('Updating README ...', flush=True)
readme_url = 'https://api.github.com/repos/' + OWNER + '/' + REPO + '/contents/README.md'
readme_file = api_get(readme_url)
readme_sha = readme_file['sha']

encoded = base64.b64encode(README.encode('utf-8')).decode()
data = {'message': 'update README: 295 channels, Tubi only', 'content': encoded, 'sha': readme_sha}
body = json.dumps(data).encode()
req = urllib.request.Request(readme_url, data=body, headers=HEADERS, method='PUT')
req.add_header('Content-Type', 'application/json')
urllib.request.urlopen(req)

print('Done!', flush=True)
