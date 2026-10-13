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

target_auth_config_id = "ac_HRZnOyymlE43" # The created custom auth config for Antigravity

print(f"Initiating connection with auth_config_id: {target_auth_config_id}...")

# Format 1: SDK initiate
try:
    req = client.connected_accounts.initiate(user_id=user_id, auth_config_id=target_auth_config_id)
    redir = getattr(req, "redirect_url", None) or getattr(req, "redirectUrl", None)
    cid = getattr(req, "id", None)
    if redir:
        print("\n" + "="*60)
        print(f"CUSTOM_AUTH_LINK: {redir}")
        print(f"CONNECTION_ID: {cid}")
        print("="*60 + "\n")
        sys.exit(0)
except Exception as e:
    print(f"SDK initiate notice: {e}")

# Format 2: Direct REST with proper nested body
payload = {
    "auth_config": {"id": target_auth_config_id},
    "connection": {"user_id": user_id}
}
r = requests.post(
    "https://backend.composio.dev/api/v3/connected_accounts",
    headers={"x-api-key": COMPOSIO_API_KEY, "Content-Type": "application/json"},
    json=payload
)
print("Initiate response status:", r.status_code, r.text)
if r.status_code in [200, 201]:
    res_json = r.json()
    redirect_url = res_json.get("redirect_url") or res_json.get("redirectUrl") or (res_json.get("connection") or {}).get("redirect_url") or (res_json.get("connection_data") or {}).get("redirect_url")
    connection_id = res_json.get("id") or (res_json.get("connection") or {}).get("id")
    print("\n" + "="*60)
    print(f"CUSTOM_AUTH_LINK: {redirect_url}")
    print(f"CONNECTION_ID: {connection_id}")
    print("="*60 + "\n")
