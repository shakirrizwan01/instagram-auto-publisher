import os
import sys
import time
from datetime import datetime
from urllib.parse import urlparse
import zoneinfo
from composio import Composio

# ==========================================
# CONFIGURATION & ACCOUNT MAPPINGS
# ==========================================
COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY")
if not COMPOSIO_API_KEY:
    print("Error: COMPOSIO_API_KEY environment variable is missing.")
    sys.exit(1)

client = Composio(api_key=COMPOSIO_API_KEY)

USER_ID = "pg-test-e25f369f-1415-44b6-9106-f2d6e6f0b793"

ACCOUNT_MAP = {
    "googledrive": "googledrive_balija-colley",   # rizwanshakir2025@gmail.com (FINAL videos)
    "googlesheets": "googlesheets_agency-broo",   # shakirrizwan01@gmail.com
    "youtube": "ca_1OmWac-CLp-J",             # Paradox Vault Dedicated YouTube OAuth Account
    "gmail": "gmail_afoul-borean"                 # shakirrizwan01@gmail.com
}

TOOLKIT_MAP = {
    "GOOGLEDRIVE_DOWNLOAD_FILE": "googledrive",
    "GOOGLESHEETS_VALUES_GET": "googlesheets",
    "GOOGLESHEETS_VALUES_UPDATE": "googlesheets",
    "YOUTUBE_MULTIPART_UPLOAD_VIDEO": "youtube",
    "YOUTUBE_POST_COMMENT": "youtube",
    "GMAIL_SEND_EMAIL": "gmail"
}

SHEET_ID = "1UTtsb83Od3wM-d5B6er9fdpczS38roLGzMjygJqSsac" # Paradox Vault Master Sheet
CHANNEL_ID = "UCSk1CAYFu0rcvtjlvZBVMPQ"

def execute_tool(slug, arguments, **kwargs):
    kwargs.setdefault("user_id", USER_ID)
    kwargs.setdefault("dangerously_skip_version_check", True)
    toolkit = TOOLKIT_MAP.get(slug)
    if toolkit and toolkit in ACCOUNT_MAP:
        kwargs.setdefault("connected_account_id", ACCOUNT_MAP[toolkit])
    if hasattr(client, "tools") and hasattr(client.tools, "execute"):
        try:
            return client.tools.execute(slug=slug, arguments=arguments, **kwargs)
        except TypeError:
            kwargs.pop("dangerously_skip_version_check", None)
            return client.tools.execute(slug=slug, arguments=arguments, **kwargs)
    elif hasattr(client, "actions") and hasattr(client.actions, "execute"):
        kwargs.pop("dangerously_skip_version_check", None)
        return client.actions.execute(action=slug, params=arguments, **kwargs)
    else:
        raise RuntimeError("No valid execution method found on Composio client")

def get_data(res):
    if isinstance(res, dict):
        return res.get("data", res)
    return getattr(res, "data", res)

def main():
    kolkata_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    now_ist = datetime.now(kolkata_tz)
    today_str = now_ist.strftime("%Y-%m-%d")
    time_str = now_ist.strftime("%H:%M")

    print("==================================================")
    print("PARADOX VAULT — YOUTUBE SHORTS CLOUD RUNNER")
    print(f"Time: {now_ist.strftime('%Y-%m-%d %H:%M:%S')} IST ({today_str} {time_str})")
    print("==================================================")

    # 1. Fetch Schedule from Google Sheet
    sheet_res = execute_tool(
        slug="GOOGLESHEETS_VALUES_GET",
        arguments={
            "spreadsheet_id": SHEET_ID,
            "range": "Sheet1!A2:T35"
        }
    )
    rows = get_data(sheet_res).get("values", [])
    print(f"Loaded {len(rows)} slots from spreadsheet.")

    target_row = None
    target_row_idx = None

    # Check for CLI override flag: python publish_paradox_vault_yt.py --row 4
    for idx, arg in enumerate(sys.argv):
        if arg == "--row" and idx + 1 < len(sys.argv):
            target_row_idx = int(sys.argv[idx + 1])
            target_row = rows[target_row_idx - 2]
            print(f"Targeting row {target_row_idx} via manual CLI flag.")
            break

    if not target_row:
        for idx, row in enumerate(rows):
            post_date = row[1] if len(row) > 1 else ""
            yt_status = row[16] if len(row) > 16 else "pending"

            # Match today or any unfulfilled past backlog slot
            if post_date and post_date <= today_str and yt_status.strip().lower() == "pending":
                target_row = row
                target_row_idx = idx + 2
                print(f"Auto-selected due slot (Row {target_row_idx}, Date: {post_date}).")
                break

    if not target_row:
        print(f"No pending YouTube Shorts found for today or backlog ({today_str}). Exiting cleanly.")
        sys.exit(0)

    post_no = target_row[0]
    title = target_row[4]
    category = target_row[5]
    drive_file_id = target_row[6]
    caption_yt = target_row[9] if len(target_row) > 9 else ""
    first_comment = target_row[11] if len(target_row) > 11 else ""

    # Parse tags
    raw_tags = target_row[10] if len(target_row) > 10 else ""
    tags = [t.strip().lstrip('#') for t in raw_tags.replace(',', '\n').split('\n') if t.strip()]

    print(f"\nLaunching Slot #{post_no}: '{title}' [{category}]")
    print(f"Drive File ID: {drive_file_id}")

    # 2. Acquire S3 direct-download key from Google Drive
    print("Fetching high-speed S3 download link from Google Drive...")
    drive_res = execute_tool(
        slug="GOOGLEDRIVE_DOWNLOAD_FILE",
        arguments={"fileId": drive_file_id}
    )
    drive_data = get_data(drive_res)
    download_info = drive_data.get("downloaded_file_content", {})
    s3key = download_info.get("s3key")
    s3url = download_info.get("s3url")

    # If s3key missing, extract path from s3url
    if not s3key and s3url:
        parsed = urlparse(s3url)
        s3key = parsed.path.lstrip('/')

    if not s3key and not s3url:
        print(f"Error fetching download info from Google Drive: {drive_res}")
        sys.exit(1)
    print("Download stream verified.")

    # 3. Upload Short to YouTube
    print("Uploading YouTube Short to @ParadoxVaultMedia...")
    yt_args = {
        "title": f"{title} #Shorts",
        "description": f"{caption_yt}\n\n#ParadoxVault #Shorts #Facts #Documentary",
        "tags": tags,
        "categoryId": "27",  # Education
        "privacyStatus": "public",
        "madeForKids": False,
        "videoFile": {
            "name": f"{title.replace(' ', '_')}.mp4",
            "mimetype": "video/mp4",
            "s3key": s3key
        }
    }

    yt_res = execute_tool(
        slug="YOUTUBE_MULTIPART_UPLOAD_VIDEO",
        arguments=yt_args
    )
    yt_data = get_data(yt_res)
    yt_video_id = (yt_data.get("video") or {}).get("id") or yt_data.get("id") or (yt_data.get("response_data") or {}).get("id")

    if not yt_video_id:
        print(f"YouTube upload failed: {yt_res}")
        sys.exit(1)

    print(f"Successfully uploaded to YouTube! Video ID: {yt_video_id}")
    yt_url = f"https://www.youtube.com/shorts/{yt_video_id}"
    print(f"Short URL: {yt_url}")

    # 4. Post Pinned Discussion Comment
    if first_comment and first_comment.strip():
        print("Posting pinned discussion starter comment...")
        try:
            execute_tool(
                slug="YOUTUBE_POST_COMMENT",
                arguments={
                    "videoId": str(yt_video_id),
                    "channelId": CHANNEL_ID,
                    "textOriginal": first_comment.strip()
                }
            )
            print("Discussion comment posted successfully.")
        except Exception as e:
            print(f"Warning: Failed to post discussion comment: {e}")

    # 5. Update Master Google Sheet Status
    print(f"Updating Google Sheet Row {target_row_idx}...")
    execute_tool(
        slug="GOOGLESHEETS_VALUES_UPDATE",
        arguments={
            "spreadsheet_id": SHEET_ID,
            "range": f"Sheet1!Q{target_row_idx}:R{target_row_idx}",
            "value_input_option": "USER_ENTERED",
            "values": [["published", str(yt_video_id)]]
        }
    )
    print("Spreadsheet row status updated.")

    # 6. Send Drop Alert Email
    try:
        execute_tool(
            slug="GMAIL_SEND_EMAIL",
            arguments={
                "recipient_email": "shakirrizwan01@gmail.com",
                "subject": f"PARADOX VAULT YOUTUBE SHORT IS LIVE: {title}",
                "body": f"""<h2>Paradox Vault YouTube Short is LIVE!</h2>
<p><strong>Title:</strong> {title}</p>
<p><strong>Category:</strong> {category}</p>
<p><strong>YouTube Short:</strong> <a href="{yt_url}">{yt_url}</a></p>
<p><strong>YouTube Video ID:</strong> {yt_video_id}</p>
<p style="color: #c62828; font-size: 16px;">
Action Required: Open YouTube Studio or the Short on your phone, find the comment below, and tap <strong>Pin</strong>:
</p>
<blockquote style="background:#ffebee; padding:10px; border-left:4px solid #c62828;">
<em>"{first_comment}"</em>
</blockquote>
""",
                "is_html": True
            }
        )
        print("Alert email sent to shakirrizwan01@gmail.com.")
    except Exception as e:
        print(f"Alert email note: {e}")

    print("\nWorkflow completed successfully.")

if __name__ == "__main__":
    main()
