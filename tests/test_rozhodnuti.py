from backoffice_agent.odpoved import rozpis_ceny
from backoffice_agent.pipeline import popis_mista, rozhodni


def udaje(**zmeny):
    zaklad = {"typ_zakazky": "cele_stehovani", "velikost": "3+1", "odkud": "Zlín", "kam": "Otrokovice",
              "patro_odkud": 3, "vytah_odkud": False, "patro_kam": None, "vytah_kam": None,
              "kam_je_dum": True, "je_obchodni_nabidka": False, "k_overeni": []}
    zaklad.update(zmeny)
    return zaklad


def test_vse_zname_je_nabidka():
    assert rozhodni(udaje()) == ("nabidka", [])


def test_spam_bez_odpovedi():
    akce, _ = rozhodni(udaje(typ_zakazky="neni_poptavka", je_obchodni_nabidka=True))
    assert akce == "bez_odpovedi"


def test_reklamace_k_cloveku():
    akce, _ = rozhodni(udaje(typ_zakazky="neni_poptavka"))
    assert akce == "predat_cloveku"


def test_ptame_se_na_patro_v_cili():
    # chyba z ručního hodnocení (P11, P12): na cíl jsme se neptali
    akce, chybi = rozhodni(udaje(kam_je_dum=None))
    assert akce == "doptat"
    assert any("nový byt" in c for c in chybi)


def test_ptame_se_na_neznamy_vytah():
    # chyba z ručního hodnocení (P14): patro známe, výtah ne
    akce, chybi = rozhodni(udaje(vytah_odkud=None))
    assert akce == "doptat"
    assert any("výtah" in c for c in chybi)


def test_z_domu_nepotrebujeme_patro():
    akce, _ = rozhodni(udaje(velikost="dum", patro_odkud=None, vytah_odkud=None))
    assert akce == "nabidka"


def test_popis_mista_rozlisuje_strany():
    assert popis_mista("Vsetín", 4, False, False) == "Vsetín, 4. patro, bez výtahu"
    assert popis_mista("Zlín", None, None, None) == "Zlín, patro neuvedeno"
    assert popis_mista("Otrokovice", None, None, True) == "Otrokovice, rodinný dům"


def test_rozpis_v_anglictine():
    r = rozpis_ceny({"práce": 3960, "doprava": 2500}, 6460, "en")
    assert "labour" in r and "Total (approx.): 6 460 CZK" in r and "práce" not in r
