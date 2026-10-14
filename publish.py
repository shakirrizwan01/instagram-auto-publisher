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

# Map tool slug to toolkit name
TOOLKIT_MAP = {
    "GMAIL_SEND_EMAIL": "gmail",
    "GOOGLESHEETS_VALUES_GET": "googlesheets",
    "GOOGLESHEETS_VALUES_UPDATE": "googlesheets",
    "GOOGLEDRIVE_DOWNLOAD_FILE": "googledrive",
    "INSTAGRAM_POST_IG_USER_MEDIA": "instagram",
    "INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH": "instagram",
    "INSTAGRAM_POST_IG_MEDIA_COMMENTS": "instagram",
    "FACEBOOK_CREATE_PAGE_FEED_POST": "facebook",
    "FACEBOOK_CREATE_COMMENT": "facebook",
    "YOUTUBE_VIDEOS_INSERT": "youtube"
}

# Explicit connected account IDs in the Project (fallback)
ACCOUNT_MAP = {
    "gmail": "ca_xLZdOBRwIJLf",
    "googlesheets": "ca_P5SOLNnc27rB",
    "googledrive": "googledrive_eyey-perch",
    "instagram": "ca_dAL2HtP-8D0G",
    "facebook": "ca_CRcdLr-bArog",
    "youtube": "ca_pUUHcPX5WySk"
}

USER_ID = "pg-test-e25f369f-1415-44b6-9106-f2d6e6f0b793"

# Dynamically discover active accounts from Composio
try:
    resp = client.connected_accounts.list()
    items = getattr(resp, "items", resp)
    print(f"Discovered {len(items)} accounts from Composio.")
    for a in items:
        aid = getattr(a, "id", None) or (a.get("id") if isinstance(a, dict) else None)
        tk = getattr(a, "toolkit", None) or (a.get("toolkit") if isinstance(a, dict) else None)
        tk_slug = getattr(tk, "slug", tk) or (tk.get("slug") if isinstance(tk, dict) else tk)
        uid = getattr(a, "user_id", None) or (a.get("user_id") if isinstance(a, dict) else None)
        status = getattr(a, "status", None) or (a.get("status") if isinstance(a, dict) else None)
        if status == "ACTIVE" and tk_slug and aid:
            # Only set if not already locked or if matching personal channel
            tk_name = str(tk_slug).lower()
            if tk_name not in ACCOUNT_MAP:
                ACCOUNT_MAP[tk_name] = aid
            if uid:
                USER_ID = uid
    print("Active accounts mapped:", ACCOUNT_MAP)
    print("Active user_id:", USER_ID)
except Exception as e:
    print("Dynamic discovery warning (using static fallback):", e)

def execute_tool(slug, arguments, **kwargs):
    kwargs.setdefault("user_id", USER_ID)
    toolkit = TOOLKIT_MAP.get(slug)
    if toolkit and toolkit in ACCOUNT_MAP:
        kwargs.setdefault("connected_account_id", ACCOUNT_MAP[toolkit])
    kwargs["dangerously_skip_version_check"] = True
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

# Check for test email mode
test_email_only = os.environ.get("TEST_EMAIL_ONLY", "false").lower() == "true" or "--test-email" in sys.argv
if test_email_only:
    print("🧪 TEST MODE: Sending drop alert test email from GitHub Actions cloud runner...")
    try:
        email_res = execute_tool(
            slug="GMAIL_SEND_EMAIL",
            arguments={
                "recipient_email": "shakirrizwan01@gmail.com",
                "subject": "🧪 LIVE DROP ALERT (Cloud Test): Instagram Auto-Publisher",
                "body": """<h2>🎉 Cloud Runner Email Alert Verified!</h2>
<p>This test email confirms that your GitHub Actions cloud runner is working 100% autonomously in the cloud.</p>
<p><strong>Status:</strong> Cloud automation verified.</p>
<p>From now on, all scheduled drops will publish and send you this email alert on time, <strong>even if your PC is completely turned off</strong>!</p>
<p style="color: #d93025; font-size: 16px;">
👉 <strong>Action Required on Drops:</strong> Open Instagram and Facebook on your phone, find the new post, and tap <strong>Share ➔ Add to Story</strong>!
</p>""",
                "is_html": True
            }
        )
        print("Test email response:", email_res)
        print("Cloud email notification test PASSED!")
        sys.exit(0)
    except Exception as e:
        print("Error sending test email from cloud:", e)
        sys.exit(1)

SHEET_ID = "1_IJaznafMh7X7rmgQ1idHSptoULSr5enoewXk8NYjCY"

kolkata_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
now_ist = datetime.now(kolkata_tz)
today_str = now_ist.strftime("%Y-%m-%d")
time_str = now_ist.strftime("%H:%M")

print(f"Running Instagram Auto Publisher at {now_ist} (Date: {today_str}, Time: {time_str} IST)")

sheet_res = execute_tool(
    slug="GOOGLESHEETS_VALUES_GET",
    arguments={
        "spreadsheet_id": SHEET_ID,
        "range": "Sheet1!A2:W57"
    }
)
sheet_data = get_data(sheet_res)
rows = sheet_data.get("values", [])
print(f"Total rows fetched: {len(rows)}")

target_row = None
target_row_idx = None

for idx, row in enumerate(rows):
    post_date = row[2] if len(row) > 2 else ""
    post_time = row[4] if len(row) > 4 else ""
    ig_status = row[21] if len(row) > 21 else "pending"

    # Only publish if date is today and scheduled time has arrived (or backlog from past date)
    is_due = False
    if ig_status.strip().lower() == "pending":
        if post_date == today_str and time_str >= post_time:
            is_due = True
        elif post_date < today_str and post_date != "":
            is_due = True

    if is_due:
        target_row = row
        target_row_idx = idx + 2
        break

if not target_row:
    print(f"No pending Instagram post due for today ({today_str} {time_str} IST). Exiting cleanly.")
    sys.exit(0)

post_no = target_row[0]
title = target_row[7]
caption_ig = target_row[15]
first_comment = target_row[16] if len(target_row) > 16 else ""
drive_file_id = target_row[18]
fb_post_id = target_row[20] if len(target_row) > 20 else ""

print(f"Found post to publish! Row {target_row_idx}: Post {post_no} — '{title}'")

print(f"Fetching S3 download URL from Google Drive for file ID {drive_file_id}...")
drive_res = execute_tool(
    slug="GOOGLEDRIVE_DOWNLOAD_FILE",
    arguments={
        "fileId": drive_file_id
    }
)
drive_data = get_data(drive_res)
s3url = drive_data.get("downloaded_file_content", {}).get("s3url")
if not s3url:
    print(f"Error fetching download URL from Google Drive: {drive_res}")
    sys.exit(1)

print("Video download URL acquired successfully.")

print("Creating Instagram media container...")
container_res = execute_tool(
    slug="INSTAGRAM_POST_IG_USER_MEDIA",
    arguments={
        "ig_user_id": "28540742058917254",
        "video_url": s3url,
        "caption": caption_ig,
        "media_type": "REELS"
    }
)
container_data = get_data(container_res)
container_id = container_data.get("id")
if not container_id:
    print(f"Error creating Instagram media container: {container_res}")
    sys.exit(1)

print(f"Container created successfully. ID: {container_id}. Publishing...")

publish_res = execute_tool(
    slug="INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH",
    arguments={
        "ig_user_id": "28540742058917254",
        "creation_id": container_id,
        "max_wait_seconds": 180
    }
)
publish_data = get_data(publish_res)
ig_media_id = publish_data.get("id")
if not ig_media_id:
    print(f"Error publishing Instagram media: {publish_res}")
    sys.exit(1)

print(f"🎉 Successfully published to Instagram! Media ID: {ig_media_id}")

# Post first comment on Instagram Reel
if first_comment and first_comment.strip():
    print(f"Posting first comment to Instagram Reel {ig_media_id}...")
    try:
        clean_comment = first_comment.replace("[YouTube] (", "YouTube: ").replace(")", "")
        ig_comment_res = execute_tool(
            slug="INSTAGRAM_POST_IG_MEDIA_COMMENTS",
            arguments={
                "ig_media_id": str(ig_media_id),
                "message": clean_comment
            }
        )
        print("Instagram first comment posted successfully:", ig_comment_res)
    except Exception as e:
        print("Warning: Failed to post first comment to Instagram:", e)

# Post first comment on Facebook Post if live
if fb_post_id and fb_post_id.strip() and first_comment and first_comment.strip():
    print(f"Posting first comment to Facebook post {fb_post_id}...")
    try:
        target_fb_id = fb_post_id.strip()
        if "_" not in target_fb_id and not target_fb_id.startswith("202789806432686"):
            target_fb_id = f"202789806432686_{target_fb_id}"
        fb_comment_res = execute_tool(
            slug="FACEBOOK_CREATE_COMMENT",
            arguments={
                "object_id": target_fb_id,
                "message": first_comment
            }
        )
        print("Facebook first comment posted successfully:", fb_comment_res)
    except Exception as e:
        print("Warning: Failed to post first comment to Facebook:", e)

print(f"Updating Google Sheet Row {target_row_idx}...")
execute_tool(
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
    execute_tool(
        slug="GMAIL_SEND_EMAIL",
        arguments={
            "recipient_email": "shakirrizwan01@gmail.com",
            "subject": f"🎬 LIVE DROP & STORY ALERT: {title[:40]}",
            "body": f'''<h2>🎉 New Post is LIVE on Instagram & Facebook!</h2>
<p><strong>Track:</strong> {title}</p>
<p><strong>Instagram Media ID:</strong> {ig_media_id}</p>
<p style="color: #1a73e8; font-size: 15px;">
📌 <strong>First Comment Posted:</strong> The first comment with your YouTube & Spotify links was posted automatically to both Instagram and Facebook. Open the apps and tap <strong>Pin to top 📌</strong>.
</p>
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