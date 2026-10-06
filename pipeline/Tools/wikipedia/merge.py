# Junta os títulos da Wikipédia (wikipedia_titles.json) aos dados da app.
# Nas competições que a Wikipédia cobre, o total e os anos da Wikipédia passam a valer:
# corrigem as falhas do Wikidata e os totais aproximados que existiam antes.
import json, os, re, unicodedata, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(here), "wikidata"))
from clubs_known import KNOWN

# país (como a Wikipédia o escreve na bandeira) -> (código, nome em inglês, confederação)
COUNTRIES = {
 "Portugal": ("PT", "UEFA"), "Spain": ("ES", "UEFA"), "England": ("GB-ENG", "UEFA"), "Scotland": ("GB-SCT", "UEFA"), "Italy": ("IT", "UEFA"),
 "Germany": ("DE", "UEFA"), "West Germany": ("DE", "UEFA"), "East Germany": ("DE", "UEFA"), "France": ("FR", "UEFA"), "Netherlands": ("NL", "UEFA"),
 "Belgium": ("BE", "UEFA"), "Austria": ("AT", "UEFA"), "Romania": ("RO", "UEFA"), "Turkey": ("TR", "UEFA"), "Russia": ("RU", "UEFA"),
 "Ukraine": ("UA", "UEFA"), "Sweden": ("SE", "UEFA"), "Greece": ("GR", "UEFA"), "Israel": ("IL", "UEFA"),
 "Socialist Federal Republic of Yugoslavia": ("RS", "UEFA"), "Yugoslavia": ("RS", "UEFA"), "Serbia": ("RS", "UEFA"), "Czechoslovakia": ("SK", "UEFA"),
 "Argentina": ("AR", "CONMEBOL"), "Brazil": ("BR", "CONMEBOL"), "Uruguay": ("UY", "CONMEBOL"), "Colombia": ("CO", "CONMEBOL"),
 "Ecuador": ("EC", "CONMEBOL"), "Chile": ("CL", "CONMEBOL"), "Paraguay": ("PY", "CONMEBOL"), "Peru": ("PE", "CONMEBOL"), "Mexico": ("MX", "CONCACAF"),
 "Egypt": ("EG", "CAF"), "Tunisia": ("TN", "CAF"), "Morocco": ("MA", "CAF"), "Cameroon": ("CM", "CAF"), "Algeria": ("DZ", "CAF"),
 "Democratic Republic of the Congo": ("CD", "CAF"), "Ghana": ("GH", "CAF"), "South Africa": ("ZA", "CAF"), "Ivory Coast": ("CI", "CAF"),
 "Guinea": ("GN", "CAF"), "Nigeria": ("NG", "CAF"), "Republic of the Congo": ("CG", "CAF"),
 "South Korea": ("KR", "AFC"), "Japan": ("JP", "AFC"), "Iran": ("IR", "AFC"), "China": ("CN", "AFC"), "United Arab Emirates": ("AE", "AFC"),
 "Qatar": ("QA", "AFC"), "Thailand": ("TH", "AFC"), "Australia": ("AU", "AFC"), "Saudi Arabia": ("SA", "AFC"),
}
# Casos em que a bandeira é de um país que já não existe e o clube é de outro país atual.
CLUB_COUNTRY = {"Dynamo Kyiv": "UA", "Dinamo Tbilisi": "GE", "Slovan Bratislava": "SK", "Red Star Belgrade": "RS", "1. FC Magdeburg": "DE"}
EXTRA_COUNTRIES = {"GE": "UEFA"}
EXCLUDED = {"SA"}   # o Pedro pediu para tirar a Arábia Saudita (3 out. 2026)
SKIP_ROWS = {"Total", "Totals"}
# Campeonatos jogados em duas metades de ano cuja página só dá o ano final: mostram-se como "2003–04".
END_YEAR_LEAGUES = {"pt-liga"}

# nome na Wikipédia -> nome curto que o clube já tem na app
ALIASES = {
 "Bayern Munich": "Bayern", "Inter Milan": "Inter", "Internazionale": "Inter", "Vitória de Guimarães": "Vitória SC", "Athletic Bilbao": "Athletic",
 "Zaragoza": "Real Zaragoza", "Wolverhampton Wanderers": "Wolves", "Borussia Mönchengladbach": "Mönchengladbach", "1860 Munich": "1860 München",
 "Reims": "Stade de Reims", "Steaua București": "FCSB", "Oxford University": "Oxford University A.", "1. FC Lokomotive Leipzig": "Lokomotive Leipzig",
 "Kickers Offenbach": "Offenbacher Fußball-Club Kickers 1901", "Schwarz-Weiss Essen": "Schwarz-Weiß Essen", "SpVg Blau-Weiß 90 Berlin": "SpVgg Blau-Weiß 1890 Berlin",
 "Roubaix-Tourcoing": "Club Olympique Roubaix-Tourcoing", "CA Paris": "Cercle Athlétique de Paris-Charenton", "Roubaix": "Excelsior AC Roubaix",
 "Nancy-Lorraine": "Équipe fédérale Nancy-Lorraine", "RAP": "RAP Amsterdam", "DWS": "Door Wilskracht Sterk", "Roda JC Kerkrade": "Roda JC",
 "Be Quick": "Be Quick 1887", "SC Enschede": "Sportclub Enschede", "De Volewijckers": "A.V.V. De Volewijckers", "SVV": "Schiedamse Voetbal Vereniging",
 "HFC": "Koninklijke HFC", "Haarlem": "HFC Haarlem", "Concordia": "VV Concordia", "Dock Sud": "Club Sportivo Dock Sud", "St. Andrew's": "St. Andrew's Athletic Club",
 "Sport": "Sport Recife", "CURCC / Peñarol": "Peñarol", "Al Ahly SC": "Al Ahly", "Zamalek SC": "Zamalek", "Manchester Utd": "Manchester United",
 "Quick": "Quick Den Haag", "Ismaily SC": "Ismaily", "Tersana SC": "Tersana", "Ghazl El Mahalla SC": "Ghazl El Mahalla",
 "Al Mokawloon Al Arab SC": "Al Mokawloon", "Sporting": "Sporting CP", "Ambrosiana-Inter": "Inter", "Ambrosiana": "Inter",
 "SL Benfica": "Benfica", "Madrid FC": "Real Madrid", "The Wednesday": "Sheffield Wednesday", "Atlético Paranaense": "Athletico Paranaense",
 "Olympique Lillois": "Lille", "Atlético Aviación": "Atlético Madrid", "Atlético de Madrid": "Atlético Madrid", "Athletic Club": "Athletic", "Toulouse (1937)": "Toulouse FC (1937)", "FC Groningen": "Groningen", "Hafia FC": "Hafia",
}
# Clubes austríacos que ganharam provas alemãs entre 1938 e 1943: são o mesmo clube, não um clube alemão.
FOREIGN_WINNERS = {"Rapid Wien", "First Vienna"}
# Cores, padrão e iniciais de clubes que só vêm da Wikipédia (nome curto -> iniciais, cor 1, cor 2, padrão).
EXTRA_KNOWN = {
 "Rangers": ("RAN", "#1B458F", "#FFFFFF", "plain"), "Aberdeen": ("ABE", "#E2001A", "#FFFFFF", "plain"), "Anderlecht": ("AND", "#51318F", "#FFFFFF", "plain"),
 "KV Mechelen": ("KVM", "#FFD100", "#E2001A", "stripes"), "Galatasaray": ("GAL", "#A90432", "#FDB912", "halves"), "CSKA Moscow": ("CSK", "#E2001A", "#0A3F86", "halves"),
 "Zenit Saint Petersburg": ("ZEN", "#0098D4", "#FFFFFF", "plain"), "Shakhtar Donetsk": ("SHA", "#F58113", "#111111", "stripes"), "Dynamo Kyiv": ("DYK", "#FFFFFF", "#0A5EB0", "plain"),
 "IFK Göteborg": ("IFK", "#0A5EB0", "#FFFFFF", "stripes"), "Olympiacos": ("OLY", "#E2001A", "#FFFFFF", "stripes"), "Slovan Bratislava": ("SLO", "#6CABDD", "#FFFFFF", "plain"),
 "Dinamo Tbilisi": ("DTB", "#0A3F86", "#FFFFFF", "plain"), "1. FC Magdeburg": ("FCM", "#0A5EB0", "#FFFFFF", "plain"),
 "Cagliari": ("CAG", "#A21C26", "#1A2F48", "halves"), "Hellas Verona": ("VER", "#FFD100", "#0A3F86", "plain"), "Pro Vercelli": ("PRO", "#FFFFFF", "#111111", "plain"),
 "Casale": ("CAS", "#111111", "#FFFFFF", "plain"), "Novese": ("NOV", "#6CABDD", "#FFFFFF", "plain"),
 "Vitesse": ("VIT", "#FFD100", "#111111", "stripes"), "Heerenveen": ("HEE", "#0A5EB0", "#FFFFFF", "stripes"), "Groningen": ("GRO", "#00843D", "#FFFFFF", "stripes"),
 "PEC Zwolle": ("PEC", "#0A5EB0", "#FFFFFF", "plain"), "Venlo": ("VVV", "#FFD100", "#111111", "plain"),
 "Birmingham City": ("BIR", "#0A3F86", "#FFFFFF", "plain"), "Queens Park Rangers": ("QPR", "#1D5BA4", "#FFFFFF", "hoops"), "Stoke City": ("STK", "#E03A3E", "#FFFFFF", "stripes"),
 "Luton Town": ("LUT", "#F78F1E", "#0A2240", "plain"), "Swindon Town": ("SWI", "#E2001A", "#FFFFFF", "plain"), "Oxford United": ("OXU", "#FFD100", "#0A2240", "plain"),
 "Swansea City": ("SWA", "#FFFFFF", "#111111", "plain"),
 "San Lorenzo": ("SLO", "#0A3F86", "#E2001A", "stripes"), "Gimnasia y Esgrima": ("GEL", "#FFFFFF", "#0A3F86", "band"), "Platense": ("PLA", "#FFFFFF", "#5B3A29", "band"),
 "Belgrano": ("BEL", "#6CABDD", "#FFFFFF", "plain"), "Chacarita Juniors": ("CHA", "#E2001A", "#111111", "stripes"), "Arsenal": ("ARS", "#6CABDD", "#E2001A", "sash"),
 "Defensa y Justicia": ("DYJ", "#FFD100", "#00843D", "plain"), "Criciúma": ("CRI", "#FFD100", "#111111", "plain"), "Juventude": ("JUV", "#00843D", "#FFFFFF", "stripes"),
 "Chapecoense": ("CHA", "#00843D", "#FFFFFF", "plain"), "Defensor Sporting": ("DEF", "#5F2C83", "#FFFFFF", "plain"), "Danubio": ("DAN", "#FFFFFF", "#111111", "sash"),
 "Montevideo Wanderers": ("WAN", "#111111", "#FFFFFF", "stripes"), "River Plate FC": ("RPL", "#E2001A", "#FFFFFF", "stripes"), "Liverpool": ("LIV", "#111111", "#0A5EB0", "stripes"),
 "Colo-Colo": ("COL", "#FFFFFF", "#111111", "plain"), "Universidad de Chile": ("UCH", "#0A3F86", "#E2001A", "plain"), "Independiente del Valle": ("IDV", "#111111", "#0A5EB0", "stripes"),
 "Cienciano": ("CIE", "#E2001A", "#FFFFFF", "plain"), "Santa Fe": ("SFE", "#E2001A", "#FFFFFF", "plain"), "Pachuca": ("PAC", "#0A3F86", "#FFFFFF", "stripes"),
 "Zamalek": ("ZAM", "#FFFFFF", "#E2001A", "band"), "Ismaily": ("ISM", "#FFD100", "#0A5EB0", "plain"), "TP Mazembe": ("TPM", "#111111", "#FFFFFF", "stripes"),
 "ES Tunis": ("EST", "#E2001A", "#FFD100", "stripes"), "Wydad AC": ("WAC", "#E2001A", "#FFFFFF", "plain"), "Raja CA": ("RCA", "#00843D", "#FFFFFF", "plain"),
 "Mamelodi Sundowns": ("SUN", "#FFD100", "#0A5EB0", "plain"), "Orlando Pirates": ("ORL", "#111111", "#FFFFFF", "plain"), "JS Kabylie": ("JSK", "#FFD100", "#00843D", "plain"),
 "Urawa Red Diamonds": ("URA", "#E2001A", "#111111", "plain"), "Kashima Antlers": ("KAS", "#B8193F", "#0A2240", "plain"), "Pohang Steelers": ("POH", "#E2001A", "#111111", "hoops"),
 "Jeonbuk Hyundai Motors": ("JEO", "#00843D", "#FFD100", "plain"), "Ulsan HD": ("ULS", "#0A5EB0", "#FFD100", "plain"), "Esteghlal": ("EST", "#0A5EB0", "#FFFFFF", "plain"),
 "Al Ain": ("AIN", "#5F2C83", "#FFFFFF", "plain"), "Al-Sadd": ("SAD", "#FFFFFF", "#111111", "plain"), "Guangzhou": ("GUA", "#E2001A", "#FFD100", "plain"),
 "Maccabi Tel Aviv": ("MTA", "#FFD100", "#0A5EB0", "plain"), "Hapoel Tel Aviv": ("HTA", "#E2001A", "#FFFFFF", "plain"), "Gamba Osaka": ("GAM", "#0A3F86", "#111111", "stripes"),
 "Western Sydney Wanderers": ("WSW", "#E2001A", "#111111", "hoops"),
}

def norm(s):
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(fc|cf|ac|sc|afc|club|football|futebol|clube|de|sv|fk|as|ss|us|cd|ca|sk|1\.)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

STOP = set("fc cf sc ac as afc rsc rfc kv krc kaa ksc ksv ksk kfc kvc sk fk nk hnk gnk sv bk ff if ik is aif cd ca cs csd club clube de del do da la el le the team".split())
def core(s):
    """Palavras que identificam o clube, sem prefixos como FC, RSC, KV ou letras soltas."""
    t = [w for w in norm(s).split() if len(w) > 1 and w not in STOP]
    return frozenset(t or norm(s).split())

def fuzzy(name, candidates):
    """O clube do mesmo país cujo nome é o mesmo a menos de prefixos ("RSC Anderlecht" = "Anderlecht"),
    ou que contém/está contido no nome ("Dinamo" = "Dinamo Zagreb"), se houver só um candidato."""
    want = core(name)
    same = [c for c in candidates if want in (core(c["shortName"]), core(c["name"]))]
    if len(same) == 1: return same[0]
    if same: return None
    near = [c for c in candidates if any(want < k or k < want for k in (core(c["shortName"]), core(c["name"])))]
    return near[0] if len(near) == 1 else None

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()).strip("-")

def end_year(label):
    m = re.match(r"(\d{4})(?:\s*[–-]\s*(\d{2,4}))?", label)
    if not m: return None
    a = int(m.group(1))
    if not m.group(2): return a
    b = m.group(2)
    return int(b) if len(b) == 4 else (a // 100) * 100 + int(b) + (100 if int(b) < a % 100 else 0)

def merge(clubs, comps, honours, countries):
    """clubs: id -> clube; comps: id -> competição; honours: (clube, comp) -> linha; countries: código -> confederação."""
    wiki = json.load(open(os.path.join(here, "wikipedia_titles.json")))
    known_by_name = {norm(v[0]): v for v in KNOWN.values()}
    report = {"novos": [], "sem_pais": [], "excluidos": [], "retirados": []}
    for comp_id, page in wiki.items():
        comp = comps.get(comp_id)
        if comp is None: continue
        index = {}
        for c in clubs.values():
            for n in (c["shortName"], c["name"]): index.setdefault(norm(n), []).append(c)
        seen = set(); before = set(clubs)
        for row in page["rows"]:
            name = re.sub(r"\s*\[\w+\]$", "", row["club"]).strip()
            if name in SKIP_ROWS: continue
            if comp["level"] == "domestic": code = comp["country"]
            else:
                code = CLUB_COUNTRY.get(name) or COUNTRIES.get(row["country"] or "", (None,))[0]
            if code is None: report["sem_pais"].append(f"{name} ({comp_id})"); continue
            if code in EXCLUDED: report["excluidos"].append(f"{name} ({comp_id})"); continue
            countries.setdefault(code, EXTRA_COUNTRIES.get(code) or next((v[1] for v in COUNTRIES.values() if v[0] == code), None))
            target = norm(ALIASES.get(name, name))
            found = index.get(target, [])
            match = [c for c in found if (c["country"] == code or name in FOREIGN_WINNERS) and (c["id"], comp_id) not in seen]
            match.sort(key=lambda c: norm(c["shortName"]) != target)   # o nome curto igual ganha ao nome completo
            if not match:
                # só contra clubes que já existiam antes desta competição e ainda não usados nela,
                # para dois clubes da mesma tabela (Club Brugge e Cercle Brugge) nunca se fundirem
                near = fuzzy(ALIASES.get(name, name), [c for c in clubs.values() if c["country"] == code
                                                       and c["id"] in before and (c["id"], comp_id) not in seen])
                if near: match = [near]
            if match: club = match[0]
            else:
                short = ALIASES.get(name, name)
                k = known_by_name.get(target)
                if k: short, abbr, c1, c2, kit = k
                elif short in EXTRA_KNOWN: abbr, c1, c2, kit = EXTRA_KNOWN[short]
                else: abbr, c1, c2, kit = re.sub(r"[^A-Za-zÀ-ÿ0-9]", "", short)[:3].upper(), "#1B3FC2", "#C8D2E8", "plain"
                cid = slug(short)
                if cid in clubs: cid = f"{cid}-{code.lower()}"
                club = {"id": cid, "name": name, "shortName": short, "country": code, "colors": [c1, c2], "kit": kit, "abbreviation": abbr}
                clubs[cid] = club; index.setdefault(target, []).append(club); report["novos"].append(f"{short} ({code})")
            key = (club["id"], comp_id); seen.add(key)
            h = honours.setdefault(key, {"club": club["id"], "competition": comp_id})
            h["count"] = row["titles"]
            years = [y.replace("-", "–").replace(" ", "") for y in row["years"]]
            if comp_id in END_YEAR_LEAGUES:   # a página dá o ano em que a época acaba
                years = [f"{int(y) - 1}–{int(y) % 100:02d}" if re.fullmatch(r"\d{4}", y) else y for y in years]
            if years: h["seasons"] = years
            elif len(h.get("seasons", [])) != row["titles"]: h.pop("seasons", None)
            if "finals" in h:
                if years:
                    ends = {end_year(y) for y in years}
                    h["finals"] = [f for f in h["finals"] if end_year(f["season"]) in ends]
                if len(h["finals"]) > row["titles"] or not h["finals"]: h.pop("finals")
        for key in [k for k in honours if k[1] == comp_id and k not in seen]:
            report["retirados"].append(f"{clubs[key[0]]['shortName']} ({comp_id})"); del honours[key]
    # Treinador campeão de cada época (só campeonatos): fica em "coaches", época -> nome.
    managers = json.load(open(os.path.join(here, "wikipedia_managers.json")))
    report["treinadores"] = {}; report["treinadores_sem_epoca"] = []
    for comp_id, page in managers.items():
        comp = comps.get(comp_id); n = 0
        if comp is None: continue
        by_club = {}
        for c in clubs.values():
            if c["country"] == comp["country"]:
                for nm in (c["shortName"], c["name"]): by_club.setdefault(norm(nm), c)
        for row in page["rows"]:
            club = by_club.get(norm(ALIASES.get(row["club"], row["club"])))
            h = honours.get((club["id"], comp_id)) if club else None
            start = row["season"][:4]
            label = next((x for x in (h or {}).get("seasons", []) if x[:4] == start
                          or (len(x) == 4 and "–" in row["season"] and int(x) == int(start) + 1)), None)
            if label is None: report["treinadores_sem_epoca"].append(f"{comp_id} {row['season']} {row['club']}"); continue
            h.setdefault("coaches", {})[label] = row["manager"]; n += 1
        report["treinadores"][comp_id] = f"{n} de {len(page['rows'])}"
    sources = {c: {"page": p["page"], "revid": p["revid"]} for c, p in wiki.items()}
    return report, sources
