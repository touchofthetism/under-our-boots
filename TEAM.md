# TEAM.md — how Claude and Muse work this project as a tag team

Two AIs, one human approver, one dataset. This file is the shared contract.
If you are Claude or Muse picking this project up cold, read this first.

## The lanes

**Claude — researcher / builder of the record.**
- Researches installations and writes the story cards in the Google Drive
  research folder (the single source of truth for cards; "start here" there
  indexes the current version of every file).
- Every claim carries an evidence level: Confirmed / Probable / Unverified /
  Refuted. Never upgrade a claim without a source. Primary sources beat
  secondary; note where the record is thin.
- Every new name gets a "Say it right" respelling in the card, a row in the
  data tables' Pronunciations tab, and a lexeme in
  `elevenlabs_pronunciations.pls`.
- Every source URL cited gets a Wayback Machine snapshot the same day
  (check `data/source_snapshots.csv` here; run `tools/archive_sources.py`
  logic — if a URL has no snapshot, submit it at web.archive.org/save).
- Cross-checks archaeological claims against tDAR first and Open Context
  second before filing a card as Confirmed.
- Files dataset changes as a change note to Shefton (Claude holds no account
  credentials — Shefton is the bridge). Never edits the production log.

**Muse — verifier / producer.**
- Verifies everything Claude files against primary sources; grades
  sub-claims plainly (supported / conflated / unsupported / contradicted).
- Applies verified dataset changes to this repository (CSV + regenerated
  site via `tools/build_site.py`), attributed to the research release.
- Files every research error found as a GitHub Issue here — installation,
  card, problem (wrong fact, dead link, licence mismatch, missing
  pronunciation) — for Claude to fix in the Drive record. The fix lands in
  Drive, gets noted in "start here"'s change log, and the Issue closes when
  Muse re-verifies it.
- Builds the episodes (real photos and footage only; ElevenLabs narration
  with the pronunciation dictionary attached; the full quality gate before
  Shefton sees a draft) and updates `EPISODES.md` and the Drive production
  log after each episode.
- Pulls public-domain footage with yt-dlp (DVIDS / NARA / Internet Archive
  only), logging source URL, licence and credit for every asset; runs
  PySceneDetect cut-density QA on every finished episode.

**Shefton — approver.** Nothing is published, posted, sent or spent without
his explicit approval each time. He relays between Claude and the accounts
only he holds.

## The loop, end to end

1. Claude researches → card filed in Drive → "start here" updated.
2. Muse verifies the card → errors become Issues here → Claude fixes in
   Drive → Muse re-verifies → Issues close.
3. Muse scripts from the card only, builds, gates, delivers for review.
4. Shefton approves → episode publishes → Muse updates `EPISODES.md`, the
   production log, and the entry page's episode badge.
5. New sources found at any step get Wayback snapshots the same day.

## What never goes in this repository

- Archaeological site or burial locations, or coordinates finer than the
  installation's public location.
- THPO / cultural-office correspondence (drafted and logged privately).
- Unpublished scripts, unapproved cuts, credentials of any kind.
