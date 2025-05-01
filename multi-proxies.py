#!/usr/bin/env python3
import asyncio
import itertools
import uuid
import random
import pathlib

import aiohttp
import uvloop

# ─── USE UVLOOP FOR MAX THROUGHPUT ───────────────────────────────────────────────
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
PAGE_URL    = "https://leaderinmespeechcontest.us.launchpad6.com/contest12/entry/7228"
VOTE_URL    = "https://leaderinmespeechcontest.us.launchpad6.com/contest12/vote"
TOTAL_RUNS  = 50000
WORKERS     = 50      # number of concurrent “worker” tasks
PAUSE       = 1       # seconds to sleep after each vote in each worker

HEADERS_BASE = {
    "Accept":           "application/json, text/javascript, */*; q=0.01",
    "Content-Type":     "application/json; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer":          PAGE_URL,
    "Origin":           "https://leaderinmespeechcontest.us.launchpad6.com",
}

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
]

# ─── LOAD PROXIES ───────────────────────────────────────────────────────────────
proxy_file = pathlib.Path("proxies.txt")
if not proxy_file.exists():
    raise RuntimeError("proxies.txt not found—one proxy per line")

raw = [line.strip() for line in proxy_file.read_text().splitlines() if line.strip()]
PROXIES = ["http://" + p if "://" not in p else p for p in raw]

# ─── WORKER ─────────────────────────────────────────────────────────────────────
async def worker(name: str, proxy: str, queue: asyncio.Queue):
    # Each worker has its own session + connector (ssl disabled for proxies)
    conn = aiohttp.TCPConnector(ssl=False)
    session = aiohttp.ClientSession(connector=conn)

    while True:
        idx = await queue.get()
        # clear cookies so every vote looks fresh
        session.cookie_jar.clear()

        # randomize payload
        payload = {
            "entryId": "7228",
            "media_id": "01b47ca353ae874a",
            "data": {
                "vote_email":  f"guest+{uuid.uuid4().hex[:8]}",
                "schedule_id": "9",
                "visitor_id":  uuid.uuid4().hex,
            }
        }
        # rotate User-Agent
        headers = HEADERS_BASE.copy()
        headers["User-Agent"] = random.choice(USER_AGENTS)

        try:
            async with session.post(
                VOTE_URL,
                json=payload,
                headers=headers,
                timeout=5,
                proxy=proxy
            ) as resp:
                ok = resp.status == 200
                print(f"[{name} | {idx:05d}/{TOTAL_RUNS}] → {resp.status} {'✔' if ok else '✖'} via {proxy}")
        except Exception as e:
            print(f"[{name} | {idx:05d}/{TOTAL_RUNS}] ✖ {e} via {proxy}")

        await asyncio.sleep(PAUSE)
        queue.task_done()

    # on shutdown
    await session.close()

# ─── MAIN ───────────────────────────────────────────────────────────────────────
async def main():
    queue = asyncio.Queue()

    # enqueue all vote indices
    for i in range(1, TOTAL_RUNS + 1):
        queue.put_nowait(i)

    # cycle proxies to assign one to each worker
    proxy_cycle = itertools.cycle(PROXIES) if PROXIES else itertools.cycle([None])
    workers = []

    for n in range(1, WORKERS + 1):
        proxy = next(proxy_cycle)
        name  = f"W{n:02d}"
        w = asyncio.create_task(worker(name, proxy, queue))
        workers.append(w)

    # wait until queue is empty
    await queue.join()

    # cancel workers
    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())