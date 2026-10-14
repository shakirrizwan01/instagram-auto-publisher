import os
import inspect
from composio import Composio

client = Composio(api_key=os.environ.get("COMPOSIO_API_KEY"))
USER_ID = "pg-test-e25f369f-1415-44b6-9106-f2d6e6f0b793"

print("initiate signature:", inspect.signature(client.connected_accounts.initiate))
try:
    link = client.connected_accounts.initiate(
        app_name="instagram",
        user_id=USER_ID
    )
    print("LINK WITH app_name:", link)
except Exception as e:
    print("Error app_name:", e)
