from cena import nacti_firmu
from mesta import over_mesto

firma = nacti_firmu("bobr")


def test_presna_shoda():
    assert over_mesto("Otrokovice", firma) == ("Otrokovice", 12)


def test_diakritika_a_velka_pismena():
    assert over_mesto("Frýšták", firma) == ("Fryšták", 9)
    assert over_mesto("zlin", firma) == ("Zlín", 0)


def test_cast_mesta():
    assert over_mesto("Malenovice", firma) == ("Zlín", 0)
    assert over_mesto("Jizni Svahy", firma) == ("Zlín", 0)


def test_zavorky():
    assert over_mesto("Zlín (Prštné)", firma) == ("Zlín", 0)


def test_nezname_mesto():
    assert over_mesto("Praha", firma) == (None, None)
    assert over_mesto("Ostrava-Poruba", firma) == (None, None)


def test_podobne_jmeno_neni_shoda():
    # Chyba z holdoutu v2: Halenkovice se dřív zaměnily za Malenovice -> Zlín
    assert over_mesto("Halenkovice", firma) == (None, None)


def test_zadne_mesto():
    assert over_mesto(None, firma) == (None, None)