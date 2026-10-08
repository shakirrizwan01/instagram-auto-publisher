# Instagram Auto Publisher (Cloud Cron)

Automated 24/7 cloud runner for @riz1shakir daily music catalog releases.

### How it Works:
- Runs automatically via GitHub Actions at 18:00 and 19:30 IST daily.
- Reads scheduled drops from Google Sheet.
- Pulls video from Google Drive and publishes to Instagram.
- Updates Google Sheet with published status and media ID.
- Sends instant drop alert to Gmail.

### Setup Requirement:
Add your Composio API key as a repository secret:
1. Go to **Settings ➔ Secrets and variables ➔ Actions**.
2. Click **New repository secret**.
3. Name: `COMPOSIO_API_KEY`
4. Value: Paste your API key from [Composio Settings](https://app.composio.dev/settings/api-keys).
