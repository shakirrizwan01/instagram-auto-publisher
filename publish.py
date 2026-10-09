import os
import sys
from datetime import datetime
import zoneinfo
from composio import Composio

COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY")
if not COMPOSIO_API_KEY:
    print("Error: COMPOSIO_API_KEY environment variable is missing.")
    sys.exit(1)

client = Composio(api_key=COMPOSIO_API_KEY)
SHEET_ID = "1_IJaznafMh7X7rmgQ1idHSptoULSr5enoewXk8NYjCY"

kolkata_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
now_ist = datetime.now(kolkata_tz)
today_str = now_ist.strftime("%Y-%m-%d")
time_str = now_ist.strftime("%H:%M")

print(f"Running Instagram Auto Publisher at {now_ist} (Date: {today_str}, Time: {time_str} IST)")

sheet_res = client.tools.execute(
    slug="GOOGLESHEETS_VALUES_GET",
    arguments={
        "spreadsheet_id": SHEET_ID,
        "range": "Sheet1!A2:W57"
    }
)
rows = sheet_res.data.get("values", [])
print(f"Total rows fetched: {len(rows)}")

target_row = None
target_row_idx = None

for idx, row in enumerate(rows):
    post_date = row[2] if len(row) > 2 else ""
    post_time = row[4] if len(row) > 4 else ""
    ig_status = row[21] if len(row) > 21 else "pending"

    if post_date == today_str and ig_status.strip().lower() == "pending":
        target_row = row
        target_row_idx = idx + 2
        break

if not target_row:
    print(f"No pending Instagram post found for today ({today_str}). Exiting cleanly.")
    sys.exit(0)

post_no = target_row[0]
title = target_row[7]
caption_ig = target_row[15]
drive_file_id = target_row[18]

print(f"Found post to publish! Row {target_row_idx}: Post {post_no} — '{title}'")

print(f"Fetching S3 download URL from Google Drive for file ID {drive_file_id}...")
drive_res = client.tools.execute(
    slug="GOOGLEDRIVE_DOWNLOAD_FILE",
    arguments={
        "fileId": drive_file_id,
        "account": "googledrive_eyey-perch"
    }
)
s3url = drive_res.data.get("downloaded_file_content", {}).get("s3url")
if not s3url:
    print(f"Error fetching download URL from Google Drive: {drive_res}")
    sys.exit(1)

print("Video download URL acquired successfully.")

print("Creating Instagram media container...")
container_res = client.tools.execute(
    slug="INSTAGRAM_POST_IG_USER_MEDIA",
    arguments={
        "ig_user_id": "me",
        "video_url": s3url,
        "caption": caption_ig,
        "media_type": "REELS"
    }
)
container_id = container_res.data.get("id")
if not container_id:
    print(f"Error creating Instagram media container: {container_res}")
    sys.exit(1)

print(f"Container created successfully. ID: {container_id}. Publishing...")

publish_res = client.tools.execute(
    slug="INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH",
    arguments={
        "ig_user_id": "me",
        "creation_id": container_id,
        "max_wait_seconds": 180
    }
)
ig_media_id = publish_res.data.get("id")
if not ig_media_id:
    print(f"Error publishing Instagram media: {publish_res}")
    sys.exit(1)

print(f"🎉 Successfully published to Instagram! Media ID: {ig_media_id}")

print(f"Updating Google Sheet Row {target_row_idx}...")
client.tools.execute(
    slug="GOOGLESHEETS_VALUES_UPDATE",
    arguments={
        "spreadsheet_id": SHEET_ID,
        "range": f"Sheet1!V{target_row_idx}:W{target_row_idx}",
        "value_input_option": "USER_ENTERED",
        "values": [["published", str(ig_media_id)]]
    }
)

print("Sending drop alert email to shakirrizwan01@gmail.com...")
try:
    client.tools.execute(
        slug="GMAIL_SEND_EMAIL",
        arguments={
            "recipient_email": "shakirrizwan01@gmail.com",
            "subject": f"🎬 LIVE DROP & STORY ALERT: {title[:40]}",
            "body": f'''<h2>🎉 New Post is LIVE on Instagram & Facebook!</h2>
<p><strong>Track:</strong> {title}</p>
<p><strong>Instagram Media ID:</strong> {ig_media_id}</p>
<p style="color: #d93025; font-size: 16px;">
👉 <strong>Action Required:</strong> Open Instagram and Facebook on your phone, find this new post, and tap <strong>Share ➔ Add to Story</strong>!
</p>''',
            "is_html": True
        }
    )
    print("Email notification sent successfully.")
except Exception as e:
    print("Email notification failed (non-critical):", e)

print("Workflow completed successfully.")
