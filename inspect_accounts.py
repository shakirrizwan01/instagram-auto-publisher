import os
from composio import Composio

client = Composio(api_key=os.environ.get("COMPOSIO_API_KEY"))
print("Composio client initialized.")

try:
    resp = client.connected_accounts.list()
    items = getattr(resp, "items", resp)
    print(f"Items found: {len(items)}")
    for a in items:
        aid = getattr(a, "id", None) or (a.get("id") if isinstance(a, dict) else None)
        tk = getattr(a, "toolkit", None) or (a.get("toolkit") if isinstance(a, dict) else None)
        uid = getattr(a, "user_id", None) or (a.get("user_id") if isinstance(a, dict) else None)
        status = getattr(a, "status", None) or (a.get("status") if isinstance(a, dict) else None)
        print(f"ACCOUNT: id={aid}, user_id={uid}, toolkit={tk}, status={status}")
except Exception as e:
    print("Error:", e)
