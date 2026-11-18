# DJ description and presentation correction

- [x] Replace unconditional null description with scoped source-body extraction. Preserve paragraphs; do not invent missing bodies or use short meta teasers.
- [x] Remove visible source links/sections from DJ pages; retain JSON provenance and rights notice.
- [x] Add offline nested-body, inline-markup, duplicate-body, absent-body, JSON-LD and persistence regression tests.
- [x] Preserve earlier description/provenance on missing extraction and fail acceptance rather than silently erase it; exclude outer chrome and reject ambiguous body candidates.
- [ ] Verify actual source HTML through permitted collection; report description coverage separately from profile-fetch coverage.
- [ ] Rerun existing manual GitHub workflow and verify committed data and production. Do not bypass access controls.

## Detail layout
- [x] Move concise facts ahead of the full description, shown once inside Profile details. Preserve JSON and hidden provenance.
- [x] Isolate no-body collection fixtures from newly populated production descriptions.

- [x] Label top rank Current Ranking, remove duplicate lower ranking; keep Ranking change separate. Show populated birth date/gender only in secondary details, omitting empty values without changing data.
