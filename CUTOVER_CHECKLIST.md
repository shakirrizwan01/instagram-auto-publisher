# Paradox Vault — phased cutover checklist (DRAFT, preparation only)

> Nothing in this checklist has been done. Each phase needs its
> stated approval before the next phase starts. If any phase fails,
> stop at that phase and report — do not skip ahead to "pause the
> Muse jobs" to force progress.

## Phase 0 — Freeze (no changes, no approvals needed to start)

- [ ] All Muse publish jobs keep running exactly as they are.
- [ ] Tomorrow's one-off job `pv-yt-restage-12` (Tue 2026-10-27
      13:15 IST, stage + flip #12) is NOT touched, paused, edited
      or replaced by this migration. It runs first, on its own.
- [ ] GitHub schedules stay commented out. No `.yml` file is edited
      in this phase. Fallback, if needed, is manual
      `workflow_dispatch` only.
- [ ] No file in `~/workspace/pv_github_migration/` is pushed to
      GitHub in this phase. These are drafts for review.

## Phase 1 — Review the diff (needs: user approval of the diff)

- [ ] User reads `MIGRATION_NOTES.md` (exact diffs vs the old
      public scripts) and both draft scripts in this folder.
- [ ] User confirms the sheet layout, status values and row map
      in the notes match the live master sheet.
- [ ] Open questions in `MIGRATION_NOTES.md` § "Open questions"
      are answered or explicitly accepted as risks:
      1. Composio secret validity / ACTIVE accounts in the GitHub
         runner's organisation (unproven until a test dispatch).
      2. Drive copy vs GitHub main — which is newer?
      3. IG test = a real public Reel, or IG live testing skipped.
      4. Images + Facebook video are NOT covered by the GitHub
         drafts (see Phase 4).
      5. Any future daily schedule needs re-planned cron times.
- [ ] User approves the diff in writing. Without this, stop here.

## Phase 2 — Dry run + Unlisted-only test (needs: Phase 1 approval)

- [ ] Static checks pass (see MIGRATION_NOTES.md test plan step 1):
      `py_compile` clean; `COMPOSIO_API_KEY` only via env;
      zero hits for comment/email tools; no hardcoded account IDs.
- [ ] Dry run passes against a COPY of the sheet (`PV_SHEET_ID`
      = test sheet), YT long-form title prints WITHOUT `#Shorts`,
      YT short title prints WITH `#Shorts`, IG caption prints
      verbatim with plain `#`. No writes, no uploads.
- [ ] YT stage-only test passes: Unlisted video verified in
      Studio, test sheet row R + `staged`, video then DELETED in
      Studio by hand. No flip run.
- [ ] IG test decision recorded: either a throwaway Reel test
      was run and read back in the app, or IG live testing was
      explicitly skipped by the user (with the risk accepted).
- [ ] Any failure in this phase stops the migration. Debug from
      runner logs; do not retry a failed upload against the master
      sheet.

## Phase 3 — Single-post real runs, gated (needs: Phase 2 pass)

- [ ] YT: one due short only. Pause ONLY that post's Muse stage
      (not any whole job). Dispatch GitHub YT stage via
      `workflow_dispatch`, verify Unlisted + sheet row, then let
      the normal Muse flip job publish it at 22:30. If the stage
      fails, re-enable that post's Muse stage and stop.
- [ ] IG: one due Reel only, after the user approves its exact
      sheet caption. Dispatch, then read the live Reel back in
      the app (full caption, hashtags, playback) before calling
      the test passed. Any mismatch stops all further dispatches.
- [ ] Both real runs are reported to the user with video/media
      IDs and sheet rows before Phase 4 is considered.

## Phase 4 — Pause duplicate Muse jobs, one platform at a time (needs: Phase 3 pass + fresh user approval)

Pause ONLY the jobs listed here, ONLY after the matching platform
has passed Phase 3, and ONLY on a fresh user go-ahead for that
platform. Pausing a job is reversible; deleting one is not part
of this checklist.

| Platform | Muse jobs to pause (in this order) | Prerequisite |
| --- | --- | --- |
| YouTube | `pv-yt-stage`, then `pv-yt-flip` | Phase 3 YT run passed; GitHub YT stage + flip both proven |
| Instagram | `pv-ig-publish`, then `pv-ig-catchup` | Phase 3 IG run passed and read back |
| Facebook video | `pv-fb-publish`, then `pv-fb-catchup` | FB native scheduled queue verified for the next batch (see FB_NATIVE_SCHEDULING.md) — NOT the GitHub drafts, which do not cover Facebook |
| Noon images | `pv-image-publish` | NOT in this migration. Do not pause it unless/until a separate image workflow is built and tested. It stays on Muse. |

Explicitly NOT paused by this migration, ever, without a separate
decision:
- `pv-yt-restage-12` (one-off, 2026-10-27 13:15 IST) — runs first.
- `pv-comment-monitor` (daily 09:00 IST engagement sweep).
- `pv-weekly-digest` (Mondays 10:00 IST).
- Any Priced In job (`pi-*`). This migration is Paradox Vault only.
- Any other Muse job not listed in the table above.

After each platform's jobs are paused, the GitHub route for that
platform becomes the live route ONLY for new slots. In-flight
Muse slots (already staged, not yet flipped) are finished by Muse,
never re-uploaded by GitHub.

## Phase 5 — Monitor + rollback (first week after each platform)

- [ ] Daily check for the first week of each platform's GitHub
      route: scheduled slot published? Sheet status + ID correct?
      Caption/title/tags read back live? Any duplicate posts?
- [ ] Any duplicate, wrong title, wrong caption, or missed slot
      triggers rollback for that platform immediately:
      1. Re-enable that platform's Muse jobs from the table above.
      2. Keep the GitHub schedules commented out; GitHub returns
         to dispatch-only fallback.
      3. Report the failure with the post number, sheet row, and
         runner log excerpt. Do not delete the duplicate or the
         wrong post without user approval.
- [ ] Rollback does not require re-creating anything: pausing a
      Muse job does not delete it, and the GitHub drafts remain
      in this folder for debugging.

## What "done" looks like

- YT + IG routine posts run from GitHub (dispatch or, only after
  a separate user decision, a re-enabled schedule with
  re-planned cron times).
- Facebook videos run from the natively scheduled queue, loaded
  in weekly batches, verified against the live queue.
- Noon images still run from Muse until a separate image workflow
  exists.
- The user no longer clicks "Allow" in chat for routine slots.
  The only remaining taps are: weekly FB batch creation (if
  loaded by Muse), delete + recreate repairs, and any new
  migration decision — exactly as designed in
  FB_NATIVE_SCHEDULING.md.
