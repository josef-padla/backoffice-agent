import json
from extrakce import client, SYSTEM, NASTROJ, predzpracuj, firma
from mesta import over_mesto

text = """Dobrý den, chtěla bych se zeptat jestli stěhujete i z menších obcí. Potřebujeme přestěhovat domek z Halenkovic do Otrokovic. Nejde o úplně všechno, část věcí si odvezeme sami."""

odpoved = client.messages.create(
    model="claude-haiku-5-5",
    max_tokens=1000,
    system=SYSTEM,
    tools=[NASTROJ],
    tool_choice={"type": "tool", "name": "zapis_poptavku"},
    messages=[{"role": "user", "content": f"<poptavka>\n{predzpracuj(text)}\n</poptavka>"}],
)
surove = odpoved.content[0].input
print("AI vrátila (před kontrolou kódem):")
print(json.dumps(surove, ensure_ascii=False, indent=2))
print("\nKód z toho udělá:")
print("odkud:", surove["odkud"], "->", over_mesto(surove["odkud"], firma))
print("kam:  ", surove["kam"], "->", over_mesto(surove["kam"], firma))