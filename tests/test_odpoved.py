from backoffice_agent.odpoved import rozpis_ceny, zkontroluj_odpoved

ROZPIS = rozpis_ceny({"práce": 5940, "doprava": 300, "balení": 0}, 6240)


def test_rozpis_vynecha_nuly_a_formatuje():
    assert "balení" not in ROZPIS
    assert "Celkem (orientačně): 6 240 Kč" in ROZPIS


def test_znacka_se_nahradi_cenou():
    text, problemy = zkontroluj_odpoved("Dobrý den,\n{{CENA}}\nTým Stěhování Bobr", "nabidka", ROZPIS)
    assert problemy == []
    assert "6 240 Kč" in text and "{{CENA}}" not in text


def test_chybejici_znacka_je_problem():
    _, problemy = zkontroluj_odpoved("Dobrý den, pošleme cenu.", "nabidka", ROZPIS)
    assert problemy


def test_vlastni_castka_od_ai_je_problem():
    _, problemy = zkontroluj_odpoved("Bude to stát asi 5 000 Kč.\n{{CENA}}", "nabidka", ROZPIS)
    assert "AI napsala do textu vlastní částku" in problemy


def test_doptani_s_cisly_bez_kc_je_v_poradku():
    _, problemy = zkontroluj_odpoved("Je byt 2+1? Ve kterém je patře, třeba 3.?", "doptat")
    assert problemy == []