import tomllib
from pathlib import Path

# Kořen projektu: src/backoffice_agent/cena.py -> o dvě složky výš
KOREN = Path(__file__).resolve().parents[2]


def nacti_firmu(nazev):
    with open(KOREN / "firmy" / f"{nazev}.toml", "rb") as f:
        return tomllib.load(f)


def spocitej_cenu(firma, velikost, km, patra_bez_vytahu=0, dalsi_lide=0,
                  baleni_hodin=0, krabice=0, tezke_predmety=0, vikend=False):
    c = firma["cenik"]
    hodiny = max(firma["odhad_hodin"][velikost], c["minimum_hodin"])

    polozky = {
        "práce": hodiny * (c["vuz_2_lide_za_hodinu"] + dalsi_lide * c["dalsi_clovek_za_hodinu"]),
        "doprava": km * c["doprava_za_km"],
        "patra bez výtahu": patra_bez_vytahu * c["patro_bez_vytahu"],
        "balení": baleni_hodin * c["baleni_za_hodinu"] + krabice * c["krabice_za_kus"],
        "těžké předměty": tezke_predmety * c["tezky_predmet"],
    }
    zaklad = sum(polozky.values())
    polozky["víkendový příplatek"] = round(zaklad * c["vikendovy_priplatek"]) if vikend else 0

    return polozky, sum(polozky.values())


if __name__ == "__main__":
    bobr = nacti_firmu("bobr")
    # Poptávka Jany Novákové: 3+1, 3. patro bez výtahu, Zlín → Otrokovice (~12 km)
    polozky, celkem = spocitej_cenu(bobr, "3+1", km=12, patra_bez_vytahu=3)
    for nazev, castka in polozky.items():
        print(f"{nazev}: {castka} Kč")
    print(f"CELKEM: {celkem} Kč")