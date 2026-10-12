# Junta às finais da app os dados do jogo lidos por harvest_finals.py (finals_details.json):
# adversário, resultado, data, estádio, marcadores e desempate por penáltis, do lado do clube vencedor.
# Chamado por Tools/wikidata/convert.py depois do merge da Wikipédia.
import json, os, re
from merge import norm, core, end_year, ALIASES
here = os.path.dirname(os.path.abspath(__file__))

def apply(clubs, comps, honours):
    path = os.path.join(here, "finals_details.json")
    report = {"finais_com_jogo": 0, "finais_com_golos": 0, "sem_o_clube": [], "resultado_nao_bate": []}
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
            if legs and len(ms) == 2: a, b = sum(own), sum(opp)
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
            if legs and len(ms) == 2: final["aggregate"] = True
            elif len(ms) > 1: final["replay"] = True
            venue = None if legs and len(ms) == 2 else (last["venue"] or old.get("venue"))
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
