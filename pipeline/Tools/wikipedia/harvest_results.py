# Competições novas cuja página da Wikipédia ainda não tem a tabela "por clube", só a lista de edições
# (Ed. | Year | Champion | Score | Runner-up | Venue). Lê o campeão de cada edição e devolve linhas no formato
# de harvest.py (clube, títulos, anos, ligação). Pedido do Pedro, 17 nov. 2026: Copa de la Liga AUF (Uruguai, desde 2026).
# Quando a página passar a ter a tabela por clube, a competição pode ir para pages_extra.json e sair daqui.
import os, re, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
from wp import tables, grid, fetch
from harvest_canada_old import _rows

PAGES = {"uy-copaliga": "Copa de la Liga AUF"}

def champions(title):
    out = []
    for t in tables(title):
        g = grid(t)
        if not g: continue
        head = [c["text"].strip() for c in g[0]]
        yi = next((i for i, h in enumerate(head) if re.fullmatch(r"Year|Season|Edition", h, re.I)), None)
        wi = next((i for i, h in enumerate(head) if re.fullmatch(r"Champions?|Winners?", h, re.I)), None)
        if yi is None or wi is None: continue
        for r in g[1:]:
            if len(r) <= max(yi, wi): continue
            y = re.search(r"\d{4}(?:–\d{2})?", r[yi]["text"])
            name = re.sub(r"\s*\(\d+\)\s*$", "", r[wi]["text"]).strip()   # "Progreso (1)" -> "Progreso"
            if y and name: out.append((y.group(), name, r[wi].get("link")))
        if out: break
    return _rows(out)

def harvest():
    """comp -> {"page", "revid", "rows"}; falha se uma página já não tem a lista de edições."""
    out = {}
    for comp, title in PAGES.items():
        rows = champions(title)
        if not rows: raise SystemExit(f"{comp}: a página «{title}» já não tem a lista de campeões onde se esperava")
        page = fetch(title)
        out[comp] = {"page": page["title"], "revid": page["revid"], "rows": rows}
    return out

if __name__ == "__main__":
    import json; print(json.dumps(harvest(), ensure_ascii=False, indent=1))
