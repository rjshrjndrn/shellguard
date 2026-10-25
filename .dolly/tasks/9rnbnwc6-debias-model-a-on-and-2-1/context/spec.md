<!-- dolly spec · task 9rnbnwc6 -->
# Spec — debias model A on ~/ and 2>&1

**current: v1** · updated 2026-10-25T17:03:32Z by @rjshrjndrn

<!-- dolly:spec-current -->
<!-- v1 · 2026-10-25T17:03:32Z · @rjshrjndrn -->

Model A learned ~/ (76% dangerous) and 2>&1 (95%, n=21) as danger tokens: ls -d ~/x ~/y 2>&1 scores 0.64. Add hand-written paired safe/dangerous rows (data/extra.csv) merged by prepare() into train+test; add measurement cases to hard.csv (exam). Ship only if dangerous recall does not drop on test/golden/hard and hard safe false alarms fall.
<!-- /dolly:spec-current -->

---

## Superseded versions

<!-- dolly:spec-history -->
_none — v1 is the first spec_
<!-- /dolly:spec-history -->
