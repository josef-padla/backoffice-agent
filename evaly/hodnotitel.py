"""LLM-as-judge, krok 2: AI hodnotitel ohodnotí odpovědi podle rubriky a porovnáme ho s člověkem."""
import json
import sys
from pathlib import Path

from backoffice_agent.extrakce import client
from kriteria import KRITERIA

EVALY = Path(__file__).resolve().parent
ODPOVEDI = EVALY / "hodnoceni" / "odpovedi.json"
MODELY = sys.argv[1:] or ["claude-sonnet-5-5", "claude-opus-5-5"]

# Plochý tvar (žádné vnořené objekty): u vnořených objektů je Sonnet občas vracel jako text.
# Pro každé kritérium dvě pole: nejdřív zdůvodnění, pak verdikt.
VLASTNOSTI = {}
for k in KRITERIA:
    VLASTNOSTI[f"{k}_zduvodneni"] = {"type": "string", "description": f"Krátké zdůvodnění pro '{k}'; u nesplnění konkrétní chyba."}
    VLASTNOSTI[k] = {"type": "boolean", "description": f"Je kritérium '{k}' splněno?"}

NASTROJ = {
    "name": "ohodnot",
    "description": "Zapíše hodnocení odpovědi podle rubriky.",
    "input_schema": {"type": "object", "properties": VLASTNOSTI, "required": list(VLASTNOSTI)},
}


def je_platne(h):
    """Kontrola kódem: hodnocení musí mít všechna pole ve správném typu."""
    return all(isinstance(h.get(k), bool) and isinstance(h.get(f"{k}_zduvodneni"), str) for k in KRITERIA)


SYSTEM = (
    "Jsi pečlivý hodnotitel e-mailových odpovědí stěhovací firmy zákazníkům. Odpovědi napsala AI a ty v nich hledáš chyby.\n"
    "Každé kritérium hodnotíš zvlášť: splněno = true, nesplněno = false. U každého nejdřív napiš zdůvodnění, pak verdikt.\n"
    "Rozpis ceny (řádky s Kč) doplnil kód – jeho výpočet nekontroluj, ale hodnoť, jestli odpovídá tomu, co text tvrdí.\n\n"
    "Kritéria:\n" + "\n".join(f"- {k}: {v}" for k, v in KRITERIA.items())
)


def ohodnot(polozka, model, pokusy=2):
    """Novější modely nedovolí nástroj vynutit – nabídneme ho a kódem ověříme, že ho model použil."""
    for _ in range(pokusy):
        odpoved = client.messages.create(
            model=model,
            max_tokens=4000,
            system=SYSTEM,
            tools=[NASTROJ],
            tool_choice={"type": "auto"},
            messages=[{"role": "user", "content": (
                f"Typ odpovědi: {polozka['akce']}\n\n"
                f"<poptavka>\n{polozka['poptavka']}\n</poptavka>\n\n"
                f"<odpoved>\n{polozka['odpoved']}\n</odpoved>\n\n"
                "Hodnocení zapiš pomocí nástroje ohodnot."
            )}],
        )
        bloky = [b for b in odpoved.content if b.type == "tool_use"]
        if bloky and je_platne(bloky[0].input):
            return bloky[0].input, odpoved.usage
    raise RuntimeError(f"{model} nevrátil platné hodnocení ani na {pokusy}. pokus ({polozka['id']})")


if __name__ == "__main__":
    data = json.loads(ODPOVEDI.read_text(encoding="utf-8"))

    for model in MODELY:
        print(f"\n===== {model} =====")
        shody = celkem = prehlednuto = prisnejsi = 0
        po_kriteriich = {k: [0, 0] for k in KRITERIA}  # [shoda, celkem]
        rozdily, vysledky = [], []
        tokeny_in = tokeny_out = 0

        for p in data:
            h, usage = ohodnot(p, model)
            tokeny_in += usage.input_tokens
            tokeny_out += usage.output_tokens
            vysledky.append({"id": p["id"], "hodnotitel": h})
            for k in KRITERIA:
                clovek, ai = p["clovek"][k], h[k]
                celkem += 1
                po_kriteriich[k][1] += 1
                if clovek == ai:
                    shody += 1
                    po_kriteriich[k][0] += 1
                else:
                    if ai and not clovek:
                        prehlednuto += 1
                        druh = "AI PŘEHLÉDLA chybu"
                    else:
                        prisnejsi += 1
                        druh = "AI je přísnější"
                    rozdily.append(f"{p['id']} {k}: {druh}\n     AI: {h[k + '_zduvodneni']}\n     člověk: {p['clovek']['poznamka']}")
            print(".", end="", flush=True)

        print(f"\nShoda s člověkem: {shody}/{celkem} ({shody / celkem:.0%})")
        print(f"AI přehlédla chybu, kterou našel člověk: {prehlednuto}×")
        print(f"AI přísnější než člověk: {prisnejsi}×")
        print("Podle kritérií:")
        for k, (ok, n) in po_kriteriich.items():
            print(f"  {k}: {ok}/{n}")
        print(f"Tokeny: {tokeny_in} in / {tokeny_out} out")
        print("Neshody:")
        for r in rozdily:
            print(" -", r)

        soubor = EVALY / "hodnoceni" / f"hodnotitel_{model}.json"
        soubor.write_text(json.dumps(vysledky, ensure_ascii=False, indent=2), encoding="utf-8")
