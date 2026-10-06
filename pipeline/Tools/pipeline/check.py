# Compara os dados novos com os publicados e decide se podem ser publicados sozinhos.
# Uso: python3 check.py publicado.json novo.json   (escreve o relatório; sai com 0 = publicar,
# 3 = nada mudou, 2 = há algo estranho e não se publica)
import json, sys

old, new = (json.load(open(p)) for p in sys.argv[1:3])

def titles(bundle):
    t = {}
    for h in bundle["dataset"]["honours"]:
        t[(h["club"], h["competition"])] = max(len(h.get("finals") or []), len(h.get("seasons") or []), h.get("count") or 0)
    for c in bundle["officialCounts"]["counts"]:
        t[(c["club"], c["competition"])] = c["count"]
    return t

def names(bundle):
    return {c["id"]: c["shortName"] for c in bundle["dataset"]["clubs"]}

to, tn = titles(old), titles(new)
no, nn = names(old), names(new)
name = lambda cid: nn.get(cid) or no.get(cid) or cid
strange, changes = [], []

if len(nn) < len(no) * 0.98: strange.append(f"O número de clubes caiu de {len(no)} para {len(nn)}.")
if sum(tn.values()) < sum(to.values()): strange.append(f"O total de títulos caiu de {sum(to.values())} para {sum(tn.values())}.")
co, cn = ({c["id"] for c in b["dataset"]["competitions"]} for b in (old, new))
if co - cn: strange.append(f"Competições que desapareceram: {sorted(co - cn)}.")
if old["scoring"] != new["scoring"]: changes.append("A pontuação mudou.")

for key in sorted(set(to) | set(tn)):
    a, b = to.get(key, 0), tn.get(key, 0)
    if a == b: continue
    line = f"{name(key[0])}, {key[1]}: {a} -> {b}"
    if b < a: strange.append("Perdeu títulos: " + line)
    elif b - a > 2: strange.append("Ganhou mais de 2 títulos de uma vez: " + line)
    else: changes.append(line)
new_clubs = [nn[c] for c in nn if c not in no]
if len(new_clubs) > 15: strange.append(f"Apareceram {len(new_clubs)} clubes novos de uma vez: {new_clubs[:15]}…")
elif new_clubs: changes.append(f"Clubes novos: {new_clubs}")
gone = [no[c] for c in no if c not in nn]
if gone: strange.append(f"Clubes que desapareceram: {gone[:20]}")

same = lambda b: json.dumps({k: v for k, v in b.items() if k != "updated"} | {"dataset": {k: v for k, v in b["dataset"].items() if k != "updated"}}, sort_keys=True)
if strange:
    print("Há alterações estranhas nos dados. NÃO foram publicados.\n")
    print("\n".join("- " + s for s in strange))
    if changes: print("\nOutras alterações (normais):\n" + "\n".join("- " + c for c in changes))
    sys.exit(2)
if same(old) == same(new):
    print("Sem alterações."); sys.exit(3)
print("Alterações publicadas:\n" + ("\n".join("- " + c for c in changes) if changes else "- Só detalhes (épocas, finais ou treinadores)."))
