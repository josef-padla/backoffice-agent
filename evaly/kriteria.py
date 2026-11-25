"""Rubrika pro hodnocení odpovědí zákazníkům.
Stejné definice používá člověk i AI hodnotitel – jinak by se jejich hodnocení nedala porovnat."""

KRITERIA = {
    "cestina": "Text je napsaný správnou češtinou (nebo jazykem zákazníka) bez gramatických chyb, špatných vazeb, "
               "špatného slovosledu a překlepů. Firma mluví jednotně v 1. osobě množného čísla ('my'), ne 'já'.",
    "osloveni": "Oslovení je vhodné pro firemní e-mail: 'pane/paní' + příjmení v 5. pádě (paní Nováková, pane Malý); "
                "když známe jen křestní jméno, tak 'pane/paní' + křestní jméno v 5. pádě (paní Hano); "
                "když jméno neznáme, neutrální 'Dobrý den,'. Nikdy holé křestní jméno ('Hano'). "
                "Platí pro češtinu a slovenštinu; v angličtině je 'Hello John' / 'Dear John' v pořádku.",
    "jen_podklady": "Odpověď neobsahuje nic, co není v poptávce nebo v podkladech, a nic z poptávky nepřekrucuje: "
                    "žádné vymyšlené údaje, sliby, slevy ani termíny; odkud/kam a patra nesmí být zaměněné.",
    "ucel": "Odpověď dělá to, co má: nabídka shrne podklady a obsahuje rozpis ceny, který odpovídá tomu, co text slibuje; "
            "doptání se ptá právě na chybějící údaje (ne na to, co zákazník napsal, že neví); "
            "předání jen potvrdí přijetí a že se ozve kolega.",
    "ton": "Tón je zdvořilý, stručný a lidský. Žádné zbytečné fráze ani přehnaná formálnost.",
}