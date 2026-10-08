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
from harvest_lib import find, PICK, split_rows
# competições extra (outros países), com a página encontrada por discover.py
_extra = os.path.join(here, "pages_extra.json")
if os.path.exists(_extra): PAGES.update(json.load(open(_extra)))

out = {}; problems = []
for comp, title in PAGES.items():
    try:
        best = find(title, PICK.get(comp))
    except SystemExit as e:
        problems.append(f"{comp}: {e}"); continue
    if not best: problems.append(f"{comp}: sem tabela em «{title}»"); continue
    _, heading, rows = best
    problems += split_rows(comp, rows)
    page = fetch(title)
    bad = [r["club"] for r in rows if not r["years"]]
    out[comp] = {"page": page["title"], "revid": page["revid"], "rows": rows}
    print(f"{comp:14} {len(rows):3} clubes {sum(r['titles'] for r in rows):4} títulos | «{heading[:28]}» | topo: {rows[0]['club']} {rows[0]['titles']} | sem anos: {len(bad)} {bad[:3]}")
print("PROBLEMAS:", problems)
if not problems: json.dump(out, open(os.path.join(here, "wikipedia_titles.json"), "w"), ensure_ascii=False, indent=1)
if problems: sys.exit(1)   # a tarefa automática pára e não publica
