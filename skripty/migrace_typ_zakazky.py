# ARCHIV: jednorázový skript, už použitý. Cesty odpovídají staré struktuře projektu (před úklidem).
import json
from pathlib import Path

# Jednorázový skript: doplní do testovacích sad očekávaný typ zakázky.
# Výchozí je "cele_stehovani", výjimky jsou vypsané níže.

JINY_TYP = {
    "P47": "jednotlive_kusy",
    "P28": "neni_poptavka", "P29": "neni_poptavka", "P30": "neni_poptavka",
    "H02": "jednotlive_kusy", "H08": "kancelar", "H09": "jednotlive_kusy",
    "H12": "cast_vybaveni", "H13": "jednotlive_kusy",
}
NEKONTROLOVAT = {"P11", "P15", "P50", "H03"}  # z textu nejde jednoznačně poznat

for soubor in [*Path("testy").glob("*.json"), *Path("testy_holdout").glob("*.json")]:
    sada = json.loads(soubor.read_text(encoding="utf-8"))
    for p in sada:
        if p["id"] in NEKONTROLOVAT:
            continue
        p["ocekavano"]["typ_zakazky"] = JINY_TYP.get(p["id"], "cele_stehovani")
    soubor.write_text(json.dumps(sada, ensure_ascii=False, indent=2), encoding="utf-8")
    print("upraveno:", soubor)