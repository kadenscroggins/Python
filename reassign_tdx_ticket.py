import requests
import json
import time

# Authentication link
AUTH_URL = "https://<Domain>.teamdynamix.com/TDWebApi/api/auth/loginadmin"

# Load API keys from file AdminTokenParameters.json
with open('AdminTokenParameters.json') as keyfile:
    AdminTokenParameters = json.load(keyfile)

# Get authentication token from TDX API with API keys
token = requests.post(AUTH_URL, AdminTokenParameters)
token = str(token.content)[2:-1] # Strip 2 characters on left (b') and character on right (') from auth token
token = 'Bearer ' + token # TDX API wants the token to be prefaced with 'Bearer '

# Headers for API calls, including Content-Type and auth token
headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Authorization": token
}

# Load ticket numbers from file
ids = []
with open("ids.csv") as idfile:
    for line in idfile:
        ids.append(line.rstrip())

# Patch to set new requestor
patch = [{"op": "replace", "path": "/RequestorUid", "value": "<RequestorUid>"}]

# Patch all tickets from list
for id in ids:
    patch_url = f'https://<Domain>.teamdynamix.com/TDWebApi/api/<Application ID>/tickets/{id}?notifyNewResponsible=false'
    requests.patch(patch_url, json=patch, headers=headers)
    print(f'Patched {id}')
    time.sleep(1.5) # Avoid rate limit of 60 calls per 60 seconds per IP
