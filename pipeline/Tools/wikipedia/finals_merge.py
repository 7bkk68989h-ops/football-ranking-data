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
    for (club_id, comp_id), h in honours.items():
        comp = comps.get(comp_id); years = details.get(comp_id)
        if not years or comp is None or comp["kind"] == "league": continue
        club = clubs[club_id]
        labels = {}
        for s in h.get("seasons") or []: labels.setdefault(end_year(s), s)
        for f in h.get("finals") or []: labels[end_year(f["season"])] = f["season"]
        for year, label in sorted((y, l) for y, l in labels.items() if y):
            entry = years.get(str(year))
            if not entry: continue
            ms = entry["matches"]
            sides = [0 if is_club(m["team1"], club) else 1 if is_club(m["team2"], club) else None for m in ms]
            if None in sides: report["sem_o_clube"].append(f"{club['shortName']} {comp_id} {year} ({entry['title']})"); continue
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
                matches.append(d)
            final["matches"] = matches
            h["finals"] = [f for f in h.get("finals") or [] if end_year(f["season"]) != year] + [final]
            report["finais_com_jogo"] += 1
            report["finais_com_golos"] += any("goals" in d for d in matches)
        if h.get("finals"): h["finals"].sort(key=lambda f: end_year(f["season"]) or 0)
    return report
