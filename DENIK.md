# Vývojový deník – AI back-office agent (Stěhování Bobr)

Záznam rozhodnutí, měření a chyb. Každé číslo je z `vysledky/`.

## Architektura
- AI (Claude Haiku) jen čte text poptávky a vrací strukturovaná data (tool use).
- Všechno ostatní dělá kód: převod „N. NP", kontrola typu zakázky, ověření měst, výpočet ceny.
- Princip: AI navrhuje, kód rozhoduje. Když si nejsme jistí, předáme člověku.

## Měření a zjištění
1. **První eval (30 poptávek): 93 %.** AI si vymýšlela města („okolí Zlína"). Oprava: popis pole „pokud není jasné, null".
2. **Nedeterminismus:** stejná poptávka jednou prošla, jednou ne („Frýšták"). Oprava: ověřování měst proti seznamu firmy kódem.
3. **Těžší sada (50 poptávek): 94 %.** AI neznala „1. NP = přízemí".
4. **Regrese 94 % → 62 %:** pravidlo pro NP začala AI používat na všechna patra. Bez evalu by se to nasadilo.
5. **Pevná pravidla do kódu:** převod NP regulárním výrazem místo promptu → 100 % ve 3 bězích.
6. **Holdout v1 (15 poptávek od jiného modelu): 73 %.** Overfitting odhalen. Rozbor: 3 bezpečné chyby, 1 nebezpečná (cena za celý dům u stěhování části věcí).
7. **Změna návrhu:** nové pole `typ_zakazky`. Cena podle velikosti jen u celého stěhování.
8. **Chyby v testech, ne v AI:** u P18/P21 měla AI pravdu, opravili jsme správné odpovědi. P18 je hraniční i pro člověka – necháno jako známý případ.
9. **Holdout v2 (22 poptávek, pestřejší): 72,7 %.** Nebezpečná chyba: Halenkovice → Zlín.
10. **Příčina byl náš kód, ne AI:** podobnostní porovnání (85,7 % podobnost s Malenovice). Oprava: přesné porovnání + regresní unit test.

## Známé limity
- Klasifikace typu zakázky je přecitlivělá: když zákazník vyjmenuje věci, AI občas označí celé stěhování jako část (bezpečná chyba → předání člověku).
- Vzdálenost = ze Zlína k vzdálenějšímu místu (zjednodušení, dál mapové API).
- Hraniční případy (P18) by měl agent řešit doptáním – zatím není.

## Náklady
- ~1 800 tokenů vstup / ~350 výstup na poptávku (Haiku), ~1,6 s na poptávku.