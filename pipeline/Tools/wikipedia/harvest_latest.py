# Últimos vencedores que as tabelas por clube da Wikipédia ainda não têm (pedido do Pedro, 18 nov. 2026: "Esta época" vazia em
# muitos países). As tabelas "performance by club" demoram a ser atualizadas; o artigo da edição ("2026 Veikkausliiga",
# "2026 Supercupa României") diz o campeão logo a seguir. Para cada competição, lê o artigo da edição mais recente que os dados
# ainda não têm: o campo champions/winners da ficha, ou, numa supertaça de um só jogo, o resultado da ficha do jogo.
# Grava latest_winners.json (competição -> época -> clube, dia, artigo); o conversor junta-o. Só clubes que já existem na app.
# Corre no fim de harvest_dates.py (a tarefa automática já o chama). À mão: python3 Tools/wikipedia/harvest_latest.py
import json, os, re, sys, datetime, urllib.parse
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(os.path.dirname(here))
sys.path.insert(0, here)
import harvest_dates as hd

# Países cuja época é o ano civil (como SeasonCalendar.calendarYearCountries na app).
CALENDAR = {"AR", "BO", "BR", "BY", "CA", "CL", "CN", "CO", "EC", "FI", "GE", "IE", "IS", "KR", "NO", "PE", "PY", "SE", "US", "UY", "VE"}
CALENDAR_CONTINENTAL = {"CONMEBOL", "CONCACAF", "OFC"}

def norm(t):
    return urllib.parse.unquote((t or "").replace("_", " ")).strip().lower()

def first_link(text):
    m = re.search(r"\[\[([^|\]#]+)", text or "")
    return m.group(1).strip() if m else None

def infobox_winner(w):
    """Clube campeão: o campo champions/winners da ficha (sem "TBD"), ou o vencedor da ficha do jogo (supertaça)."""
    head = re.split(r"\n==[^=]", w, 1)[0]
    m = re.search(r"\n\s*\|\s*(champions?|winners?)\s*=([^\n]*)", head)
    if m:
        v = re.sub(r"<!--.*?-->|<ref.*?(</ref>|/>)", "", m.group(2), flags=re.S)
        if re.search(r"TBD|TBA|not completed|cancel", v, re.I): return None
        return first_link(v)
    box = re.search(r"\{\{\s*(?:Football ?box|#invoke:football box|Infobox football match)(.*?)\n\s*\}\}", w, re.S | re.I)
    if not box: return None
    f = dict((k.lower(), v) for k, v in re.findall(r"\n\s*\|\s*(\w+)\s*=([^\n]*)", box.group(1)))
    t1, t2 = first_link(f.get("team1")), first_link(f.get("team2"))
    if f.get("team1score", "").strip() and f.get("team2score", "").strip():   # {{Infobox football match}}
        s = re.findall(r"\d+", f["team1score"])[:1] + re.findall(r"\d+", f["team2score"])[:1]
    else:
        s = re.findall(r"\d+", re.sub(r"\{\{.*?\}\}|<.*?>", "", f.get("score", "")))
    if not (t1 and t2 and len(s) >= 2): return None
    a, b = int(s[0]), int(s[1])
    if a == b:
        p = re.findall(r"\d+", f.get("penaltyscore", "") or f.get("penalties", ""))
        if len(p) >= 2 and p[0] != p[1]: a, b = int(p[0]), int(p[1])
        else:   # "Universitatea Craiova won 5–3 on penalties"
            m = re.search(r"(?:\[\[(?:[^|\]]*\|)?)?([^\]\[|]+?)\]?\]?\s+won\s+\d+\s*[–-]\s*\d+\s+on\s+(?:\[\[[^|\]]*\|)?penalties", f.get("details", "") + " " + f.get("result", ""), re.I)
            if not m: return None
            name = m.group(1).strip().lower()
            shown = lambda t: re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t or "").strip().lower()
            if name in (shown(f.get("team1")), t1.lower()): return t1
            if name in (shown(f.get("team2")), t2.lower()): return t2
            return None
    return t1 if a > b else t2

def main():
    today = datetime.date.today()
    data = json.load(open(os.path.join(root, "FootballRanking/Resources/football_data.json")))
    extra = json.load(open(os.path.join(root, "Tools/wikidata/extra_competitions.json")))
    arts_path = os.path.join(root, "Tools/crests/club_articles.json")
    club_by_article = {norm(a): c for c, a in json.load(open(arts_path)).items()} if os.path.exists(arts_path) else {}
    clubs = {c["id"]: c for c in data["clubs"]}
    have = {}
    for h in data["honours"]:
        for s in (h.get("seasons") or []) + [f["season"] for f in h.get("finals") or []]:
            have.setdefault(h["competition"], set()).add(s)
    wanted = {}
    for c in data["competitions"]:
        if c.get("defunct") or c["level"] == "world": continue
        calendar = (c.get("country") in CALENDAR) if c["level"] == "domestic" else (c.get("confederation") in CALENDAR_CONTINENTAL)
        y = today.year
        if c["kind"] in ("superCup", "continentalSuperCup") or calendar: editions = [str(y)]
        else: editions = [f"{y - 1}–{y % 100:02d}"]
        if any(re.search(r"[A-Za-z]", x) for x in have.get(c["id"], [])): continue   # torneios curtos ("2026 Clausura"): à parte
        labels = sorted(have.get(c["id"], []), key=hd.end_year)
        dash = bool(labels) and "–" in labels[-1]
        article = hd.ARTICLES.get(c["id"]) or (extra.get(c["id"]) or {}).get("name") or c["name"]
        for e in editions:
            label = e if (dash or "–" not in e) else str(hd.end_year(e))
            if label in have.get(c["id"], set()) or e in have.get(c["id"], set()): continue
            wanted[(c["id"], label)] = [f"{e} {article}"] + ([f"{article} {e}"] if c["kind"] == "superCup" else [])
    titles = sorted({t for ts in wanted.values() for t in ts})
    pages = {}
    for i in range(0, len(titles), 20):
        r = hd.wp_api({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main", "redirects": 1, "titles": "|".join(titles[i:i + 20])})
        norm_map = {n["from"]: n["to"] for n in r["query"].get("normalized", []) + r["query"].get("redirects", [])}
        got = {p["title"]: p["revisions"][0]["slots"]["main"]["content"] for p in r["query"]["pages"] if p.get("revisions")}
        for t in titles[i:i + 20]:
            final = norm_map.get(norm_map.get(t, t), norm_map.get(t, t))
            if final in got: pages[t] = (final, got[final])
    # Ligações da ficha que são redirecionamentos ("CSU Craiova" -> "CS Universitatea Craiova"): o título final é o que a app guarda.
    links = sorted({l for t, (title, w) in pages.items() for l in [infobox_winner(w)] if l})
    final_title = {}
    for i in range(0, len(links), 50):
        r = hd.wp_api({"action": "query", "redirects": 1, "titles": "|".join(links[i:i + 50])})
        steps = {n["from"]: n["to"] for n in r["query"].get("normalized", []) + r["query"].get("redirects", [])}
        for l in links[i:i + 50]:
            t = l
            for _ in range(3): t = steps.get(t, t)
            final_title[l] = t
    # Ficam os encontrados nas recolhas anteriores (o conversor ignora-os quando a tabela por clube já os tiver); só se
    # esquecem os de épocas com mais de dois anos.
    _prev = os.path.join(here, "latest_winners.json")
    out = {c: {s: w for s, w in v.items() if hd.end_year(s) >= today.year - 2} for c, v in (json.load(open(_prev)) if os.path.exists(_prev) else {}).items()}
    report = {"novos": [], "clube_fora_da_app": [], "sem_vencedor": []}
    for (cid, label), ts in sorted(wanted.items()):
        page = next((pages[t] for t in ts if t in pages), None)
        if not page: continue
        link = infobox_winner(page[1])
        if not link: report["sem_vencedor"].append(f"{cid} {label} ({page[0]})"); continue
        club = club_by_article.get(norm(link)) or club_by_article.get(norm(final_title.get(link)))
        if not club:
            report["clube_fora_da_app"].append(f"{cid} {label}: {link}"); continue
        comp = next(c for c in data["competitions"] if c["id"] == cid)
        if comp["kind"] == "superCup" or comp["kind"] != "league":
            day = hd.final_date(page[1]) or hd.infobox_end(page[1], label, single_ok=True)
        else:
            day = hd.clinched(page[1], label) or hd.infobox_end(page[1], label)
        if not day:   # ficha do jogo: "date1 = 16 July 2026"
            m = re.search(r"\n\s*\|\s*date1?\s*=([^\n]*)", page[1])
            found = hd.dates_in(hd.clean(m.group(1))) if m else []
            day = found[0].isoformat() if len(found) == 1 else None
        if day and day > today.isoformat(): day = None
        out.setdefault(cid, {})[label] = {"club": club, "article": page[0], **({"date": day} if day else {})}
        report["novos"].append(f"{cid} {label}: {clubs.get(club, {}).get('shortName', club)} {day or ''}")
    json.dump(out, open(os.path.join(here, "latest_winners.json"), "w"), ensure_ascii=False, indent=1, sort_keys=True)
    json.dump(report, open(os.path.join(here, "latest_winners_report.json"), "w"), ensure_ascii=False, indent=1)
    print(f"últimos vencedores: {len(report['novos'])} novos | clube fora da app: {len(report['clube_fora_da_app'])} | sem vencedor: {len(report['sem_vencedor'])}")

if __name__ == "__main__":
    main()
