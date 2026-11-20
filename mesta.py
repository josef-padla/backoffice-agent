import difflib
import unicodedata


def _bez_diakritiky(text):
    rozlozeny = unicodedata.normalize("NFD", text)
    return "".join(z for z in rozlozeny if unicodedata.category(z) != "Mn").lower().strip()


def over_mesto(nazev, firma):
    """Najde město v seznamu firmy. Vrátí (správný název, km ze Zlína),
    nebo (None, None), když město firma nezná."""
    if nazev is None:
        return None, None
    mesta = firma["mesta"]
    podle_klice = {_bez_diakritiky(m): m for m in mesta}
    shoda = difflib.get_close_matches(_bez_diakritiky(nazev), podle_klice.keys(), n=1, cutoff=0.85)
    if not shoda:
        return None, None
    spravne = podle_klice[shoda[0]]
    return spravne, mesta[spravne]