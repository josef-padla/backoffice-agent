"""Rubrika pro hodnocení odpovědí zákazníkům.
Stejné definice používá člověk i AI hodnotitel – jinak by se jejich hodnocení nedala porovnat."""

KRITERIA = {
    "cestina": "Text je napsaný správnou češtinou (nebo jazykem zákazníka) bez gramatických chyb a krkolomných vazeb.",
    "osloveni": "Oslovení je vhodné pro firemní e-mail: 'pane/paní' + příjmení ve 3. pádě, nebo neutrální 'Dobrý den,'. "
                "Ne křestní jméno s 'pane/paní'.",
    "jen_podklady": "Odpověď neobsahuje nic, co není v poptávce nebo v podkladech: žádné vymyšlené údaje, sliby, slevy ani termíny.",
    "ucel": "Odpověď dělá to, co má: nabídka shrne podklady a obsahuje rozpis ceny; doptání se ptá právě na chybějící údaje; "
            "předání jen potvrdí přijetí a že se ozve kolega.",
    "ton": "Tón je zdvořilý, stručný a lidský. Žádné zbytečné fráze ani přehnaná formálnost.",
}