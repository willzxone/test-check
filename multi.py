#!/usr/bin/env python3
import asyncio
import uuid
import random

import aiohttp
import uvloop

# ─── CONFIG ────────────────────────────────────────────────────────────────────
PAGE_URL    = "https://leaderinmespeechcontest.us.launchpad6.com/contest12/entry/7228"
VOTE_URL    = "https://leaderinmespeechcontest.us.launchpad6.com/contest12/vote"
TOTAL_RUNS  = 50000
CONCURRENCY = 10      # how many requests in flight at once
PAUSE       = 1       # seconds to sleep after each vote

# Webshare rotating backconnect proxy endpoint
ROTATE_PROXY = "http://wnnkfnzz-rotate:6dpzirmjctl7@p.webshare.io:80/"

# Pool of User-Agents to randomize per request
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
]

# Base headers for the vote POST (we'll override UA each time)
HEADERS_BASE = {
    "Accept":           "application/json, text/javascript, */*; q=0.01",
    "Content-Type":     "application/json; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer":          PAGE_URL,
    "Origin":           "https://leaderinmespeechcontest.us.launchpad6.com",
}

# ─── SINGLE VOTE TASK ──────────────────────────────────────────────────────────
async def vote(idx: int):
    # Every vote gets a brand-new session (fresh cookies + connections)
    conn    = aiohttp.TCPConnector(ssl=False)
    jar     = aiohttp.DummyCookieJar()          # drop any cookies set
    session = aiohttp.ClientSession(connector=conn, cookie_jar=jar)

    try:
        # Build the fixed payload
        payload = {
            "entryId": "7228",
            "media_id": "01b47ca353ae874a",
            "data": {
                "vote_email":  f"guest+{uuid.uuid4().hex[:8]}",
                "schedule_id": "9",
                "visitor_id":  uuid.uuid4().hex,
            }
        }

        # Copy headers and randomize only the User-Agent
        headers = HEADERS_BASE.copy()
        headers["User-Agent"] = random.choice(USER_AGENTS)

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

    finally:
        # Tear down the session (drops any pooled connections)
        await session.close()

    # Pause to throttle
    await asyncio.sleep(PAUSE)

# ─── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    uvloop.install()
    sem   = asyncio.Semaphore(CONCURRENCY)
    tasks = []

    for i in range(1, TOTAL_RUNS + 1):
        await sem.acquire()
        task = asyncio.create_task(vote(i))
        task.add_done_callback(lambda _: sem.release())
        tasks.append(task)

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())