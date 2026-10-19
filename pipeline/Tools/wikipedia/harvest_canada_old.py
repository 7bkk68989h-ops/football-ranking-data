# Competições extintas do Canadá (pedido do Pedro, 13 out. 2026), que não têm tabela "por clube" na Wikipédia:
# o campeão de cada edição lê-se do resumo das épocas (CSL, 1987–92) ou da ficha da página (CPSL, 1983).
# Devolve linhas no formato de harvest.py (clube, títulos, anos, ligação), que o merge trata como as outras.
# Campeão = o vencedor dos play-offs (MITA Cup; na CPSL, o campeão da ficha), como a North Star Cup na CPL.
import os, re, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
from wp import tables, grid, fetch

PAGES = {"ca-csl": "Canadian Soccer League (1987–1992)", "ca-cpsl": "Canadian Professional Soccer League (1983)"}

def _rows(champions):
    """champions: [(ano, nome, ligação)] -> linhas por clube, do que mais ganhou para o que menos."""
    by = {}
    for year, name, link in champions:
        r = by.setdefault(name, {"club": name, "titles": 0, "years": [], "country": None, "link": link})
        r["titles"] += 1; r["years"].append(year)
    return sorted(by.values(), key=lambda r: (-r["titles"], r["years"][0]))

def csl():
    out = []
    for t in tables(PAGES["ca-csl"]):
        if t["heading"].strip() != "Season summary": continue
        g = grid(t); head = [c["text"] for c in g[0]]
        wi = next(i for i, h in enumerate(head) if re.search(r"playoff champions", h, re.I))
        for r in g[1:]:
            y = re.fullmatch(r"\d{4}", r[0]["text"].strip())
            if y and r[wi]["text"].strip(): out.append((y.group(), r[wi]["text"].strip(), r[wi].get("link")))
    return _rows(out)

def cpsl():
    for t in tables(PAGES["ca-cpsl"]):
        info = {r[0]["text"]: r[1] for r in grid(t) if len(r) == 2}
        if "Champions" in info and "Season" in info:
            return _rows([(info["Season"]["text"].strip(), info["Champions"]["text"].strip(), info["Champions"].get("link"))])
    return []

def harvest():
    """comp -> {"page", "revid", "rows"}; falha se uma das páginas já não tem o que se espera."""
    out = {}
    for comp, rows in (("ca-csl", csl()), ("ca-cpsl", cpsl())):
        if not rows: raise SystemExit(f"{comp}: a página «{PAGES[comp]}» já não tem o campeão onde se esperava")
        page = fetch(PAGES[comp])
        out[comp] = {"page": page["title"], "revid": page["revid"], "rows": rows}
    return out

if __name__ == "__main__":
    import json; print(json.dumps(harvest(), ensure_ascii=False, indent=1))
