# Época a época (e, nas taças, a final) das competições que só tinham o total por clube na Wikipédia
# (pedido do Pedro, 13 out. 2026: o aviso "Details of these titles will come from Wikidata").
# Lê as tabelas "Season/Year | Winner | Score | Runner-up | Venue" das páginas de PAGES e grava
# season_tables.json. Correr a partir da raiz: python3 Tools/wikipedia/harvest_seasons.py
import json, os, re, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
from wp import tables, grid
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from harvest import PAGES
PAGES = dict(PAGES, **{"bg-taca": "List of Bulgarian Cup finals", "be-taca": "List of Belgian Cup finals", "us-taca": "List of U.S. Open Cup finals"})

COMPS = "sct-liga pl-liga ru-liga bg-taca cm-liga cm-taca qa-taca za-taca gh-taca th-taca hr-liga cn-taca si-taca by-liga us-liga il-liga kr-liga be-taca us-taca bg-liga hr-taca hr-supertaca".split()
SEASON = re.compile(r"^(vte\s+)?(season|year|year/season|edition)\b", re.I)
WINNER = re.compile(r"^(?!.*runner)(.*\b)?(winners?|champions?|champion\(s\))\b", re.I)
SCORE = re.compile(r"^(score|result)", re.I)
RUNNER = re.compile(r"runners?[- –]?up|finalist", re.I)
VENUE = re.compile(r"venue|stadium", re.I)
SKIP = re.compile(r"not finished|not held|no championship|no competition|not played|suspended|cancel|abandon|not awarded|postponed|won the double|n/a|^—$|^–$", re.I)

# Tabelas da página que não são a primeira divisão nem o campeonato nacional (regionais, 2.ª divisão, prémios).
SKIP_TABLE = {"ru-liga": r"SFSR|USSR championship|First Group", "pl-liga": r"Kraków Championship"}
# Supertaça da Croácia a duas mãos (a tabela põe "4–4, 0–0 (a)" e "1–0, 0–1 (aet), (5–4 p)" numa só célula).
TWO_LEGS = {("hr-supertaca", "1993"): {"score": [4, 4], "aggregate": True, "venue": "Maksimir, Zagreb / Poljud, Split"},
            ("hr-supertaca", "1994"): {"score": [1, 1], "aggregate": True, "extraTime": True, "penalties": [5, 4], "venue": "Poljud, Split / Maksimir, Zagreb"}}
def norm_name(s): return re.sub(r"[^a-z]", "", s.lower())
def clean(s):
    s = re.sub(r"\[[^\]]*\]", "", s)
    return re.sub(r"\s+", " ", s).strip(" *†‡§#^,⭐★")
def names(cell):
    parts = re.split(r",\s*and,?\s*|\s+and\s+(?=[A-Z])|,\s+(?=[A-Z])|\s*/\s*(?=[A-Z])", cell)
    out = []
    for p in parts:
        p = re.sub(r"\s+and$", "", clean(re.sub(r"\(\d+\)|\([^)]*\)$", "", p)))
        if p: out.append(p)
    return out
def score(text):
    t = text.replace("&ndash;", "–")
    m = re.search(r"(\d+)\s*[–\-:]\s*(\d+)", t)
    if not m: return None
    s = {"score": [int(m.group(1)), int(m.group(2))]}
    if re.search(r"a\.?e\.?t|extra|\bet\b|aet", t, re.I): s["extraTime"] = True
    rest = t[m.end():]
    p = re.search(r"(\d+)\s*[–\-:]\s*(\d+)\s*(?:pen|p\b|n\.\s?[eE]|i\.\s?[eE])", rest) or re.search(r"\(\s*(\d+)\s*[–\-:]\s*(\d+)\s*\)", rest)
    if p and s["score"][0] == s["score"][1]: s["penalties"] = [int(p.group(1)), int(p.group(2))]
    return s

def unminus(t): return t.replace("\u2212", "–")   # a Wikipédia usa às vezes o sinal de menos ("2014−15", "2−0")
out = {}
for comp in COMPS:
    rows = {}
    for t in tables(PAGES[comp]):
        g = grid(t)
        if len(g) < 4 or re.search(SKIP_TABLE.get(comp, "(?!)"), t["heading"]): continue
        for hi in range(min(2, len(g))):
            head = [re.sub(r"\s+", " ", c["text"]).strip() for c in g[hi]]
            si = next((i for i, h in enumerate(head) if SEASON.match(h)), None)
            wi = next((i for i, h in enumerate(head) if WINNER.match(h) and i != si), None)
            if si is None or wi is None or any(re.search(r"top scorer|goalscorer|player", h, re.I) for h in head[:wi]) or any(re.fullmatch(r"position", h, re.I) for h in head): continue
            sc = next((i for i, h in enumerate(head) if SCORE.match(h)), None)
            ru = next((i for i, h in enumerate(head) if RUNNER.search(h)), None)
            ve = next((i for i, h in enumerate(head) if VENUE.search(h)), None)
            comp_col = next((i for i, h in enumerate(head) if h.lower() == "competition"), None)
            for r in g[hi + 1:]:
                r = [dict(c, text=unminus(c["text"])) for c in r]
                if len(r) <= max(si, wi): continue
                y = re.match(r"\d{4}(?:\s*[–\-/]\s*\d{2,4})?", r[si]["text"].strip())
                if y and re.search(r"\bwon\b.*\b(aggregate|away goals|penalties)", r[wi]["text"]):
                    # linha que fecha uma final a duas mãos ("Shanghai Greenland Shenhua won 3–1 on aggregate.")
                    k = re.sub(r"\s", "", y.group()).replace("-", "–").replace("/", "–")
                    m = re.match(r"^(.*?)\s+won\s+(\d+)\s*[–\-]\s*(\d+)", r[wi]["text"])
                    if k in rows and m:
                        w = clean(m.group(1)); prev = rows[k]
                        if norm_name(w) != norm_name(prev["winners"][0]):
                            prev["winners"], prev["runnerUp"] = [w], prev["winners"][0]
                            prev["winnerLinks"], prev["runnerUpLink"] = [None], None
                        a, b = int(m.group(2)), int(m.group(3)); prev["score"] = [max(a, b), min(a, b)] if a != b else [a, b]; prev["aggregate"] = True; prev.pop("replay", None); prev.pop("firstGame", None)
                    continue
                if not y or SKIP.search(r[wi]["text"]): continue
                season = re.sub(r"\s", "", y.group()).replace("-", "–").replace("/", "–")
                if "–" in season and len(season.split("–")[1]) == 4: season = season.split("–")[0] + "–" + season.split("–")[1][2:]
                w = names(r[wi]["text"])
                if not w: continue
                row = {"season": season, "winners": w, "winnerLinks": [r[wi].get("link")]}
                if comp_col is not None: row["competition"] = r[comp_col]["text"]
                if sc is not None and len(r) > sc:
                    s = score(r[sc]["text"])
                    if s: row.update(s)
                if ru is not None and len(r) > ru and not SKIP.search(r[ru]["text"]):
                    row["runnerUp"] = (names(r[ru]["text"]) or [None])[0]; row["runnerUpLink"] = r[ru].get("link")
                if ve is not None and len(r) > ve and clean(r[ve]["text"]): row["venue"] = clean(r[ve]["text"])
                prev = rows.get(season)
                if prev and prev.get("score") and prev["score"][0] == prev["score"][1] and not prev.get("penalties") and "score" in row \
                        and not prev.get("aggregate") and prev.get("competition") == row.get("competition"):
                    # final empatada e repetida: vale o último jogo (se for a duas mãos, a linha de fecho corrige)
                    row["replay"] = True; row["firstGame"] = prev["score"]; rows[season] = row; continue
                rows.setdefault(season, row)
            break
    for r in rows.values():
        if comp == "hr-taca" and ";" in r.get("venue", ""): r["aggregate"] = True   # final a duas mãos: dois estádios na tabela
        fix = TWO_LEGS.get((comp, r["season"]))
        if fix: r.update(fix)
    out[comp] = sorted(rows.values(), key=lambda x: x["season"])
    print(f"{comp:10} {len(out[comp]):3} épocas | com resultado {sum('score' in r for r in out[comp])} | finalista {sum('runnerUp' in r for r in out[comp])}")
# Taça do Emir do Qatar: a página inglesa só tem o total, a espanhola tem as finais época a época
# (confirmada na alemã e no Wikidata, ver validate no relatório).
def other_language(comp, title, lang, cols):
    rows = {}
    for t in tables(title, lang):
        g = grid(t)
        if len(g) < 15: continue
        head = [c["text"].strip() for c in g[0]]
        if not all(c in head for c in cols.values()): continue
        ix = {k: head.index(v) for k, v in cols.items()}
        for r in g[1:]:
            y = re.match(r"\d{4}(?:\s*[–\-/]\s*\d{2,4})?", r[ix["season"]]["text"].strip())
            if not y: continue
            season = re.sub(r"\s", "", y.group()).replace("-", "–").replace("/", "–")
            if "–" in season and len(season.split("–")[1]) == 4: season = season.split("–")[0] + "–" + season.split("–")[1][2:]
            row = {"season": season, "winners": names(r[ix["winner"]]["text"]), "winnerLinks": [None], "source": f"{lang}.wikipedia: {title}"}
            sc = score(r[ix["score"]]["text"].replace(" ", ""))
            if sc: row.update(sc)
            ru = names(r[ix["runner"]]["text"])
            if ru: row["runnerUp"] = ru[0]; row["runnerUpLink"] = None
            if "venue" in ix and clean(r[ix["venue"]]["text"]): row["venue"] = clean(r[ix["venue"]]["text"])
            if row["winners"]: rows.setdefault(season, row)
        break
    out[comp] = sorted(rows.values(), key=lambda x: x["season"])
    print(f"{comp:10} {len(out[comp]):3} épocas ({lang}) | com resultado {sum('score' in r for r in out[comp])}")
# MLS Cup: a tabela inglesa que serve é a da CONCACAF (o ano é o da prova seguinte); a alemã tem as finais.
other_language("us-liga", "MLS Cup", "de", {"season": "Saison", "winner": "Meister", "score": "Ergebnis", "runner": "Finalist", "venue": "Stadion"})
other_language("qa-taca", "Copa del Emir de Catar", "es", {"season": "Temporada", "winner": "Campeón", "score": "Resultado", "runner": "Finalista", "venue": "Sede de la final"})
json.dump(out, open(os.path.join(here, "season_tables.json"), "w"), ensure_ascii=False, indent=1)
