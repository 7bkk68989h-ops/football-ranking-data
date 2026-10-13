# Vai buscar à Wikipédia em português as finais do Campeonato de Portugal e da Taça de Portugal
# (pedido do Pedro, 13 out. 2026): época ("1938–39"), vencedor, resultado, finalista e local.
# Grava pt_taca_finals.json. Correr a partir da raiz: python3 Tools/wikipedia/harvest_pt_taca.py
import json, os, re, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
from wp import tables, grid, fetch

PAGE = "Taça de Portugal"
TABLES = {"Finais do Campeonato de Portugal": "pt-campeonato", "Finais da Taça de Portugal": "pt-taca"}

def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", "", s)).strip()

def games(text):
    """"4 – 4 ap , 2 – 1" são dois jogos (final repetida); "2 – 2 ap, (3–1 gp)" é um jogo com penáltis."""
    pens = re.search(r"\(\s*(\d+)\s*[–-]\s*(\d+)\s*(?:gp|g\.p\.|pen)", text)
    out = [{"score": [int(a), int(b)], **({"extraTime": True} if ap else {})}
           for a, b, ap in re.findall(r"(\d+)\s*[–-]\s*(\d+)(\s*a\.?p\b)?", re.sub(r"\([^)]*\)", "", text))]
    if pens and out: out[-1]["penalties"] = [int(pens.group(1)), int(pens.group(2))]
    return out

out = {c: [] for c in TABLES.values()}
for t in tables(PAGE, "pt"):
    g = grid(t)
    comp = TABLES.get(g[0][0]["text"].strip()) if g and g[0] else None
    if comp is None: continue
    for r in g[2:]:
        if len(r) < 5 or not re.fullmatch(r"\d{4}[–-]\d{2}", r[0]["text"].strip()): continue
        ms = games(r[2]["text"])
        if not ms: continue   # época sem final ("Não disputada")
        season = r[0]["text"].strip().replace("-", "–")
        for m in ms: m["venue"] = clean(r[4]["text"])
        last = out[comp][-1] if out[comp] else None
        if last and last["season"] == season:   # segunda linha da mesma época: a finalíssima
            last["matches"] += ms; continue
        out[comp].append({"season": season, "winner": clean(r[1]["text"]), "winnerLink": r[1].get("link"),
                          "runnerUp": clean(r[3]["text"]), "runnerUpLink": r[3].get("link"), "matches": ms})
for comp, rows in out.items():
    print(f"{comp:14} {len(rows):3} finais | {rows[0]['season'] if rows else None} a {rows[-1]['season'] if rows else None} | "
          f"{sum(len(r['matches']) > 1 for r in rows)} repetidas")
if len(out["pt-campeonato"]) != 17 or len(out["pt-taca"]) < 86:
    sys.exit("Tabelas de finais da Taça de Portugal incompletas")   # a tarefa automática pára e não publica
page = fetch(PAGE, "pt")
json.dump({"lang": "pt", "page": page["title"], "revid": page["revid"], "finals": out},
          open(os.path.join(here, "pt_taca_finals.json"), "w"), ensure_ascii=False, indent=1)
