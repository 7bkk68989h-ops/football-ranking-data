# Converte os dados do Wikidata (vencedores.json) para o formato da app.
# Junta-os aos dados de base (base_sample.json): os clubes e cores que já existiam mantêm-se,
# e cada troféu fica com o maior dos dois totais (o Wikidata tem falhas; ver relatorio.md).
# Correr a partir da raiz: python3 Tools/wikidata/convert.py
import json, os, re, sys, collections, unicodedata, datetime
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(os.path.dirname(here))
sys.path.insert(0, here)
from clubs_known import SAMPLE_QIDS, MERGE_QIDS, COUNTRY_FIX, KNOWN

base = json.load(open(os.path.join(here, 'base_sample.json')))
wins = json.load(open(os.path.join(here, 'vencedores.json')))

COMP = {"por-liga": "pt-liga", "por-taca": "pt-taca", "por-taca-liga": "pt-tacaliga", "por-supertaca": "pt-supertaca",
        "esp-liga": "es-liga", "esp-taca": "es-copa", "ing-liga": "gb-liga", "ing-taca": "gb-fa", "ita-taca": "it-coppa",
        "ale-liga": "de-liga", "ale-taca": "de-pokal", "fra-liga": "fr-liga", "fra-taca": "fr-coupe", "hol-liga": "nl-liga",
        "bra-liga": "br-liga", "arg-liga": "ar-liga", "uefa-cl": "uefa-cl", "uefa-el": "uefa-el", "conmebol-lib": "conmebol-lib",
        "fifa-mundial-clubes": "fifa-cwc", "intercontinental": "fifa-ic"}
LEAGUES = {c["id"] for c in base["competitions"] if c["kind"] == "league"}

# Registos errados no Wikidata, retirados (competição de origem, ano, QID do clube).
WRONG = {("uefa-el", 2010, "Q18708"), ("fifa-mundial-clubes", 2008, "Q249643"), ("fifa-mundial-clubes", 2008, "Q736937"),
         ("conmebol-lib", 1991, "Q719338"), ("conmebol-lib", 1997, "Q604581"), ("conmebol-lib", 1998, "Q757418"),
         ("por-supertaca", 1980, "Q2895813"),
         # "Primeira Liga" do Brasil (Copa Sul-Minas-Rio), confundida com a liga portuguesa
         ("por-liga", 2016, "Q80987"), ("por-liga", 2017, "Q1633430")}
dropped = collections.Counter()
def keep(r):
    if r["competicao"] == "ita-liga": dropped["Serie A: o item do Wikidata é o campeonato feminino"] += 1; return False
    if re.search(r"Femminile|Women", r["clube"]): dropped["equipas femininas"] += 1; return False
    if r["competicao"] == "ing-liga" and r["ano"] >= 1993 and "First Division" in r["epoca"]:
        dropped["Inglaterra: campeões da segunda divisão depois de 1992"] += 1; return False
    if "Segunda" in r["epoca"]: dropped["segundas divisões"] += 1; return False
    if (r["competicao"], r["ano"], r["clube_qid"]) in WRONG: dropped["finalistas vencidos, clube sem nome ou prova trocada"] += 1; return False
    return True

def season_label(r, league):
    m = re.search(r"(\d{4})\s*[–\-/]\s*(\d{2,4})", r["epoca"])
    if m:
        a, b = int(m.group(1)), m.group(2)
        return f"{a}–{b}" if len(b) == 4 and a == 1999 else f"{a}–{int(b) % 100:02d}"
    if league and not r["competicao"].startswith(("bra", "arg")) and not re.search(r"\b(18|19|20)\d\d\b", r["epoca"]):
        return f"{r['ano'] - 1}–{r['ano'] % 100:02d}"
    m = re.search(r"\b((18|19|20)\d\d)\b", r["epoca"])
    return m.group(1) if m else str(r["ano"])

def slug(s):
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

STRIP = [r"\bFootball Club\b", r"\bFutebol Clube\b", r"\bFútbol Club\b", r"\bFutbol Club\b", r"\bClub de Fútbol\b", r"\bAssociation Football Club\b",
         r"\bFoot[- ]?Ball Club\b", r"\bF\.C\.", r"\bA\.F\.C\.", r"\bAFC\b", r"\bFC\b", r"\be\. V\.", r"\bClub Atlético\b", r"\bClube Atlético\b",
         r"\bSport Club\b", r"\bEsporte Clube\b", r"\bFootball Association\b", r"\bCalcio\b"]
def short_name(name):
    s = name
    for p in STRIP: s = re.sub(p, "", s)
    s = re.sub(r"\s+", " ", s).strip(" -–")
    return s or name

# --- clubes ---
clubs = {c["id"]: c for c in base["clubs"]}
qid_to_id = dict(SAMPLE_QIDS)
for q, cid in SAMPLE_QIDS.items(): clubs[cid]["wikidataId"] = q
records = []
for r in wins:
    if not keep(r): continue
    r = dict(r); r["clube_qid"] = MERGE_QIDS.get(r["clube_qid"], r["clube_qid"]); records.append(r)
neutral = 0
for r in records:
    q = r["clube_qid"]
    if q in qid_to_id: continue
    code = COUNTRY_FIX.get(q, r["pais_clube_codigo"])
    if q in KNOWN:
        short, abbr, c1, c2, kit = KNOWN[q]
    else:
        short = short_name(r["clube"]); neutral += 1
        abbr = re.sub(r"[^A-Za-zÀ-ÿ0-9]", "", short)[:3].upper(); c1, c2, kit = "#1B3FC2", "#C8D2E8", "plain"
    cid = slug(short) or q.lower()
    if cid in clubs: cid = f"{cid}-{q.lower()}"
    qid_to_id[q] = cid
    clubs[cid] = {"id": cid, "name": r["clube"], "shortName": short, "country": code, "colors": [c1, c2],
                  "kit": kit, "abbreviation": abbr, "wikidataId": q}
short_by_qid = {q: clubs[cid]["shortName"] for q, cid in qid_to_id.items()}

# --- troféus ---
comps = {c["id"]: c for c in base["competitions"]}
base_ids = set(comps)
honours = {(h["club"], h["competition"]): dict(h) for h in base["honours"]}
wd = collections.defaultdict(dict)   # (clube, competição) -> {época: registo}
for r in records:
    comp = COMP[r["competicao"]]
    if comp == "pt-taca" and "Campeonato de Portugal" in r["epoca"]: comp = "pt-campeonato"
    league = comp in LEAGUES
    label = season_label(r, league)
    if not league: label = label[:2] + label[-2:] if "–" in label and len(label) == 7 and int(label[-2:]) != 0 else label  # 1960–61 -> 1961
    if not league and "–" in label: label = str(r["ano"])
    wd[(qid_to_id[r["clube_qid"]], comp)].setdefault(label, r)

def final_of(label, r):
    fs = [f for f in r.get("finais", []) if f.get("adversario")]
    if not fs: return None
    f = fs[-1]
    out = {"season": label, "opponent": short_by_qid.get(f.get("adversario_qid"), short_name(f["adversario"]))}
    out["score"] = f"{f['golos_pro']}–{f['golos_contra']}" if f.get("golos_pro") is not None and f.get("golos_contra") is not None else ""
    if f.get("data") and not f["data"].endswith("-01-01"): out["date"] = f["data"]
    if f.get("adversario_pais_codigo"): out["opponentCountry"] = f["adversario_pais_codigo"]
    if f.get("penaltis_pro") is not None and f.get("penaltis_contra") is not None: out["penalties"] = f"{f['penaltis_pro']}–{f['penaltis_contra']}"
    if f.get("local"): out["venue"] = f["local"]
    return out

for key, by_season in wd.items():
    h = honours.setdefault(key, {"club": key[0], "competition": key[1]})
    seasons = sorted(by_season)
    if len(seasons) >= len(h.get("seasons", [])): h["seasons"] = seasons
    if key[1] not in LEAGUES:
        finals = [f for f in (final_of(s, by_season[s]) for s in seasons) if f]
        if len(finals) > len(h.get("finals", [])): h["finals"] = finals

# competição acrescentada pelas correções oficiais, para o conversor a conhecer
if "pt-campeonato" not in comps:
    comps["pt-campeonato"] = {"id": "pt-campeonato", "name": "Campeonato de Portugal", "level": "domestic", "kind": "cup", "country": "PT"}

# --- Wikipédia: completa e corrige o que o Wikidata não tem ---
sys.path.insert(0, os.path.join(os.path.dirname(here), "wikipedia"))
from merge import merge as wikipedia_merge
for c in clubs.values():
    if c["country"] == "GB": c["country"] = "GB-ENG"
for c in comps.values():
    if c.get("country") == "GB": c["country"] = "GB-ENG"
confed = {"PT": "UEFA", "ES": "UEFA", "GB-ENG": "UEFA", "GB-SCT": "UEFA", "IT": "UEFA", "DE": "UEFA", "FR": "UEFA", "NL": "UEFA", "AT": "UEFA",
          "RO": "UEFA", "RS": "UEFA", "AR": "CONMEBOL", "BR": "CONMEBOL", "UY": "CONMEBOL", "CO": "CONMEBOL", "PY": "CONMEBOL", "EC": "CONMEBOL",
          "CL": "CONMEBOL", "PE": "CONMEBOL", "MX": "CONCACAF", "EG": "CAF"}
# Campeonatos e taças de outros países (pedido do Pedro, 6 out. 2026): só existem na Wikipédia.
for cid, c in json.load(open(os.path.join(here, "extra_competitions.json"))).items():
    comps[cid] = {"id": cid, "name": c["name"], "level": "domestic", "kind": c["kind"], "country": c["country"]}
    confed.setdefault(c["country"], c["confederation"])
report, sources = wikipedia_merge(clubs, comps, honours, confed)

# Finais postas à mão, quando faltam nas duas fontes ou vêm sem resultado; substituem a da mesma época.
MANUAL_FINALS = {("chelsea", "fifa-cwc"): [
    {"season": "2021", "date": "2022-02-12", "opponent": "Palmeiras", "opponentCountry": "BR", "score": "2–1", "extraTime": True,
     "venue": "Mohammed Bin Zayed Stadium, Abu Dhabi"},
    {"season": "2025", "date": "2025-07-13", "opponent": "PSG", "opponentCountry": "FR", "score": "3–0",
     "venue": "MetLife Stadium, East Rutherford"}]}
for key, extra in MANUAL_FINALS.items():
    h = honours[key]; manual = {f["season"] for f in extra}
    h["finals"] = [f for f in h.get("finals", []) if f["season"] not in manual] + extra

used_clubs = {k[0] for k in honours}
used = sorted({c["country"] for c in clubs.values() if c["id"] in used_clubs})
missing = [u for u in used if not confed.get(u)]; assert not missing, missing
countries = [{"id": u, "name": u, "confederation": confed[u]} for u in used]
out = {"source": "Wikidata and Wikipedia.", "updated": datetime.date.today().isoformat(),
       "countries": countries, "competitions": [c for c in comps.values() if c["id"] != "pt-campeonato" and (c["id"] in base_ids or c["id"] in {k[1] for k in honours})],
       "clubs": [c for c in clubs.values() if c["id"] in used_clubs], "honours": list(honours.values())}
json.dump(out, open(os.path.join(root, 'FootballRanking/Resources/football_data.json'), 'w'), ensure_ascii=False, indent=1)
# Pacote que a app descarrega para se atualizar sem nova versão (dados + pontuação + correções).
res = os.path.join(root, 'FootballRanking/Resources')
bundle = {"updated": out["updated"], "dataset": out, "scoring": json.load(open(os.path.join(res, 'scoring.json'))),
          "officialCounts": json.load(open(os.path.join(res, 'official_counts.json')))}
os.makedirs(os.path.join(root, 'remote'), exist_ok=True)
json.dump(bundle, open(os.path.join(root, 'remote/data_bundle.json'), 'w'), ensure_ascii=False, separators=(",", ":"))
json.dump({"wikipedia": sources, "report": report}, open(os.path.join(here, 'merge_report.json'), 'w'), ensure_ascii=False, indent=1)
neutral = sum(1 for c in out["clubs"] if c["colors"] == ["#1B3FC2", "#C8D2E8"])
print(f"{len(out['clubs'])} clubes ({neutral} com escudo neutro), {len(countries)} países, {len(out['honours'])} linhas de troféus")
print("Wikidata, retirados:", dict(dropped))
print("Wikipédia:", {k: len(v) for k, v in report.items() if isinstance(v, list)}, "| sem país:", report["sem_pais"], "| excluídos:", report["excluidos"])
print("retirados pela Wikipédia:", report["retirados"])
print("treinadores:", report["treinadores"], "| sem época:", len(report["treinadores_sem_epoca"]), report["treinadores_sem_epoca"][:25])
