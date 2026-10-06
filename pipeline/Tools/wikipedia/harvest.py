# Vai buscar à Wikipédia (tabelas "performance by club") os títulos por clube e os anos,
# para as competições que o Wikidata não tem ou tem incompletas. Grava wikipedia_titles.json.
# Correr a partir da raiz: python3 Tools/wikipedia/harvest.py
import json, os, re, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
from wp import tables, grid, fetch

# id da competição na app -> página da Wikipédia em inglês
PAGES = {
 "it-liga": "List of Italian football champions", "it-coppa": "Coppa Italia",
 "pt-liga": "List of Portuguese football champions", "pt-taca": "Taça de Portugal", "pt-supertaca": "Supertaça Cândido de Oliveira",
 "pt-tacaliga": "Taça da Liga", "pt-campeonato": "Taça de Portugal",
 "es-liga": "List of Spanish football champions", "es-copa": "Copa del Rey", "es-super": "Supercopa de España",
 "gb-liga": "List of English football champions", "gb-fa": "FA Cup", "gb-lc": "EFL Cup",
 "de-liga": "List of German football champions", "de-pokal": "DFB-Pokal",
 "fr-liga": "List of French football champions", "fr-coupe": "Coupe de France",
 "nl-liga": "List of Dutch football champions", "nl-knvb": "KNVB Cup",
 "ar-liga": "List of Argentine Primera División champions", "br-liga": "List of Brazilian football champions", "br-copa": "Copa do Brasil",
 "uy-liga": "Uruguayan Primera División", "eg-liga": "Egyptian Premier League",
 "uefa-cl": "List of European Cup and UEFA Champions League finals", "uefa-el": "UEFA Cup and Europa League records and statistics",
 "uefa-cwc": "UEFA Cup Winners' Cup", "uefa-ecl": "UEFA Conference League", "uefa-super": "UEFA Super Cup",
 "conmebol-lib": "Copa Libertadores", "conmebol-sud": "Copa Sudamericana", "caf-cl": "CAF Champions League", "afc-cl": "AFC Champions League Elite",
 "fifa-cwc": "FIFA Club World Cup",
}
CLUB = re.compile(r"^(club|team|clubs|teams)$", re.I)
COUNT = re.compile(r"^(winners?|titles?|title\(s\)|champions?|won|wins|championships?)$", re.I)
YEARS = re.compile(r"(winning|won|champion|title).*(years?|seasons?)|(years?|seasons?).*(won|winning|champion)|^(winning )?(seasons|years)$", re.I)

# Quando a página tem várias tabelas "por clube", diz qual: parte do título da secção, ou "menor".
PICK = {"fr-liga": "club in professional era", "pt-campeonato": "menor"}

# Títulos retirados que a página ainda lista entre os anos (não contam no total).
REVOKED = {"Juventus": ("2004–05",), "Torino": ("1926–27",)}

def find(title, pick=None):
    best = None
    for t in tables(title):
        if pick and pick != "menor" and pick not in t["heading"].lower(): continue
        g = grid(t)
        if len(g) < 3: continue
        for hi in range(min(2, len(g))):
            head = [re.sub(r"^vte\s+", "", c["text"].strip()) for c in g[hi]]
            ci = next((i for i, h in enumerate(head) if CLUB.match(h)), None)
            ni = next((i for i, h in enumerate(head) if COUNT.match(h)), None)
            yi = next((i for i, h in enumerate(head) if YEARS.search(h) and "runner" not in h.lower() and "second" not in h.lower()), None)
            if ci is None or ni is None: continue
            rows = []
            for r in g[hi + 1:]:
                if len(r) <= max(ci, ni): continue
                m = re.match(r"\d+", r[ni]["text"])
                name = re.sub(r"\s*\((?!\d{4}\))[^()]*\)\s*$", "", r[ci]["text"]).strip(" *†‡")
                if not m or not name or int(m.group()) == 0: continue
                years = r[yi]["text"] if yi is not None and len(r) > yi else ""
                ys = [y.strip() for y in re.findall(r"\d{4}(?:\s*[–-]\s*\d{2,4})?", years)]
                rows.append({"club": name, "titles": int(m.group()), "years": ys, "country": (r[ci]["flags"] or [None])[0]})
            for x in rows:
                x["years"] = [y for y in x["years"] if y.replace("-", "–") not in REVOKED.get(x["club"], ())]
                if len(x["years"]) != x["titles"]: x["years"] = []   # coluna com outros anos misturados
            score = sum(x["titles"] for x in rows) + (1000 if yi is not None else 0)
            if pick == "menor": score = -score
            if rows and (best is None or score > best[0]): best = (score, t["heading"].strip(), rows)
    return best

out = {}; problems = []
for comp, title in PAGES.items():
    try:
        best = find(title, PICK.get(comp))
    except SystemExit as e:
        problems.append(f"{comp}: {e}"); continue
    if not best: problems.append(f"{comp}: sem tabela em «{title}»"); continue
    _, heading, rows = best
    page = fetch(title)
    bad = [r["club"] for r in rows if not r["years"]]
    out[comp] = {"page": page["title"], "revid": page["revid"], "rows": rows}
    print(f"{comp:14} {len(rows):3} clubes {sum(r['titles'] for r in rows):4} títulos | «{heading[:28]}» | topo: {rows[0]['club']} {rows[0]['titles']} | sem anos: {len(bad)} {bad[:3]}")
print("PROBLEMAS:", problems)
if not problems: json.dump(out, open(os.path.join(here, "wikipedia_titles.json"), "w"), ensure_ascii=False, indent=1)
if problems: sys.exit(1)   # a tarefa automática pára e não publica
