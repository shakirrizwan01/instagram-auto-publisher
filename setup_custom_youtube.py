import os
import sys
import json
import requests
from composio import Composio

COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY")
if not COMPOSIO_API_KEY:
    print("Missing COMPOSIO_API_KEY")
    sys.exit(1)

client = Composio(api_key=COMPOSIO_API_KEY)

# 1. Discover user_id
user_id = "pg-test-e25f369f-1415-44b6-9106-f2d6e6f0b793"
try:
    accs = client.connected_accounts.list()
    items = getattr(accs, "items", accs)
    for a in items:
        uid = getattr(a, "user_id", None) or (a.get("user_id") if isinstance(a, dict) else None)
        if uid:
            user_id = uid
            break
except Exception as e:
    print("Warning getting user_id:", e)

print(f"Using user_id: {user_id}")

CLIENT_ID = "715668673207-pthq2eqm33ct79e294cl1oiguh09835o.apps.googleusercontent.com"
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "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")

# 2. Check existing auth configs for YouTube
target_auth_config_id = None
try:
    resp = client.auth_configs.list(toolkit_slug="youtube")
    items = getattr(resp, "items", []) or (resp.get("items", []) if isinstance(resp, dict) else [])
    print(f"Found {len(items)} auth configs for YouTube:")
    for ac in items:
        acid = getattr(ac, "id", None) or (ac.get("id") if isinstance(ac, dict) else None)
        name = getattr(ac, "name", None) or (ac.get("name") if isinstance(ac, dict) else None)
        is_managed = getattr(ac, "is_composio_managed", None) or (ac.get("is_composio_managed") if isinstance(ac, dict) else None)
        print(f"  Auth Config ID: {acid} | Name: {name} | Managed: {is_managed}")
        if not is_managed:
            target_auth_config_id = acid
            print(f"--> Using existing custom auth config: {target_auth_config_id}")
except Exception as e:
    print("Warning listing auth configs:", e)

# 3. If no custom auth config exists, create it
if not target_auth_config_id:
    print("Creating new custom Auth Config for YouTube...")
    try:
        r = requests.post(
            "https://backend.composio.dev/api/v3/auth_configs",
            headers={"x-api-key": COMPOSIO_API_KEY, "Content-Type": "application/json"},
            json={
                "toolkit": {"slug": "youtube"},
                "auth_config": {
                    "name": "Antigravity YouTube Custom App",
                    "type": "use_custom_auth",
                    "authScheme": "OAUTH2",
                    "credentials": {
                        "client_id": CLIENT_ID,
                        "client_secret": CLIENT_SECRET
                    }
                }
            }
        )
        print("Create auth config status:", r.status_code, r.text)
        if r.status_code in [200, 201]:
            data = r.json()
            target_auth_config_id = data.get("auth_config", {}).get("id") or data.get("id")
            print(f"🎉 Created custom Auth Config: {target_auth_config_id}")
    except Exception as e:
        print(f"Error creating auth config via requests: {e}")

if not target_auth_config_id:
    print("❌ Failed to obtain target_auth_config_id")
    sys.exit(1)

# 4. Initiate connection request using the custom auth config!
print(f"Initiating connection with auth_config_id: {target_auth_config_id}...")
try:
    r = requests.post(
        "https://backend.composio.dev/api/v3/connected_accounts",
        headers={"x-api-key": COMPOSIO_API_KEY, "Content-Type": "application/json"},
        json={
            "user_id": user_id,
            "auth_config_id": target_auth_config_id
        }
    )
    print("Initiate response status:", r.status_code, r.text)
    res_json = r.json()
    redirect_url = res_json.get("redirect_url") or res_json.get("redirectUrl") or res_json.get("connection_data", {}).get("redirect_url")
    connection_id = res_json.get("id") or res_json.get("connected_account_id")
    print("\n" + "="*60)
    print(f"CUSTOM_AUTH_LINK: {redirect_url}")
    print(f"CONNECTION_ID: {connection_id}")
    print("="*60 + "\n")
except Exception as e:
    print(f"Error initiating connection: {e}")
    sys.exit(1)
