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
from backoffice_agent.rag import najdi_v_faq
from backoffice_agent.odpoved import napis_odpoved, rozpis_ceny, zkontroluj_odpoved

LOGY = KOREN / "logy"

# Čtení poptávky zvládne levný Haiku, psaní e-mailů líp Sonnet (změřeno: bez chyby 7/11 vs 5/11)
PISATEL_VYCHOZI = "claude-sonnet-5-5"


def rozhodni(udaje):
    """Kód rozhodne, co se zprávou: 'nabidka', 'doptat', 'predat_cloveku', nebo 'bez_odpovedi'."""
    typ = udaje["typ_zakazky"]

    # Obchodní nabídky a spam: neodpovídáme, jen označíme pro člověka
    if typ == "neni_poptavka" and udaje.get("je_obchodni_nabidka"):
        return "bez_odpovedi", ["obchodní nabídka / spam – neodpovídáme, jen označit"]

    # Zakázky, které se automaticky nenaceňují, a zprávy, které nejsou poptávka (reklamace, dotazy)
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
    priblizne = udaje["kam"] is None and udaje.get("kam_priblizne")
    if udaje["kam"] is None and not priblizne:
        chybi.append("kam se stěhujete (obec)")

    # Patra a výtahy na OBOU koncích – bez nich by cena byla podhodnocená
    if udaje["velikost"] != "dum":
        if udaje["patro_odkud"] is None:
            chybi.append("ve kterém patře je současný byt a zda je v domě výtah")
        elif udaje["patro_odkud"] > 0 and udaje["vytah_odkud"] is None:
            chybi.append("zda je v domě, ze kterého se stěhujete, výtah")
    # Když cíl zákazník zatím nezná (jen „okolí Zlína"), na patro v cíli se neptáme – nemůže ho vědět
    if not udaje.get("kam_je_dum") and not priblizne:
        if udaje["patro_kam"] is None:
            chybi.append("ve kterém patře je nový byt a zda je tam výtah (případně že jde o rodinný dům)")
        elif udaje["patro_kam"] > 0 and udaje["vytah_kam"] is None:
            chybi.append("zda je v novém domě výtah")

    if chybi:
        return "doptat", chybi
    return "nabidka", []


def popis_mista(obec, patro, vytah, je_dum):
    """Srozumitelný popis jednoho konce stěhování pro podklady AI."""
    if je_dum:
        return f"{obec}, rodinný dům"
    if patro is None:
        return f"{obec}, patro neuvedeno"
    if patro == 0:
        return f"{obec}, přízemí"
    vytah_text = {True: "s výtahem", False: "bez výtahu", None: "výtah neuveden"}[vytah]
    return f"{obec}, {patro}. patro, {vytah_text}"


def sestav_podklady(udaje, akce, duvody, rozhodnuti):
    """Kód připraví pro AI fakta – po stranách (odkud/kam), aby si je nemohla zaměnit."""
    radky = [f"Jméno: {udaje['jmeno']}", f"Jazyk odpovědi: {udaje.get('jazyk', 'cs')}"]
    if akce == "nabidka":
        radky += [
            f"Odkud: {popis_mista(udaje['odkud'], udaje['patro_odkud'], udaje['vytah_odkud'], udaje['velikost'] == 'dum')}",
            (f"Kam: {popis_mista(udaje['kam'], udaje['patro_kam'], udaje['vytah_kam'], udaje.get('kam_je_dum'))}"
             if udaje["kam"] is not None else
             f"Kam: zatím neznámé, zákazník uvádí okolí obce {udaje['kam_priblizne']} – cena je ODHAD "
             f"s rezervou na vzdálenost; napiš to zákazníkovi a požádej, ať cíl upřesní, až ho bude znát"),
            f"Velikost: {udaje['velikost']}",
            f"Termín: {udaje['datum']}",
        ]
        if rozhodnuti.get("tezke_predmety"):
            radky.append(f"Těžké předměty v ceně: {rozhodnuti['tezke_predmety']}")
        if rozhodnuti.get("vikend"):
            radky.append("Víkendový příplatek je v ceně započten.")
    elif akce == "doptat":
        radky.append("Chybějící údaje:")
        radky += [f"- {d}" for d in duvody]
    else:
        radky.append("(Poptávku vyřeší kolega osobně.)")
    return "\n".join(radky)


def zpracuj_poptavku(text, model="claude-haiku-5-5", model_pisatel=None):
    """model = čte poptávku (extrakce), model_pisatel = píše odpověď (výchozí PISATEL_VYCHOZI)."""
    pisatel = model_pisatel or PISATEL_VYCHOZI
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
        if udaje["kam"] is not None:
            _, km_kam = over_mesto(udaje["kam"], firma)
        else:  # jen „okolí X": vzdálenost k X + rezerva z konfigurace firmy
            _, km_kam = over_mesto(udaje["kam_priblizne"], firma)
            km_kam += firma["cenik"].get("rezerva_km_okoli", 0)
        patra = patra_bez_vytahu(udaje["patro_odkud"], udaje["vytah_odkud"]) \
              + patra_bez_vytahu(udaje["patro_kam"], udaje["vytah_kam"])
        km = max(km_odkud, km_kam)  # zjednodušení: vzdálenost ze Zlína k vzdálenějšímu místu
        tezke = udaje.get("tezke_predmety") or 0
        vikend = bool(udaje.get("vikend"))
        polozky, celkem = spocitej_cenu(firma, udaje["velikost"], km=km, patra_bez_vytahu=patra,
                                        tezke_predmety=tezke, vikend=vikend)
        rozpis = rozpis_ceny(polozky, celkem, udaje.get("jazyk", "cs"))
        rozhodnuti.update({"km": km, "patra_bez_vytahu": patra, "tezke_predmety": tezke, "vikend": vikend,
                           "polozky": polozky, "celkem": celkem})
    kroky.append(rozhodnuti)

    # 5. + 6. Návrh odpovědi (AI) a její kontrola (kód) – u spamu neodpovídáme vůbec
    if akce == "bez_odpovedi":
        navrh, hotova, problemy = None, None, []
    else:
        podklady = sestav_podklady(udaje, akce, duvody, rozhodnuti)
        # RAG: kód najde v příručce firmy, co by mohlo odpovídat na dotazy zákazníka
        faq = najdi_v_faq(text)
        kroky.append({"krok": "Hledání v FAQ", "kdo": "kód",
                      "nalezeno": [{"otazka": f["otazka"], "skore": f["skore"]} for f in faq]})
        if faq:
            podklady += "\n\nInformace z FAQ firmy (použij jen na to, na co se zákazník ptá):\n" + "\n".join(
                f"- {f['otazka']} {f['odpoved']}" for f in faq)
        navrh, usage2 = napis_odpoved(text, akce, podklady, pisatel)
        kroky.append({"krok": "Návrh odpovědi", "kdo": "AI", "model": pisatel, "podklady": podklady,
                      "vystup": navrh,
                      "tokeny": {"vstup": usage2.input_tokens, "vystup": usage2.output_tokens}})
        hotova, problemy = zkontroluj_odpoved(navrh, akce, rozpis)
        kroky.append({"krok": "Kontrola odpovědi", "kdo": "kód", "problemy": problemy})

    zaznam = {
        "cas": datetime.now().isoformat(timespec="seconds"),
        "poptavka": text,
        "udaje": udaje,
        "akce": akce,
        "odpoved": hotova,
        "k_rucni_uprave": bool(problemy),
        "navrh": navrh,      # text od AI ještě se značkou {{CENA}} – potřeba pro pozdější úpravy
        "rozpis": rozpis,    # rozpis ceny od kódu
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
                  f"patro kam: {v['patro_kam']} (výtah {v['vytah_kam']}, dům: {v.get('kam_je_dum')})")
            print(f"  těžké předměty: {v.get('tezke_predmety')}, víkend: {v.get('vikend')}, jazyk: {v.get('jazyk')}")
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
        elif k["krok"] == "Hledání v FAQ":
            for f in k["nalezeno"]:
                print(f"  nalezeno: {f['otazka']} (skóre {f['skore']})")
            if not k["nalezeno"]:
                print("  nic relevantního")
        elif k["krok"] == "Návrh odpovědi":
            print("  podklady pro AI:")
            for r in k["podklady"].splitlines():
                print(f"    {r}")
            print(f"  tokeny: {k['tokeny']['vstup']} in / {k['tokeny']['vystup']} out")
        elif k["krok"] == "Kontrola odpovědi":
            for p in k["problemy"]:
                print(f"  PROBLÉM: {p}")
            if not k["problemy"]:
                print("  v pořádku")

    print("\n" + "=" * 50)
    if zaznam["odpoved"] is None:
        print("BEZ ODPOVĚDI (označeno pro člověka)")
    else:
        print("NÁVRH ODPOVĚDI" + ("  (⚠ K RUČNÍ ÚPRAVĚ)" if zaznam["k_rucni_uprave"] else ""))
        print("=" * 50)
        print(zaznam["odpoved"])
    print(f"\nHotovo za {zaznam['doba_s']} s")


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else (
        "Dobrý den, stěhujeme se 12. 3. z bytu 3+1 ve 3. patře (bez výtahu) "
        "ve Zlíně do domu v Otrokovicích. Kolik by to stálo? Díky, Jana Nováková")
    vypis(zpracuj_poptavku(text))
