import os
from composio import Composio

client = Composio(api_key=os.environ.get("COMPOSIO_API_KEY"))
print("Composio client initialized.")

try:
    accs = client.connected_accounts.list()
    print(f"Total connected accounts: {len(accs)}")
    for a in accs:
        aid = getattr(a, "id", None)
        tk = getattr(a, "toolkit", None)
        uid = getattr(a, "user_id", None)
        status = getattr(a, "status", None)
        print(f"Account: id={aid}, toolkit={tk}, user_id={uid}, status={status}")
except Exception as e:
    print("Error listing connected accounts:", e)

try:
    if hasattr(client, "users"):
        users = client.users.list()
        print("Users list:", users)
except Exception as e:
    print("Error listing users:", e)
