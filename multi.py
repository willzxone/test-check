#!/usr/bin/env python3
import asyncio
import ssl
import uuid
import random

import aiohttp
import certifi
import uvloop

# ─── Use uvloop for best performance ────────────────────────────────────────────
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# ─── CONFIG ────────────────────────────────────────────────────────────────────
PAGE_URL     = "https://leaderinmespeechcontest.us.launchpad6.com/contest12/entry/7228"
VOTE_URL     = "https://leaderinmespeechcontest.us.launchpad6.com/contest12/vote"
TOTAL_RUNS   = 50000
CONCURRENCY  = 10      # in-flight at once
PAUSE        = 1       # per-task sleep after each vote, in seconds

# If you have HTTP proxies, put them here:
PROXIES = [
    # "http://user:pass@1.2.3.4:8080",
    # "http://user:pass@5.6.7.8:3128",
]

# A small pool of User-Agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
]

HEADERS_BASE = {
    "Accept":           "application/json, text/javascript, */*; q=0.01",
    "Content-Type":     "application/json; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer":          PAGE_URL,
    "Origin":           "https://leaderinmespeechcontest.us.launchpad6.com",
}

# ─── SSL CONTEXT ────────────────────────────────────────────────────────────────
ssl_context = ssl.create_default_context(cafile=certifi.where())

# ─── SINGLE VOTE TASK ───────────────────────────────────────────────────────────
async def vote(session: aiohttp.ClientSession, idx: int):
    # wipe local cookies
    session.cookie_jar.clear()

    # build a fresh payload with a random visitor_id (and optional random email)
    payload = {
        "entryId": "7228",
        "media_id": "01b47ca353ae874a",
        "data": {
            "vote_email":   f"guest+{uuid.uuid4().hex[:8]}",  # randomize email
            "schedule_id":  "9",
            "visitor_id":   uuid.uuid4().hex,                # random visitor_id
        }
    }

    # rotate User-Agent
    headers = HEADERS_BASE.copy()
    headers["User-Agent"] = random.choice(USER_AGENTS)

    # pick a proxy if you have any
    proxy = random.choice(PROXIES) if PROXIES else None

    try:
        async with session.post(VOTE_URL, json=payload, headers=headers,
                                timeout=5, proxy=proxy) as resp:
            ok = resp.status == 200
            print(f"[{idx:05d}/{TOTAL_RUNS:05d}] → {resp.status} {'✔' if ok else '✖'}")
    except Exception as e:
        print(f"[{idx:05d}/{TOTAL_RUNS:05d}] Exception: {e}")

    if PAUSE:
        await asyncio.sleep(PAUSE)

# ─── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(ssl=ssl_context)

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