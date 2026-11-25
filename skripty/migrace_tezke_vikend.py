# Jednorázový skript (použitý 24. 11.): údaje o těžkých předmětech a víkendu, které agent
# nově vytahuje, se přesunou z "pozdeji" do "ocekavano" – od teď se v evalu kontrolují.
import json
from pathlib import Path

EVALY = Path(__file__).resolve().parents[1] / "evaly"

for soubor in sorted((EVALY / "sady" / "hlavni").glob("*.json")):
    sada = json.loads(soubor.read_text(encoding="utf-8"))
    for p in sada:
        pozdeji = p.get("pozdeji", {})
        for pole in ("tezke_predmety", "vikend"):
            if pole in pozdeji:
                p["ocekavano"][pole] = pozdeji.pop(pole)
                print(f"{p['id']}: {pole} = {p['ocekavano'][pole]}")
        if "pozdeji" in p and not p["pozdeji"]:
            del p["pozdeji"]
    soubor.write_text(json.dumps(sada, ensure_ascii=False, indent=2), encoding="utf-8")
