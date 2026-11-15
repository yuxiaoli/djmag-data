# Vegas venue catalog

The venue extension collects the nightclub and pool-party directories at No Cover Nightclubs. The first verified collection on 2026-11-15 contains 22 detail records, 11 from each directory, with zero fetch failures. This is source-directory coverage, not a claim to cover every venue in Las Vegas.

Each `data/venues/<id>.json` preserves source identity, category, hotel, operating-day labels, music, size, address/hours where parsed, concise factual description, source-provided image/video/tour links, section references and retrieval provenance. Editorial prose and reviews are not republished. Directory observations remain separate from profile facts because the publisher sometimes disagrees with itself. Unverified facts stay absent; missing map URLs are not fabricated.

Commands:

```
python scripts/sync_venues.py
python scripts/build_site.py
python scripts/build_venues.py
python -m unittest discover -s tests -v
```

The static venue index is `venues/index.html`; records are published at `data/venues/<id>.json` and their detail pages at `venues/<id>.html`. `data/venues/index.json` is generated with `{venues: [{id,name,type,detail_url,json_url}]}`, URLs relative to the catalog root. Existing DJ index and records are unchanged.

The annual venue workflow has its own cadence and `VENUE_COLLECTION_ENABLED` gate, independent of DJ collection. Initial cadence is annual, not monthly. The gate has not been enabled. It validates all discovered records before writing and fails on a fetch/structure error instead of publishing partial refresh data. The workflow only updates data; publication is through the existing manual Pages workflow, not a second deployment pipeline. Annual automation is therefore prepared, not yet fully commissioned end to end.

Vegas Party Menu must join with explicitly reviewed venue labels plus hotel/type evidence. Dayclub, nightclub and after-hours identities must not be collapsed. Consumer integration and live acceptance are tracked separately; this source checkpoint alone is not completed integration.
