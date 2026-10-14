import os
from composio import Composio

COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY")
client = Composio(api_key=COMPOSIO_API_KEY)

for aid in ["ca_1OmWac-CLp-J", "ca_pUUHcPX5WySk", "ca_dAL2HtP-8D0G"]:
    acc = client.connected_accounts.get(id=aid)
    d = acc.model_dump() if hasattr(acc, "model_dump") else (acc.dict() if hasattr(acc, "dict") else vars(acc))
    print(f"ACCOUNT {aid}: keys={list(d.keys())}")
    for k in ["app_name", "appName", "toolkit", "user_info", "data", "integration_id", "auth_config_id"]:
        if k in d:
            print(f"  {k} = {d[k]}")
