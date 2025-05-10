import base64
import io
import json
import os
import logging
from datetime import date, datetime, time
from pytz import timezone
from time import sleep

import pandas as pd
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

TOKEN_FILE = "token.json"


def authenticate_with_google() -> Credentials:
    """Authenticate with credentials.json or token.json if it exists.

    Returns
    -------
    Credentials
        Credentials for the Google API.
    """
    logging.info("Authenticating with Google API...")
    creds = None

    # Check if token.json file exists
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        logging.info("Loaded credentials from token file.")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logging.info("Refreshed expired credentials.")
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secrets.json",
                scopes=SCOPES,
            )
            creds = flow.run_local_server(port=0)  # Open a browser for authentication
            logging.info("Authenticated via browser flow.")

        # Save the credentials for the next run
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
            logging.info("Saved new credentials to token file.")

    return creds


def create_email_message(sender: str, to: str, body: str) -> dict:
    """Create an email message in MIME format.

    Parameters
    ----------
    sender: str
        The email address of the message sender.
    to: str
        The email address of the message recipient.
    body: str
        The message content.

    Returns
    -------
    dict
        Dictionary containing the message in utf-8
    """
    logging.debug(f"Creating email from {sender} to {to}.")
    message = MIMEMultipart()
    message["to"] = to
    message["from"] = sender
    msg = MIMEText(body)
    message.attach(msg)
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw_message}


def send_email(service: Resource, sender: str, to: str, body: str) -> None:
    """Send an email using Gmail API.

    Parameters
    ----------
    service: Resource
        Resource authenticated with Google's API to send messages.
    sender: str
        The sender of the message.
    to: str
        The recipient of the message.
    body: str
        The content of the message.
    """
    try:
        message = create_email_message(sender, to, body)
        service.users().messages().send(userId="me", body=message).execute()
        logging.info(f"Email sent to {to}.")
    except HttpError as error:
        logging.error(f"Failed to send email: {error}")


def get_spreads(current_date: date, key=str) -> pd.DataFrame:
    """Get the spreads for all MLB games for a particular date.

    Parameters
    ----------
    current_date: date
        The date to get the MLB spreads for.
    key: str
        Key to use for the request to The Odds API.

    Returns
    -------
    pd.DataFrame
        DataFrame containing the name of each MLB team who plays on `current_date` along with their moneyline odds and
        spread.
    """
    logging.info(f"Fetching spreads for {current_date.isoformat()}...")
    date_format = "%Y-%m-%dT%H:%M:%SZ"
    start = datetime.combine(current_date, time(10, 0, 0)).astimezone(timezone("UTC")).strftime(date_format)
    end = datetime.combine(current_date, time(23, 59, 59)).astimezone(timezone("UTC")).strftime(date_format)

    params = {
        "api_key": key,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
        "bookmakers": "fanduel",
        "commenceTimeFrom": start,
        "commenceTimeTo": end,
    }
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/"
    res = requests.get(url, params=params)
    odds = json.load(io.BytesIO(res.content))

    logging.debug(f"Received odds data: {json.dumps(odds, indent=2)[:500]}...")  # Truncated for brevity

    spreads = pd.DataFrame.from_records(
        [team for game in odds for team in game["bookmakers"][0]["markets"][0]["outcomes"]]
    )
    logging.info(f"Fetched {len(spreads)} spread records.")
    return spreads


def main() -> None:
    """Send the best MLB odds as an email every day."""
    sender_email = os.environ["SENDER_EMAIL"]
    recipient_email = os.environ["RECIPIENT_EMAIL"]
    key = os.environ["ODDS_API_KEY"]

    new_day = True
    while True:
        try:
            if new_day:
                # Get best bet for the current date
                current_date = datetime.now(timezone("US/Eastern")).date()
                logging.info(f"Starting routine for {current_date}...")

                spreads = get_spreads(current_date, key)

                if spreads.empty:
                    logging.warning("No spread data found for today.")
                else:
                    try:
                        best_bet = spreads.loc[spreads.price.idxmin()]
                        logging.info(f"Best bet selected: {best_bet.to_dict()}")
                    except Exception as e:
                        logging.error(f"Error selecting best bet: {e}")
                        best_bet = None

                    if best_bet is not None:
                        # Authenticate with google and send best bet message
                        creds = authenticate_with_google()
                        service = build("gmail", "v1", credentials=creds)
                        send_email(service, sender_email, recipient_email, body=str(best_bet))

            new_day = current_date < datetime.now(timezone("US/Eastern")).date()
            sleep(60)

        except Exception as e:
            logging.exception(f"Unexpected error in main loop: {e}")
            sleep(60)


if __name__ == "__main__":
    main()
