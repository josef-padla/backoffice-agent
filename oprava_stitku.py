import json
from pathlib import Path

# Jednorázová oprava správných odpovědí: P18 a P21 jsou ve skutečnosti
# stěhování jen části věcí (zbytek nábytku zůstává), ne celé domácnosti.
OPRAVY = {
    "P18": {"typ_zakazky": "cast_vybaveni", "velikost": None},
    "P21": {"typ_zakazky": "cast_vybaveni", "velikost": None},
}

soubor = Path("testy/poptavky.json")
sada = json.loads(soubor.read_text(encoding="utf-8"))
for p in sada:
    if p["id"] in OPRAVY:
        p["ocekavano"].update(OPRAVY[p["id"]])
        print("opraveno:", p["id"], p["ocekavano"])
soubor.write_text(json.dumps(sada, ensure_ascii=False, indent=2), encoding="utf-8")