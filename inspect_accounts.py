import os
from composio import Composio

client = Composio(api_key=os.environ.get("COMPOSIO_API_KEY"))
print("Composio client initialized.")

USER_ID = "pg-test-e25f369f-1415-44b6-9106-f2d6e6f0b793"

try:
    resp = client.connected_accounts.list()
    items = getattr(resp, "items", resp)
    print(f"Total accounts found: {len(items)}")
    for a in items:
        aid = getattr(a, "id", None) or (a.get("id") if isinstance(a, dict) else None)
        tk = getattr(a, "toolkit", None) or (a.get("toolkit") if isinstance(a, dict) else None)
        tk_slug = getattr(tk, "slug", tk) or (tk.get("slug") if isinstance(tk, dict) else tk)
        uid = getattr(a, "user_id", None) or (a.get("user_id") if isinstance(a, dict) else None)
        status = getattr(a, "status", None) or (a.get("status") if isinstance(a, dict) else None)
        print(f"ACCOUNT: id={aid}, toolkit={tk_slug}, user_id={uid}, status={status}")
except Exception as e:
    print("Error listing accounts:", e)

print("\n--- Testing Instagram info ---")
for candidate in ["ca_dAL2HtP-8D0G", "instagram_ossify-requit"]:
    for test_uid in [USER_ID, None]:
        try:
            kwargs = {"dangerously_skip_version_check": True}
            if test_uid:
                kwargs["user_id"] = test_uid
            kwargs["connected_account_id"] = candidate
            res = client.tools.execute(slug="INSTAGRAM_GET_USER_INFO", arguments={"fields": "id,username,name"}, **kwargs)
            print(f"SUCCESS with candidate={candidate}, user_id={test_uid}: {res}")
        except Exception as err:
            print(f"FAILED with candidate={candidate}, user_id={test_uid}: {err}")
