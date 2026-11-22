"""LLM-as-judge, krok 1: vygeneruje odpovědi na vybrané poptávky k RUČNÍMU ohodnocení."""
import json
from pathlib import Path

from backoffice_agent.pipeline import zpracuj_poptavku
from kriteria import KRITERIA

EVALY = Path(__file__).resolve().parent
CIL = EVALY / "hodnoceni" / "odpovedi.json"

# Mix situací: nabídka, doptání, předání, cizí jazyk
VYBER = ["P01", "P05", "P11", "P12", "P14", "P16", "P22", "P28", "P29", "P33", "P34", "P47"]

# Pojistka: ruční hodnocení je drahé, nesmí se omylem přepsat
if CIL.exists():
    raise SystemExit(f"{CIL} už existuje – nepřepisuji ruční hodnocení. Smaž ho ručně, pokud opravdu chceš nové.")

sada = {}
for soubor in sorted((EVALY / "sady" / "hlavni").glob("*.json")):
    for p in json.loads(soubor.read_text(encoding="utf-8")):
        sada[p["id"]] = p

vystup = []
for pid in VYBER:
    zaznam = zpracuj_poptavku(sada[pid]["text"])
    print(pid, zaznam["akce"])
    vystup.append({
        "id": pid,
        "poptavka": sada[pid]["text"],
        "akce": zaznam["akce"],
        "odpoved": zaznam["odpoved"],
        "clovek": {**{k: None for k in KRITERIA}, "poznamka": ""},
    })

CIL.parent.mkdir(exist_ok=True)
CIL.write_text(json.dumps(vystup, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nUloženo do {CIL} – teď ohodnoť každou odpověď ručně.")