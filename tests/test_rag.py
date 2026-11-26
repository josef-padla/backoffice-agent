"""Testy hledání ve FAQ – rychlé, bez AI."""
from backoffice_agent.rag import najdi_v_faq, normalizuj


def test_tvary_slov_se_sjednoti():
    assert normalizuj("krabice")[0] == normalizuj("krabicemi")[0]


def test_bez_diakritiky_najde_totez():
    s = najdi_v_faq("mate i krabice?")[0]["otazka"]
    assert s == najdi_v_faq("máte i krabice?")[0]["otazka"]


def test_najde_tezky_predmet():
    assert "piano" in najdi_v_faq("Stěhujete i pianina?")[0]["otazka"]


def test_bezna_poptavka_bez_dotazu_nic_nenajde():
    # Regrese: dřív obyčejná poptávka „našla" 3 nesouvisející otázky jen kvůli slovu „stěhujeme"
    assert najdi_v_faq("Dobrý den, stěhujeme byt 2+1 z Otrokovic do Zlína, 3. patro s výtahem.") == []


def test_klicova_slova_nejsou_v_odpovedi():
    assert all("Klíčová slova" not in f["odpoved"] for f in najdi_v_faq("krabice platba pojištění"))
