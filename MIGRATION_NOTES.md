# Paradox Vault — GitHub Actions migration notes (DRAFT, preparation only)

> Do NOT push anything in this folder to GitHub, do NOT pause or change
> any Muse cron job, and do NOT run either draft script against the live
> sheet until the cutover checklist is approved by the user.
> Tomorrow's one-off job `pv-yt-restage-12` (Tue 2026-10-27 13:15 IST)
> is untouched by this migration.

## Source of truth

- Current publisher: `~/workspace/pv_publisher/publish.py` (read 2026-10-26).
  It is the reference for every column, status value and title rule below.
- Old public scripts (fetched from
  `shakirrizwan01/instagram-auto-publisher` on main, 2026-10-26):
  `publish_paradox_vault_yt.py`, `publish_paradox_vault_ig.py`, and
  `.github/workflows/paradox_vault_yt.yml` /
  `paradox_vault_ig.yml`. In both workflow files the `schedule:` trigger
  is commented out ("PAUSED: Schedule paused by user request") and only
  `workflow_dispatch` (with an optional `target_row` input) is live.
  That is already the right shape for a fallback: dispatch-only, no
  daily schedule to double-post against the Muse jobs.

## Current sheet layout (what the drafts match)

| Col | Meaning |
| --- | --- |
| E | title |
| G | drive_file_id |
| H | caption_fb |
| I | caption_ig |
| J | caption_yt |
| K | tags_yt |
| M / N | fb status / fb id |
| O / P | ig status / ig id |
| Q / R | yt status / yt id |
| S | published timestamp (IST `YYYY-MM-DD HH:MM`) |
| T | notes / timestamped errors |
| U / V / W | yt / ig / fb dates |
| X / Y | ig / fb catchup dates |

Status values today: `scheduled` / `staged` / `published`.
Row map: post #0 → sheet row 21; #1–19 → n+1; #n≥20 → n+2.
Current Muse cadence: YT stage 12:45 IST + flip 22:30, IG reel 23:00,
FB video 23:30, noon image 12:00.

## Exact diffs: draft vs old public scripts

### Both scripts
1. **Sheet range:** old `Sheet1!A2:T35` → draft `Sheet1!A2:Y150`.
   The old range misses columns U–Y entirely (all current dates) and
   any row past 35. The current schedule runs to Jan 2027 (~90 rows).
2. **Status values:** old code looks for `"pending"` → draft requires
   `"scheduled"` (stage/publish) or `"staged"` (flip). With the old
   value, a dispatch today would find nothing due — or, worse, a
   future sheet edit reintroducing "pending" could publish the wrong row.
3. **Date columns:** old code reads post date from col B and treats
   "today or any unfulfilled past backlog" as due → draft reads the
   per-platform date column (YT: U, IG prime: V, IG catchup: X) and
   matches it exactly to the run date (or to `--date`). Backlog
   auto-selection is removed: a stale row must be dispatched explicitly
   with `--post-no` / `--sheet-row`, so a dispatch can never sweep up
   an old row by accident.
4. **Row selection:** old `--row` meant "Nth fetched row" (fragile:
   it shifts if the sheet gains a blank row) → draft `--post-no`
   uses the stable row map above, with `--sheet-row` as an explicit
   direct alternative. `--all-due` scans by post number + date + status.
5. **Sheet writes:** old `value_input_option: USER_ENTERED` on a
   two-cell range → draft writes each cell separately with `RAW`,
   matching the current publisher (no Sheets reformatting of IDs/dates).
   Stage writes R + Q only; flip writes Q + S; IG publish writes
   P + O + S (and clears X on a successful catch-up). Errors go to
   col T only and never overwrite a status.
6. **Accounts:** old scripts hardcode connected-account IDs as static
   fallbacks and a fixed user ID → draft has NO hardcoded account IDs
   and NO fixed user ID. Accounts are discovered at runtime (ACTIVE
   only); optional per-toolkit env overrides exist
   (`COMPOSIO_GOOGLEDRIVE_ACCOUNT_ID`, `COMPOSIO_GOOGLESHEETS_ACCOUNT_ID`,
   `COMPOSIO_YOUTUBE_ACCOUNT_ID`, `COMPOSIO_INSTAGRAM_ACCOUNT_ID`).
   If an account cannot be discovered, the script fails clearly.
   The API key is only ever `COMPOSIO_API_KEY` from the environment
   (GitHub secret). No key or account ID appears in any file here.
7. **Follow-up actions removed:** old scripts posted a first/pinned
   comment and sent a Gmail drop alert → draft does neither, ever.
   The standing rule is: never add a comment or follow-up action to a
   published post on the publisher's own initiative.
8. **Failure handling:** old scripts printed a failure and exited,
   but the YT script had already decided the upload "succeeded" from
   a loose ID lookup → draft validates the video/media ID explicitly,
   logs a truncated response on failure, writes col T, leaves the
   status unchanged (`scheduled`), and exits non-zero. This is the
   same validation fix applied to `publish.py` on 2026-10-26 after it
   marked two rows "staged" with an empty video ID.

### YouTube draft only
9. **Stage vs flip split:** old script uploaded straight to `public`
   → draft has `--action stage` (Unlisted) and `--action flip`
   (public), mirroring the current publisher and the 12:45 / 22:30
   cadence. Flip refuses to run unless col R holds an ID and col Q
   is `staged`.
10. **Title logic:** old script appended `" #Shorts"` to EVERY title
    → draft adds it only for shortform titles. Titles containing
    "documentary" or "longform" (case-insensitive) are uploaded
    verbatim. This is the critical fix for #12, "PV Longform -
    Zubeen x MJ: The Pattern": the old script would have published
    a long-form essay as a Short.
11. **Description:** old script appended
    `#ParadoxVault #Shorts #Facts #Documentary` to the sheet caption
    → draft sends col J verbatim, nothing appended. Metadata is
    verified before publish, never rewritten by the publisher.
12. **Tags:** old script split tags on commas AND newlines and
    stripped a leading `#` → draft splits on commas only and strips
    whitespace only, matching the current publisher. Tags are ALWAYS
    passed as a list: passing a single string is what produced the
    Composio 400 on 2026-10-26.
13. **URL printed:** Shorts URL for shortform, watch URL for
    long-form (the old script always printed a Shorts URL).

### Instagram draft only
14. **Caption:** old script sent col I as-is → draft sends col I
    verbatim with plain `#`, and FAILS FAST if the caption contains
    `%23`, because that renders literally on Instagram and IG
    captions cannot be edited via API afterwards.
15. **User ID:** old script hardcoded an Instagram user ID with a
    `get_user_info` fallback → draft always resolves it via
    `INSTAGRAM_GET_USER_INFO` ("me") and fails if it cannot be
    resolved. No hardcoded ID.
16. **Publish wait:** old `max_wait_seconds` 180 → draft 300,
    matching the current publisher.
17. **Catch-up:** draft adds `--catchup` (col X) and clears X on
    success, mirroring the current publisher. The old script had no
    catch-up concept and would re-publish a noon catch-up at prime time.

## What the old scripts would get wrong today (summary)

- Find nothing (status `"pending"` never matches) or pick the wrong
  row (col B date, A2:T35 range, positional `--row`).
- Publish a long-form video as a Short, public immediately, with
  extra hashtags appended to a verified description.
- Post a first/pinned comment and send an alert email on every publish.
- Write status with USER_ENTERED over a two-cell range, and — on a
  failed upload — leave no usable error in col T.
- Use stale hardcoded account IDs if Composio discovery changed
  (the exact failure mode seen with the defunct Facebook alias in
  the Muse publisher).

## Safe test plan (cannot double-post)

No step below publishes anything to a public feed except step 4,
which is a single explicitly-approved stage of a real due post,
and step 5, which is that same post's normal flip.

1. **Static checks (no API calls, no sheet writes).**
   `python3 -m py_compile` on both drafts. Grep both drafts for
   `COMPOSIO_API_KEY` — the only occurrence must be
   `os.environ.get("COMPOSIO_API_KEY")`. Grep for `POST_COMMENT`,
   `MEDIA_COMMENTS`, `GMAIL_SEND_EMAIL`, `first_comment` — zero hits.
   Confirm no hardcoded account ID pattern appears in either file.
2. **Dry run against a COPY of the sheet, never the master.**
   Set `PV_SHEET_ID` to a duplicated test sheet (same layout, one
   test row). Run both drafts with `--dry-run` and `--post-no`.
   Expected: prints title, description length, tags, and every
   intended sheet write; writes nothing; uploads nothing; exit 0.
   Run the YT draft with a long-form title and confirm the printed
   title has NO `#Shorts` suffix; run it with a short title and
   confirm the suffix IS present.
3. **Unlisted-only live test (no public feed, no master sheet).**
   Using the TEST sheet copy and a short test video file in Drive
   (not a scheduled post), dispatch the YT draft with
   `--action stage` only. Verify in YouTube Studio: the video exists
   as Unlisted, title/description/tags match the test row exactly.
   Then DELETE that Unlisted video in Studio by hand. Verify the
   test sheet row reads R=<id>, Q=`staged`, and that no flip was run.
   Repeat the same pattern for IG only if a throwaway Reel is
   acceptable — otherwise skip IG live testing and rely on steps
   1, 2 and 4, because an IG publish cannot be undone to Unlisted.
   (IG has no Unlisted state; a test IG publish IS a public post.)
4. **Single-post real run, gated before flip (YT only).**
   Pick the next due short, pause ONLY its Muse stage for that one
   post (do not pause any whole job), dispatch the GitHub YT stage
   via `workflow_dispatch` with that post number, verify the
   Unlisted video in Studio and the sheet row (R + `staged`), then
   let the normal Muse flip job publish it at 22:30. If the stage
   fails, the Muse stage job for that post is re-enabled and the
   GitHub run is debugged from its logs — nothing is re-uploaded.
5. **IG single-post real run, gated by read-back.**
   Dispatch the IG workflow for one due Reel only after steps 1–2
   pass and the user has approved the exact caption in the sheet.
   Immediately after dispatch, read the live Reel back in the
   Instagram app (full caption, hashtags, playback) before marking
   the test passed. If anything differs, stop all further GitHub
   dispatches and report — do not "fix" it with a comment or edit
   from the runner.
6. **Cutover gate.** Only after steps 1–5 pass AND the user has
   approved the diff in this folder does any Muse job get paused,
   one platform at a time (see CUTOVER_CHECKLIST.md). The GitHub
   schedules stay commented out throughout: fallback = manual
   `workflow_dispatch` only, until a separate user decision
   re-enables a schedule.

## Open questions (block pushing to GitHub)

1. **Composio secret validity:** is the `COMPOSIO_API_KEY` secret
   in `shakirrizwan01/instagram-auto-publisher` still valid, and
   does its Composio organisation still have ACTIVE Drive / Sheets /
   YouTube / Instagram accounts? The drafts fail clearly if not,
   but this cannot be checked without a dispatch — and a dispatch
   must not run against the master sheet until step 2 passes.
   (Note: the old YT script enforced a dedicated YouTube OAuth
   account for a private project quota. Whether that account is
   still ACTIVE, and whether it avoids the shared-quota 429 seen on
   2026-10-26, is unproven until a stage-only test dispatch.)
2. **Drive copy vs GitHub main:** the user said the `.yml` / `.py`
   files are also in Drive. The Drive reachable from Muse has no
   such files, so the Drive copy is in a different Drive account.
   Which copy is newer — Drive or GitHub main? Do not push until
   that is resolved, or the push could overwrite a newer Drive copy.
3. **Instagram test:** there is no safe Unlisted equivalent for
   IG. The user must explicitly accept that an IG test dispatch is
   a real public Reel, or accept skipping IG live testing (step 3).
4. **Images and Facebook video:** there is no GitHub workflow for
   the noon image posts or for Facebook video in this repo. Those
   stay on Muse jobs (see FB_NATIVE_SCHEDULING.md for Facebook).
   The migration as drafted covers YT + IG only.
5. **Workflow file changes:** the two `.yml` files need no change
   for dispatch-only fallback (schedule already commented out), but
   if a daily schedule is ever re-enabled, the cron times must be
   re-planned against the current Muse cadence (12:45 / 22:30 /
   23:00 / 23:30 IST) to avoid collisions — that is a separate
   decision, not part of this draft.
