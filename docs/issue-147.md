# Issue 147 — Profile metrics

GET `/api/v1/users/me/metrics?bundle=profile&period=all_time` requires the existing JWT authentication. Both query parameters have defaults; unsupported periods/bundles return 422.

Periods: `all_time`, `last_30_days`, `last_90_days`, `last_year`. Rolling windows include today and respectively 29, 89 or 364 preceding civil days in America/Sao_Paulo. Queries include the lower midnight boundary and exclude timestamps after the captured request clock. `last_year` means 365 civil days, not the previous calendar year.

Only the authenticated account's live Recordas participate. Artist and genre ties use ascending snapshot names. The artist image is the latest cover snapshot for that artist in the period (timestamp then Recorda ID). Genre percentages use all live Recordas in the period as denominator, including missing genres, and are rounded to two decimals. Empty history returns a null artist, empty genres and zero streak with null last date.

Streak uses full live history, independent of the period filter. A day with multiple posts counts once. Today may still be open: a sequence ending yesterday remains current. A completed missing day breaks a sequence, and subsequent posts start a new one. Deleted posts cannot preserve an active day. The calculator also returns historical maximum internally; the profile DTO only exposes current days and last active publication date.

The existing US35 profile-header streak intentionally remains unchanged: that contract includes deleted publications. This endpoint implements the separate live-publication rule requested in issue 147.

The Strategy registry exposes all six calculators. Only top artists, top genres and streak run for the profile bundle. Total Recordas is reusable directly. Engagement consumes explicit received-like and active-comment totals; tagged users consumes explicit tag relations supplied in MetricsContext. There is no persisted tag relation in the current schema, so no retrospective endpoint or notification-based approximation is introduced here. A future retrospective service must supply those inputs from its authoritative source; omitted auxiliary inputs default to empty/zero.

The engine registry declares the result contract for each strategy, including replacements. Queries project only the five fields used by calculators into immutable snapshots. Historical dates stream in batches for filtered periods; all_time reuses the snapshots already loaded instead of issuing a second history query. Cover selection compares timestamp and Recorda ID explicitly and does not depend on input ordering.

Validation: `tests/test_metrics_engine.py` covers local midnight, period bounds, deleted/foreign/future publications, empty states, strategy replacement, ranking, cover selection with shuffled inputs and tied timestamps, strict current/historical streak, authentication and parameter validation. Aggregation, period bounds and the deleted-day streak case run on both SQLite and a disposable PostgreSQL database. Static checking with mypy covers the metrics engine, calculators, schemas and repository. HTTP smoke validation uses a real local server with login and JWT authentication.
