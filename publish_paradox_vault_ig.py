#!/usr/bin/env python3
"""
DRAFT — Paradox Vault Instagram Reels publisher for GitHub Actions.
PREPARATION ONLY. Do not push this file to GitHub, do not run it against
the live sheet, and do not dispatch any workflow until the cutover
checklist in CUTOVER_CHECKLIST.md is approved by the user.

What this draft changes vs the old public script
(publish_paradox_vault_ig.py on main):
  * Matches the CURRENT master sheet layout (see SHEET COLUMNS below),
    not the old A2:T35 / "pending" layout. Prime slots use ig date
    (col V) with ig status (col O); noon catch-up slots use ig catchup
    date (col X) with the same status column.
  * Caption is the sheet caption (col I) verbatim, with plain '#'.
    Nothing is encoded as %23 (that renders literally on Instagram and
    captions cannot be edited via API afterwards).
  * A missing container ID or media ID is a failure: the row is left
    "scheduled", a timestamped error is written to col T, and the script
    exits non-zero. It never writes "published" without a real media ID.
  * NO first comment, NO follow-up action on a published post, NO alert
    email. Those were in the old script and are removed.
  * NO hardcoded Composio API key, NO hardcoded connected-account IDs,
    and NO hardcoded Instagram user ID. The API key comes only from the
    COMPOSIO_API_KEY environment variable (GitHub secret). Connected
    accounts are discovered at runtime; the Instagram user ID is resolved
    via INSTAGRAM_GET_USER_INFO ("me") on every run. If either cannot
    be resolved, the script fails clearly instead of using a stale ID.
  * Sheet writes use value_input_option RAW, matching the current
    publisher, not USER_ENTERED.
  * Publish wait is max_wait_seconds 300, matching the current publisher
    (the old script used 180).

SHEET COLUMNS (master sheet, Sheet1; 0-based index in brackets):
  E title [4], G drive_file_id [6], I caption_ig [8],
  O ig status [14], P ig id [15], S timestamp [18], T notes [19],
  V ig date [21], X ig catchup date [23].
  Status values today: "scheduled" / "published" (never "pending").
  Row map: post #0 -> sheet row 21; #1-19 -> n+1; #n>=20 -> n+2.

USAGE (after cutover approval only):
  python publish_paradox_vault_ig.py --post-no 3
  python publish_paradox_vault_ig.py --post-no 3 --catchup
  python publish_paradox_vault_ig.py --all-due [--date YYYY-MM-DD]
  python publish_paradox_vault_ig.py --post-no 3 --dry-run

VERIFICATION LIMIT (honest, read before cutover):
  Composio's publish response returns a media ID but does not echo the
  full caption back. This script therefore verifies (a) a non-empty
  container ID, (b) a non-empty media ID, (c) the sheet row holds that
  media ID with status "published", and (d) it prints the exact caption
  it submitted. The full live read-back (Instagram app: caption text,
  hashtags, Reel playback) is a required step in the test plan in
  MIGRATION_NOTES.md before any cutover approval — it is not something
  this script can prove alone.
"""

import argparse
import os
import sys
import time
import zoneinfo
from datetime import datetime

from composio import Composio

SHEET_ID = os.environ.get(
    "PV_SHEET_ID", "1UTtsb83Od3wM-d5B6er9fdpczS38roLGzMjygJqSsac"
)
SHEET_RANGE = "Sheet1!A2:Y150"
DRY = False


def log(*a):
    print("[pv-ig]", *a, flush=True)


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
    "INSTAGRAM_GET_USER_INFO": "instagram",
    "INSTAGRAM_POST_IG_USER_MEDIA": "instagram",
    "INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH": "instagram",
}

ENV_ACCOUNT_OVERRIDE = {
    "googledrive": "COMPOSIO_GOOGLEDRIVE_ACCOUNT_ID",
    "googlesheets": "COMPOSIO_GOOGLESHEETS_ACCOUNT_ID",
    "instagram": "COMPOSIO_INSTAGRAM_ACCOUNT_ID",
}


def discover_accounts():
    """Discover ACTIVE connected accounts at runtime. No static fallbacks."""
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
                ACCOUNT_MAP.setdefault(str(tk_slug).lower(), aid)
            if uid and not USER_ID:
                USER_ID = uid
    except Exception as e:  # noqa: BLE001
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


def parse_post_no(cell):
    text = (cell or "").strip().lstrip("#")
    return int(text) if text.isdigit() else None


def fetch_rows():
    res = execute_tool(
        "GOOGLESHEETS_VALUES_GET",
        {"spreadsheet_id": SHEET_ID, "range": SHEET_RANGE},
    )
    rows = get_data(res).get("values", [])
    return [list(row) + [""] * (25 - len(row)) for row in rows]


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


def write_error(sheet_row, message):
    write_cell(sheet_row, "T", f"{ist_now()} ig/publish FAILED: {str(message)[:120]}")


# ---------------------------------------------------------------- Action
def resolve_ig_user_id():
    res = execute_tool(
        "INSTAGRAM_GET_USER_INFO",
        {"ig_user_id": "me", "fields": "id,user_id,username"},
    )
    data = get_data(res)
    ig_id = None
    if isinstance(data, dict):
        ig_id = data.get("user_id") or data.get("id")
    if not ig_id:
        raise SystemExit(f"Could not resolve Instagram user id: {str(res)[:300]}")
    log(f"Resolved Instagram user id: {ig_id} (username field, if returned: "
        f"{data.get('username') if isinstance(data, dict) else ''})")
    return str(ig_id)


def do_publish(row, sheet_row, catchup=False):
    post_no = parse_post_no(row[0])
    title = (row[4] or "").strip()
    drive_id = (row[6] or "").strip()
    cap_ig = row[8] or ""
    ig_status = (row[14] or "").strip().lower()
    if not title or not drive_id or drive_id.startswith("TBD"):
        raise SystemExit(f"Row {sheet_row}: title or drive_file_id missing/TBD")
    if not cap_ig.strip():
        raise SystemExit(f"Row {sheet_row}: caption_ig (col I) is empty — refusing to publish without a caption")
    if "%23" in cap_ig:
        # Plain '#' only. A %23 in the sheet caption would render literally.
        raise SystemExit(f"Row {sheet_row}: caption_ig contains '%23' — fix the sheet caption to plain '#' first")
    if ig_status != "scheduled":
        raise SystemExit(f"Row {sheet_row}: ig status is '{ig_status}', not 'scheduled' — refusing to publish")
    log(f"Publishing IG Reel post #{post_no} (row {sheet_row}): {title} (catchup={catchup})")
    if DRY:
        log("DRY: would create REELS container + publish with caption verbatim (see below)")
        log(f"DRY: caption ({len(cap_ig)} chars): {cap_ig[:200]}")
        return
    ig_user_id = resolve_ig_user_id()
    drive_res = execute_tool(
        "GOOGLEDRIVE_DOWNLOAD_FILE", {"fileId": drive_id}
    )
    dl = get_data(drive_res).get("downloaded_file_content", {})
    s3url = dl.get("s3url")
    if not s3url:
        write_error(sheet_row, f"no s3url from Drive download: {str(drive_res)[:200]}")
        raise SystemExit("Drive download returned no s3url")
    container_res = execute_tool(
        "INSTAGRAM_POST_IG_USER_MEDIA",
        {
            "ig_user_id": ig_user_id,
            "media_type": "REELS",
            "video_url": s3url,
            "caption": cap_ig,  # verbatim, plain '#', never %23
        },
    )
    cdata = get_data(container_res)
    cid = None
    if isinstance(cdata, dict):
        cid = cdata.get("id") or cdata.get("creation_id")
    if response_failed(container_res) or not cid:
        write_error(sheet_row, f"no container id: {str(container_res)[:300]}")
        raise SystemExit("IG container creation FAILED; row left scheduled")
    log(f"Container: {cid}")
    time.sleep(15)
    publish_res = execute_tool(
        "INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH",
        {
            "ig_user_id": ig_user_id,
            "creation_id": str(cid),
            "max_wait_seconds": 300,
        },
    )
    pdata = get_data(publish_res)
    mid = pdata.get("id") if isinstance(pdata, dict) else None
    if response_failed(publish_res) or not mid:
        write_error(sheet_row, f"no media id on publish: {str(publish_res)[:300]}")
        raise SystemExit("IG publish FAILED; row left scheduled")
    # Verification (see module docstring limit): media ID + sheet write +
    # the exact submitted caption printed here for the app read-back.
    log(f"Published, media id: {mid}")
    log(f"Submitted caption verbatim ({len(cap_ig)} chars): {cap_ig}")
    write_cell(sheet_row, "P", str(mid))
    write_cell(sheet_row, "O", "published")
    write_cell(sheet_row, "S", ist_now())
    if catchup:
        # Mirror the current publisher: a successful catch-up clears the
        # catchup date so the prime-time job does not re-publish it.
        write_cell(sheet_row, "X", "")


def main():
    global CLIENT, DRY
    ap = argparse.ArgumentParser()
    ap.add_argument("--post-no", type=int, default=None)
    ap.add_argument("--sheet-row", type=int, default=None)
    ap.add_argument("--catchup", action="store_true",
                    help="Use ig catchup date (col X) instead of ig date (col V)")
    ap.add_argument("--all-due", action="store_true")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today IST")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    DRY = a.dry_run
    CLIENT = build_client()
    discover_accounts()
    datestr = a.date or today_ist()
    date_col_idx = 23 if a.catchup else 21
    rows = fetch_rows()

    targets = []
    if a.sheet_row is not None:
        targets.append(a.sheet_row)
    elif a.post_no is not None:
        targets.append(sheet_row_for_post_no(a.post_no))
    elif a.all_due:
        for idx, row in enumerate(rows):
            sheet_row = idx + 2
            if parse_post_no(row[0]) is None:
                continue
            if (row[date_col_idx] or "").strip() == datestr and (row[14] or "").strip().lower() == "scheduled":
                targets.append(sheet_row)
        log(f"Due for ig/publish on {datestr} (catchup={a.catchup}): sheet rows {targets}")
    else:
        raise SystemExit("need --post-no, --sheet-row, or --all-due")

    failed = 0
    for sheet_row in targets:
        row = row_by_sheet_row(rows, sheet_row)
        try:
            do_publish(row, sheet_row, catchup=a.catchup)
        except SystemExit as e:
            print(f"FAILED row {sheet_row}: {e}", file=sys.stderr)
            failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"ERROR row {sheet_row}: {type(e).__name__}: {e}", file=sys.stderr)
            if not DRY:
                try:
                    write_error(sheet_row, f"{type(e).__name__}: {e}")
                except Exception:
                    pass
            failed += 1
    if failed:
        sys.exit(1)
    log("done")


if __name__ == "__main__":
    main()
