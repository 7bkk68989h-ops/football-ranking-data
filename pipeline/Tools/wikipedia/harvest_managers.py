# Vai buscar à Wikipédia o treinador campeão de cada época dos campeonatos. Grava wikipedia_managers.json.
# Correr a partir da raiz: python3 Tools/wikipedia/harvest_managers.py
import json, os, re, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
from wp import tables, grid, fetch

# competição -> (língua da Wikipédia, página)
PAGES = {
 "pt-liga": ("pt", "Primeira Liga"), "es-liga": ("en", "List of La Liga winning managers"),
 "gb-liga": ("en", "List of English football championship–winning managers"), "it-liga": ("en", "List of Serie A winning managers"),
 "fr-liga": ("en", "List of Ligue 1 winning managers"), "br-liga": ("en", "List of Campeonato Brasileiro Série A winning managers"),
 "uy-liga": ("en", "Uruguayan Primera División"),
}
SEASON = re.compile(r"^(season|época|year)$", re.I)
MANAGER = re.compile(r"(winning )?(manager|treinador|coach)", re.I)
CLUB = re.compile(r"^(club|winners?|vencedor|champions?)", re.I)

def clean(s):
    s = re.sub(r"\[[^\]]*\]", "", s); s = re.sub(r"\s*\(\d+\)\s*", " ", s)
    return re.sub(r"\s+", " ", s).strip(" ,*†‡—-")

out = {}
for comp, (lang, title) in PAGES.items():
    best = []
    for t in tables(title, lang):
        g = grid(t)
        if len(g) < 10: continue
        head = [c["text"].strip() for c in g[0]]
        si = next((i for i, h in enumerate(head) if SEASON.match(h)), None)
        mi = next((i for i, h in enumerate(head) if MANAGER.search(h)), None)
        ci = next((i for i, h in enumerate(head) if CLUB.match(h)), None)
        if None in (si, mi, ci): continue
        rows = []
        for r in g[1:]:
            if len(r) <= max(si, mi, ci): continue
            m = re.match(r"\d{4}(?:\s*[–-]\s*\d{2,4})?", r[si]["text"])
            manager, club = clean(r[mi]["text"]), clean(r[ci]["text"])
            if not m or not manager or not club or manager == club or re.search(r"\d{4}|not held|suspended|cancel", manager, re.I): continue
            rows.append({"season": m.group().replace(" ", "").replace("-", "–"), "club": club, "manager": manager})
        if len(rows) > len(best): best = rows
    page = fetch(title, lang)
    out[comp] = {"lang": lang, "page": page["title"], "revid": page["revid"], "rows": best}
    print(f"{comp:8} {len(best):3} épocas | {best[0] if best else None} | {best[-1] if best else None}")
short = [c for c, v in out.items() if len(v["rows"]) < 50]
if short: sys.exit(f"Tabelas de treinadores incompletas: {short}")   # a tarefa automática pára e não publica
json.dump(out, open(os.path.join(here, "wikipedia_managers.json"), "w"), ensure_ascii=False, indent=1)
