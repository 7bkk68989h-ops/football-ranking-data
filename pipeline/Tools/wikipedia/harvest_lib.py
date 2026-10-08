# Leitura das tabelas "títulos por clube" da Wikipédia (usada por harvest.py e discover.py).
import re, os, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
from wp import tables, grid, fetch

CLUB = re.compile(r"^(club|team|clubs|teams)$", re.I)
COUNT = re.compile(r"^(winners?|titles?|title\(s\)|champions?|won|wins|championships?)$", re.I)
YEARS = re.compile(r"(winning|won|champion|title).*(years?|seasons?)|(years?|seasons?).*(won|winning|champion)|^(winning )?(seasons|years)$", re.I)

# Quando a página tem várias tabelas "por clube", diz qual: parte do título da secção, ou "menor".
PICK = {"fr-liga": "club in professional era", "pt-campeonato": "menor"}

# Linhas da Wikipédia que juntam vários clubes (fusões): a tabela por clube dá tudo ao clube atual,
# mas a lista época a época da mesma página diz quem ganhou. Competição -> linha -> clube -> épocas.
# O que sobra fica na linha original. (Pedido do Pedro, 8 out. 2026: o Pezoporikos tem 2 campeonatos.)
SPLIT = {
 "cy-liga": {"AEK Larnaca": {"EPA Larnaca": ["1944–45", "1945–46", "1969–70"], "Pezoporikos Larnaca": ["1953–54", "1987–88"]}},
 "cy-taca": {"AEK Larnaca": {"EPA Larnaca": ["1944–45", "1945–46", "1949–50", "1952–53", "1954–55"], "Pezoporikos Larnaca": ["1969–70"]}},
 "at-liga": {"SK Admira Wien": {"Wacker Wien": ["1946–47"]},
             "FC Wacker Innsbruck": {"Swarovski Tirol": ["1988–89", "1989–90"], "Tirol Innsbruck": ["1999–2000", "2000–01", "2001–02"]}},
 "at-taca": {"SK Admira Wien": {"Wacker Wien": ["1947"]}, "Wacker Innsbruck": {"Swarovski Tirol": ["1989"]}},
 "ro-liga": {"Farul Constanța": {"Viitorul Constanța": ["2016–17"]}},
}
def split_rows(comp, rows):
    """Aplica SPLIT; devolve a lista de problemas (linha ou época que a página já não tem)."""
    problems = []
    for name, parts in SPLIT.get(comp, {}).items():
        row = next((r for r in rows if r["club"] == name), None)
        if row is None: problems.append(f"{comp}: sem a linha «{name}»"); continue
        have = [y.replace("-", "–") for y in row["years"]]
        for club, years in parts.items():
            missing = [y for y in years if y not in have]
            if missing: problems.append(f"{comp}: «{name}» sem {missing}"); continue
            have = [y for y in have if y not in years]
            rows.append({"club": club, "titles": len(years), "years": list(years), "country": row["country"]})
            row["titles"] -= len(years)
        row["years"] = have
    rows[:] = sorted((r for r in rows if r["titles"] > 0), key=lambda r: -r["titles"])
    return problems

# Títulos retirados que a página ainda lista entre os anos (não contam no total).
REVOKED = {"Juventus": ("2004–05",), "Torino": ("1926–27",)}

def find(title, pick=None):
    best = None
    for t in tables(title):
        if pick and pick != "menor" and pick not in t["heading"].lower(): continue
        g = grid(t)
        if len(g) < 3: continue
        for hi in range(min(2, len(g))):
            head = [re.sub(r"^vte\s+", "", c["text"].strip()) for c in g[hi]]
            ci = next((i for i, h in enumerate(head) if CLUB.match(h)), None)
            ni = next((i for i, h in enumerate(head) if COUNT.match(h)), None)
            yi = next((i for i, h in enumerate(head) if YEARS.search(h) and "runner" not in h.lower() and "second" not in h.lower()), None)
            if ci is None or ni is None: continue
            # tabelas por cidade ou região repetem o total da região em cada clube: não servem
            if any(re.search(r"\b(city|cities|area|emirates?|regions?|states?|provinces?|federation|cantons?)\b", h, re.I) for h in head[:ci]): continue
            rows = []; joined = 0
            for r in g[hi + 1:]:
                if len(r) <= max(ci, ni): continue
                m = re.match(r"\d+", r[ni]["text"])
                name = re.sub(r"\s*\((?!\d{4}\))[^()]*\)\s*$", "", r[ci]["text"]).strip(" *†‡")
                name = re.sub(r"\s*\[[^\]]*\]", "", name); name = re.sub(r"[⭐★☆,]+\s*$", "", name).strip(" ,")
                if not m or not name or int(m.group()) == 0: continue
                if int(m.group()) > 150: rows = []; break                      # coluna errada (anos)
                if re.search(r"\(\d+\)\s*,", r[ci]["text"]):                   # várias equipas na mesma célula
                    joined += 1
                    if joined >= 3: rows = []; break
                    name = r[ci]["text"].split("(")[0].strip()                  # fica a primeira; SPLIT separa as outras
                years = r[yi]["text"] if yi is not None and len(r) > yi else ""
                ys = [y.strip() for y in re.findall(r"\d{4}(?:\s*[–-]\s*\d{2,4})?", years)]
                rows.append({"club": name, "titles": int(m.group()), "years": ys, "country": (r[ci]["flags"] or [None])[0]})
            for x in rows:
                x["years"] = [y for y in x["years"] if y.replace("-", "–") not in REVOKED.get(x["club"], ())]
                if len(x["years"]) != x["titles"]: x["years"] = []   # coluna com outros anos misturados
            score = sum(x["titles"] for x in rows) + (1000 if yi is not None else 0)
            if pick == "menor": score = -score
            if rows and (best is None or score > best[0]): best = (score, t["heading"].strip(), rows)
    return best

