"""Celá cesta jedné poptávky agentem, včetně TRACE – záznamu každého kroku.

Trace odpovídá na otázku „proč agent udělal tohle?": co řekla AI, co kód opravil
a podle čeho padlo rozhodnutí. Slouží k hledání chyb a později pro webové demo.
"""
import json
import sys
import time
from datetime import datetime

from backoffice_agent.cena import KOREN, spocitej_cenu
from backoffice_agent.extrakce import firma, patra_bez_vytahu, predzpracuj, zavolej_ai, zkontroluj
from backoffice_agent.mesta import over_mesto

LOGY = KOREN / "logy"


def zpracuj_poptavku(text, model="claude-haiku-5-5"):
    start = time.time()
    kroky = []

    # 1. Předzpracování (kód)
    upraveny = predzpracuj(text)
    kroky.append({"krok": "Předzpracování", "kdo": "kód",
                  "zmena": upraveny if upraveny != text else None})

    # 2. AI extrakce (AI)
    surove, usage = zavolej_ai(text, model)
    kroky.append({"krok": "AI extrakce", "kdo": "AI", "model": model, "vystup": surove,
                  "tokeny": {"vstup": usage.input_tokens, "vystup": usage.output_tokens}})

    # 3. Kontroly (kód)
    udaje, zasahy = zkontroluj(surove)
    kroky.append({"krok": "Kontroly kódem", "kdo": "kód",
                  "zasahy": zasahy, "k_overeni": udaje["k_overeni"]})

    # 4. Rozhodnutí (kód): spočítat cenu, nebo předat člověku
    _, km_odkud = over_mesto(udaje["odkud"], firma)
    _, km_kam = over_mesto(udaje["kam"], firma)
    duvody = []
    if udaje["typ_zakazky"] != "cele_stehovani":
        duvody.append(f"typ zakázky '{udaje['typ_zakazky']}' se automaticky nenaceňuje")
    elif udaje["velikost"] is None:
        duvody.append("chybí velikost bytu")
    if km_odkud is None:
        duvody.append("město odkud chybí nebo ho firma nezná")
    if km_kam is None:
        duvody.append("město kam chybí nebo ho firma nezná")

    if duvody:
        vysledek = {"akce": "predat_cloveku", "duvody": duvody}
    else:
        patra = patra_bez_vytahu(udaje["patro_odkud"], udaje["vytah_odkud"]) \
              + patra_bez_vytahu(udaje["patro_kam"], udaje["vytah_kam"])
        km = max(km_odkud, km_kam)  # zjednodušení: vzdálenost ze Zlína k vzdálenějšímu místu
        polozky, celkem = spocitej_cenu(firma, udaje["velikost"], km=km, patra_bez_vytahu=patra)
        vysledek = {"akce": "nabidka", "km": km, "patra_bez_vytahu": patra,
                    "polozky": polozky, "celkem": celkem}
    kroky.append({"krok": "Rozhodnutí", "kdo": "kód", **vysledek})

    zaznam = {
        "cas": datetime.now().isoformat(timespec="seconds"),
        "poptavka": text,
        "udaje": udaje,
        "vysledek": vysledek,
        "kroky": kroky,
        "doba_s": round(time.time() - start, 2),
    }
    uloz(zaznam)
    return zaznam


def uloz(zaznam):
    LOGY.mkdir(exist_ok=True)
    soubor = LOGY / f"{datetime.now():%Y-%m-%d_%H-%M-%S}.json"
    soubor.write_text(json.dumps(zaznam, ensure_ascii=False, indent=2), encoding="utf-8")


def vypis(zaznam):
    for k in zaznam["kroky"]:
        print(f"\n[{k['kdo']}] {k['krok']}")
        if k["krok"] == "Předzpracování":
            print("  beze změny" if k["zmena"] is None else f"  text upraven: {k['zmena']}")
        elif k["krok"] == "AI extrakce":
            v = k["vystup"]
            print(f"  typ: {v['typ_zakazky']}, velikost: {v['velikost']}, odkud: {v['odkud']}, kam: {v['kam']}")
            print(f"  patro odkud: {v['patro_odkud']} (výtah {v['vytah_odkud']}), "
                  f"patro kam: {v['patro_kam']} (výtah {v['vytah_kam']})")
            print(f"  tokeny: {k['tokeny']['vstup']} in / {k['tokeny']['vystup']} out")
        elif k["krok"] == "Kontroly kódem":
            for z in k["zasahy"]:
                print(f"  oprava: {z}")
            for z in k["k_overeni"]:
                print(f"  k ověření: {z}")
            if not k["zasahy"] and not k["k_overeni"]:
                print("  vše v pořádku, kód nic neměnil")
        elif k["krok"] == "Rozhodnutí":
            if k["akce"] == "nabidka":
                for nazev, castka in k["polozky"].items():
                    if castka:
                        print(f"  {nazev}: {castka} Kč")
                print(f"  CELKEM: {k['celkem']} Kč")
            else:
                print("  PŘEDAT ČLOVĚKU:")
                for d in k["duvody"]:
                    print(f"   - {d}")
    print(f"\nHotovo za {zaznam['doba_s']} s")


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else (
        "Dobrý den, stěhujeme se 12. 3. z bytu 3+1 ve 3. patře (bez výtahu) "
        "ve Zlíně do domu v Otrokovicích. Kolik by to stálo? Díky, Jana Nováková")
    vypis(zpracuj_poptavku(text))
