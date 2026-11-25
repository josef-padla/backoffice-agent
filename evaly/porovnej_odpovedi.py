"""Porovná kvalitu odpovědí před a po změně agenta.

Stejný hodnotitel (Opus) + stejná rubrika + stejné poptávky → rozdíl v číslech je
způsobený změnou agenta, ne změnou měření.

Použití: uv run evaly/porovnej_odpovedi.py [stare.json] [nove.json]
"""
import hashlib
import json
import sys
from pathlib import Path

from hodnotitel import ohodnot
from kriteria import KRITERIA

EVALY = Path(__file__).resolve().parent
MODEL = "claude-opus-5-5"
STARE, NOVE = (sys.argv[1:3] if len(sys.argv) >= 3 else ["odpovedi.json", "odpovedi_v2.json"])


# Otisk rubriky a hodnotitele – když se nezmění, smíme znovu použít uložené hodnocení
OTISK = hashlib.sha256((MODEL + json.dumps(KRITERIA, ensure_ascii=False)).encode()).hexdigest()[:12]


def ohodnot_soubor(nazev):
    cil = EVALY / "hodnoceni" / f"opus_{nazev}"
    # Úspora: stejné odpovědi se stejnou rubrikou už Opus hodnotil → použijeme uložené
    if cil.exists():
        ulozene = json.loads(cil.read_text(encoding="utf-8"))
        if isinstance(ulozene, dict) and ulozene.get("otisk") == OTISK:
            print("  (použito uložené hodnocení, nic se neplatí)")
            return ulozene["vysledky"]

    data = json.loads((EVALY / "hodnoceni" / nazev).read_text(encoding="utf-8"))
    vysledky = {}
    for p in data:
        if p["odpoved"] is None:          # např. spam – agent záměrně neodpověděl
            vysledky[p["id"]] = {"akce": p["akce"], "hodnoceni": None}
        else:
            h, _ = ohodnot(p, MODEL)
            vysledky[p["id"]] = {"akce": p["akce"], "hodnoceni": h}
        print(".", end="", flush=True)
    print()
    cil.write_text(json.dumps({"otisk": OTISK, "vysledky": vysledky}, ensure_ascii=False, indent=2), encoding="utf-8")
    return vysledky


def souhrn(vysledky):
    hodnocene = [v["hodnoceni"] for v in vysledky.values() if v["hodnoceni"]]
    splneno = {k: sum(h[k] for h in hodnocene) for k in KRITERIA}
    bez_chyby = sum(all(h[k] for k in KRITERIA) for h in hodnocene)
    return splneno, bez_chyby, len(hodnocene)


print(f"Hodnotím {STARE}"); stare = ohodnot_soubor(STARE)
print(f"Hodnotím {NOVE}"); nove = ohodnot_soubor(NOVE)
s1, b1, n1 = souhrn(stare)
s2, b2, n2 = souhrn(nove)

print("\n===== POROVNÁNÍ (hodnotitel: Opus) =====")
print(f"{'kritérium':<14}{'před':>8}{'po':>8}")
for k in KRITERIA:
    print(f"{k:<14}{f'{s1[k]}/{n1}':>8}{f'{s2[k]}/{n2}':>8}")
print(f"{'bez chyby':<14}{f'{b1}/{n1}':>8}{f'{b2}/{n2}':>8}")

print("\nZměny u jednotlivých odpovědí:")
for pid in stare:
    a, b = stare[pid], nove.get(pid)
    if b is None:
        continue
    if a["akce"] != b["akce"]:
        print(f"  {pid}: akce {a['akce']} → {b['akce']}")
    if not a["hodnoceni"] or not b["hodnoceni"]:
        continue
    for k in KRITERIA:
        pred, po = a["hodnoceni"][k], b["hodnoceni"][k]
        if pred and not po:
            print(f"  {pid} {k}: ZHORŠENÍ – {b['hodnoceni'][k + '_zduvodneni']}")
        elif po and not pred:
            print(f"  {pid} {k}: zlepšení")

print("\nZbylé chyby v nových odpovědích:")
for pid, v in nove.items():
    if v["hodnoceni"]:
        for k in KRITERIA:
            if not v["hodnoceni"][k]:
                print(f"  {pid} {k}: {v['hodnoceni'][k + '_zduvodneni']}")
