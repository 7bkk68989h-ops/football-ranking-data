# Junta às finais da app os dados do jogo lidos por harvest_finals.py (finals_details.json):
# adversário, resultado, data, estádio, marcadores e desempate por penáltis, do lado do clube vencedor.
# Chamado por Tools/wikidata/convert.py depois do merge da Wikipédia.
import json, os, re
from merge import norm, core, end_year, ALIASES
here = os.path.dirname(os.path.abspath(__file__))

def apply(clubs, comps, honours):
    path = os.path.join(here, "finals_details.json")
    report = {"finais_com_jogo": 0, "finais_com_golos": 0, "sem_o_clube": [], "resultado_nao_bate": []}
    season_tables(clubs, comps, honours, report)
    if not os.path.exists(path): return report
    details = json.load(open(path))
    by_link = {c["_wiki"]: c for c in clubs.values() if c.get("_wiki")}
    def is_club(team, club):
        if team["link"] and team["link"] == club.get("_wiki"): return True
        names = {norm(club["shortName"]), norm(club["name"])}
        cands = [team["name"], team["link"] or ""]; cands += [ALIASES.get(x, x) for x in cands]
        return any(norm(x) in names for x in cands if x) or any(core(x) in (core(club["shortName"]), core(club["name"])) for x in cands if x)
    taken = {}   # competição -> anos já atribuídos a um clube
    for (club_id, comp_id), h in honours.items():
        for x in (h.get("seasons") or []) + [f["season"] for f in h.get("finals") or []]:
            if end_year(x): taken.setdefault(comp_id, set()).add(end_year(x))
    for comp_id in details: taken.setdefault(comp_id, set())
    for (club_id, comp_id), h in honours.items():
        comp = comps.get(comp_id); years = details.get(comp_id)
        if not years or comp is None or comp["kind"] == "league": continue
        club = clubs[club_id]
        labels = {}
        for s in h.get("seasons") or []: labels.setdefault(end_year(s), s)
        for f in h.get("finals") or []: labels[end_year(f["season"])] = f["season"]
        # Taças sem lista de anos (a tabela da Wikipédia só dá o total): o artigo da final diz quem ganhou,
        # por isso experimentam-se também os anos que nenhum clube tem atribuídos.
        titles = max(len(h.get("finals") or []), len(h.get("seasons") or []), h.get("count") or 0)
        guess = [] if len(labels) >= titles else [int(y) for y in years if int(y) not in labels and int(y) not in taken[comp_id]]
        for year, label in sorted([(y, l) for y, l in labels.items() if y] + [(y, None) for y in guess]):
            entry = years.get(str(year))
            if not entry: continue
            ms = entry["matches"]
            sides = [0 if is_club(m["team1"], club) else 1 if is_club(m["team2"], club) else None for m in ms]
            if None in sides:
                if label: report["sem_o_clube"].append(f"{club['shortName']} {comp_id} {year} ({entry['title']})")
                continue
            if label is None:   # ano por confirmar: só se este clube ganhou mesmo o jogo
                o = sum(m["score"][x] for m, x in zip(ms, sides)) if len(ms) == 2 and sides[0] != sides[1] else ms[-1]["score"][sides[-1]]
                q = sum(m["score"][1 - x] for m, x in zip(ms, sides)) if len(ms) == 2 and sides[0] != sides[1] else ms[-1]["score"][1 - sides[-1]]
                pk = ms[-1]["penscore"]
                if not (o > q or (o == q and pk and pk[sides[-1]] > pk[1 - sides[-1]])) or len(labels) >= titles: continue
                label = str(year); labels[year] = label; report["anos_descobertos"] = report.get("anos_descobertos", 0) + 1
            taken[comp_id].add(year)
            own = [m["score"][s] for m, s in zip(ms, sides)]; opp = [m["score"][1 - s] for m, s in zip(ms, sides)]
            legs = len(ms) >= 2 and sides[0] != sides[1]
            last = ms[-1]; ls = sides[-1]
            two = legs and len(ms) in (2, 4)   # duas mãos; com quatro jogos, a eliminatória repetiu-se (Supertaça de 1984)
            if two: a, b = sum(own[-2:]), sum(opp[-2:])
            else: a, b = own[-1], opp[-1]
            pens = None
            if last["penscore"]: pens = (last["penscore"][ls], last["penscore"][1 - ls])
            if a < b or (pens and pens[0] < pens[1]):   # o clube não ganhou este jogo: artigo de outra edição
                report["resultado_nao_bate"].append(f"{club['shortName']} {comp_id} {year} ({entry['title']})"); continue
            other = last["team2"] if ls == 0 else last["team1"]
            known = by_link.get(other["link"]) if other["link"] else None
            old = next((f for f in h.get("finals") or [] if end_year(f["season"]) == year), {})
            final = {"season": label, "opponent": known["shortName"] if known else other["name"], "score": f"{a}–{b}"}
            date = last["date"] or old.get("date")
            if date: final["date"] = date
            country = other["country"] or (known["country"] if known else None) or old.get("opponentCountry")
            if comp["level"] != "domestic" and country: final["opponentCountry"] = country
            if last["aet"]: final["extraTime"] = True
            if pens: final["penalties"] = f"{pens[0]}–{pens[1]}"
            if two: final["aggregate"] = True
            if len(ms) > 2 or (len(ms) == 2 and not two): final["replay"] = True
            venue = None if two else (last["venue"] or old.get("venue"))
            if venue: final["venue"] = venue
            matches = []
            for m, s in zip(ms, sides):
                d = {"score": f"{m['score'][s]}–{m['score'][1 - s]}"}
                if m["date"]: d["date"] = m["date"]
                if m["venue"]: d["venue"] = m["venue"]
                if m["aet"]: d["extraTime"] = True
                if m["penscore"]: d["penalties"] = f"{m['penscore'][s]}–{m['penscore'][1 - s]}"
                goals = [{"minute": g["minute"], "player": g["player"], "own": side == s, **({"note": g["note"]} if g.get("note") else {})}
                         for side, key in ((0, "goals1"), (1, "goals2")) for g in m[key]]
                # só se os marcadores batem com o resultado; uma lista incompleta enganava
                if goals and len(goals) == sum(m["score"]): d["goals"] = goals
                # pela ordem em que foram batidos: um de cada equipa, alternadamente
                kicks = [{"player": k["player"], "own": side == s, "scored": k["scored"]}
                         for i in range(max(len(m["pens1"]), len(m["pens2"]))) for side, key in ((0, "pens1"), (1, "pens2")) for k in m[key][i:i + 1]]
                if kicks and m["penscore"] and sum(1 for k in kicks if k["scored"]) == sum(m["penscore"]): d["shootout"] = kicks
                if m.get("attendance"): d["attendance"] = m["attendance"]
                if m.get("referee"): d["referee"] = m["referee"]
                if m.get("lineup1"):   # onzes: titulares e só os suplentes que entraram
                    def sheet(t):
                        keep = ("name", "number", "captain", "yellow", "red", "off", "on")
                        out = {"starters": [{k: p[k] for k in keep if k in p} for p in t["start"]]}
                        used = [{k: p[k] for k in keep if k in p} for p in t["sub"] if "on" in p]
                        if used: out["substitutes"] = used
                        if t["coach"]: out["coach"] = t["coach"]
                        return out
                    d["lineups"] = {"own": sheet(m["lineup1"] if s == 0 else m["lineup2"]), "opponent": sheet(m["lineup2"] if s == 0 else m["lineup1"])}
                    report["finais_com_onzes"] = report.get("finais_com_onzes", 0) + 1
                matches.append(d)
            final["matches"] = matches
            h["finals"] = [f for f in h.get("finals") or [] if end_year(f["season"]) != year] + [final]
            report["finais_com_jogo"] += 1
            report["finais_com_golos"] += any("goals" in d for d in matches)
        if h.get("finals"): h["finals"].sort(key=lambda f: end_year(f["season"]) or 0)
    wikidata(clubs, comps, honours, report)
    pt_taca(clubs, comps, honours, report)
    return report

FINAL = re.compile(r"final|finale|super|intercontinental|recopa", re.I)
def wikidata(clubs, comps, honours, report):
    """Segunda fonte (o Pedro, 12 out. 2026: validar sempre nas duas): os jogos de finais do Wikidata.
    Onde a Wikipédia já deu o jogo, confirma o resultado e completa assistência e árbitro; onde não deu,
    cria a final com adversário, resultado, data, estádio, assistência e árbitro (sem marcadores)."""
    wd = os.path.join(os.path.dirname(here), "wikidata")
    if not os.path.exists(os.path.join(wd, "wikidata_finals.json")): return
    finals = json.load(open(os.path.join(wd, "wikidata_finals.json"))); qids = json.load(open(os.path.join(wd, "club_qids.json")))
    by_q = {}
    for c in clubs.values():
        q = qids.get(c.get("_wiki") or "")
        if q: by_q.setdefault(q, c)
    report.update({"wikidata_novas": 0, "wikidata_confirmam": 0, "wikidata_completam": 0, "wikidata_divergem": []})
    for comp_id, matches in finals.items():
        comp = comps.get(comp_id)
        if comp is None or comp["kind"] == "league": continue
        groups = {}
        for m in matches:
            if FINAL.search(m["label"] or "") and not re.search(r"semi|quarter", m["label"] or "", re.I): groups.setdefault((m["year"], m["winner"]), []).append(m)
        for (year, winner), ms in sorted(groups.items()):
            club = by_q.get(winner); h = honours.get((club["id"], comp_id)) if club else None
            if h is None or len(ms) > 2: continue
            ms.sort(key=lambda m: m["date"] or "")
            def side(m):
                own = next((t for t in m["teams"] if t["qid"] == winner), None); opp = next((t for t in m["teams"] if t["qid"] != winner), None)
                return own, opp
            pairs = [side(m) for m in ms]
            if any(o is None or p is None for o, p in pairs): continue
            known = all(o["goals"] is not None and p["goals"] is not None for o, p in pairs)
            a = sum(o["goals"] for o, p in pairs) if known else None; b = sum(p["goals"] for o, p in pairs) if known else None
            if known and a < b: continue
            score = f"{a}–{b}" if known else None
            old = next((f for f in h.get("finals") or [] if end_year(f["season"]) == year), None)
            last = ms[-1]
            if old and old.get("matches"):   # as duas fontes têm o jogo: comparar e completar
                if score and len(old["matches"]) == len(ms):
                    x, y = old["score"].split("–")
                    if old["score"] == score: report["wikidata_confirmam"] += 1
                    elif x == y and not old.get("penalties") and a > b and len(ms) == 1:
                        # empate sem penáltis na Wikipédia e vitória no Wikidata: houve jogo de repetição
                        old["matches"].append({"score": score, **{k: last[k] for k in ("date", "venue", "attendance", "referee") if last.get(k)}})
                        old["score"] = score; old["replay"] = True
                        if last["date"]: old["date"] = last["date"]
                        report["wikidata_completam"] += 1; continue
                    else: report["wikidata_divergem"].append(f"{club['shortName']} {comp_id} {year}: Wikipédia {old['score']}, Wikidata {score}")
                if len(old["matches"]) == len(ms):
                    for d, m in zip(old["matches"], ms):
                        for k in ("attendance", "referee"):
                            if m.get(k) and not d.get(k): d[k] = m[k]; report["wikidata_completam"] += 1
                continue
            labels = {end_year(x): x for x in (h.get("seasons") or [])}
            titles = max(len(h.get("finals") or []), len(h.get("seasons") or []), h.get("count") or 0)
            if year not in labels and (labels and len(labels) >= titles or len(h.get("finals") or []) >= titles): continue
            if not score and not old: continue
            opp = pairs[-1][1]; known_opp = by_q.get(opp["qid"])
            final = dict(old or {}); final.update({"season": (old or {}).get("season") or labels.get(year) or str(year),
                                                   "opponent": known_opp["shortName"] if known_opp else opp["label"]})
            if score: final["score"] = score
            final.setdefault("score", "")
            if last["date"]: final["date"] = last["date"]
            if len(ms) == 2: final["aggregate"] = True
            elif last.get("venue"): final["venue"] = last["venue"]
            if comp["level"] != "domestic" and known_opp and not final.get("opponentCountry"): final["opponentCountry"] = known_opp["country"]
            if score:
                final["matches"] = [{"score": f"{o['goals']}–{p['goals']}", **{k: m[k] for k in ("date", "venue", "attendance", "referee") if m.get(k)}}
                                    for m, (o, p) in zip(ms, pairs)]
            h["finals"] = sorted([f for f in h.get("finals") or [] if end_year(f["season"]) != year] + [final], key=lambda f: end_year(f["season"]) or 0)
            report["wikidata_novas"] += 1

def pt_taca(clubs, comps, honours, report):
    """Taça de Portugal e Campeonato de Portugal (o Pedro, 13 out. 2026): a época ("1938–39") em vez do ano
    da final, pela tabela de finais da Wikipédia em português (pt_taca_finals.json). Onde a final já tem o
    jogo, só muda a época e compara-se o resultado; onde não tem, a tabela dá adversário, resultado e local."""
    path = os.path.join(here, "pt_taca_finals.json")
    if not os.path.exists(path): return
    pt = {}
    for c in clubs.values():
        if c["country"] == "PT": pt.setdefault(norm(c["shortName"]), c)
    def club_of(name): return pt.get(norm(ALIASES.get(name, name)))
    rep = report["taca_de_portugal"] = {"epocas": 0, "finais_novas": 0, "vencedor_diferente": [], "resultado_diferente": [], "fora_da_tabela": []}
    for comp_id, rows in json.load(open(path))["finals"].items():
        seen = set()
        for row in rows:
            year = end_year(row["season"]); club = club_of(row["winner"])
            h = honours.get((club["id"], comp_id)) if club else None
            if h is None or year not in {end_year(x) for x in (h.get("seasons") or []) + [f["season"] for f in h.get("finals") or []]}:
                rep["vencedor_diferente"].append(f"{comp_id} {row['season']}: {row['winner']}"); continue
            seen.add((club["id"], year)); rep["epocas"] += 1
            if h.get("seasons"): h["seasons"] = [row["season"] if end_year(x) == year else x for x in h["seasons"]]
            ms = row["matches"]; last = ms[-1]
            score = f"{last['score'][0]}–{last['score'][1]}"
            pens = f"{last['penalties'][0]}–{last['penalties'][1]}" if last.get("penalties") else None
            old = next((f for f in h.get("finals") or [] if end_year(f["season"]) == year), None)
            other = club_of(row["runnerUp"])
            if old and old.get("matches"):
                old["season"] = row["season"]
                if other: old["opponent"] = other["shortName"]
                if old["score"] != score or old.get("penalties") != pens:
                    rep["resultado_diferente"].append(f"{club['shortName']} {comp_id} {row['season']}: tinha {old['score']} {old.get('penalties') or ''}, a tabela diz {score} {pens or ''}".replace("  ", " ").strip())
                continue
            final = {k: v for k, v in (old or {}).items() if k in ("date",)}
            final.update({"season": row["season"], "opponent": other["shortName"] if other else row["runnerUp"], "score": score})
            if last.get("extraTime"): final["extraTime"] = True
            if pens: final["penalties"] = pens
            if last.get("venue"): final["venue"] = last["venue"]
            if len(ms) > 1:   # final repetida: os dois jogos, para se ver o primeiro resultado
                final["replay"] = True
                final["matches"] = [{"score": f"{m['score'][0]}–{m['score'][1]}", **({"extraTime": True} if m.get("extraTime") else {}),
                                     **({"venue": m["venue"]} if m.get("venue") else {})} for m in ms]
            h["finals"] = sorted([f for f in h.get("finals") or [] if end_year(f["season"]) != year] + [final], key=lambda f: end_year(f["season"]) or 0)
            rep["finais_novas"] += 1
        for (club_id, c), h in honours.items():   # títulos que a app tem e a tabela não
            if c != comp_id: continue
            for x in {end_year(x) for x in (h.get("seasons") or []) + [f["season"] for f in h.get("finals") or []]}:
                if (club_id, x) not in seen: rep["fora_da_tabela"].append(f"{clubs[club_id]['shortName']} {comp_id} {x}")


# Nomes das tabelas época a época que não são os do clube na app (nome da época -> nome curto).
SEASON_ALIASES = {
 "Dynamo Kiev": "Dynamo Kyiv", "Dnipro Dnipropetrovsk": "Dnipro", "Litex Lovech": "Lovech", "AS 23 Sofia": "AS-23",
 "Accra Hearts of Oak": "Hearts of Oak", "Accra Hearts of Oak SC": "Hearts of Oak", "Kumasi Cornerstones": "Cornerstones",
 "Sekondi Eleven Wise": "Eleven Wise", "Thai Port": "Port", "Waterschei": "SV Thor Waterschei", "RC Bruxelles": "Racing de Bruxelles",
 "RFC Liège": "Liégeois", "Parthenay Lion Yaoundé": "Lion Yaoundé", "Ajax Cape Town": "Cape Town Spurs / Ajax Cape Town",
 "Shandong Luneng Taishan": "Shandong Taishan", "Jinan Taishan": "Shandong Taishan", "Shanghai Greenland Shenhua": "Shanghai Shenhua",
 "Shanghai": "Shanghai Shenhua", "Beijing Sinobo Guoan": "Beijing Guoan", "Beijing": "Beijing Guoan", "Tianjin TEDA": "Tianjin Jinmen Tiger",
 "Guangzhou Evergrande": "Guangzhou", "Guangzhou Evergrande Taobao": "Guangzhou", "Guizhou Renhe": "Beijing Renhe", "Jiangsu Guoxin Sainty": "Jiangsu",
 "Chongqing Longxin": "Chongqing Liangjiang Athletic", "Qingdao Hademen": "Qingdao Hainiu", "Vladislav Varna": "Vladislav",
 "Kansas City Wizards": "Sporting Kansas City", "Al Ahli Doha": "Al-Ahli", "Al-Gharafa": "Al-Gharrafa", "Al-Duhail": "Al Duhail", "Lekhwiya": "Al Duhail", "Umm-Salal SC": "Umm-Salal",
 "Seoul Police Department": "National Police Department", "Ulsan Hyundai Horang-i": "Ulsan HD", "Ulsan Hyundai": "Ulsan HD",
}

# Quando dois clubes da app têm o mesmo nome na tabela: (competição, época, nome) -> clube.
# Totais da tabela por clube da Wikipédia que as outras fontes desmentem: Shakhtyor Soligorsk tem 4 campeonatos
# (2005, 2020, 2021, 2022) na lista época a época, e no Wikidata, e só 3 na tabela por clube.
COUNT_FIX = {("by-liga", "Shakhtyor Soligorsk"): 4}
# Épocas que só a tabela por clube da Wikipédia dá (a lista época a época atribui-as a outro clube):
# Donmoon, Taça da Tailândia de 1981 (a lista dá 1981 ao Bangkok Bank, que já tem os seus 3 anos).
SEASON_EXTRA = {("th-taca", "Donmoon"): ["1981"]}
SEASON_FIX = {("si-taca", "1994–95", "Mura"): "Mura", ("si-taca", "2019–20", "Mura"): "NŠ Mura"}

def season_tables(clubs, comps, honours, report):
    """Épocas (e, nas taças, adversário, resultado, penáltis e local) de season_tables.json, lidas por
    harvest_seasons.py das tabelas época a época da Wikipédia, para os títulos que só tinham o total
    (o aviso "Details of these titles will come from Wikidata", pedido do Pedro, 13 out. 2026)."""
    path = os.path.join(here, "season_tables.json")
    if not os.path.exists(path): return
    rep = report["epocas_wikipedia"] = {"preenchidas": {}, "titulos_a_mais": [], "sem_clube": [], "sem_epocas": []}
    for comp_id, rows in json.load(open(path)).items():
        comp = comps.get(comp_id)
        if comp is None: continue
        mine = {k[0]: h for k, h in honours.items() if k[1] == comp_id}
        cands = [clubs[c] for c in mine]
        def find(name, link):
            if name in SEASON_ALIASES: link = None
            if link:
                hit = [c for c in cands if c.get("_wiki") == link]
                if hit: return hit[0]
            name = SEASON_ALIASES.get(name, name)
            t = norm(ALIASES.get(name, name))
            hit = [c for c in cands if t in (norm(c["shortName"]), norm(c["name"]))]
            if len(hit) == 1: return hit[0]
            w = core(ALIASES.get(name, name))
            hit = [c for c in cands if w in (core(c["shortName"]), core(c["name"]))]
            return hit[0] if len(hit) == 1 else None
        won = {}; lost = []
        for r in rows:
            for i, w in enumerate(r["winners"]):
                fix = SEASON_FIX.get((comp_id, r["season"], w))
                c = next((c for c in cands if c["shortName"] == fix), None) if fix else find(w, r["winnerLinks"][0] if len(r["winners"]) == 1 else None)
                if c is None: lost.append(f"{r['season']} {w}"); continue
                won.setdefault(c["id"], []).append((r, len(r["winners"]) == 1))
        rep["sem_clube"] += [f"{comp_id} {x}" for x in lost]
        filled = 0
        for club_id, items in won.items():
            h = mine[club_id]
            titles = max(len(h.get("finals") or []), len(h.get("seasons") or []), h.get("count") or 0)
            if h.get("seasons") or h.get("finals"): continue   # já tem épocas: não se mexe
            if (comp_id, clubs[club_id]["shortName"]) in COUNT_FIX:
                titles = h["count"] = COUNT_FIX[(comp_id, clubs[club_id]["shortName"])]; rep.setdefault("total_corrigido", []).append(f"{clubs[club_id]['shortName']} {comp_id}: {titles}")
            seen = {}
            for r, solo in items: seen.setdefault(r["season"], (r, solo))
            if 0 < len(seen) - titles <= 2 and comp_id == "pl-liga":
                # campeonatos de antes da liga (Warta 1913–14) ou do tempo da guerra (Polonia 1942–43) que a tabela
                # por clube da Wikipédia não conta: ficam os últimos, tantos quantos os títulos
                dropped = sorted(seen, key=lambda y: end_year(y) or 0)[:len(seen) - titles]
                rep.setdefault("nao_oficiais", []).append(f"{clubs[club_id]['shortName']} {comp_id}: {dropped}")
                for y in dropped: del seen[y]
            if len(seen) > titles:
                rep["titulos_a_mais"].append(f"{clubs[club_id]['shortName']} {comp_id}: {len(seen)} épocas para {titles} títulos"); continue
            h["seasons"] = sorted(seen, key=lambda y: end_year(y) or 0)
            if len(seen) < titles: rep["sem_epocas"].append(f"{clubs[club_id]['shortName']} {comp_id}: {len(seen)} de {titles}")
            filled += titles
            if comp["kind"] == "league": continue
            finals = []
            for r, solo in seen.values():
                if "score" not in r and not r.get("runnerUp"): continue
                opp = r.get("runnerUp"); oc = find(opp, r.get("runnerUpLink")) if opp else None
                f = {"season": r["season"], "opponent": (oc["shortName"] if oc else opp) or "", "score": ""}
                if "score" in r:
                    a, b = r["score"]; f["score"] = f"{a}–{b}"
                    if a < b and not r.get("penalties"): f["score"] = f"{b}–{a}"   # a tabela às vezes põe o vencido primeiro
                if r.get("extraTime"): f["extraTime"] = True
                if r.get("penalties"): f["penalties"] = f"{r['penalties'][0]}–{r['penalties'][1]}"
                if r.get("replay"): f["replay"] = True
                if r.get("aggregate"): f["aggregate"] = True   # duas mãos: o local e o jogo seriam só os da primeira
                if r.get("venue") and (not r.get("aggregate") or comp_id.startswith("hr-")): f["venue"] = r["venue"]   # Croácia: a tabela dá os dois estádios
                if f["score"]:
                    m = {"score": f["score"]}
                    for k in ("extraTime", "penalties", "venue"):
                        if k in f: m[k] = f[k]
                    f["matches"] = [m]
                finals.append(f)
            if finals: h["finals"] = sorted(finals, key=lambda f: end_year(f["season"]) or 0)
        for club_id, h in mine.items():
            extra = SEASON_EXTRA.get((comp_id, clubs[club_id]["shortName"]))
            if extra and not h.get("seasons") and not h.get("finals"): h["seasons"] = extra; filled += len(extra); rep.setdefault("so_na_tabela_por_clube", []).append(f"{clubs[club_id]['shortName']} {comp_id}: {extra}")
        rep["preenchidas"][comp_id] = filled
