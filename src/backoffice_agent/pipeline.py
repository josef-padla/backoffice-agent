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
from backoffice_agent.odpoved import napis_odpoved, rozpis_ceny, zkontroluj_odpoved

LOGY = KOREN / "logy"


def rozhodni(udaje):
    """Kód rozhodne, co s poptávkou: 'nabidka', 'doptat', nebo 'predat_cloveku'."""
    typ = udaje["typ_zakazky"]

    # Zakázky, které se automaticky nenaceňují, a zprávy, které nejsou poptávka
    if typ in ("cast_vybaveni", "jednotlive_kusy", "kancelar", "neni_poptavka"):
        return "predat_cloveku", [f"typ zakázky '{typ}' se automaticky nenaceňuje"]

    # Místo, které firma nezná (jiný kraj, neznámá obec) – rozhodne člověk
    if udaje["k_overeni"]:
        return "predat_cloveku", udaje["k_overeni"]

    # Chybějící údaje – doptáme se zákazníka
    chybi = []
    if udaje["velikost"] is None:
        chybi.append("velikost bytu (např. 2+1) nebo zda jde o rodinný dům")
    if udaje["odkud"] is None:
        chybi.append("odkud se stěhujete (obec)")
    if udaje["kam"] is None:
        chybi.append("kam se stěhujete (obec)")
    if udaje["velikost"] != "dum" and udaje["patro_odkud"] is None:
        chybi.append("ve kterém patře je současný byt a zda je v domě výtah")
    if chybi:
        return "doptat", chybi

    return "nabidka", []


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

    # 4. Rozhodnutí (kód)
    akce, duvody = rozhodni(udaje)
    rozhodnuti = {"krok": "Rozhodnutí", "kdo": "kód", "akce": akce, "duvody": duvody}
    rozpis = None
    if akce == "nabidka":
        _, km_odkud = over_mesto(udaje["odkud"], firma)
        _, km_kam = over_mesto(udaje["kam"], firma)
        patra = patra_bez_vytahu(udaje["patro_odkud"], udaje["vytah_odkud"]) \
              + patra_bez_vytahu(udaje["patro_kam"], udaje["vytah_kam"])
        km = max(km_odkud, km_kam)  # zjednodušení: vzdálenost ze Zlína k vzdálenějšímu místu
        polozky, celkem = spocitej_cenu(firma, udaje["velikost"], km=km, patra_bez_vytahu=patra)
        rozpis = rozpis_ceny(polozky, celkem)
        rozhodnuti.update({"km": km, "patra_bez_vytahu": patra, "polozky": polozky, "celkem": celkem})
    kroky.append(rozhodnuti)

    # 5. Návrh odpovědi (AI) – podklady sestaví kód, AI z nich jen napíše text
    if akce == "nabidka":
        podklady = (f"Jméno: {udaje['jmeno']}\nOdkud: {udaje['odkud']}\nKam: {udaje['kam']}\n"
                    f"Velikost: {udaje['velikost']}\nTermín: {udaje['datum']}\n"
                    f"Patra bez výtahu celkem: {rozhodnuti['patra_bez_vytahu']}")
    elif akce == "doptat":
        podklady = f"Jméno: {udaje['jmeno']}\nChybějící údaje:\n" + "\n".join(f"- {c}" for c in duvody)
    else:
        podklady = f"Jméno: {udaje['jmeno']}\n(Poptávku vyřeší kolega osobně.)"
    navrh, usage2 = napis_odpoved(text, akce, podklady, model)
    kroky.append({"krok": "Návrh odpovědi", "kdo": "AI", "model": model, "vystup": navrh,
                  "tokeny": {"vstup": usage2.input_tokens, "vystup": usage2.output_tokens}})

    # 6. Kontrola odpovědi (kód) – dosazení ceny a kontrola, že AI nepsala vlastní částky
    hotova, problemy = zkontroluj_odpoved(navrh, akce, rozpis)
    kroky.append({"krok": "Kontrola odpovědi", "kdo": "kód", "problemy": problemy})

    zaznam = {
        "cas": datetime.now().isoformat(timespec="seconds"),
        "poptavka": text,
        "udaje": udaje,
        "akce": akce,
        "odpoved": hotova,
        "k_rucni_uprave": bool(problemy),
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
            print(f"  akce: {k['akce']}")
            for d in k["duvody"]:
                print(f"   - {d}")
            if k["akce"] == "nabidka":
                print(f"  celkem: {k['celkem']} Kč")
        elif k["krok"] == "Návrh odpovědi":
            print(f"  tokeny: {k['tokeny']['vstup']} in / {k['tokeny']['vystup']} out")
        elif k["krok"] == "Kontrola odpovědi":
            for p in k["problemy"]:
                print(f"  PROBLÉM: {p}")
            if not k["problemy"]:
                print("  v pořádku")

    print("\n" + "=" * 50)
    print("NÁVRH ODPOVĚDI" + ("  (⚠ K RUČNÍ ÚPRAVĚ)" if zaznam["k_rucni_uprave"] else ""))
    print("=" * 50)
    print(zaznam["odpoved"])
    print(f"\nHotovo za {zaznam['doba_s']} s")


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else (
        "Dobrý den, stěhujeme se 12. 3. z bytu 3+1 ve 3. patře (bez výtahu) "
        "ve Zlíně do domu v Otrokovicích. Kolik by to stálo? Díky, Jana Nováková")
    vypis(zpracuj_poptavku(text))