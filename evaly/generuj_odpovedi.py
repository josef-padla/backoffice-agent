"""LLM-as-judge, krok 1: vygeneruje odpovědi na vybrané poptávky (k ručnímu hodnocení nebo k porovnání).

Použití: uv run evaly/generuj_odpovedi.py [nazev_souboru.json] [model_pisatele]
  např.: uv run evaly/generuj_odpovedi.py odpovedi_sonnet.json claude-sonnet-5-5
"""
import json
import sys
from pathlib import Path

from backoffice_agent.pipeline import zpracuj_poptavku
from kriteria import KRITERIA

EVALY = Path(__file__).resolve().parent
CIL = EVALY / "hodnoceni" / (sys.argv[1] if len(sys.argv) > 1 else "odpovedi.json")
PISATEL = sys.argv[2] if len(sys.argv) > 2 else None  # None = výchozí pisatel agenta (Sonnet)

# Mix situací: nabídka, doptání, předání, cizí jazyk
VYBER = ["P01", "P05", "P11", "P12", "P14", "P16", "P22", "P28", "P29", "P33", "P34", "P47"]

# Pojistka: ruční hodnocení je drahé, nesmí se omylem přepsat
if CIL.exists():
    raise SystemExit(f"{CIL} už existuje – nepřepisuji ho. Zvol jiný název, nebo starý soubor smaž ručně.")

sada = {}
for soubor in sorted((EVALY / "sady" / "hlavni").glob("*.json")):
    for p in json.loads(soubor.read_text(encoding="utf-8")):
        sada[p["id"]] = p

vystup = []
for pid in VYBER:
    zaznam = zpracuj_poptavku(sada[pid]["text"], model_pisatel=PISATEL)
    print(pid, zaznam["akce"])
    vystup.append({
        "id": pid,
        "poptavka": sada[pid]["text"],
        "akce": zaznam["akce"],
        "odpoved": zaznam["odpoved"],
        "pisatel": PISATEL or "výchozí (Sonnet)",
        "clovek": {**{k: None for k in KRITERIA}, "poznamka": ""},
    })

CIL.parent.mkdir(exist_ok=True)
CIL.write_text(json.dumps(vystup, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nUloženo do {CIL}")