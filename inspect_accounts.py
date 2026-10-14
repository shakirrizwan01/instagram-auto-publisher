import os
from composio import Composio

client = Composio(api_key=os.environ.get("COMPOSIO_API_KEY"))
USER_ID = "pg-test-e25f369f-1415-44b6-9106-f2d6e6f0b793"

print("connected_accounts methods:", dir(client.connected_accounts))

try:
    link_info = client.connected_accounts.initiate(
        toolkit="instagram",
        user_id=USER_ID
    )
    print("INITIATE LINK INFO:", link_info)
except Exception as e:
    print("Initiate error:", e)
