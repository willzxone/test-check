#!/usr/bin/env python3
import asyncio
import uuid
import random

import aiohttp
import uvloop

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
PAGE_URL    = "https://leaderinmespeechcontest.us.launchpad6.com/contest12/entry/7228"
VOTE_URL    = "https://leaderinmespeechcontest.us.launchpad6.com/contest12/vote"
TOTAL_RUNS  = 50000
CONCURRENCY = 10     # how many requests in flight at once
PAUSE       = 1      # seconds to sleep after each vote

# Webshare “backconnect” rotating proxy endpoint
ROTATE_PROXY = "http://wnnkfnzz-rotate:6dpzirmjctl7@p.webshare.io:80/"

# Pool of User-Agents to randomize per request
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
]

# Base headers for the vote POST
HEADERS_BASE = {
    "Accept":           "application/json, text/javascript, */*; q=0.01",
    "Content-Type":     "application/json; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer":          PAGE_URL,
    "Origin":           "https://leaderinmespeechcontest.us.launchpad6.com",
}

# ─── ASYNC VOTE TASK ────────────────────────────────────────────────────────────
async def vote(session: aiohttp.ClientSession, idx: int):
    # clear cookies to simulate a fresh session each time
    session.cookie_jar.clear()

    # build randomized payload
    payload = {
        "entryId": "7228",
        "media_id": "01b47ca353ae874a",
        "data": {
            "vote_email":  "guest",
            "schedule_id": "9",
            "visitor_id":  "",
        }
    }

    # copy and randomize User-Agent
    headers = HEADERS_BASE.copy()
    headers["User-Agent"] = random.choice(USER_AGENTS)

    try:
        async with session.post(
            VOTE_URL,
            json=payload,
            headers=headers,
            proxy=ROTATE_PROXY,
            timeout=10
        ) as resp:
            ok = (resp.status == 200)
            mark = "✔" if ok else "✖"
            print(f"[{idx:05d}/{TOTAL_RUNS:05d}] {resp.status} {mark}")
    except Exception as e:
        print(f"[{idx:05d}/{TOTAL_RUNS:05d}] ✖ {e!r}")

    # small delay to avoid hammering
    await asyncio.sleep(PAUSE)

# ─── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    # install uvloop for improved performance
    uvloop.install()

    sem = asyncio.Semaphore(CONCURRENCY)
    # disable SSL verification for ProxyScrape (optional)
    connector = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i in range(1, TOTAL_RUNS + 1):
            await sem.acquire()
            task = asyncio.create_task(vote(session, i))
            task.add_done_callback(lambda t: sem.release())
            tasks.append(task)

        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())