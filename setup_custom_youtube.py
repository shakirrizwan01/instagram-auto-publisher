import os
import sys
from composio import Composio

COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY")
if not COMPOSIO_API_KEY:
    print("Missing COMPOSIO_API_KEY")
    sys.exit(1)

client = Composio(api_key=COMPOSIO_API_KEY)
accs = client.connected_accounts.list()
items = getattr(accs, "items", accs)
print(f"Total connected accounts: {len(items)}")
for a in items:
    cid = getattr(a, "id", None) or a.get("id")
    app = getattr(a, "app_name", None) or getattr(a, "appName", None) or a.get("appName")
    status = getattr(a, "status", None) or a.get("status")
    auth_config_id = getattr(a, "auth_config_id", None) or getattr(a, "authConfigId", None) or a.get("authConfigId")
    user_id = getattr(a, "user_id", None) or getattr(a, "userId", None) or a.get("userId")
    print(f"ID: {cid} | App: {app} | Status: {status} | AuthConfig: {auth_config_id} | User: {user_id}")
