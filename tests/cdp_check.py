"""End-to-end check of the calculator UI over the Chrome DevTools Protocol.

Drives real clicks on every tab and the language toggle, captures console
errors and uncaught exceptions, and prints the rendered card titles so the
i18n wiring can be confirmed rather than assumed.
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

import websockets

# Point at any running instance: PORTO_URL=http://127.0.0.1:9000/ ...
URL = os.environ.get("PORTO_URL", "http://127.0.0.1:8000/")
PORT = int(os.environ.get("PORTO_CDP_PORT", "9333"))

ERRORS = []


async def main():
    # A unique profile per run. Reusing one lets localStorage leak between runs,
    # which made the "default language" observation depend on the previous run.
    profile = tempfile.mkdtemp(prefix="porto-cdp-")
    proc = subprocess.Popen([
        "google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
        "--remote-debugging-port=%d" % PORT,
        "--user-data-dir=" + profile,
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
            default_tabs = await ev("[].map.call(document.querySelectorAll('.tab'),function(b){return b.textContent})")
            print("tabs:", default_tabs)
            # A fresh profile must start in Indonesian. If this shows English,
            # either the default regressed or the profile was not clean.
            if default_tabs != ["Investasi", "Portofolio", "Trading", "Simulasi"]:
                ok = False
                print("   FAIL: default language is not Indonesian:", default_tabs)
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

            print("\n== Simulate: manual inputs drive the Monte Carlo table ==")
            await ev("var s=document.querySelector('#lang');s.value='en';s.dispatchEvent(new Event('change'));")
            await asyncio.sleep(0.6)
            await ev('document.querySelector(\'[data-tab="Simulate"]\').click()')
            await asyncio.sleep(1.0)
            # A small, fast run so the check stays quick.
            await ev("document.querySelector('#sim-sims').value='200';"
                     "document.querySelector('#sim-trades').value='50';")
            await ev("document.querySelector('#sim-sims').dispatchEvent(new Event('input'));")
            await asyncio.sleep(2.5)
            sim = await ev(
                "(function(){var p=document.getElementById('panel-Simulate');"
                "return {heads:[].map.call(p.querySelectorAll('#sim-table thead th'),"
                "function(h){return h.textContent}),"
                "row:(p.querySelector('#sim-table tbody tr')||{}).textContent||'',"
                "rows:p.querySelectorAll('#sim-table tbody tr').length,"
                "cards:[].map.call(p.querySelectorAll('.cards h4'),function(h){return h.textContent}),"
                "err:(p.querySelector('.err')||{}).textContent||''};})()"
            )
            print("columns:", sim["heads"])
            print("cards:", sim["cards"])
            print("rows:", sim["rows"], "first row:", sim["row"])
            print("err:", repr(sim["err"]))
            want_cols = ["WR", "Mean net", "P(success)", "P(busted)", "Expectancy", "Sharpe"]
            if sim["heads"] != want_cols:
                ok = False
                print("   FAIL: columns were", sim["heads"])
            want_cards = ["Best by net", "Ruin risk", "Position size"]
            if sim["cards"] != want_cards:
                ok = False
                print("   FAIL: cards were", sim["cards"])
            if "P(success)" not in sim["heads"] or "P(busted)" not in sim["heads"]:
                ok = False
                print("   FAIL: P(success)/P(busted) columns missing")
            if sim["rows"] < 1 or "%" not in sim["row"]:
                ok = False
                print("   FAIL: no simulation rows rendered")
            if sim["err"]:
                ok = False

            print("\n== Simulate: changing risk per trade changes the result ==")
            before = await ev("document.querySelector('#sim-table tbody tr').textContent")
            await ev("document.querySelector('#sim-risk-pct').value='10';"
                     "document.querySelector('#sim-risk-pct').dispatchEvent(new Event('input'));")
            await asyncio.sleep(2.5)
            after = await ev("document.querySelector('#sim-table tbody tr').textContent")
            print("before:", before[:70])
            print("after: ", after[:70])
            if before == after:
                ok = False
                print("   FAIL: risk per trade had no effect on the results")
            await ev("document.querySelector('#sim-risk-pct').value='1';"
                     "document.querySelector('#sim-risk-pct').dispatchEvent(new Event('input'));")
            await asyncio.sleep(2.0)

            print("\n== switch back to id, currency IDR ==")
            await ev("var l=document.querySelector('#lang');l.value='id';l.dispatchEvent(new Event('change'));"
                     "var c=document.querySelector('#currency');c.value='IDR';c.dispatchEvent(new Event('change'));")
            await asyncio.sleep(1.2)
            res = await read_tab("Invest")
            print("Invest cards:", res["cards"])

            print("\n== persistence: write inputs, reload, expect them restored ==")
            # 500/month over 24 months at 12% (annuity-due) must recompute to
            # exactly 13621.6, so a stale default cannot masquerade as a restore.
            await ev(
                "localStorage.setItem('porto-calculator.inputs.v1', JSON.stringify({"
                "lang:'en',currency:'USD','dca-monthly':'500','dca-months':'24',"
                "'cagr-return':'150','cagr-years':'5','dca-roi':'12'}));"
            )
            await send("Page.reload", {})
            await asyncio.sleep(3)
            state = await ev(
                "(function(){return {"
                "lang:document.querySelector('#lang').value,"
                "currency:document.querySelector('#currency').value,"
                "tab:document.querySelector('.tab.is-active').textContent,"
                "fv:(document.querySelector('#invest-cards .big.b')||{}).textContent||''};})()"
            )
            print("restored:", state)
            for field, want in (("lang", "en"), ("currency", "USD"), ("tab", "Invest")):
                if state.get(field) != want:
                    ok = False
                    print("   FAIL: %s restored as %r, expected %r" % (field, state.get(field), want))
            if "13,621.6" not in state.get("fv", ""):
                ok = False
                print("   FAIL: recomputed future value was %r, expected 13,621.6" % state.get("fv"))

            print("\n== console errors ==")
            real = [e for e in ERRORS if "favicon" not in e.lower()]
            print("\n".join(real) if real else "(none)")
            if real:
                ok = False
            print("\nRESULT:", "PASS" if ok else "FAIL")
            return 0 if ok else 1
    finally:
        proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


sys.exit(asyncio.run(main()))
