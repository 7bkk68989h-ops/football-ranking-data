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
# Mais campeonatos (pedido do Pedro, 17 nov. 2026: os treinadores da Argentina e dos outros): os anexos "Entrenadores campeones de…"
# da Wikipédia em espanhol e as listas "… winning managers" da inglesa.
ES = "Anexo:Entrenadores campeones de la "
PAGES.update({
 "ar-liga": ("es", ES + "Primera División de Argentina"), "bo-liga": ("es", ES + "Primera División de Bolivia"),
 "be-liga": ("es", ES + "Primera División de Bélgica"), "cl-liga": ("es", ES + "Primera División de Chile"),
 "mx-liga": ("es", ES + "Primera División de México"), "ve-liga": ("es", ES + "Primera División de Venezuela"),
 "pe-liga": ("es", ES + "Primera División del Perú"), "hr-liga": ("es", ES + "Primera Liga de Croacia"),
 "rs-liga": ("es", ES + "Primera Liga de Yugoslavia y Superliga de Serbia"), "sct-liga": ("en", "List of Scottish football championship–winning managers"),
 "ch-liga": ("es", ES + "Superliga de Suiza"), "tr-liga": ("es", ES + "Superliga de Turquía"), "gr-liga": ("es", ES + "Superliga de Grecia"),
 "sk-liga": ("es", ES + "Superliga de Eslovaquia"), "ru-liga": ("es", ES + "Liga Premier de Rusia"), "ua-liga": ("es", ES + "Liga Premier de Ucrania"),
 "de-liga": ("es", ES + "Bundesliga (Alemania)"), "at-liga": ("es", ES + "Bundesliga de Austria"), "nl-liga": ("es", ES + "Eredivisie"),
 "jp-liga": ("es", ES + "J League"), "kr-liga": ("es", ES + "K League"), "us-liga": ("es", ES + "Major League Soccer"),
 "cz-liga": ("es", ES + "Primera División de Checoslovaquia y Liga Checa de fútbol"), "ir-liga": ("en", "List of Iranian Football League winning managers"),
 "dz-liga": ("en", "List of Algerian Ligue Professionnelle 1 winning managers"), "tn-liga": ("en", "List of Tunisian Ligue Professionnelle 1 winning managers"),
})
# Páginas mais curtas (campeonatos recentes): mínimo de épocas para a tabela contar como completa.
MIN_ROWS = {"ru-liga": 20, "ua-liga": 20, "us-liga": 20, "jp-liga": 20, "kr-liga": 25, "hr-liga": 20, "sk-liga": 20, "cz-liga": 25,
            "ir-liga": 15, "dz-liga": 15, "tn-liga": 25, "bo-liga": 25, "ve-liga": 25}
SEASON = re.compile(r"^(season|época|year|temporada|año|torneo|campeonato|edición)$", re.I)
MANAGER = re.compile(r"(winning )?(manager|treinador|coach|entrenador|director técnico|técnico)", re.I)
CLUB = re.compile(r"^(club|winners?|vencedor|champions?|campeón|equipo)", re.I)

def clean(s):
    s = re.sub(r"\[[^\]]*\]", "", s); s = re.sub(r"\s*\(\d+(?:/\d+)?\)\s*", " ", s).replace("\u200b", "")
    s = re.sub(r"\s*\((?:en|pt|de|it|fr)\)", "", s)   # ligação para outra Wikipédia: "Anatoli Zaiaev (en)"
    return re.sub(r"\s+", " ", s).strip(" ,*†‡—-")

TOURNAMENT_COL = re.compile(r"^(torneo|tournament)$", re.I)
SECOND_HALF = re.compile(r"clausura|final|verano|nacional", re.I)   # torneo da segunda metade de uma época "1990–91"
FIRST_HALF = re.compile(r"apertura|inicial|invierno|metropolitano", re.I)

def season_of(text, tournament):
    """Época da linha. Numa época repartida com dois torneios ("1990-91", Apertura e Clausura) cada torneio fica com o seu ano
    (o Apertura 1990, o Clausura 1991), como nos dados da app; um torneio com nome ("2025", "Apertura") guarda-se à parte."""
    m = re.match(r"\d{4}(?:\s*[–-]\s*\d{2,4})?", text)
    if not m: return None
    season = m.group().replace(" ", "").replace("-", "–")
    if "–" in season and tournament:
        a = int(season[:4])
        if SECOND_HALF.search(tournament): return str(a + 1)
        if FIRST_HALF.search(tournament): return str(a)
    return season

OLD = {"pt-liga", "es-liga", "gb-liga", "it-liga", "fr-liga", "br-liga", "uy-liga"}   # só a maior tabela, como antes
_prev_path = os.path.join(here, "wikipedia_managers.json")
previous = json.load(open(_prev_path)) if os.path.exists(_prev_path) else {}
out, failed = {}, []

def page_rows(comp, lang, title):
    """Linhas (época, clube, treinador) da página. Nas páginas novas juntam-se todas as tabelas (o anexo da Argentina tem uma
    por era); nas 7 primeiras fica só a maior, como sempre."""
    tables_rows = []
    for t in tables(title, lang):
        g = grid(t)
        if len(g) < 3: continue
        head = [c["text"].strip() for c in g[0]]
        si = next((i for i, h in enumerate(head) if SEASON.match(h)), None)
        mi = next((i for i, h in enumerate(head) if MANAGER.search(h) and not re.search(r"nacionalidad|país|nationality|nation", h, re.I)), None)
        ci = next((i for i, h in enumerate(head) if CLUB.match(h)), None)
        ti = next((i for i, h in enumerate(head) if TOURNAMENT_COL.match(h)), None)
        if None in (si, mi, ci): continue
        rows = []
        for r in g[1:]:
            if len(r) <= max(si, mi, ci): continue
            tournament = r[ti]["text"].strip() if ti is not None and ti < len(r) else None
            season = season_of(r[si]["text"], tournament)
            manager, club = clean(r[mi]["text"]), clean(r[ci]["text"])
            if not season or not manager or not club or manager == club or re.search(r"\d{4}|not held|suspended|cancel|sin datos|desconocido", manager, re.I): continue
            row = {"season": season, "club": club, "manager": manager}
            if r[ci].get("link"): row["link"] = r[ci]["link"]
            if r[mi].get("link"): row["manager_link"] = r[mi]["link"]
            if tournament and not re.match(r"primera|liga$|first", tournament, re.I): row["tournament"] = tournament
            rows.append(row)
        tables_rows.append(rows)
    if comp in OLD:
        return max(tables_rows, key=len, default=[])
    out_rows, seen = [], set()
    for rows in tables_rows:
        for row in rows:
            key = (row["season"], row["club"], row["manager"])
            if key not in seen: seen.add(key); out_rows.append(row)
    return out_rows

for comp, (lang, title) in PAGES.items():
    try:
        best = page_rows(comp, lang, title)
        page = fetch(title, lang)
        out[comp] = {"lang": lang, "page": page["title"], "revid": page["revid"], "rows": best}
        print(f"{comp:8} {len(best):3} épocas | {best[0] if best else None} | {best[-1] if best else None}", flush=True)
    except SystemExit as e:   # página que não respondeu: fica a versão anterior
        failed.append(f"{comp}: {e}")
        if comp in previous: out[comp] = previous[comp]
        print(f"{comp:8} FALHOU, fica a anterior: {e}", flush=True)
# Artigo em inglês do clube de cada linha (pela ligação da tabela), para o merge o ligar ao clube da app mesmo quando o nome
# vem noutra língua ("Club Brujas", "Estrella Roja").
import urllib.request, urllib.parse, time
def english_titles(lang, titles):
    found = {}
    titles = sorted(set(titles))
    for i in range(0, len(titles), 50):
        url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "prop": "langlinks", "lllang": "en",
              "redirects": 1, "titles": "|".join(titles[i:i + 50]), "format": "json", "formatversion": 2, "lllimit": "max"})
        for attempt in range(8):
            try: data = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "FootballRankingApp/0.1 (coaches)"}), timeout=60)); break
            except Exception: time.sleep(20 * (attempt + 1)); data = None
        if not data: continue
        q = data["query"]; back = {}
        for n in q.get("normalized", []) + q.get("redirects", []): back.setdefault(n["to"], []).append(n["from"])
        for p in q["pages"]:
            en = (p.get("langlinks") or [{}])[0].get("title")
            if not en: continue
            for t in [p["title"]] + back.get(p["title"], []) + sum((back.get(x, []) for x in back.get(p["title"], [])), []): found[t] = en
        time.sleep(3)
    return found
# O que a Wikipédia não respondeu (limite de pedidos) fica como na recolha anterior.
_before = {(c, r["season"], r["club"]): r for c, v in previous.items() for r in v.get("rows", [])}
def keep_previous(comp, row):
    old = _before.get((comp, row["season"], row["club"]))
    if not old: return
    if "en" not in row and old.get("en"): row["en"] = old["en"]
    if "manager_es" not in row and old.get("manager_es") and old["manager_es"] == row["manager"]:
        row["manager_es"], row["manager"] = old["manager_es"], old["manager"]
for comp, v in out.items():
    if v.get("lang") == "en":
        for row in v["rows"]:
            if row.get("link"): row["en"] = row["link"]
        continue
    en = english_titles(v["lang"], [r["link"] for r in v["rows"] if r.get("link")])
    for row in v["rows"]:
        if en.get(row.get("link")): row["en"] = en[row["link"]]
    # Nome do treinador como na Wikipédia inglesa ("Serguéi Semak" -> "Sergei Semak"), para a página da pessoa o encontrar.
    en = english_titles(v["lang"], [r["manager_link"] for r in v["rows"] if r.get("manager_link")])
    for row in v["rows"]:
        title = en.get(row.get("manager_link"))
        if title and not re.search(r"[–/]| y | e | and |-[A-ZÁÉÍÓÚ]\.? ", row["manager"]):   # dois treinadores: fica o texto da tabela
            row["manager_es"] = row["manager"]
            row["manager"] = re.sub(r"\s*\([^)]*\)$", "", title)
    for row in v["rows"]: keep_previous(comp, row)
if any(f.split(":")[0] in OLD and f.split(":")[0] not in out for f in failed): sys.exit(f"Falharam: {failed}")
short = [c for c, v in out.items() if len(v["rows"]) < MIN_ROWS.get(c, 50)]
if short: sys.exit(f"Tabelas de treinadores incompletas: {short}")   # a tarefa automática pára e não publica
json.dump(out, open(os.path.join(here, "wikipedia_managers.json"), "w"), ensure_ascii=False, indent=1)
