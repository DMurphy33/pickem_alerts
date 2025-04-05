# Pick'em Alerts

This project is to help decide which team select for the daily pick'em in MLB 9 Innings. It will query the [Odds API](https://the-odds-api.com/) for all the upcoming games for the day and text you who has the best odds to win.

## Installation

```bash
pip install uv
git clone git@github.com:DMurphy33/pickem_alerts.git
cd pickem_alerts
uv sync
```

## Usage
You will need to have the following environment variables set for this script to work.

```bash
export ODDS_API_KEY="<your-key>"
export SENDER_EMAIL="<your-gmail>"
export RECIPIENT_EMAIL="<your-destination-email>"
```

For the `RECIPIENT_EMAIL` you can use a phone number instead by formatting it as an email in your phone provider's format. For example, for verizon it would be `1234567890@vtext.com`. You can find your provider's format [here](https://avtech.com/articles/138/list-of-email-to-sms-addresses/).

You will also need to have a file in the root directory of this repository called `credentials.json` that contains your [Google API](https://console.cloud.google.com/apis/credentials) client ID and client secret.

To run the script, simply run this command from the root directory of this repository.

```bash
uv run main.py
```