# Telling staff from customers: methods and sources

Many stores have no staff-only area, so our staff zones can't be the only answer. This lists how
others do it. Research notes from 2026-10-16; nothing here is built yet beyond staff zones.

| Method | How it works | Catch | Used by / source |
|---|---|---|---|
| **Wearable tag** | Staff carry a Bluetooth tag, or wear a reflective lanyard; the counter ignores anyone with one | Staff must wear it every day | Ipsos ([retail-systems](https://www.retail-systems.com/rs/Ipsos_Retail_Footfall_Accuracy_Tracker_Tool_Release.php)) |
| **Visual badge or patch** | A patterned chest badge or fabric patch the camera recognises | Visible; must not be covered | FootfallCam ([method comparison](https://www.footfallcam.com/blog/?p=3347)) |
| **Uniform recognition** | Staff clothing looks different from customers' | Needs a distinctive uniform | FootfallCam (same), XXII ([blog](https://xxiiai.com/en/le-blog/comment-exclure-le-personnel-du-comptage-en-magasin)), Xovis licence option ([Vemco guide](https://intercom.help/vemco/en/articles/15444658-xovis-adults-children-groups-staff-counting-setup)) |
| **Unsupervised look clustering** | Group people by appearance with no labels; staff form their own cluster | Open-source analogue from sports, untested in stores | Roboflow team clustering, SigLIP + UMAP + KMeans ([blog](https://blog.roboflow.com/identify-basketball-players/)) |
| **Uniform + position, learned** | Combine clothing colour with where people stand (e.g. near the till) | Patent, expired; no accuracy published | IBM, US8694443 ([Google Patents](https://patents.google.com/patent/US8694443B2/en)) |
| **Repeat appearances (re-ID)** | The same person (clothes, build, walk; not face) seen many times a day is staff | Needs a person-matching model; vendor claims only | FootfallCam ([methodology](https://www.footfallcam.com/blog/2025/07/staff-exclusion-methodology/)), isarsoft ([Re-ID](https://www.isarsoft.com/article/what-is-re-id)) |
| **Movement pattern** | Path heatmap per person, image classifier: staff stay behind counters | Long tracks only; needs labelled staff from that store | Sunmi paper, 93% ([arXiv 2005.08009](https://arxiv.org/abs/2005.08009)) |
| **Staff zone** (ours today) | Time inside a drawn staff-only area tags the track | Store needs such an area | `src/main.py` staff tagging |
| **Long dwell time** | Anyone present longer than X is staff | Rated lowest (3/5) by FootfallCam; catches waiting customers, misses staff whose ID breaks | FootfallCam (method comparison) |
| **Wall button / staff lane** | Staff press a button or use a separate door lane | Depends on staff discipline | FootfallCam (method comparison) |

**Cheap signals worth adding to any of these:** seen before opening or after closing time; appears
inside without crossing the entrance tripwire (came from the back); an owner taps today's staff in
a dashboard snapshot each morning.

**Privacy:** avoid faces (biometric data under India's DPDP Act needs consent). Appearance features
kept only for the day are the safer design.

**Test footage:** `data/sample_videos/restaurant_ch17/` (from the team shared drive, not in git) has staff behind a bar counter, useful for
trying any of these.
