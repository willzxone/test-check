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
CONCURRENCY  = 5      # in-flight at once
PAUSE        = 1       # per-task sleep after each vote, in seconds

# raw proxies in host:port:user:pass format
_RAW_PROXIES = [
    "38.154.227.167:5868:wnnkfnzz:6dpzirmjctl7",
    "45.127.248.127:5128:wnnkfnzz:6dpzirmjctl7",
    "198.23.239.134:6540:wnnkfnzz:6dpzirmjctl7",
    "38.153.152.244:9594:wnnkfnzz:6dpzirmjctl7",
    "86.38.234.176:6630:wnnkfnzz:6dpzirmjctl7",
    "173.211.0.148:6641:wnnkfnzz:6dpzirmjctl7",
    "216.10.27.159:6837:wnnkfnzz:6dpzirmjctl7",
    "154.36.110.199:6853:wnnkfnzz:6dpzirmjctl7",
    "45.151.162.198:6600:wnnkfnzz:6dpzirmjctl7",
    "188.74.210.21:6100:wnnkfnzz:6dpzirmjctl7",
]

# build proper proxy URLs with auth embedded
PROXIES = []
for line in _RAW_PROXIES:
    host, port, user, pwd = line.split(":", 3)
    PROXIES.append(f"http://{user}:{pwd}@{host}:{port}")

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

    # build a fresh payload
    payload = {
        "entryId": "7228",
        "media_id": "01b47ca353ae874a",
        "data": {
            "vote_email":   f"guest+{uuid.uuid4().hex[:8]}",
            "schedule_id":  "9",
            "visitor_id":   uuid.uuid4().hex,
        }
    }

    # rotate User-Agent
    headers = HEADERS_BASE.copy()
    headers["User-Agent"] = random.choice(USER_AGENTS)

    # pick a proxy if you have any
    proxy = random.choice(PROXIES) if PROXIES else None

    try:
        async with session.post(
            VOTE_URL,
            json=payload,
            headers=headers,
            timeout=5,
            proxy=proxy
        ) as resp:
            ok = resp.status == 200
            print(f"[{idx:05d}/{TOTAL_RUNS:05d}] → {resp.status} {'✔' if ok else '✖'} via {proxy}")
    except Exception as e:
        print(f"[{idx:05d}/{TOTAL_RUNS:05d}] Exception: {e} via {proxy}")

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