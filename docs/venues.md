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

The annual venue workflow has its own cadence and `VENUE_COLLECTION_ENABLED` gate, independent of DJ collection. Initial cadence is annual, not monthly. The gate has not been enabled. It honors robots crawl-delay and request-rate limits with a minimum ten-second interval between logical fetches and before every allowed redirect hop. Robots-file and standalone fetch redirects use the ten-second minimum until an effective robots delay is supplied. Redirect targets must pass same-source HTTPS checks and, once robots rules are loaded, the same robots policy before any wait or follow. Initial robots-file retrieval has no loaded robots policy yet. The collector requires explicitly labelled profile facts, validates all discovered records and rejects duplicate venue IDs before writing. Discovery must retain the IDs, categories and exact profile/listing URLs already recorded from these source directories; a missing identity stops with evidence for review. Legitimate retirement or renaming needs a reviewed baseline update rather than an automatic deletion. A fetch, parse, coverage or validation failure stops the workflow before data commit or publication; existing source records are retained rather than pruned. Unknown or independently sourced records do not become this collector's source baseline.

In the prepared publication flow, a successful venue refresh commits venue data, builds both the DJ and venue catalogs, then uploads and deploys the combined site through GitHub Pages. The annual DJ refresh also builds both catalogs. Both annual workflows and manual Pages publication share the `catalog-publish` concurrency group with `cancel-in-progress: false` and `queue: max`, and check out fresh `develop` after acquiring that workflow slot. GitHub permits up to 100 pending runs with this queue setting; additional runs are canceled when full, and dispatch order is not a guaranteed execution order. See the [GitHub concurrency contract](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency). The manual Pages workflow remains available without collecting either source. These code paths are prepared, not activated or commissioned end to end; source publication and offline tests do not establish live collection or scheduled acceptance. Baseline coverage protection cannot prove that an upstream response contains every new venue that has never been observed.

Vegas Party Menu must join with explicitly reviewed venue labels plus hotel/type evidence. Dayclub, nightclub and after-hours identities must not be collapsed. Consumer integration and live acceptance are tracked separately; this source checkpoint alone is not completed integration.
