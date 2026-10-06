# Lê tabelas de páginas da Wikipédia em inglês (API pública; texto sob CC BY-SA 4.0).
import json, os, re, time, urllib.request, urllib.parse
from html.parser import HTMLParser
here = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "FootballRankingApp/0.1 (trophy tables for an iOS app)"}
DELAY = float(os.environ.get("WP_DELAY", "1.2"))   # segundos entre pedidos; maior na tarefa automática

def fetch(title, lang="en"):
    path = os.path.join(here, "cache", ("" if lang == "en" else lang + "_") + re.sub(r"[^A-Za-z0-9]+", "_", title) + ".json")
    if os.path.exists(path): return json.load(open(path))
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "parse", "page": title, "prop": "text|revid", "format": "json", "redirects": 1, "formatversion": 2})
    for attempt in range(6):
        try:
            data = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30)); break
        except Exception as e:
            time.sleep(DELAY * 5 * (attempt + 1)); data = {"error": str(e)}
    if "parse" not in data: raise SystemExit(f"{title}: {data.get('error')}")
    out = {"title": data["parse"]["title"], "revid": data["parse"]["revid"], "html": data["parse"]["text"]}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(out, open(path, "w")); time.sleep(DELAY)
    return out

class Tables(HTMLParser):
    """Tabelas como listas de linhas; cada célula é (texto, [países das bandeiras], cabeçalho?)."""
    def __init__(self):
        super().__init__(); self.tables = []; self.stack = []; self.cell = None; self.skip = 0; self.heading = ""; self.inh = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("h2", "h3", "h4"): self.inh = True; self.heading = ""
        if tag == "table": self.stack.append({"rows": [], "heading": self.heading, "row": None})
        if not self.stack: return
        t = self.stack[-1]
        if tag == "tr": t["row"] = []
        if tag in ("td", "th") and t["row"] is not None:
            self.cell = {"text": "", "flags": [], "th": tag == "th", "span": int(re.sub(r"\D", "", a.get("rowspan", "1")) or 1),
                         "colspan": int(re.sub(r"\D", "", a.get("colspan", "1")) or 1)}
        if tag in ("sup", "style", "script"): self.skip += 1
        if self.cell is not None:
            if tag == "br": self.cell["text"] += ", "
            if tag == "img" and a.get("alt"): self.cell["flags"].append(a["alt"])
            if tag == "a" and a.get("title") and "flag" in (a.get("class") or ""): self.cell["flags"].append(a["title"])
    def handle_endtag(self, tag):
        if tag in ("h2", "h3", "h4"): self.inh = False
        if tag in ("sup", "style", "script") and self.skip: self.skip -= 1
        if not self.stack: return
        t = self.stack[-1]
        if tag in ("td", "th") and self.cell is not None and t["row"] is not None:
            self.cell["text"] = re.sub(r"\s+", " ", self.cell["text"]).strip(); t["row"].append(self.cell); self.cell = None
        if tag == "tr" and t["row"] is not None:
            if t["row"]: t["rows"].append(t["row"])
            t["row"] = None
        if tag == "table": self.tables.append(self.stack.pop())
    def handle_data(self, data):
        if self.skip: return
        if self.inh: self.heading += data
        if self.cell is not None: self.cell["text"] += data

def tables(title, lang="en"):
    p = Tables(); p.feed(fetch(title, lang)["html"]); return p.tables

def grid(table):
    """Expande rowspan/colspan para uma grelha retangular de células."""
    rows = []; pending = {}
    for r in table["rows"]:
        out = []; cells = list(r); col = 0
        while cells or col in pending:
            if col in pending:
                c, left = pending[col]; out.append(c)
                if left > 1: pending[col] = (c, left - 1)
                else: del pending[col]
                col += 1; continue
            c = cells.pop(0)
            for _ in range(c["colspan"]):
                out.append(c)
                if c["span"] > 1: pending[col] = (c, c["span"] - 1)
                col += 1
        rows.append(out)
    return rows

if __name__ == "__main__":
    import sys
    for t in tables(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else "en"):
        g = grid(t)
        if len(g) < 3: continue
        print("==", t["heading"].strip()[:50], "|", len(g), "linhas |", [c["text"][:22] for c in g[0]])
        if len(sys.argv) > 2: print("   ", [(c["text"][:60], c["flags"][:1]) for c in g[1]])
