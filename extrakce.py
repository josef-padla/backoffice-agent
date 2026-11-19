import json
from dotenv import load_dotenv
import anthropic
from cena import nacti_firmu, spocitej_cenu

load_dotenv()
client = anthropic.Anthropic()
firma = nacti_firmu("bobr")

NASTROJ = {
    "name": "zapis_poptavku",
    "description": "Zapíše údaje vytažené z poptávky na stěhování.",
    "input_schema": {
        "type": "object",
        "properties": {
            "jmeno": {"type": ["string", "null"]},
            "datum": {"type": ["string", "null"], "description": "Datum stěhování tak, jak ho zákazník napsal"},
            "odkud": {"type": ["string", "null"], "description": "Město, odkud se stěhuje"},
            "kam": {"type": ["string", "null"], "description": "Město, kam se stěhuje"},
            "velikost": {"type": ["string", "null"], "enum": list(firma["odhad_hodin"].keys()) + [None]},
            "patro_odkud": {"type": ["integer", "null"]},
            "vytah_odkud": {"type": ["boolean", "null"]},
            "patro_kam": {"type": ["integer", "null"]},
            "vytah_kam": {"type": ["boolean", "null"]},
            "chybejici_udaje": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Údaje potřebné pro cenu, které v poptávce chybí",
            },
        },
        "required": ["jmeno", "datum", "odkud", "kam", "velikost", "patro_odkud",
                     "vytah_odkud", "patro_kam", "vytah_kam", "chybejici_udaje"],
    },
}

PROMPT = ("Vytáhni údaje z této poptávky. Nic si nevymýšlej – co v ní není, "
          "dej null a uveď to v chybejici_udaje.\n\n")


def vytahni_udaje(text, model="claude-haiku-5-5"):
    odpoved = client.messages.create(
        model=model,
        max_tokens=1000,
        tools=[NASTROJ],
        tool_choice={"type": "tool", "name": "zapis_poptavku"},
        messages=[{"role": "user", "content": PROMPT + text}],
    )
    return odpoved.content[0].input, odpoved.usage


def patra_bez_vytahu(patro, vytah):
    return patro if patro and vytah is False else 0


if __name__ == "__main__":
    poptavka = """Dobrý den, stěhujeme se 12. 3. z bytu 3+1 ve 3. patře (bez výtahu)
ve Zlíně do domu v Otrokovicích. Kolik by to stálo? Díky, Jana Nováková"""

    udaje, _ = vytahni_udaje(poptavka)
    print(json.dumps(udaje, ensure_ascii=False, indent=2))

    if udaje["velikost"] is None:
        print("Chybí velikost bytu – cenu nelze spočítat.")
    else:
        patra = patra_bez_vytahu(udaje["patro_odkud"], udaje["vytah_odkud"]) \
              + patra_bez_vytahu(udaje["patro_kam"], udaje["vytah_kam"])
        polozky, celkem = spocitej_cenu(firma, udaje["velikost"], km=12, patra_bez_vytahu=patra)
        print("---")
        for nazev, castka in polozky.items():
            print(f"{nazev}: {castka} Kč")
        print(f"CELKEM: {celkem} Kč")