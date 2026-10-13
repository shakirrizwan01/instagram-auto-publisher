import os
import sys
import time
from datetime import datetime
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

ACCOUNT_MAP = {
    "googledrive": "googledrive_balija-colley",   # rizwanshakir2025@gmail.com (FINAL videos)
    "googlesheets": "googlesheets_agency-broo",   # shakirrizwan01@gmail.com
    "instagram": "instagram_ossify-requit",       # Paradox Vault Instagram (@paradoxvaultmedia)
    "gmail": "gmail_afoul-borean"                 # shakirrizwan01@gmail.com
}

TOOLKIT_MAP = {
    "GOOGLEDRIVE_DOWNLOAD_FILE": "googledrive",
    "GOOGLESHEETS_VALUES_GET": "googlesheets",
    "GOOGLESHEETS_VALUES_UPDATE": "googlesheets",
    "INSTAGRAM_POST_IG_USER_MEDIA": "instagram",
    "INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH": "instagram",
    "GMAIL_SEND_EMAIL": "gmail"
}

SHEET_ID = "1UTtsb83Od3wM-d5B6er9fdpczS38roLGzMjygJqSsac" # Paradox Vault Sheet

def execute_tool(slug, arguments, **kwargs):
    toolkit = TOOLKIT_MAP.get(slug)
    call_kwargs = {}
    if toolkit and toolkit in ACCOUNT_MAP:
        call_kwargs["connected_account_id"] = ACCOUNT_MAP[toolkit]
    if hasattr(client, "tools") and hasattr(client.tools, "execute"):
        return client.tools.execute(slug=slug, arguments=arguments, **call_kwargs)
    elif hasattr(client, "actions") and hasattr(client.actions, "execute"):
        return client.actions.execute(action=slug, params=arguments, **call_kwargs)
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
    print("🟣 PARADOX VAULT — INSTAGRAM REELS CLOUD RUNNER")
    print(f"Time: {now_ist.strftime('%Y-%m-%d %H:%M:%S')} IST ({today_str} {time_str})")
    print("==================================================")

    # 1. Fetch Schedule from Google Sheet
    sheet_res = execute_tool(
        slug="GOOGLESHEETS_VALUES_GET",
        arguments={
            "spreadsheet_id": SHEET_ID,
            "range": "Sheet1!A2:T15"
        }
    )
    rows = get_data(sheet_res).get("values", [])
    print(f"Loaded {len(rows)} slots from spreadsheet.")

    target_row = None
    target_row_idx = None

    # Check for CLI override flag: python publish_paradox_vault_ig.py --row 2
    for idx, arg in enumerate(sys.argv):
        if arg == "--row" and idx + 1 < len(sys.argv):
            target_row_idx = int(sys.argv[idx + 1])
            target_row = rows[target_row_idx - 2]
            print(f"Targeting row {target_row_idx} via manual CLI flag.")
            break

    if not target_row:
        for idx, row in enumerate(rows):
            post_date = row[1] if len(row) > 1 else ""
            ig_status = row[14] if len(row) > 14 else "pending"

            if post_date == today_str and ig_status.strip().lower() == "pending":
                target_row = row
                target_row_idx = idx + 2
                break

    if not target_row:
        print(f"No pending Instagram Reels found for today ({today_str}). Exiting cleanly.")
        sys.exit(0)

    post_no = target_row[0]
    title = target_row[4]
    category = target_row[5]
    drive_file_id = target_row[6]
    caption_ig = target_row[8]
    first_comment = target_row[11] if len(target_row) > 11 else ""

    print(f"\n🚀 Launching Slot #{post_no}: '{title}' [{category}]")
    print(f"Drive File ID: {drive_file_id}")

    # 2. Acquire S3 direct-download URL from Google Drive
    print("Fetching high-speed S3 download link from Google Drive...")
    drive_res = execute_tool(
        slug="GOOGLEDRIVE_DOWNLOAD_FILE",
        arguments={"fileId": drive_file_id}
    )
    drive_data = get_data(drive_res)
    download_info = drive_data.get("downloaded_file_content", {})
    s3url = download_info.get("s3url")

    if not s3url:
        print(f"Error fetching download URL from Google Drive: {drive_res}")
        sys.exit(1)
    print("✅ Download stream verified.")

    # 3. Create Instagram media container
    print("Creating Instagram media container (@paradoxvaultmedia)...")
    container_res = execute_tool(
        slug="INSTAGRAM_POST_IG_USER_MEDIA",
        arguments={
            "ig_user_id": "39170856485894595",
            "video_url": s3url,
            "caption": caption_ig,
            "media_type": "REELS"
        }
    )
    container_id = get_data(container_res).get("id")
    if not container_id:
        print(f"Error creating Instagram media container: {container_res}")
        sys.exit(1)

    print(f"Container created successfully ({container_id}). Waiting for media processing...")
    time.sleep(10)

    # 4. Publish Instagram Reel
    print("Publishing Reel...")
    publish_res = execute_tool(
        slug="INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH",
        arguments={
            "ig_user_id": "39170856485894595",
            "creation_id": container_id,
            "max_wait_seconds": 180
        }
    )
    ig_media_id = get_data(publish_res).get("id")
    if not ig_media_id:
        print(f"Error publishing Instagram media: {publish_res}")
        sys.exit(1)

    print(f"🎉 Successfully published to Instagram! Media ID: {ig_media_id}")

    # 5. Update Master Google Sheet Status
    print(f"Updating Google Sheet Row {target_row_idx}...")
    execute_tool(
        slug="GOOGLESHEETS_VALUES_UPDATE",
        arguments={
            "spreadsheet_id": SHEET_ID,
            "range": f"Sheet1!O{target_row_idx}:P{target_row_idx}",
            "value_input_option": "USER_ENTERED",
            "values": [["published", str(ig_media_id)]]
        }
    )
    print("✅ Spreadsheet row status updated.")

    # 6. Send Drop Alert Email
    try:
        execute_tool(
            slug="GMAIL_SEND_EMAIL",
            arguments={
                "recipient_email": "shakirrizwan01@gmail.com",
                "subject": f"🟣 PARADOX VAULT IG DROP IS LIVE: {title}",
                "body": f"""<h2>🎉 Paradox Vault Instagram Reel is LIVE!</h2>
<p><strong>Title:</strong> {title}</p>
<p><strong>Category:</strong> {category}</p>
<p><strong>Instagram Media ID:</strong> {ig_media_id}</p>
<p style="color: #6a1b9a; font-size: 16px;">
👉 <strong>Action Required:</strong> Open Instagram on your phone, find the Reel, and pin this debate comment:
</p>
<blockquote style="background:#f3e5f5; padding:10px; border-left:4px solid #8e24aa;">
<em>"{first_comment}"</em>
</blockquote>
""",
                "is_html": True
            }
        )
        print("✅ Alert email sent to shakirrizwan01@gmail.com.")
    except Exception as e:
        print(f"Alert email note: {e}")

    print("\nWorkflow completed successfully.")

if __name__ == "__main__":
    main()
