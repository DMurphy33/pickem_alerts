import base64
import io
import json
import os
from datetime import datetime
from pytz import timezone
from time import sleep

import pandas as pd
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Define the required scope
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# Path to store token (if you're saving it locally)
TOKEN_FILE = 'token.json'

def authenticate_with_client_id_and_secret():
    """Authenticate using client ID and client secret from environment variables."""
    creds = None

    # Check if token.json file exists (it stores user's access and refresh tokens)
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Create the OAuth flow using the client ID and secret from the environment variables
            flow = InstalledAppFlow.from_client_info(
                client_info={
                    'installed': {
                        'client_id': os.environ["GOOGLE_CLIENT_ID"],
                        'client_secret': os.environ["GOOGLE_CLIENT_SECRET"],
                        'redirect_uris': ['http://localhost'],
                        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                        'token_uri': 'https://oauth2.googleapis.com/token',
                    }
                },
                scopes=SCOPES
            )
            creds = flow.run_local_server(port=0)  # Open a browser for authentication

        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return creds


def main():
    key = os.environ["ODDS_API_KEY"]
    current_date = datetime.now(timezone('US/Eastern')).date()
    new_day = True
    while True:
        if new_day:
            params = {
                'api_key': key,
                'regions': 'us',
                'markets': 'h2h,spreads',
                'oddsFormat': 'american',
                'bookmakers': 'fanduel',
            }
            url = 'https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/'
            res = requests.get(url, params=params)
            odds = json.load(io.BytesIO(res.content))
            spreads = pd.DataFrame.from_records([team for game in odds for team in game['bookmakers'][0]['markets'][0]['outcomes']])
            print(spreads.loc[spreads.point.idxmin()])
        
        new_day = current_date < datetime.now(timezone('US/Eastern')).date()
        sleep(60)


if __name__ == "__main__":
    main()
