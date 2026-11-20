import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from extrakce import vytahni_udaje

MODEL = "claude-haiku-5-5"
OPAKOVANI = 3  # kolikrát projedeme celou sadu – AI neodpovídá pokaždé stejně
SLOZKA = sys.argv[1] if len(sys.argv) > 1 else "testy"  # uv run eval.py testy_holdout

# Načte všechny sady ze zvolené složky
sada = []
for soubor in sorted(Path(SLOZKA).glob("*.json")):
    sada += json.loads(soubor.read_text(encoding="utf-8"))


def shoda(ocekavano, dostal):
    if isinstance(ocekavano, str) and isinstance(dostal, str):
        return ocekavano.strip().lower() == dostal.strip().lower()
    return type(ocekavano) is type(dostal) and ocekavano == dostal


behy = []                                  # výsledek každého běhu
vysledky_poptavek = defaultdict(list)      # id -> [True/False za každý běh]
chyby = []
tokeny_in = tokeny_out = 0
start = time.time()

for beh in range(1, OPAKOVANI + 1):
    print(f"\n--- Běh {beh}/{OPAKOVANI} ---")
    spravna_pole = celkem_pole = spravne_poptavky = 0

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
                chyby.append(f"běh {beh}: {p['id']} ({p['kategorie']}) {pole}: čekal {ocek!r}, dostal {dostal!r}")
        spravne_poptavky += vse_ok
        vysledky_poptavek[p["id"]].append(vse_ok)
        print(f"{p['id']} {'✅' if vse_ok else '❌'}  {p['kategorie']}")

    behy.append({"spravna_pole": spravna_pole, "celkem_pole": celkem_pole,
                 "spravne_poptavky": spravne_poptavky, "celkem_poptavek": len(sada)})

doba = time.time() - start
volani = OPAKOVANI * len(sada)
procenta = [b["spravne_poptavky"] / b["celkem_poptavek"] for b in behy]
nestabilni = [pid for pid, v in vysledky_poptavek.items() if any(v) and not all(v)]
vzdy_spatne = [pid for pid, v in vysledky_poptavek.items() if not any(v)]

print("\n===== VÝSLEDEK =====")
print(f"Sada: {SLOZKA}, model: {MODEL}, běhů: {OPAKOVANI}, poptávek: {len(sada)}")
for i, b in enumerate(behy, 1):
    print(f"  Běh {i}: poptávky bez chyby {b['spravne_poptavky']}/{b['celkem_poptavek']}, "
          f"pole {b['spravna_pole']}/{b['celkem_pole']}")
print(f"Průměr poptávek bez chyby: {sum(procenta) / len(procenta):.1%} "
      f"(nejhorší běh {min(procenta):.0%}, nejlepší {max(procenta):.0%})")
print(f"Nestabilní poptávky (jednou dobře, jednou špatně): {', '.join(nestabilni) or 'žádné'}")
print(f"Vždy špatně: {', '.join(vzdy_spatne) or 'žádné'}")
print(f"Tokeny: {tokeny_in} in / {tokeny_out} out (průměr {tokeny_in // volani} / {tokeny_out // volani} na poptávku)")
print(f"Čas: {doba:.1f} s (průměr {doba / volani:.1f} s na poptávku)")

print("\nChyby:")
for ch in chyby:
    print(" -", ch)

Path("vysledky").mkdir(exist_ok=True)
soubor = Path("vysledky") / f"{datetime.now():%Y-%m-%d_%H-%M}_{SLOZKA}_{MODEL}_x{OPAKOVANI}.json"
soubor.write_text(json.dumps({
    "sada": SLOZKA, "model": MODEL, "opakovani": OPAKOVANI, "behy": behy,
    "prumer_poptavek_bez_chyby": round(sum(procenta) / len(procenta), 3),
    "nestabilni": nestabilni, "vzdy_spatne": vzdy_spatne,
    "tokeny_in": tokeny_in, "tokeny_out": tokeny_out,
    "doba_s": round(doba, 1), "chyby": chyby,
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nUloženo do {soubor}")