#!/usr/bin/env python3

import time
import requests

# --- CONFIGURE THESE ---
PAGE_URL      = "https://leaderinmespeechcontest.us.launchpad6.com/contest12/entry/7228"
VOTE_URL      = "https://leaderinmespeechcontest.us.launchpad6.com/contest12/vote"
TOTAL_RUNS    = 50000
PAUSE_BETWEEN = 0    # seconds between votes

# Your JSON payload
PAYLOAD = {
    "entryId": "7228",
    "media_id": "01b47ca353ae874a",
    "data": {
        "vote_email": "guest",
        "schedule_id": "9",
        "visitor_id": ""
    }
}

# Headers to mimic an XHR from a browser
HEADERS = {
    "User-Agent":       "Mozilla/5.0 (X11; Linux x86_64)",
    "Accept":           "application/json, text/javascript, */*; q=0.01",
    "Content-Type":     "application/json; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer":          PAGE_URL,
    "Origin":           "https://leaderinmespeechcontest.us.launchpad6.com",
}

def vote_direct(runs=TOTAL_RUNS, pause=PAUSE_BETWEEN):
    for i in range(1, runs + 1):
        # start a fresh session (clears cookies)
        session = requests.Session()

        # (Optional) prime session / get cookies or CSRF token
        # resp = session.get(PAGE_URL, headers=HEADERS, timeout=5)
        # if you need a token:
        #   token = extract_from(resp.text)
        #   PAYLOAD["csrf_token"] = token

        try:
            resp = session.post(VOTE_URL, json=PAYLOAD, headers=HEADERS, timeout=5)
            status = resp.status_code
            ok     = resp.ok
            print(f"[{i:03d}/{runs:03d}] POST → {status} {'✔' if ok else '✖'}")
        except Exception as e:
            print(f"[{i:03d}/{runs:03d}] Exception:", e)

        time.sleep(pause)

if __name__ == "__main__":
    vote_direct()