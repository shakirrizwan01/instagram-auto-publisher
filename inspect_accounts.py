import os
from composio import Composio

client = Composio(api_key=os.environ.get("COMPOSIO_API_KEY"))

try:
    resp = client.connected_accounts.list()
    items = getattr(resp, "items", resp)
    print(f"Total accounts: {len(items)}")
    for a in items:
        aid = getattr(a, "id", None) or (a.get("id") if isinstance(a, dict) else None)
        tk = getattr(a, "toolkit", None) or (a.get("toolkit") if isinstance(a, dict) else None)
        tk_slug = getattr(tk, "slug", tk) or (tk.get("slug") if isinstance(tk, dict) else tk)
        uid = getattr(a, "user_id", None) or (a.get("user_id") if isinstance(a, dict) else None)
        status = getattr(a, "status", None) or (a.get("status") if isinstance(a, dict) else None)
        user_info = getattr(a, "user_info", {}) or (a.get("user_info", {}) if isinstance(a, dict) else {})
        print(f"ID: {aid} | Toolkit: {tk_slug} | User: {uid} | Status: {status} | Info: {user_info}")
except Exception as e:
    print("Error:", e)
