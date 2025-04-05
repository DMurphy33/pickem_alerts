import base64
import io
import json
import os
from datetime import datetime, time
from pytz import timezone
from time import sleep

import pandas as pd
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

TOKEN_FILE = "token.json"


def authenticate_with_google():
    """Authenticate with credentials.json or token.json if it exists."""
    creds = None

    # Check if token.json file exists (it stores user's access and refresh tokens)
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secrets.json",
                scopes=SCOPES,
            )
            creds = flow.run_local_server(port=0)  # Open a browser for authentication

        # Save the credentials for the next run
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def create_email_message(sender, to, body):
    """Create an email message in MIME format."""
    message = MIMEMultipart()
    message["to"] = to
    message["from"] = sender
    msg = MIMEText(body)
    message.attach(msg)
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw_message}


def send_email(service, sender, to, body):
    """Send an email using Gmail API."""
    try:
        message = create_email_message(sender, to, body)
        service.users().messages().send(userId="me", body=message).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")


def get_spreads(date):
    key = os.environ["ODDS_API_KEY"]
    date_format = "%Y-%m-%dT%H:%M:%SZ"
    start = datetime.combine(date, time(0, 0, 0)).astimezone(timezone("UTC")).strftime(date_format)
    end = datetime.combine(date, time(23, 59, 59)).astimezone(timezone("UTC")).strftime(date_format)

    params = {
        "api_key": key,
        "regions": "us",
        "markets": "h2h,spreads",
        "oddsFormat": "american",
        "bookmakers": "fanduel",
        "commenceTimeFrom": start,
        "commenceTimeTo": end,
    }
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/"
    res = requests.get(url, params=params)
    odds = json.load(io.BytesIO(res.content))
    spreads = pd.DataFrame.from_records(
        [team for game in odds for team in game["bookmakers"][0]["markets"][0]["outcomes"]]
    )
    return spreads


def main():
    service = build("gmail", "v1", credentials=creds)
    sender_email = os.environ["SENDER_EMAIL"]
    recipient_email = os.environ["RECIPIENT_EMAIL"]

    new_day = True
    while True:
        if new_day:
            current_date = datetime.now(timezone("US/Eastern")).date()
            creds = authenticate_with_google()
            spreads = get_spreads(current_date)
            best_bet = spreads.loc[spreads.price.idxmin()]
            send_email(service, sender_email, recipient_email, body=str(best_bet))

        new_day = current_date < datetime.now(timezone("US/Eastern")).date()
        sleep(60)


if __name__ == "__main__":
    main()
