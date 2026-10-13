import os
import sys
import json
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
    d = a.model_dump() if hasattr(a, "model_dump") else (a.dict() if hasattr(a, "dict") else vars(a))
    cid = d.get("id")
    app = d.get("app_name") or d.get("appName")
    status = d.get("status")
    auth_config_id = d.get("auth_config_id") or d.get("authConfigId")
    user_id = d.get("user_id") or d.get("userId")
    print(f"ACCOUNT_INFO: id={cid} app={app} status={status} authConfig={auth_config_id} user={user_id}")
