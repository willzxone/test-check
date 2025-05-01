#!/usr/bin/env python3
import asyncio
import ssl
import uuid
import random
import aiohttp
import certifi
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# ─── CONFIG ────────────────────────────────────────────────────────────────────
PAGE_URL     = "https://leaderinmespeechcontest.us.launchpad6.com/contest12/entry/7228"
VOTE_URL     = "https://leaderinmespeechcontest.us.launchpad6.com/contest12/vote"
TOTAL_RUNS   = 50000
CONCURRENCY  = 10       # in-flight at once
PAUSE        = 1        # pause after each vote
FAIL_LIMIT   = 3        # retire proxy after this many fails
RETRIES      = 2        # retries per vote
PROXY_API    = (
    "https://api.proxyscrape.com/v2/"
    "?request=displayproxies"
    "&protocol=http"
    "&timeout=10000"
    "&country=all"
    "&ssl=all"
    "&anonymity=all"
)
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
ssl_ctx = ssl.create_default_context(cafile=certifi.where())

# ─── PROXY POOL ────────────────────────────────────────────────────────────────
class ProxyPool:
    def __init__(self):
        self.proxies = []
        self.fails = {}
        self.lock = asyncio.Lock()

    async def refresh(self):
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_ctx)) as s:
            r = await s.get(PROXY_API, timeout=10)
            lines = (await r.text()).splitlines()[:100]
        async with self.lock:
            self.proxies = [f"http://{ln.strip()}" for ln in lines if ln.strip()]
            self.fails = {p: 0 for p in self.proxies}
        print(f"🔄 Loaded {len(self.proxies)} proxies")

    async def get(self):
        async with self.lock:
            if not self.proxies:
                await self.refresh()
            return random.choice(self.proxies)

    async def report(self, proxy, success):
        async with self.lock:
            if not success:
                self.fails[proxy] = self.fails.get(proxy, 0) + 1
                if self.fails[proxy] >= FAIL_LIMIT:
                    self.proxies.remove(proxy)
                    print(f"❌ Retired {proxy}")
            else:
                self.fails[proxy] = 0

# ─── VOTE WITH RETRIES ──────────────────────────────────────────────────────────
async def vote_once(pool: ProxyPool, session, idx):
    for attempt in range(1, RETRIES + 2):  # initial + retries
        proxy = await pool.get()
        session.cookie_jar.clear()
        payload = {
            "entryId": "7228",
            "media_id": "01b47ca353ae874a",
            "data": {
                "vote_email": f"guest+{uuid.uuid4().hex[:8]}",
                "schedule_id": "9",
                "visitor_id": uuid.uuid4().hex,
            }
        }
        headers = HEADERS_BASE.copy()
        headers["User-Agent"] = random.choice(USER_AGENTS)
        try:
            async with session.post(
                VOTE_URL, json=payload, headers=headers,
                timeout=5, proxy=proxy
            ) as resp:
                ok = resp.status == 200
                await pool.report(proxy, ok)
                mark = "✔" if ok else "✖"
                print(f"[{idx:05d}] {resp.status} {mark} via {proxy}")
                if ok:
                    break
        except Exception as e:
            await pool.report(proxy, False)
            print(f"[{idx:05d}] ✖ {e!r} via {proxy}")
        # on fail, retry with a new proxy
    await asyncio.sleep(PAUSE)

# ─── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    pool = ProxyPool()
    await pool.refresh()

    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(ssl=ssl_ctx)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i in range(1, TOTAL_RUNS + 1):
            await sem.acquire()
            t = asyncio.create_task(
                vote_once(pool, session, i)
            )
            t.add_done_callback(lambda _: sem.release())
            tasks.append(t)
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())