# USA TV Next

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
