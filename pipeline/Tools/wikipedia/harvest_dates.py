# Data em que cada título recente ficou decidido (pedido do Pedro, 17 nov. 2026: "Títulos recentes" na app).
# As finais já trazem a data; os campeonatos e as taças sem final no artigo não. Para essas épocas vai buscar
# o fim da edição às duas fontes (regra do Pedro: validar sempre nas duas):
#   Wikidata (CC0): a edição (P3450 = a competição) com fim (P582) ou data (P585);
#   Wikipédia (CC BY-SA 4.0): o parâmetro "dates"/"date" da ficha do artigo da edição ("2025–26 Primeira Liga").
# Fica com a Wikipédia quando as duas existem (o Wikidata às vezes tem só o ano) e regista as diferenças.
# Só as épocas dos últimos anos (RECENT): é o que a app mostra. Grava title_dates.json, que o conversor junta.
# Correr a partir da raiz: python3 Tools/wikipedia/harvest_dates.py
import json, os, re, sys, time, datetime, urllib.request, urllib.parse
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(os.path.dirname(here))
UA = {"User-Agent": "FootballRankingApp/0.1 (title dates for an iOS app)"}
DELAY = float(os.environ.get("WP_DELAY", "1.2"))
RECENT = datetime.date.today().year - 2          # épocas que acabam neste ano ou depois

def get(url, data=None, accept="application/json"):
    err = None
    for attempt in range(6):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, data=data, headers={**UA, "Accept": accept}), timeout=90))
        except Exception as e:
            err = e; time.sleep(DELAY * 5 * (attempt + 1))
    raise SystemExit(f"sem resposta: {err}")

def wp_api(params):
    time.sleep(DELAY)
    return get("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": 2}))

# Artigo da própria competição (o nome das edições é "<época> <artigo>"), quando não é o nome da competição.
ARTICLES = {
    "pt-liga": "Primeira Liga", "pt-taca": "Taça de Portugal", "pt-supertaca": "Supertaça Cândido de Oliveira", "pt-tacaliga": "Taça da Liga",
    "es-liga": "La Liga", "es-copa": "Copa del Rey", "es-super": "Supercopa de España", "gb-liga": "Premier League", "gb-fa": "FA Cup",
    "gb-lc": "EFL Cup", "it-liga": "Serie A", "it-coppa": "Coppa Italia", "de-liga": "Bundesliga", "de-pokal": "DFB-Pokal",
    "fr-liga": "Ligue 1", "fr-coupe": "Coupe de France", "nl-liga": "Eredivisie", "nl-knvb": "KNVB Cup",
    "ar-liga": "Argentine Primera División", "br-liga": "Campeonato Brasileiro Série A", "br-copa": "Copa do Brasil",
    "uy-liga": "Uruguayan Primera División", "eg-liga": "Egyptian Premier League", "uefa-cl": "UEFA Champions League",
    "uefa-el": "UEFA Europa League", "uefa-ecl": "UEFA Conference League", "uefa-super": "UEFA Super Cup",
    "conmebol-lib": "Copa Libertadores", "conmebol-sud": "Copa Sudamericana", "caf-cl": "CAF Champions League",
    "afc-cl": "AFC Champions League Elite", "fifa-cwc": "FIFA Club World Cup", "fifa-ic": "FIFA Intercontinental Cup",
    "hr-supertaca": "Croatian Football Super Cup", "hr-taca": "Croatian Football Cup", "us-liga": "Major League Soccer",
    "mx-liga": "Liga MX", "au-liga": "A-League Men", "ie-liga": "League of Ireland Premier Division", "gr-liga": "Super League Greece",
}
# Edições com nome próprio: (competição, época da app) -> artigo
SEASON_ARTICLES = {}

def season_titles(comp, season, article):
    """Títulos possíveis do artigo da edição."""
    s = season
    m = re.match(r"(\d{4}) (Apertura|Clausura)$", s)
    if m: return [f"{m.group(2)} {m.group(1)} {article} final phase", f"{article} {m.group(2)} {m.group(1)}", f"{m.group(1)} {m.group(2)} {article}"]
    if comp == "us-liga": return [f"MLS Cup {s}", f"{s} MLS Cup"]
    return [f"{s} {article}"]

def end_year(season):
    """Ano em que a época acaba: "2025–26" -> 2026, "1999–2000" -> 2000, "2025 Apertura" -> 2025."""
    m = re.match(r"(\d{4})(?:–(\d{2,4}))?", season)
    if not m: return 0
    a, b = int(m.group(1)), m.group(2)
    if not b: return a
    return int(b) if len(b) == 4 else a // 100 * 100 + int(b) + (100 if int(b) < a % 100 else 0)

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                       "september", "october", "november", "december"], 1)}
def dates_in(text):
    """Todas as datas completas de um texto da ficha (modelos {{end date|2026|5|17}} ou "17 May 2026")."""
    out = []
    for y, mo, d in re.findall(r"\{\{\s*(?:end|start)[ _]date(?:[ _]and[ _]age)?\s*\|\s*(?:df=\w+\|)?(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})", text, re.I):
        out.append((int(y), int(mo), int(d)))
    for d, mo, y in re.findall(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b", text):
        if mo.lower() in MONTHS: out.append((int(y), MONTHS[mo.lower()], int(d)))
    for mo, d, y in re.findall(r"\b([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\b", text):
        if mo.lower() in MONTHS: out.append((int(y), MONTHS[mo.lower()], int(d)))
    ok = []
    for t in out:
        try: ok.append(datetime.date(*t))
        except ValueError: pass
    return ok

def clean(v):
    v = re.sub(r"<ref[^>]*/>|<ref.*?</ref>|<!--.*?-->", "", v, flags=re.S)
    v = re.sub(r"<br\s*/?>", " ", v)
    for _ in range(3): v = re.sub(r"\{\{\s*(?:nowrap|nobr|small)\s*\|([^{}]*)\}\}", r"\1", v, flags=re.I)
    return v

def final_date(wikitext):
    """Dia da final, pela ficha do jogo na secção "Final" do artigo da edição de uma taça."""
    m = re.search(r"\n==+\s*Final\s*==+(.*?)(?=\n==[^=]|$)", wikitext, re.S)
    if not m: return None
    box = re.search(r"\{\{\s*(?:Football ?box|#invoke:football box)(.*?)\n\s*\}\}", m.group(1), re.S | re.I)
    if not box: return None
    d = re.search(r"\|\s*date\s*=([^\n]*)", box.group(1))
    found = dates_in(clean(d.group(1))) if d else []
    return found[0].isoformat() if len(found) == 1 else None

def infobox_end(wikitext, season, single_ok=False):
    """Último dia da edição, pelo parâmetro dates/date da ficha. Só um intervalo fechado serve ("15 February –
    30 November", "8 August 2025 – 17 May 2026"): uma data sozinha é quase sempre só o início (exceto no artigo
    de uma final, `single_ok`), e "24 January 2025 –" é uma edição sem fim escrito."""
    head = re.split(r"\n==[^=]", wikitext, 1)[0]
    for field in ("dates", "date"):
        m = re.search(r"\n\s*\|\s*" + field + r"\s*=(.*?)(?=\n\s*[|}])", head, re.S)
        if not m: continue
        v = clean(m.group(1)).strip()
        if re.search(r"present|ongoing|TBD|TBA", v, re.I): return None
        found = dates_in(v)
        if single_ok and len(found) == 1: return found[0].isoformat()
        parts = re.split(r"\s*(?:–|—|&ndash;|\bto\b)\s*", v)
        if len(parts) < 2 or not parts[1].strip(): return None
        if not dates_in(parts[1]):   # "30 November", ano subentendido
            mm = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\b|\b([A-Za-z]+)\s+(\d{1,2})\b", parts[1])
            if mm:
                d, mo = (mm.group(1), mm.group(2)) if mm.group(1) else (mm.group(4), mm.group(3))
                if mo.lower() in MONTHS:
                    try: found.append(datetime.date(end_year(season), MONTHS[mo.lower()], int(d)))
                    except ValueError: pass
        if found: return max(found).isoformat()
    return None

def clinched(wikitext, season):
    """Dia em que o campeonato ficou decidido, quando o artigo o diz ("clinching the championship with three
    rounds to go after a 2–1 win over Ñublense on 8 November 2026"). Num campeonato decidido antes da última
    jornada é essa a data que conta; o fim da época pode ainda nem ter chegado."""
    body = clean(re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", wikitext))
    for sentence in re.split(r"(?<=[.!?])\s+|\n", body):
        if not re.search(r"clinch\w*\s+(?:the|their|its)\b[^.]{0,40}\b(?:title|championship)|(?:were|was)\s+(?:crowned|confirmed as)\s+(?:the\s+)?champions", sentence, re.I):
            continue
        if re.search(r"promotion|relegat|Primera B|second division|play-?off", sentence, re.I): continue
        m = re.search(r"\bon\s+(\d{1,2}\s+[A-Z][a-z]+(?:\s+\d{4})?|[A-Z][a-z]+\s+\d{1,2}(?:,\s*\d{4})?)", sentence)
        if not m: continue
        txt = m.group(1)
        found = dates_in(txt) or dates_in(f"{txt} {end_year(season)}" if not re.search(r",", txt) else f"{txt}, {end_year(season)}")
        if found: return found[0].isoformat()
    return None

def won_on(wikitext, names, season):
    """Numa época com dois campeões (Apertura e Clausura com o mesmo rótulo), o dia em que um deles ganhou,
    pela frase do artigo que o nomeia: "Belgrano won their first national league championship on 24 May 2026"."""
    body = clean(re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", re.sub(r"<!--.*?-->", "", wikitext, flags=re.S)))
    for sentence in re.split(r"(?<=[.!?])\s+|\n", body):
        if not re.search(r"\bwon\s+(?:their|its)\b[^.]{0,60}\b(?:title|championship)|\bwere\s+(?:crowned\s+)?champions", sentence, re.I):
            continue
        before = re.split(r"\bwon\b|\bwere\b", sentence, 1)[0]
        if not any(re.search(r"\b" + re.escape(n) + r"\b", before) for n in names): continue
        m = re.search(r"\bon\s+(\d{1,2}\s+[A-Z][a-z]+\s+\d{4}|[A-Z][a-z]+\s+\d{1,2},\s*\d{4})", sentence)
        found = dates_in(m.group(1)) if m else []
        if found: return found[0].isoformat()
    return None

# Campeonatos com vários títulos na mesma época (Torneo Apertura, Torneo Clausura, Campeón de Liga).
SEVERAL_TITLES = {"ar-liga", "co-liga", "py-liga"}
TOURNAMENT = r"Torneo\s+(?:Apertura|Clausura)|Campe[oó]n de Liga|\bApertura\b|\bClausura\b|Finalizaci[oó]n|Inicial|\bFinal\b(?=\s+tournament)"
def tournament_of(wikitext, names):
    """Que torneio ganhou um dos campeões de uma época com vários ("Torneo Apertura", "Campeón de Liga"): o nome de
    torneio mais perto do clube nas frases que o dão como vencedor (prosa ou "winners = Apertura: Belgrano")."""
    body = clean(re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", re.sub(r"<!--.*?-->", "", wikitext, flags=re.S)))
    best = None
    for sentence in re.split(r"(?<=[.!?])\s+|\n", body):
        if not re.search(r"\bwon\b|\bearned\b|\bwere\s+(?:crowned\s+)?champions|\bwinners?\s*=", sentence, re.I): continue
        spots = [m.start() for n in names for m in re.finditer(r"\b" + re.escape(n) + r"\b", sentence)]
        if not spots: continue
        for m in re.finditer(TOURNAMENT, sentence):
            d = min(abs(m.start() - p) for p in spots)
            if best is None or d < best[0]: best = (d, m.group(0))
    if not best: return None
    t = best[1].replace("Campeon", "Campeón")
    return "Torneo " + t if t in ("Apertura", "Clausura", "Finalización", "Finalizacion") else t

def label_key(label):
    """Época de um rótulo do Wikidata ou de um título: "2025–26", "2025", "2025 Apertura"."""
    m = re.search(r"\b(\d{4})(?:\s*[–\-/]\s*(\d{2,4}))?\b", label)
    if not m: return None
    k = m.group(1) + (f"–{m.group(2)[-2:]}" if m.group(2) else "")
    t = re.search(r"Apertura|Clausura", label)
    return f"{k} {t.group(0)}" if t else k

def app_keys(season, split):
    """Rótulos possíveis da edição para uma época da app. Numa taça de época repartida ("2025–26 Austrian Cup")
    a época "2026" da app é a edição 2025–26."""
    m = re.match(r"(\d{4})–(\d{2,4})(.*)", season)
    if m: return [f"{m.group(1)}–{m.group(2)[-2:]}{m.group(3)}"]
    m = re.match(r"(\d{4})(.*)", season)
    y, rest = int(m.group(1)), m.group(2)
    prev = f"{y - 1}–{y % 100:02d}{rest}"
    return [prev, season] if split else [season, prev]

def main():
    data = json.load(open(os.path.join(root, "FootballRanking/Resources/football_data.json")))
    extra = json.load(open(os.path.join(root, "Tools/wikidata/extra_competitions.json")))
    comps = {c["id"]: c for c in data["competitions"]}
    club_names = {c["id"]: {c["name"], c["shortName"]} for c in data["clubs"]}
    articles = {cid: ARTICLES.get(cid) or (extra.get(cid) or {}).get("name") or c["name"] for cid, c in comps.items()}

    # Épocas recentes que precisam de data: sem final datada.
    need = {}
    for h in data["honours"]:
        dated = {f["season"] for f in h.get("finals") or [] if f.get("date") or any(m.get("date") for m in f.get("matches") or [])}
        for s in set(h.get("seasons") or []) | {f["season"] for f in h.get("finals") or []}:
            if end_year(s) >= RECENT and s not in dated and h["competition"] in comps:
                need.setdefault(h["competition"], {}).setdefault(s, []).append(h["club"])
    print(f"{sum(map(len, need.values()))} épocas recentes sem data, em {len(need)} competições", flush=True)

    # Item do Wikidata de cada competição, pelo artigo.
    qids = {}
    names = sorted({articles[c] for c in need})
    for i in range(0, len(names), 50):
        r = wp_api({"action": "query", "prop": "pageprops", "ppprop": "wikibase_item", "redirects": 1, "titles": "|".join(names[i:i + 50])})
        norm = {n["from"]: n["to"] for n in r["query"].get("normalized", []) + r["query"].get("redirects", [])}
        items = {p["title"]: p.get("pageprops", {}).get("wikibase_item") for p in r["query"]["pages"]}
        for n in names[i:i + 50]:
            t = norm.get(norm.get(n, n), norm.get(n, n))
            if items.get(t): qids[n] = items[t]

    # Wikidata: edições recentes de cada competição (e das que ela substituiu), com o fim e o artigo em inglês.
    wd = {}
    comp_q = {c: qids[articles[c]] for c in need if articles[c] in qids}
    q_comp = {}
    for c, q in comp_q.items(): q_comp.setdefault(q, []).append(c)
    qs = sorted(q_comp)
    for i in range(0, len(qs), 25):
        query = """SELECT ?c ?s ?sLabel ?end ?pe ?pit ?pp ?art WHERE {
          VALUES ?c { %s } ?s wdt:P3450 ?c .
          OPTIONAL { ?s p:P582/psv:P582 [ wikibase:timeValue ?end ; wikibase:timePrecision ?pe ] }
          OPTIONAL { ?s p:P585/psv:P585 [ wikibase:timeValue ?pit ; wikibase:timePrecision ?pp ] }
          OPTIONAL { ?art schema:about ?s ; schema:isPartOf <https://en.wikipedia.org/> }
          ?s rdfs:label ?sLabel . FILTER(LANG(?sLabel) = "en") FILTER(REGEX(?sLabel, "20[2-9][0-9]")) }""" % " ".join("wd:" + q for q in qs[i:i + 25])
        rows = get("https://query.wikidata.org/sparql", urllib.parse.urlencode({"query": query, "format": "json"}).encode(),
                   accept="application/sparql-results+json")["results"]["bindings"]
        for b in rows:
            v = lambda k: b[k]["value"] if k in b else None
            for c in q_comp[v("c").rsplit("/", 1)[1]]:
                art = urllib.parse.unquote(v("art").rsplit("/wiki/", 1)[1]).replace("_", " ") if v("art") else None
                # só datas com o dia (precisão 11); "2026-05" ou "2026" não dizem quando
                end = v("end") if v("pe") == "11" else v("pit") if v("pp") == "11" else None
                wd.setdefault(c, []).append({"label": v("sLabel"), "end": end[:10] if end else None, "article": art})
        time.sleep(2)

    # Liga cada época da app a um artigo: o do Wikidata cujo nome a contém, senão o nome habitual.
    wanted = {}
    for c, seasons in need.items():
        rows = [r for r in wd.get(c, []) if not re.search(r"qualif|women|youth|U-?\d\d|play-?off|final$", r["label"], re.I)]
        split = any(re.search(r"\d{4}[–\-/]\d{2}", r["label"]) for r in rows)
        for s in seasons:
            keys = app_keys(s, split and comps[c]["kind"] != "league")
            hit = next((r for k in keys for r in rows if label_key(r["label"]) == k), None)
            tries = [t for k in keys for t in season_titles(c, k, articles[c])]
            wanted[(c, s)] = {"wikidata": hit["end"] if hit else None, "item": hit["label"] if hit else None,
                              "tries": ([hit["article"]] if hit and hit["article"] else []) + tries}

    # Wikipédia: o texto de cada artigo, 50 de cada vez.
    # DATES_CACHE=1 guarda e reutiliza os artigos (para afinar o script sem repetir pedidos); sem ele vai sempre à Wikipédia.
    cache_path = os.path.join(here, "cache", "title_dates_pages.json")
    use_cache = os.environ.get("DATES_CACHE") == "1"
    text = {k: tuple(v) if v else None for k, v in json.load(open(cache_path)).items()} if use_cache and os.path.exists(cache_path) else {}
    def fetch_pages(titles):
        missing = sorted({t for t in titles if t not in text})
        for i in range(0, len(missing), 50):
            r = wp_api({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main", "redirects": 1, "titles": "|".join(missing[i:i + 50])})
            norm = {}
            for n in r["query"].get("normalized", []) + r["query"].get("redirects", []): norm[n["from"]] = n["to"]
            pages = {p["title"]: p["revisions"][0]["slots"]["main"]["content"] for p in r["query"]["pages"] if p.get("revisions")}
            for t in missing[i:i + 50]:
                final = norm.get(norm.get(t, t), norm.get(t, t))
                text[t] = (final, pages[final]) if final in pages else None
        if use_cache:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True); json.dump(text, open(cache_path, "w"))
    fetch_pages(t for w in wanted.values() for t in w["tries"])
    # Taças em que a final tem artigo próprio ("{{main|2026 Greek Football Cup final}}"): a data vem de lá.
    def main_final(page):
        m = re.search(r"\n==+\s*Final\s*==+\s*\{\{\s*main\s*\|([^}|]+)", page[1], re.I) if page else None
        return m.group(1).strip() if m else None
    fetch_pages(filter(None, (main_final(text.get(t)) for w in wanted.values() for t in w["tries"])))

    def wp_date(c, s, page):
        if not page: return None
        if comps[c]["kind"] != "league":
            d = final_date(page[1])
            if not d and main_final(page) and text.get(main_final(page)):
                d = infobox_end(text[main_final(page)][1], s, single_ok=True)
            if d: return d
        end = infobox_end(page[1], s, single_ok=comps[c]["kind"] == "superCup" or bool(re.search(r"MLS Cup \d{4}|\bfinal(?: phase)?$", page[0], re.I)))
        if comps[c]["kind"] == "league":
            won = clinched(page[1], s)
            if won and (not end or won <= end) and won >= f"{end_year(s) - 1}-07-01": return won
        return end

    today = datetime.date.today().isoformat()
    out, report = {}, {"iguais": 0, "so_wikipedia": [], "so_wikidata": [], "divergem": [], "sem_data": [], "data_futura": [], "varios_campeoes": []}
    for (c, s), w in sorted(wanted.items()):
        found = [(text[t], wp_date(c, s, text[t])) for t in w["tries"] if text.get(t)]
        page, wp = next(((p, d) for p, d in found if d), (found[0][0], None) if found else (None, None))
        wdd = w["wikidata"]
        date = wp or wdd
        key = f"{c} {s}"
        if wp and wdd:
            if wp == wdd: report["iguais"] += 1
            else: report["divergem"].append(f"{key}: Wikipédia {wp}, Wikidata {wdd}")
        elif wp: report["so_wikipedia"].append(f"{key} ({page[0]})")
        elif wdd: report["so_wikidata"].append(f"{key} ({w['item']})")
        else: report["sem_data"].append(f"{key}" + (f" ({page[0]})" if page else ""))
        # Dois torneios na mesma época (Apertura e Clausura): o dia de cada um pela frase que o nomeia. Nos campeonatos com
        # vários títulos por época (SEVERAL_TITLES) o torneio também se guarda com um só vencedor, porque o conversor tira os
        # vencedores do Apertura e do Clausura da Argentina e o que fica tem de continuar marcado como "Campeón de Liga".
        if len(need[c][s]) > 1 or (c in SEVERAL_TITLES and page):
            per_club, tournaments = {}, {}
            ok = lambda d: d and d <= today and end_year(s) <= int(d[:4]) <= end_year(s) + (0 if "–" in s else 1)
            for club in need[c][s]:
                t = page and tournament_of(page[1], club_names[club])
                if t: tournaments[club] = t
                d = page and won_on(page[1], club_names[club], s)
                if ok(d): per_club[club] = d
                elif len(need[c][s]) == 1 and ok(date): per_club[club] = date
            if per_club or tournaments:
                out.setdefault(c, {})[s] = {"clubs": per_club, "tournaments": tournaments, "source": "Wikipedia", "article": page[0]}
            report["varios_campeoes"].append(f"{key}: " + ", ".join(f"{k} {per_club.get(k, 'sem data')} {tournaments.get(k, '?')}" for k in need[c][s]))
            continue
        if date and date > today:   # o fim da época ainda não chegou e o artigo não diz quando o título ficou decidido
            report["data_futura"].append(f"{key}: {date}"); continue
        if date and end_year(s) <= int(date[:4]) <= end_year(s) + (0 if "–" in s else 1):
            out.setdefault(c, {})[s] = {"date": date, "source": "Wikipedia" if wp else "Wikidata",
                                        **({"article": page[0]} if page else {})}
    json.dump(out, open(os.path.join(here, "title_dates.json"), "w"), ensure_ascii=False, indent=1, sort_keys=True)
    json.dump(report, open(os.path.join(here, "title_dates_report.json"), "w"), ensure_ascii=False, indent=1)
    print(f"com data: {sum(map(len, out.values()))} | nas duas fontes iguais: {report['iguais']} | divergem: {len(report['divergem'])} | "
          f"só Wikipédia: {len(report['so_wikipedia'])} | só Wikidata: {len(report['so_wikidata'])} | sem data: {len(report['sem_data'])}")

if __name__ == "__main__":
    main()
