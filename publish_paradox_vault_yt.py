#!/usr/bin/env python3
"""
DRAFT — Paradox Vault YouTube publisher for GitHub Actions.
PREPARATION ONLY. Do not push this file to GitHub, do not run it against
the live sheet, and do not dispatch any workflow until the cutover
checklist in CUTOVER_CHECKLIST.md is approved by the user.

What this draft changes vs the old public script
(publish_paradox_vault_yt.py on main):
  * Matches the CURRENT master sheet layout (see SHEET COLUMNS below),
    not the old A2:T35 / "pending" layout.
  * Stage (Unlisted) and flip (public) are separate actions, mirroring
    ~/workspace/pv_publisher/publish.py. The old script published
    everything straight to public.
  * Long-form vs Shorts is handled correctly: the " #Shorts" suffix is
    added ONLY for shortform titles. Titles containing "documentary" or
    "longform" are uploaded verbatim, with no suffix.
  * Description is the sheet caption (col J) verbatim. No hashtags are
    appended by this script.
  * Tags are the sheet tags (col K) split on commas only, matching the
    current publisher. The 2026-10-26 staging failure was a Composio
    400 because tags were passed as a single string; tags MUST be a list.
  * A missing video ID is a failure: the row is left "scheduled", a
    timestamped error is written to col T, and the script exits non-zero.
    It never writes "staged"/"published" without a real video ID.
  * NO first/pinned comment, NO follow-up action on a published post,
    NO alert email. Those were in the old script and are removed.
  * NO hardcoded Composio API key and NO hardcoded connected-account IDs.
    The API key comes only from the COMPOSIO_API_KEY environment variable
    (GitHub secret). Connected accounts are discovered at runtime from
    Composio; optional per-toolkit overrides are env vars only
    (COMPOSIO_GOOGLEDRIVE_ACCOUNT_ID, COMPOSIO_GOOGLESHEETS_ACCOUNT_ID,
    COMPOSIO_YOUTUBE_ACCOUNT_ID). If an account cannot be discovered,
    the script fails clearly instead of silently using a stale ID.
  * Sheet writes use value_input_option RAW, matching the current
    publisher, not USER_ENTERED.

SHEET COLUMNS (master sheet, Sheet1; 0-based index in brackets):
  E title [4], G drive_file_id [6], H caption_fb [7], I caption_ig [8],
  J caption_yt [9], K tags_yt [10],
  M fb status [12], N fb id [13], O ig status [14], P ig id [15],
  Q yt status [16], R yt id [17], S timestamp [18], T notes [19],
  U yt date [20], V ig date [21], W fb date [22],
  X ig catchup date [23], Y fb catchup date [24].
  Status values today: "scheduled" / "staged" / "published"
  (never "pending" — that was the old layout).
  Row map: post #0 -> sheet row 21; #1-19 -> n+1; #n>=20 -> n+2.

USAGE (after cutover approval only):
  python publish_paradox_vault_yt.py --action stage --post-no 12
  python publish_paradox_vault_yt.py --action flip  --post-no 12
  python publish_paradox_vault_yt.py --action stage --all-due [--date YYYY-MM-DD]
  python publish_paradox_vault_yt.py --action stage --post-no 12 --dry-run

VERIFICATION LIMIT (honest, read before cutover):
  Composio's upload/publish responses return an ID but do not echo the
  full title/description/caption back. This script therefore verifies
  (a) a non-empty video ID was returned, (b) the sheet row holds that
  ID with the correct status, and (c) it prints the exact title,
  description and tags it submitted. The full live read-back
  (YouTube Studio Content list: title, description, tags, visibility)
  is a required step in the test plan in MIGRATION_NOTES.md before any
  cutover approval — it is not something this script can prove alone.
"""

import argparse
import os
import sys
import zoneinfo
from datetime import datetime
from urllib.parse import urlparse

from composio import Composio

SHEET_ID = os.environ.get(
    "PV_SHEET_ID", "1UTtsb83Od3wM-d5B6er9fdpczS38roLGzMjygJqSsac"
)
SHEET_RANGE = "Sheet1!A2:Y150"
DRY = False


def log(*a):
    print("[pv-yt]", *a, flush=True)


def ist_now():
    return datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M")


def today_ist():
    return datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")


# ---------------------------------------------------------------- Composio
def build_client():
    api_key = os.environ.get("COMPOSIO_API_KEY")
    if not api_key:
        print("Error: COMPOSIO_API_KEY environment variable is missing.")
        sys.exit(1)
    return Composio(api_key=api_key)


CLIENT = None
ACCOUNT_MAP = {}
USER_ID = None

TOOLKIT_MAP = {
    "GOOGLEDRIVE_DOWNLOAD_FILE": "googledrive",
    "GOOGLESHEETS_VALUES_GET": "googlesheets",
    "GOOGLESHEETS_VALUES_UPDATE": "googlesheets",
    "YOUTUBE_MULTIPART_UPLOAD_VIDEO": "youtube",
    "YOUTUBE_UPDATE_VIDEO": "youtube",
}

ENV_ACCOUNT_OVERRIDE = {
    "googledrive": "COMPOSIO_GOOGLEDRIVE_ACCOUNT_ID",
    "googlesheets": "COMPOSIO_GOOGLESHEETS_ACCOUNT_ID",
    "youtube": "COMPOSIO_YOUTUBE_ACCOUNT_ID",
}


def discover_accounts():
    """Discover ACTIVE connected accounts at runtime. No static fallbacks.

    If a toolkit has no ACTIVE account, it is absent from ACCOUNT_MAP and
    execute_tool() fails with a clear message instead of using a stale ID.
    """
    global USER_ID
    for toolkit, env_name in ENV_ACCOUNT_OVERRIDE.items():
        override = os.environ.get(env_name)
        if override:
            ACCOUNT_MAP[toolkit] = override
    try:
        resp = CLIENT.connected_accounts.list()
        items = getattr(resp, "items", resp)
        for a in items:
            aid = getattr(a, "id", None) or (a.get("id") if isinstance(a, dict) else None)
            tk = getattr(a, "toolkit", None) or (a.get("toolkit") if isinstance(a, dict) else None)
            tk_slug = getattr(tk, "slug", tk) or (tk.get("slug") if isinstance(tk, dict) else tk)
            uid = getattr(a, "user_id", None) or (a.get("user_id") if isinstance(a, dict) else None)
            status = getattr(a, "status", None) or (a.get("status") if isinstance(a, dict) else None)
            if status == "ACTIVE" and tk_slug and aid:
                # Env overrides win over discovery, so never overwrite one.
                ACCOUNT_MAP.setdefault(str(tk_slug).lower(), aid)
            if uid and not USER_ID:
                USER_ID = uid
    except Exception as e:  # noqa: BLE001 - discovery failure is non-fatal only
        # if every toolkit needed is already covered by an env override.
        print("Account discovery warning:", e)
    env_uid = os.environ.get("COMPOSIO_USER_ID")
    if env_uid:
        USER_ID = env_uid
    log("Active accounts discovered for toolkits:", sorted(ACCOUNT_MAP.keys()))


def execute_tool(slug, arguments):
    toolkit = TOOLKIT_MAP.get(slug)
    if toolkit and toolkit not in ACCOUNT_MAP:
        raise RuntimeError(
            f"No ACTIVE Composio account discovered for toolkit '{toolkit}' "
            f"(tool {slug}). Refusing to use a stale hardcoded account ID."
        )
    kwargs = {"dangerously_skip_version_check": True}
    if USER_ID:
        kwargs["user_id"] = USER_ID
    if toolkit and toolkit in ACCOUNT_MAP:
        kwargs["connected_account_id"] = ACCOUNT_MAP[toolkit]
    if hasattr(CLIENT, "tools") and hasattr(CLIENT.tools, "execute"):
        try:
            return CLIENT.tools.execute(slug=slug, arguments=arguments, **kwargs)
        except TypeError:
            kwargs.pop("dangerously_skip_version_check", None)
            return CLIENT.tools.execute(slug=slug, arguments=arguments, **kwargs)
    if hasattr(CLIENT, "actions") and hasattr(CLIENT.actions, "execute"):
        kwargs.pop("dangerously_skip_version_check", None)
        return CLIENT.actions.execute(action=slug, params=arguments, **kwargs)
    raise RuntimeError("No valid execution method found on Composio client")


def get_data(res):
    if isinstance(res, dict):
        return res.get("data", res)
    return getattr(res, "data", res)


def response_failed(res):
    """True when a Composio wrapper explicitly reports failure."""
    if isinstance(res, dict):
        if res.get("successful") is False:
            return True
        inner = res.get("response", {})
        if isinstance(inner, dict) and inner.get("successful") is False:
            return True
    return False


# ---------------------------------------------------------------- Sheet
def sheet_row_for_post_no(n):
    if n == 0:
        return 21
    if n < 20:
        return n + 1
    return n + 2


def post_no_for_sheet_row(r):
    if r == 21:
        return 0
    if r <= 20:
        return r - 1
    return r - 2


def fetch_rows():
    res = execute_tool(
        "GOOGLESHEETS_VALUES_GET",
        {"spreadsheet_id": SHEET_ID, "range": SHEET_RANGE},
    )
    rows = get_data(res).get("values", [])
    padded = []
    for row in rows:
        padded.append(list(row) + [""] * (25 - len(row)))
    return padded


def row_by_sheet_row(rows, sheet_row):
    idx = sheet_row - 2
    if idx < 0 or idx >= len(rows):
        raise SystemExit(f"Sheet row {sheet_row} is outside fetched range {SHEET_RANGE}")
    return rows[idx]


def write_cell(sheet_row, col_letter, value):
    if DRY:
        log(f"DRY: would write {col_letter}{sheet_row} = {str(value)[:80]}")
        return
    execute_tool(
        "GOOGLESHEETS_VALUES_UPDATE",
        {
            "spreadsheet_id": SHEET_ID,
            "range": f"Sheet1!{col_letter}{sheet_row}",
            "value_input_option": "RAW",
            "values": [[value]],
        },
    )


def write_error(sheet_row, action, message):
    # Never let an error write mask the live status: col T only.
    write_cell(sheet_row, "T", f"{ist_now()} yt/{action} FAILED: {str(message)[:120]}")


def parse_post_no(cell):
    text = (cell or "").strip().lstrip("#")
    return int(text) if text.isdigit() else None


def is_shortform(title):
    return not any(k in title.lower() for k in ("documentary", "longform"))


def yt_title_for(title):
    if is_shortform(title):
        return title if title.endswith("#Shorts") else f"{title} #Shorts"
    return title


def parse_tags(raw):
    # Matches the current publisher: split on commas only, strip
    # whitespace, drop empties. Do NOT strip a leading '#' here — the
    # sheet tags are stored without it, and the old script's lstrip('#')
    # is not needed to match current behaviour.
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    return [t.strip() for t in str(raw or "").split(",") if t.strip()]


# ---------------------------------------------------------------- Actions
def do_stage(row, sheet_row):
    post_no = parse_post_no(row[0])
    title = (row[4] or "").strip()
    drive_id = (row[6] or "").strip()
    cap_yt = row[9] or ""
    tags = parse_tags(row[10])
    yt_status = (row[16] or "").strip().lower()
    if not title or not drive_id or drive_id.startswith("TBD"):
        raise SystemExit(f"Row {sheet_row}: title or drive_file_id missing/TBD")
    if not cap_yt.strip():
        raise SystemExit(f"Row {sheet_row}: caption_yt (col J) is empty — refusing to stage without metadata")
    if yt_status != "scheduled":
        raise SystemExit(f"Row {sheet_row}: yt status is '{yt_status}', not 'scheduled' — refusing to stage")
    yt_title = yt_title_for(title)
    log(f"Staging post #{post_no} (row {sheet_row}): {yt_title}")
    log(f"  shortform={is_shortform(title)} tags={tags}")
    if DRY:
        log("DRY: would upload Unlisted via YOUTUBE_MULTIPART_UPLOAD_VIDEO")
        log(f"DRY: description (verbatim, {len(cap_yt)} chars) and tags as above")
        return
    drive_res = execute_tool(
        "GOOGLEDRIVE_DOWNLOAD_FILE", {"fileId": drive_id}
    )
    dl = get_data(drive_res).get("downloaded_file_content", {})
    s3key = dl.get("s3key")
    s3url = dl.get("s3url")
    if not s3key and s3url:
        s3key = urlparse(s3url).path.lstrip("/")  # no leading slash: with it, storage 404s
    name = dl.get("name") or f"{title}.mp4"
    if not s3key:
        write_error(sheet_row, "stage", f"no s3key/s3url from Drive download: {str(drive_res)[:200]}")
        raise SystemExit("Drive download returned no s3key/s3url")
    yt_res = execute_tool(
        "YOUTUBE_MULTIPART_UPLOAD_VIDEO",
        {
            "title": yt_title,
            "description": cap_yt,  # verbatim — nothing appended
            "categoryId": "27",  # Education, as in the current publisher
            "privacyStatus": "unlisted",
            "madeForKids": False,
            "tags": tags,  # MUST be a list; a string triggers Composio 400
            "videoFile": {"name": name, "s3key": s3key, "mimetype": "video/mp4"},
        },
    )
    data = get_data(yt_res)
    vid = None
    if isinstance(data, dict):
        vid = (
            data.get("video_id")
            or data.get("id")
            or (data.get("video") or {}).get("id")
            or (data.get("response_data") or {}).get("id")
        )
    if response_failed(yt_res) or not vid:
        write_error(sheet_row, "stage", f"no video id returned: {str(yt_res)[:300]}")
        raise SystemExit("yt/stage FAILED: no video id returned; row left scheduled")
    # Verification (see module docstring limit): ID + sheet write + the
    # exact submitted payload printed here for the Studio read-back.
    log(f"Staged, video id: {vid}")
    log(f"Submitted title: {yt_title}")
    log(f"Submitted description chars: {len(cap_yt)}; tags: {tags}")
    write_cell(sheet_row, "R", vid)
    write_cell(sheet_row, "Q", "staged")
    url = (
        f"https://www.youtube.com/shorts/{vid}"
        if is_shortform(title)
        else f"https://www.youtube.com/watch?v={vid}"
    )
    log(f"Staged URL (Unlisted until flip): {url}")


def do_flip(row, sheet_row):
    post_no = parse_post_no(row[0])
    vid = (row[17] or "").strip()
    yt_status = (row[16] or "").strip().lower()
    if not vid or vid.startswith("DRY"):
        raise SystemExit(f"Row {sheet_row}: no staged video id in col R — refusing to flip")
    if yt_status != "staged":
        raise SystemExit(f"Row {sheet_row}: yt status is '{yt_status}', not 'staged' — refusing to flip")
    log(f"Flipping post #{post_no} (row {sheet_row}) video {vid} to public")
    if DRY:
        log("DRY: would YOUTUBE_UPDATE_VIDEO privacyStatus=public")
        return
    res = execute_tool(
        "YOUTUBE_UPDATE_VIDEO",
        {"videoId": vid, "privacyStatus": "public"},
    )
    if response_failed(res):
        raise SystemExit(f"yt/flip FAILED: {str(res)[:300]}")
    write_cell(sheet_row, "Q", "published")
    write_cell(sheet_row, "S", ist_now())
    log(f"Flipped to public: {vid}")


def main():
    global CLIENT, DRY
    ap = argparse.ArgumentParser()
    ap.add_argument("--action", required=True, choices=["stage", "flip"])
    ap.add_argument("--post-no", type=int, default=None)
    ap.add_argument("--sheet-row", type=int, default=None,
                    help="Direct Sheet1 row number (overrides --post-no mapping)")
    ap.add_argument("--all-due", action="store_true")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today IST")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    DRY = a.dry_run
    CLIENT = build_client()
    discover_accounts()
    datestr = a.date or today_ist()
    rows = fetch_rows()

    targets = []
    if a.sheet_row is not None:
        targets.append(a.sheet_row)
    elif a.post_no is not None:
        targets.append(sheet_row_for_post_no(a.post_no))
    elif a.all_due:
        want = "scheduled" if a.action == "stage" else "staged"
        for idx, row in enumerate(rows):
            sheet_row = idx + 2
            if parse_post_no(row[0]) is None:
                continue
            if (row[20] or "").strip() == datestr and (row[16] or "").strip().lower() == want:
                targets.append(sheet_row)
        log(f"Due for yt/{a.action} on {datestr}: sheet rows {targets}")
    else:
        raise SystemExit("need --post-no, --sheet-row, or --all-due")

    failed = 0
    for sheet_row in targets:
        row = row_by_sheet_row(rows, sheet_row)
        try:
            if a.action == "stage":
                do_stage(row, sheet_row)
            else:
                do_flip(row, sheet_row)
        except SystemExit as e:
            print(f"FAILED row {sheet_row}: {e}", file=sys.stderr)
            failed += 1
        except Exception as e:  # noqa: BLE001 - report, do not mask the row
            print(f"ERROR row {sheet_row}: {type(e).__name__}: {e}", file=sys.stderr)
            if not DRY:
                try:
                    write_error(sheet_row, a.action, f"{type(e).__name__}: {e}")
                except Exception:
                    pass
            failed += 1
    if failed:
        sys.exit(1)
    log("done")


if __name__ == "__main__":
    main()
