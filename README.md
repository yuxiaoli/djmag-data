# DJ metadata catalog

Public source-attributed DJ metadata and static artist pages. One JSON per `data/djs/<id>.json`, described by `data/dj.schema.json`.

## Scope

Collect the latest DJ Mag ranking edition only. Historical year links are excluded, not followed. Include ranks beyond 100 only if the current edition actually provides them; do not manufacture additional artists to meet a numerical target. The observed 2026 page supplies 100 artists. Prior-year links alone are not a reason to expand collection.

Refresh annually, not weekly. Prepared Actions schedule: November 15 at 04:17 Asia/Hong_Kong. Collection remains gated by `SOURCE_COLLECTION_ENABLED` (not enabled) until the existing access denial is resolved. Publishing the workflow alone is not activation. Manual execution remains available for initial collection and repairs. The annual workflow collects current profiles with a 1,000-profile safety budget and 350-minute maximum; any incomplete coverage must be reported, not hidden.

## Data

Rank and edition year remain separate from fetch/publication dates. Preserve verified ranking history already collected, without proactively crawling historical editions. Origin is distinct from nationality/citizenship. Explicit profile labels, style, best-known-for, movement/place delta, article metadata and image source links are retained with provenance. Publisher social accounts are never mistaken for artist accounts. Missing birth date, gender or nationality stays unknown; no inference from names/images. Long editorial biography is linked rather than copied wholesale. Age should be calculated from verified birth date at display time.

## Commands

```
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/sync.py
python scripts/enrich_profiles.py --max-profiles 1000
python scripts/build_site.py
```

Requests honor robots and a minimum 10-second delay, fail on unexpected hosts/structure, and never bypass access controls. Profile writes checkpoint atomically; collection failure does not publish a partial workflow result.

## Current checkpoint

100 current-year ranking records and image source links; 24 profiles enriched with source labels and exact movement. The remaining 76 are not represented as complete. The original reviewed HTTP collector resumed successfully after the earlier policy denial, then checkpointed 24 profiles before the execution service returned a further djmag.com network-policy denial. Black Coffee was subsequently collected successfully. No alternate route or automatic retry is used. Annual collection remains disabled pending complete validated operation.

The catalog is live at https://yuxiaoli.github.io/djmag-data/ . Stable discovery index: `data/index.json`; each entry links its JSON record and detail page. Generated ranking summaries have been removed from the biography field. Full editorial biographies are linked at the source, not represented as collected text. Unknown birth date/gender render empty; From and DJ style appear once. Missing profile fields remain explicitly unknown. Movement text and source place value are retained without inferring previous ranks.

## Follow-on integration

Half Saints / Vegas Party Menu daily DJ listings should link stable `/djs/<id>.html` pages and show annual rank with its year, not a fabricated daily ranking. Join through stable IDs and explicitly reviewed aliases. Preserve original event descriptions, arrival times, schedules and fallback text. Ambiguous or unnamed performers remain unmatched; genre strings and event titles are not artists.

## Attribution

DJ Mag: https://djmag.com/top100djs . Independent project, not affiliated with DJ Mag. Source text and images retain their owners' rights. Images are linked, not copied into the repository. Wikidata CC0 structured facts may later enrich missing fields with provenance; image licensing is separate.

Pages workflow is manual-only and Pages uses GitHub Actions. Source publication alone does not trigger deployment or collection.
