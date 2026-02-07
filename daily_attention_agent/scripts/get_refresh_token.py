from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": "PASTE_NEW_CLIENT_ID_HERE",
            "client_secret": "PASTE_NEW_CLIENT_SECRET_HERE",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    },
    SCOPES,
)

creds = flow.run_local_server(
    port=0,
    prompt="consent",
    access_type="offline",
)

print("\n=== REFRESH TOKEN (COPY IMMEDIATELY) ===\n")
print(creds.refresh_token)
