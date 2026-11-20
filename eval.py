import json
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from extrakce import vytahni_udaje

MODEL = "claude-haiku-5-5"

# Načte všechny sady ze složky testy/
sada = []
for soubor in sorted(Path("testy").glob("*.json")):
    sada += json.loads(soubor.read_text(encoding="utf-8"))


def shoda(ocekavano, dostal):
    if isinstance(ocekavano, str) and isinstance(dostal, str):
        return ocekavano.strip().lower() == dostal.strip().lower()
    return type(ocekavano) is type(dostal) and ocekavano == dostal


spravna_pole = celkem_pole = spravne_poptavky = 0
tokeny_in = tokeny_out = 0
chyby = []
podle_kategorie = defaultdict(lambda: [0, 0])  # [bez chyby, celkem]
start = time.time()

for p in sada:
    udaje, usage = vytahni_udaje(p["text"], MODEL)
    tokeny_in += usage.input_tokens
    tokeny_out += usage.output_tokens

    vse_ok = True
    for pole, ocek in p["ocekavano"].items():
        celkem_pole += 1
        dostal = udaje.get(pole)
        if shoda(ocek, dostal):
            spravna_pole += 1
        else:
            vse_ok = False
            chyby.append(f"{p['id']} ({p['kategorie']}) {pole}: čekal {ocek!r}, dostal {dostal!r}")
    spravne_poptavky += vse_ok
    podle_kategorie[p["kategorie"]][0] += vse_ok
    podle_kategorie[p["kategorie"]][1] += 1
    print(f"{p['id']} {'✅' if vse_ok else '❌'}  {p['kategorie']}")

doba = time.time() - start

print("\n===== VÝSLEDEK =====")
print(f"Model: {MODEL}")
print(f"Správná pole: {spravna_pole}/{celkem_pole} ({spravna_pole / celkem_pole:.0%})")
print(f"Celé poptávky bez chyby: {spravne_poptavky}/{len(sada)} ({spravne_poptavky / len(sada):.0%})")
print(f"Tokeny: {tokeny_in} in / {tokeny_out} out")
print(f"Čas: {doba:.1f} s (průměr {doba / len(sada):.1f} s na poptávku)")

print("\nPodle kategorií:")
for kategorie, (ok, celkem) in sorted(podle_kategorie.items()):
    print(f"  {kategorie}: {ok}/{celkem}")

print("\nChyby:")
for ch in chyby:
    print(" -", ch)

Path("vysledky").mkdir(exist_ok=True)
soubor = Path("vysledky") / f"{datetime.now():%Y-%m-%d_%H-%M}_{MODEL}.json"
soubor.write_text(json.dumps({
    "model": MODEL,
    "spravna_pole": spravna_pole, "celkem_pole": celkem_pole,
    "spravne_poptavky": spravne_poptavky, "celkem_poptavek": len(sada),
    "tokeny_in": tokeny_in, "tokeny_out": tokeny_out,
    "doba_s": round(doba, 1),
    "podle_kategorie": dict(podle_kategorie),
    "chyby": chyby,
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nUloženo do {soubor}")