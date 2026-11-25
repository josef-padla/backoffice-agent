from backoffice_agent.extrakce import zkontroluj


def surove(**zmeny):
    zaklad = {"typ_zakazky": "cele_stehovani", "velikost": "2+1", "odkud": "Zlín", "kam": "Otrokovice",
              "patro_odkud": 1, "vytah_odkud": True, "patro_kam": None, "vytah_kam": None}
    zaklad.update(zmeny)
    return zaklad


def test_bez_zasahu():
    udaje, zasahy = zkontroluj(surove())
    assert zasahy == [] and udaje["k_overeni"] == []


def test_cast_vybaveni_rusi_velikost():
    udaje, zasahy = zkontroluj(surove(typ_zakazky="cast_vybaveni"))
    assert udaje["velikost"] is None and len(zasahy) == 1


def test_oprava_diakritiky_je_videt():
    udaje, zasahy = zkontroluj(surove(odkud="Frýšták"))
    assert udaje["odkud"] == "Fryšták"
    assert zasahy == ["odkud: 'Frýšták' → 'Fryšták'"]


def test_nezname_mesto_k_overeni():
    udaje, _ = zkontroluj(surove(odkud="Halenkovice"))
    assert udaje["odkud"] == "Halenkovice"
    assert udaje["k_overeni"] == ["odkud: neznámé město 'Halenkovice'"]


def test_surovy_vystup_se_nemeni():
    s = surove(odkud="Frýšták", typ_zakazky="jednotlive_kusy")
    zkontroluj(s)
    assert s["odkud"] == "Frýšták" and s["velikost"] == "2+1"


def test_prompt_obsahuje_vsechny_obce_firmy():
    # Seznam obcí v promptu se skládá z konfigurace firmy – když firma přidá obec, musí se objevit i tady
    from backoffice_agent.extrakce import SYSTEM, firma
    assert all(obec in SYSTEM for obec in firma["mesta"])


def test_okoli_nezname_mesto_se_ignoruje():
    udaje, zasahy = zkontroluj(surove(kam=None, kam_priblizne="Praha"))
    assert udaje["kam_priblizne"] is None and zasahy


def test_okoli_zname_mesto_se_normalizuje():
    udaje, _ = zkontroluj(surove(kam=None, kam_priblizne="zlin"))
    assert udaje["kam_priblizne"] == "Zlín"
