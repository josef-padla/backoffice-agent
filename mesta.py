import difflib
import re
import unicodedata


def _bez_diakritiky(text):
    rozlozeny = unicodedata.normalize("NFD", text)
    return "".join(z for z in rozlozeny if unicodedata.category(z) != "Mn").lower().strip()


def over_mesto(nazev, firma):
    """Najde město v seznamu firmy. Vrátí (správný název, km ze Zlína),
    nebo (None, None), když město firma nezná.
    Zná i části měst (např. Malenovice -> Zlín)."""
    if nazev is None:
        return None, None

    # Závorky pryč: "Zlín (Prštné)" -> "Zlín"
    nazev = re.sub(r"\(.*?\)", "", nazev).strip()

    mesta = firma["mesta"]
    casti = firma.get("casti_mest", {})
    kandidati = {_bez_diakritiky(m): m for m in mesta}
    kandidati.update({_bez_diakritiky(c): mesto for c, mesto in casti.items()})

    shoda = difflib.get_close_matches(_bez_diakritiky(nazev), kandidati.keys(), n=1, cutoff=0.85)
    if not shoda:
        return None, None
    spravne = kandidati[shoda[0]]
    return spravne, mesta[spravne]