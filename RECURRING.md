# Daily production and publication

Authorized 2026-10-27: daily 10:00 and 18:00 Europe/Berlin, each batch exactly three newly produced and quality-reviewed MANUAL Trial Reels. No regular fallback, no automatic graduation. Ambiguity tolerance remains deferred. Never recycle published media just to fill a slot.

Production is performed by the Codex thread heartbeat at06:00/14:00 local time; Codex and this Mac must be available for production. Keep the next two publication slots stocked when possible. Prepared batches publish on a GitHub-hosted runner without the Mac. GitHub scheduling can be delayed; target windows are10:00–10:20 and18:00–18:20. Jobs begin09:17/17:17 and never publish before target. A missed/empty/failed slot is reported as workflow failure. No emergency replacement, no blind retries.

## Producer procedure
1. Read production-queue.json, publishing-journal.json, current Insights reports and QUALITY-REFERENCE.md in ../instagram-batch. Fetch remote recurring-queue.json and recurring-state.json via gh API; remote is authoritative. Check queued and already published sources. Read latest account Insights when helpful; do not infer a winner from early samples.
2. Select an unproduced topic, excluding Ambiguitätstoleranz and duplicate original uploads. Produce three meaningfully different voice edits, structures and two custom explanatory animations each. Preserve the original natural hook, face and voice, tighten after the hook. Prefer22–30s if natural; up to35% of runtime with animated additions. No permanent white box, no name footer. HyperFrames UI only internal browser. Quiet synchronized SFX, no duplicate subtitles.
3. Render and inspect actual exports, animation states, every edit seam, beginning/end and caption safety. Verify decode, audio gain and language continuity. Record real review limits. Rework failures; don't publish poor substitutes. Compress transfer copies while preserving original masters and verify transfer copies again.
4. For each final file create publication-review.json with passed:true, publication_allowed:true and exact file sha256 only AFTER successful review. Save REVIEW.md. User authorizes autonomous production and publication; no further approval needed for conforming batches.
5. Write a local batch manifest: id (lowercase letters/digits/hyphens), account:pierreagbeme, publish_at (ISO with correct timezone offset,10:00/18:00), variants:[{id,file (absolute MP4 path),review_file (absolute review JSON path),caption}]. Three distinct reviewed files.
6. Run python3 enqueue.py /absolute/path/batch-manifest.json from this directory. Existing slot/batch is a stop-and-inspect condition. On uncertain GitHub writes inspect remote queue and release; never blindly recreate or re-publish. Queue at least60min before slot; if late use next unfilled slot and report the missed one. Do not publish directly from production.
7. Inspect prior cloud runs and remote recurring-state. Synchronize confirmed publications and links to local production state. Notify this chat only on published batches, meaningful errors, insufficient production capacity or needed user action. Stay quiet for unchanged status.

## Cloud safety
recurring.py validates account, manual trial policy, batch size, unique assets, reviewed file hashes and time window. It journals create/publish attempts BEFORE Meta mutations. Unknown outcomes require remote reconciliation, not retries. All three containers must be ready before starting a new batch. Partial publication failures retain successful IDs and never duplicate them. No paid services.

## Current initial state
Schedule configured with an empty queue; previously published batches are intentionally excluded. First production run is28.10.2026 06:00 Berlin, targeting28.10.2026 10:00 and optionally18:00. No new batch is promised until production/review finishes. New uploads are never created merely by running validate.

## Recovery 2026-10-28
The morning schedule event never produced a run by10:46 Berlin, despite successful manual validation. Validation proves account/queue policy, not scheduled delivery. Schedule now has repeated triggers09:07–09:57 and10:07/10:17, with equivalent evening triggers, all Europe/Berlin. Concurrency and per-video journal prevent duplicates. GitHub scheduling remains best effort. Explicit workflow_dispatch catch-up requires an exact batch ID and only accepts a past slot on the same Berlin date, with a fresh20-minute deadline; use only after user authorizes late publication. User authorized the28Oct10:00 Selbstwirksamkeit batch to be caught up now.
