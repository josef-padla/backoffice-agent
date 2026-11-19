from dotenv import load_dotenv
import anthropic

load_dotenv()
client = anthropic.Anthropic()

poptavka = """Dobrý den, stěhujeme se 12. 3. z bytu 3+1 ve 3. patře (bez výtahu)
ve Zlíně do domu v Otrokovicích. Kolik by to stálo? Díky, Jana Nováková"""

odpoved = client.messages.create(
    model="claude-haiku-5-5",
    max_tokens=500,
    messages=[{"role": "user", "content": f"Shrň stručně tuhle poptávku stěhovací firmě:\n\n{poptavka}"}],
)

print(odpoved.content[0].text)
print("---")
print("Tokeny:", odpoved.usage.input_tokens, "in /", odpoved.usage.output_tokens, "out")
