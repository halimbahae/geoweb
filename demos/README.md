# GeoWeb demo archive

The bundled demos — photo and video — that `demos/seed.py` imports into your
archive so the console is instantly explorable.

> GeoWeb · Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

## Media

| Demo session | Media file | Kind | Subject (answer key) |
| --- | --- | --- | --- |
| `demo-image-1` | `demo-image-1.jpg` | Photo | Milan Cathedral — landmark, clean sun, GPS stripped |
| `demo-image-2` | `demo-image-2.jpg` | Photo | Colosseum, Rome — architecture + people (CC0) |
| `demo-image-3` | `demo-image-3.jpg` | Photo | Shibuya scramble crossing, Tokyo — dense signs & text (CC0) |
| `demo-image-4` | `demo-image-4.jpg` | Photo | Eiffel Tower, Paris (public domain) |
| `demo-image-5` | `demo-image-5.jpg` | Photo | Taj Mahal, Agra (CC BY-SA 4.0), EXIF stripped |
| `demo-video-1` | `demo-video-1.mp4` | Video | Real footage: Tokyo street at night, neon signs |
| `demo-video-2` | `demo-video-2.mp4` | Video | Real footage: Colosseum in daylight |

Session and media names are intentionally opaque (`demo-image-N` / `demo-video-N`)
so opening a demo doesn't spoil the answer — the *Subject* column above is the
answer key, kept here in the docs only.

The video demo sessions are cut from **real internet footage** so they exercise
GeoWeb's frame sampler — scene-change detection and dHash dedupe — on genuine
camera motion, not synthetic slideshows.

## Sources & licences

| File | Source | Licence | Author |
| --- | --- | --- | --- |
| `demo-image-1.jpg` | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Milano,_Duomo_with_Milan_Cathedral_and_Galleria_Vittorio_Emanuele_II,_2016.jpg) | CC BY-SA 4.0 | Carschten |
| `demo-image-2.jpg` | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Cross_Colosseum_Rome_Italy.jpg) | CC0 | Jebulon |
| `demo-image-3.jpg` | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Shibuya_crossing,_seen_from_Shibuya_Stream.jpg) | CC0 | Syced |
| `demo-image-4.jpg` | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Tour_Eiffel_Wikimedia_Commons.jpg) | Public domain | Benh LIEU SONG |
| `demo-image-5.jpg` | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Taj_Mahal,_Agra,_India_edit2.jpg) | CC BY-SA 4.0 | Yann |
| `demo-video-1.mp4` | [Pexels](https://www.pexels.com/video/busy-tokyo-street-scene-with-pedestrians-31051227/) | Pexels Licence (free, no attribution) | Hairul Faidz |
| `demo-video-2.mp4` | [Pexels](https://www.pexels.com/video/iconic-colosseum-in-rome-during-daylight-36559603/) | Pexels Licence (free, no attribution) | Pexels |

Retrieved via the Wikimedia Commons API and Pexels, resized/transcoded for
packaging (photos ≤1100px, videos 640×360 / 12fps, ~9s). Any embedded GPS/EXIF
was stripped so the archive stays a fair mystery.

## Seeding

```bash
make demos                     # uv run demos/seed.py  → ~/geoweb-photos, FULL recon
uv run demos/seed.py --root /mnt/photos --recon quick   # fast pass, no ML models
uv run demos/seed.py --force                            # erase + re-seed
```

The seeder copies each file into a named session folder, writes `session.json`,
cuts frames for videos and runs the **full recon** (metadata, OCR, reverse
search, text→countries, detection, calibration, world prior) on each photo — or
on the last-scene frame of each video. Finished demos are skipped on re-runs.

The demo sessions stay `pending` until you open the console, look at the
evidence and finish them — that's the whole point of the exercise. The pre-built
screenshots in `landing/assets/img/` come from these sessions.