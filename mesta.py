import re
import unicodedata


def _bez_diakritiky(text):
    rozlozeny = unicodedata.normalize("NFD", text)
    return "".join(z for z in rozlozeny if unicodedata.category(z) != "Mn").lower().strip()


def over_mesto(nazev, firma):
    """Najde město v seznamu firmy. Vrátí (správný název, km ze Zlína),
    nebo (None, None), když město firma nezná.
    Zná i části měst (např. Malenovice -> Zlín).

    Porovnáváme PŘESNĚ (jen bez diakritiky a velikosti písmen), ne podobnostně.
    Podobnostní porovnání zaměnilo Halenkovice za Malenovice -> Zlín (špatná cena).
    Když si nejsme jistí, je bezpečnější město nenajít a předat poptávku člověku."""
    if nazev is None:
        return None, None

    # Závorky pryč: "Zlín (Prštné)" -> "Zlín"
    nazev = re.sub(r"\(.*?\)", "", nazev).strip()

    mesta = firma["mesta"]
    casti = firma.get("casti_mest", {})
    kandidati = {_bez_diakritiky(m): m for m in mesta}
    kandidati.update({_bez_diakritiky(c): mesto for c, mesto in casti.items()})

    spravne = kandidati.get(_bez_diakritiky(nazev))
    if spravne is None:
        return None, None
    return spravne, mesta[spravne]