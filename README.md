# USA TV Next

190 live TV channels across 10 genres: Sports, Entertainment, News, Premium, Kids, Lifestyle, Documentaries, Local, Music, Latino.

Static Stremio addon hosted entirely on GitHub using raw URLs — no server required.

## Install

```
stremio://raw.githubusercontent.com/yowmamasita/usa-tv-next/main/manifest.json
```

[Install via Stremio Web](stremio://raw.githubusercontent.com/hotwheelz3000/usa-tv-next/main/manifest.json)

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
