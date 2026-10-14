import os
import sys
from composio import Composio

COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY")
client = Composio(api_key=COMPOSIO_API_KEY)

accs = client.connected_accounts.list()
items = getattr(accs, "items", accs)
for a in items:
    d = a.model_dump() if hasattr(a, "model_dump") else (a.dict() if hasattr(a, "dict") else vars(a))
    aid = d.get("id")
    appName = d.get("app_name") or d.get("appName")
    status = d.get("status")
    print(f"ACCOUNT_DETAIL: id={aid} app={appName} status={status}")
