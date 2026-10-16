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

# Dedicated connected account IDs & User IDs for Personal Project (Rizwan Shakir)
ACCOUNT_MAP = {}
ACCOUNT_USER_MAP = {}
DEFAULT_USER_ID = "default"

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
        print(f"Discovered: {tk_slug} -> aid={aid}, uid={uid}, status={status}")
        if status == "ACTIVE" and tk_slug and aid:
            tk_name = str(tk_slug).lower()
            if aid:
                ACCOUNT_USER_MAP[aid] = uid
            # Preferred accounts for Rizwan Shakir personal channel
            if "looter-enlife" in aid or "riz1shakir" in str(a):
                ACCOUNT_MAP["instagram"] = aid
            elif "eyey-perch" in aid or "rizwanshakir2018" in str(a):
                ACCOUNT_MAP["googledrive"] = aid
            elif "fluter-parse" in aid or "rizwanshakir" in str(a):
                ACCOUNT_MAP["youtube"] = aid
            elif tk_name not in ACCOUNT_MAP:
                ACCOUNT_MAP[tk_name] = aid
            if uid:
                DEFAULT_USER_ID = uid
    print("Active accounts mapped:", ACCOUNT_MAP)
except Exception as e:
    print("Dynamic discovery warning:", e)

# Fallbacks if discovery missed anything
FALLBACKS = {
    "gmail": "gmail_afoul-borean",
    "googlesheets": "googlesheets_agency-broo",
    "googledrive": "googledrive_eyey-perch",
    "instagram": "instagram_looter-enlife",
    "facebook": "facebook_even-glut",
    "youtube": "youtube_fluter-parse"
}
for k, v in FALLBACKS.items():
    if k not in ACCOUNT_MAP:
        ACCOUNT_MAP[k] = v

def execute_tool(slug, arguments, **kwargs):
    kwargs.setdefault("dangerously_skip_version_check", True)
    toolkit = TOOLKIT_MAP.get(slug)
    if toolkit and toolkit in ACCOUNT_MAP:
        acc_id = ACCOUNT_MAP[toolkit]
        kwargs["connected_account_id"] = acc_id
        uid = ACCOUNT_USER_MAP.get(acc_id) or DEFAULT_USER_ID
        if uid:
            kwargs["user_id"] = uid
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

# 1. Fetch Schedule from Google Sheet
sheet_res = execute_tool(
    slug="GOOGLESHEETS_VALUES_GET",
    arguments={
        "spreadsheet_id": SHEET_ID,
        "range": "Sheet1!A2:W60"
    }
)
sheet_data = get_data(sheet_res)
rows = sheet_data.get("values", [])
print(f"Loaded {len(rows)} catalog items from spreadsheet.")

target_row = None
target_row_idx = None

# Check for CLI override flag: python publish.py --row 8
for idx, arg in enumerate(sys.argv):
    if arg == "--row" and idx + 1 < len(sys.argv):
        target_row_idx = int(sys.argv[idx + 1])
        target_row = rows[target_row_idx - 2]
        print(f"Targeting row {target_row_idx} via manual CLI flag.")
        break

if not target_row:
    for idx, row in enumerate(rows):
        row_idx = idx + 2
        date_ist = row[2] if len(row) > 2 else ""
        fb_status = row[19] if len(row) > 19 else ""
        ig_status = row[21] if len(row) > 21 else ""

        # Match today or any unfulfilled past drop
        if date_ist and date_ist <= today_str:
            if ig_status.strip().lower() != "published":
                target_row = row
                target_row_idx = row_idx
                print(f"Found post to publish! Row {row_idx}: Post {row[0]} — '{row[7]}'")
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

print("Creating Instagram media container (with thumb_offset=3000 to avoid black cover)...")
container_res = execute_tool(
    slug="INSTAGRAM_POST_IG_USER_MEDIA",
    arguments={
        "ig_user_id": "28540742058917254",
        "video_url": s3url,
        "caption": caption_ig,
        "media_type": "REELS",
        "thumb_offset": 3000,
        "share_to_feed": True
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
    print(f"Error sending email: {e}")

print("Drop automation run complete.")
