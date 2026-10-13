import os
import sys
from composio import Composio

COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY")
if not COMPOSIO_API_KEY:
    print("Missing COMPOSIO_API_KEY")
    sys.exit(1)

client = Composio(api_key=COMPOSIO_API_KEY)

yt_title = "Does The Universe Only Exist When You Look? 👁️ #Shorts"
yt_description = """Does The Universe Only Exist When You Look? 👁️ #Shorts

The famous double-slit experiment showed that subatomic particles behave like waves of pure probability—until an observer measures them. The moment they are observed, the wave collapses into physical reality. Does this mean physical reality only exists when observed?

Subscribe to Paradox Vault for more quantum mysteries.

#Shorts #QuantumPhysics #DoubleSlitExperiment #SimulationTheory #Universe #ParadoxVault"""

tags = ["quantum physics", "double slit experiment", "quantum observer effect", "simulation hypothesis", "does reality exist", "universe mysteries", "deep science shorts", "quantum paradox"]

s3key = "977053/googledrive/GOOGLEDRIVE_DOWNLOAD_FILE/response/f295cf3f2246af3ce304a4d532677fc6"

upload_args = {
    "videoFile": {
        "name": "Does_the_universe_only_exist_when_we_look_FINAL.mp4",
        "mimetype": "video/mp4",
        "s3key": s3key
    },
    "title": yt_title,
    "description": yt_description,
    "tags": tags,
    "categoryId": "28",
    "privacyStatus": "public",
    "madeForKids": False
}

user_id = "pg-test-e25f369f-1415-44b6-9106-f2d6e6f0b793"

print(f"Executing with user_id={user_id} and connected_account_id=ca_1OmWac-CLp-J...")
try:
    res = client.tools.execute(
        slug="YOUTUBE_MULTIPART_UPLOAD_VIDEO",
        arguments=upload_args,
        user_id=user_id,
        connected_account_id="ca_1OmWac-CLp-J",
        dangerously_skip_version_check=True
    )
    print("SUCCESS RESULT:", res)
except Exception as e:
    print("UPLOAD EXCEPTION:", e)
