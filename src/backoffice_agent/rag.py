"""RAG = agent si před psaním odpovědi najde v příručce firmy (FAQ) relevantní informace.

Jak hledáme (záměrně jednoduše, bez dalších služeb a bez placení):
  1. FAQ rozdělíme na kousky – jedna otázka + odpověď = jeden kousek.
  2. Slova zjednodušíme: malá písmena, bez diakritiky, a každé slovo zkrátíme na prvních 5 písmen
     („krabice", „krabic", „krabicemi" -> „krabi"). Čeština má hodně tvarů slov, tohle je nejjednodušší trik.
  3. Kousky seřadíme podle BM25 – klasický vzorec vyhledávačů: víc bodů za shodu ve vzácných slovech
     („trezor"), málo za běžná slova („stěhování", které je skoro všude).
Ve firmě s tisíci dokumenty by se místo kroku 2–3 použily „embeddingy" (hledání podle významu).
Pro 18 otázek je tohle rychlejší, zdarma a dá se snadno otestovat – a vyměnit jde jen tahle funkce.
"""
import math
import re
import unicodedata
from collections import Counter

from backoffice_agent.cena import KOREN

FAQ_SOUBOR = KOREN / "firmy" / "bobr_faq.md"
DELKA_KORENE = 5
MIN_SKORE = 2.0   # pod tímhle skóre kousek nepoužijeme – radši nic než nesouvisející informace

# Slova, která nic neříkají o tématu (spojky, zájmena, zdvořilosti z e-mailů).
NEVYZNAMNA = {
    "a", "i", "je", "jsem", "jsme", "jste", "se", "si", "na", "v", "ve", "do", "z", "ze", "s", "k", "o", "u",
    "to", "ten", "ta", "ty", "by", "bych", "bychom", "byste", "mi", "me", "nam", "vam", "vas", "nas", "ale",
    "nebo", "jak", "co", "kdy", "jen", "uz", "take", "tak", "dobry", "den", "dekuji", "dekujeme", "diky",
    "prosim", "pozdravem", "chtel", "chtela", "chteli", "potrebuji", "potrebuju", "mate", "muzete", "zda",
    "jestli", "kolik", "ano", "ne", "pro", "po", "pri", "za", "od", "nase", "nasi", "vase", "jsou", "bude", "byt",
}


OBECNE = ("steh", "prest", "stah", "prest", "moving", "move")


def normalizuj(text):
    """Text -> seznam „kořenů" slov."""
    bez_hacku = unicodedata.normalize("NFKD", text.lower())
    bez_hacku = "".join(z for z in bez_hacku if not unicodedata.combining(z))
    slova = re.findall(r"[a-z]+", bez_hacku)
    # Slova o stěhování samotném jsou skoro v každém e-mailu i v každé otázce FAQ – o tématu nic neříkají.
    return [s[:DELKA_KORENE] for s in slova
            if s not in NEVYZNAMNA and len(s) > 1 and not s.startswith(OBECNE)]


def nacti_faq(soubor=FAQ_SOUBOR):
    """Rozdělí FAQ na kousky podle nadpisů '## Otázka'."""
    kousky = []
    for blok in soubor.read_text(encoding="utf-8").split("\n## ")[1:]:
        otazka, _, zbytek = blok.partition("\n")
        klicova = ""
        if zbytek.startswith("Klíčová slova:"):  # slova jen pro hledání, do e-mailu je AI nedostane
            klicova, _, zbytek = zbytek.partition("\n")
            klicova = klicova.removeprefix("Klíčová slova:").strip()
        kousky.append({"otazka": otazka.strip(), "klicova": klicova, "odpoved": zbytek.strip()})
    return kousky


class Hledac:
    """BM25 nad kousky FAQ. Otázka (nadpis) má dvojnásobnou váhu – nejlépe vystihuje téma."""

    def __init__(self, kousky, k1=1.5, b=0.75):
        self.kousky = kousky
        self.k1, self.b = k1, b
        self.dokumenty = [Counter((normalizuj(k["otazka"]) + normalizuj(k["klicova"])) * 2 + normalizuj(k["odpoved"])) for k in kousky]
        self.prumerna_delka = sum(sum(d.values()) for d in self.dokumenty) / len(self.dokumenty)
        n = len(self.dokumenty)
        vyskyty = Counter(slovo for d in self.dokumenty for slovo in d)
        self.idf = {s: math.log(1 + (n - v + 0.5) / (v + 0.5)) for s, v in vyskyty.items()}

    def skore(self, dotaz_slova, dokument):
        delka = sum(dokument.values())
        celkem = 0.0
        for slovo in set(dotaz_slova):
            f = dokument.get(slovo, 0)
            if f:
                celkem += self.idf[slovo] * f * (self.k1 + 1) / (
                    f + self.k1 * (1 - self.b + self.b * delka / self.prumerna_delka))
        return celkem

    def najdi(self, text, kolik=3, min_skore=MIN_SKORE):
        slova = normalizuj(text)
        vysledky = [(self.skore(slova, d), k) for d, k in zip(self.dokumenty, self.kousky)]
        vysledky.sort(key=lambda x: x[0], reverse=True)
        return [{**k, "skore": round(s, 2)} for s, k in vysledky[:kolik] if s >= min_skore]


_hledac = None


def najdi_v_faq(text, kolik=3):
    """Hlavní funkce pro zbytek agenta. FAQ se načte jen jednou."""
    global _hledac
    if _hledac is None:
        _hledac = Hledac(nacti_faq())
    return _hledac.najdi(text, kolik)
