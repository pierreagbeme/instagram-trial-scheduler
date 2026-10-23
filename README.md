# One-time manual Trial Reel publisher

Runs on standard GitHub-hosted Ubuntu runners (free for public repositories). Videos and captions are encrypted in batch.enc; decryption key and Meta token are Actions secrets. No personal computer is needed.

Approved batch: October 24, 2026 at 08:00 UTC / 10:00 Europe/Berlin. Only MANUAL Trial Reels. No regular-Reel fallback. Publishing is time-guarded; failed or uncertain writes are not automatically repeated. Public state contains only container IDs, status, and published permalinks.

Prepare uploads in advance and verifies Meta ingestion. Publish starts with scheduling headroom and waits until the target. GitHub schedules can be delayed; exact timing is not guaranteed. Dates outside the authorized window are refused. No paid services or self-hosted runners.
