# FIX — allowed-entries selection + auto-remap to certified firing spec + measure cache + quiet registry
from pathlib import Path

p = Path("src/scan.py")
c = p.read_text(encoding="utf-8")
if "_measured = {}" not in c:
    c = c.replace('_tick = {"ts": 0, "data": {}}', '_tick = {"ts": 0, "data": {}}\n_measured = {}', 1)
c = c.replace("def risk_filter(decisions):", "def risk_filter(decisions, trig=None):", 1)
old = '''        menu = symbol_menu(sym)
        sid = d.get("setup_id")
        if not menu or sid not in [m["spec"] for m in menu]:
            try:
                row = st.db.execute("SELECT spec FROM strategies WHERE id=?", (sid,)).fetchone()
                if row:
                    sp = json.loads(row[0])
                    from src.backtest import run_backtest
                    res, hit = run_backtest(st, sp, sym, sp.get("tf", "1h"))
                    from src.bootstrap import phase_registry
                    phase_registry(st)
                    logger.info(f"measured {sid} on {sym}: eligible={res.get('eligible')}")
            except Exception as e:
                logger.warning(f"measure failed {sid}/{sym}: {e}")
            continue'''
new = '''        menu = symbol_menu(sym)
        sid = d.get("setup_id")
        if not menu or sid not in [m["spec"] for m in menu]:
            alt = next((t["spec"] for t in (trig or [])
                        if t["symbol"] == sym and t["side"] == sd), None)
            if alt and alt in [m["spec"] for m in menu]:
                logger.info(f"remap {sym}: {sid} -> {alt} (certified+firing)")
                sid = alt
                d["setup_id"] = alt
            else:
                key = (sid, sym)
                if time.time() - _measured.get(key, 0) < 3600:
                    continue
                _measured[key] = time.time()
                try:
                    row = st.db.execute("SELECT spec FROM strategies WHERE id=?", (sid,)).fetchone()
                    if row:
                        sp = json.loads(row[0])
                        from src.backtest import run_backtest
                        res, hit = run_backtest(st, sp, sym, sp.get("tf", "1h"))
                        from src.bootstrap import phase_registry
                        phase_registry(st, verbose=False)
                        logger.info(f"measured {sid} on {sym}: eligible={res.get('eligible')}")
                except Exception as e:
                    logger.warning(f"measure failed {sid}/{sym}: {e}")
                continue'''
if old in c:
    c = c.replace(old, new, 1)
    p.write_text(c, encoding="utf-8")
    print("scan: remap + measure cache + quiet registry")
else:
    print("scan: certification block anchor miss")

p = Path("src/bootstrap.py")
c = p.read_text(encoding="utf-8")
c = c.replace("def phase_registry(store):", "def phase_registry(store, verbose=True):", 1)
c = c.replace('    print(f"P3 registry: validated={nv} rejected={sum(1 for r in reg if r[\'status\']==\'rejected\')}")',
              '    if verbose:\n        print(f"P3 registry: validated={nv} rejected={sum(1 for r in reg if r[\'status\']==\'rejected\')}")', 1)
c = c.replace("    for r in reg[:12]:", "    for r in (reg[:12] if verbose else []):", 1)
p.write_text(c, encoding="utf-8")
print("bootstrap: phase_registry verbose flag")

p = Path("src/ai_brain.py")
c = p.read_text(encoding="utf-8")
c = c.replace("TRIGGERS (radar, full market):",
              "ALLOWED LIVE ENTRIES (symbol | spec | side):\n{allowed}\nTRIGGERS (radar, full market):", 1)
c = c.replace('.replace("{triggers}", triggers_block)',
              '.replace("{allowed}", allowed_block)\n                  .replace("{triggers}", triggers_block)', 1)
old_mk = '        market_block = "\\n".join(mk[:60]) if mk else "(no live prices)"'
new_mk = ('        allowed_block = "\\n".join(f"- {t[\'symbol\']} | {t[\'spec\']} | {t[\'side\']}" for t in trig) or "(none)"\n'
              + old_mk)
if old_mk in c:
    c = c.replace(old_mk, new_mk, 1)
c = c.replace("decisions = scan.risk_filter(decisions)", "decisions = scan.risk_filter(decisions, trig)", 1)
p.write_text(c, encoding="utf-8")
print("ai_brain: allowed-entries block + trig passed to risk_filter")