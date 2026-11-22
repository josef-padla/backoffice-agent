# AI back-office agent – Stěhování Bobr

Portfoliový projekt: AI agent, který zpracovává poptávky fiktivní stěhovací firmy.
(Popis projektu doplním. Níže je zatím jen technický přehled.)

## Struktura

```
src/backoffice_agent/   kód agenta
  extrakce.py           AI čte poptávku + kontroly kódem
  pipeline.py           celá cesta poptávky + trace (záznam kroků do logy/)
  mesta.py              ověření měst podle seznamu firmy
  cena.py               načtení firmy a výpočet ceny
firmy/bobr.toml         „firma": ceník, odhad hodin, města, části měst
evaly/
  eval.py               měření přesnosti AI
  sady/hlavni/          hlavní testovací sada (podle ní ladím)
  sady/holdout_v1/      nezávislé sady (podle nich NEladím)
  sady/holdout_v2/
  vysledky/             výsledky všech běhů evalu
tests/                  unit testy kódu (pytest)
skripty/                pomocné a jednorázové skripty
DENIK.md                vývojový deník
```

## Spuštění

```
uv run python -m backoffice_agent.pipeline   # ukázka s trace
uv run python -m backoffice_agent.pipeline "text poptávky"
uv run pytest                                # unit testy kódu
uv run evaly/eval.py                         # eval na hlavní sadě
uv run evaly/eval.py holdout_v2              # eval na jiné sadě
```

Potřebuje soubor `.env` s `ANTHROPIC_API_KEY=...`.
