"""End-to-end check of the calculator UI over the Chrome DevTools Protocol.

Drives real clicks on every tab and the language toggle, captures console
errors and uncaught exceptions, and prints the rendered card titles so the
i18n wiring can be confirmed rather than assumed.
"""
import asyncio
import json
import subprocess
import sys
import urllib.request

import websockets

URL = "http://127.0.0.1:8011/"
PORT = 9333

ERRORS = []


async def main():
    proc = subprocess.Popen([
        "google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
        "--remote-debugging-port=%d" % PORT, "--user-data-dir=/tmp/cdpprof",
        "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    ws_url = None
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % PORT) as r:
                targets = json.load(r)
            pages = [t for t in targets if t.get("type") == "page"]
            if pages:
                ws_url = pages[0]["webSocketDebuggerUrl"]
                break
        except Exception:
            pass
        await asyncio.sleep(0.25)
    if not ws_url:
        print("FAIL: chrome did not expose a page target")
        proc.kill()
        return 1

    try:
        async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
            counter = [0]

            async def send(method, params=None):
                counter[0] += 1
                mid = counter[0]
                await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
                    if msg.get("id") == mid:
                        return msg.get("result", {})
                    _handle_event(msg)

            def _handle_event(msg):
                m = msg.get("method")
                if m == "Runtime.exceptionThrown":
                    d = msg["params"]["exceptionDetails"]
                    ERRORS.append("exception: " + (d.get("exception", {}).get("description") or d.get("text", "")))
                elif m == "Runtime.consoleAPICalled" and msg["params"]["type"] in ("error", "warning"):
                    parts = [a.get("value") or a.get("description", "") for a in msg["params"]["args"]]
                    ERRORS.append("%s: %s" % (msg["params"]["type"], " ".join(str(p) for p in parts)))
                elif m == "Log.entryAdded":
                    e = msg["params"]["entry"]
                    if e.get("level") in ("error", "warning"):
                        ERRORS.append("%s: %s %s" % (e["level"], e.get("text", ""), e.get("url", "")))

            async def ev(expr):
                r = await send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
                return r.get("result", {}).get("value")

            await send("Runtime.enable")
            await send("Log.enable")
            await send("Page.enable")
            await send("Page.navigate", {"url": URL})
            await asyncio.sleep(3)

            async def read_tab(tab):
                await ev('document.querySelector(\'[data-tab="%s"]\').click()' % tab)
                await asyncio.sleep(1.2)
                return await ev(
                    "(function(){var p=document.getElementById('panel-%s');"
                    "return {cards:[].map.call(p.querySelectorAll('.cards h4'),function(h){return h.textContent}),"
                    "err:(p.querySelector('.err')||{}).textContent||''};})()" % tab
                )

            ok = True
            print("== language: id (default) ==")
            print("tabs:", await ev("[].map.call(document.querySelectorAll('.tab'),function(b){return b.textContent})"))
            for tab in ("Invest", "Portfolio", "Trading", "Simulate"):
                res = await read_tab(tab)
                print("%-10s cards=%s err=%r" % (tab, res["cards"], res["err"]))
                if not res["cards"]:
                    ok = False
                    print("   FAIL: no cards rendered")

            print("\n== switch to en ==")
            await ev("var s=document.querySelector('#lang');s.value='en';s.dispatchEvent(new Event('change'));")
            await asyncio.sleep(1.0)
            print("tabs:", await ev("[].map.call(document.querySelectorAll('.tab'),function(b){return b.textContent})"))
            for tab in ("Invest", "Trading", "Simulate"):
                res = await read_tab(tab)
                print("%-10s cards=%s" % (tab, res["cards"]))
                for c in res["cards"]:
                    if "." in c and c.split(".")[0] in ("card", "label", "note"):
                        ok = False
                        print("   FAIL: untranslated key leaked:", c)

            print("\n== switch back to id, currency IDR ==")
            await ev("var l=document.querySelector('#lang');l.value='id';l.dispatchEvent(new Event('change'));"
                     "var c=document.querySelector('#currency');c.value='IDR';c.dispatchEvent(new Event('change'));")
            await asyncio.sleep(1.2)
            res = await read_tab("Invest")
            print("Invest cards:", res["cards"])

            print("\n== console errors ==")
            real = [e for e in ERRORS if "favicon" not in e.lower()]
            print("\n".join(real) if real else "(none)")
            if real:
                ok = False
            print("\nRESULT:", "PASS" if ok else "FAIL")
            return 0 if ok else 1
    finally:
        proc.kill()


sys.exit(asyncio.run(main()))
