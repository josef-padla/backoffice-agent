"""Server pro nasazení (Render): webové demo + Telegram bot v jednom.

Rozdíl proti spuštění na Macu:
- Na Macu se bot pořád ptá Telegramu „máš pro mě zprávu?" (polling) – to potřebuje běžet nonstop.
- Na serveru je to naopak: Telegram sám pošle zprávu na naši adresu (webhook). Díky tomu může
  bezplatný server spát a probudí se, až něco přijde.

Spuštění lokálně:  uv run uvicorn backoffice_agent.server:app --reload
"""
import asyncio
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from telegram import Update
from telegram.ext import Application

from backoffice_agent.pipeline import zpracuj_poptavku
from backoffice_agent.telegram_bot import TOKEN, pridej_handlery

VEREJNA_ADRESA = os.environ.get("RENDER_EXTERNAL_URL")   # Render ji nastaví sám
TAJNY_KLIC = os.environ.get("WEBHOOK_SECRET", "")        # aby nám zprávy „od Telegramu" nemohl posílat kdokoli
DENNI_LIMIT = int(os.environ.get("DEMO_DENNI_LIMIT", "30"))  # ochrana kreditů: max. zpracování dema za den
MAX_ZA_MINUTU_Z_IP = 3

bot = pridej_handlery(Application.builder().token(TOKEN).updater(None).build())


@asynccontextmanager
async def zivotni_cyklus(app):
    await bot.initialize()
    await bot.start()
    if VEREJNA_ADRESA:
        await bot.bot.set_webhook(f"{VEREJNA_ADRESA}/telegram", secret_token=TAJNY_KLIC or None,
                                  allowed_updates=["message", "callback_query"])
    yield
    await bot.stop()
    await bot.shutdown()


app = FastAPI(lifespan=zivotni_cyklus)
STRANKA = (Path(__file__).parent / "demo.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
async def demo():
    return STRANKA


@app.get("/zdravi")
async def zdravi():
    return {"ok": True}


@app.post("/telegram")
async def telegram(request: Request):
    if TAJNY_KLIC and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != TAJNY_KLIC:
        raise HTTPException(403)
    # Zprávu jen předáme botovi a hned odpovíme – Telegram nemusí čekat, než agent dopíše.
    try:
        update = Update.de_json(await request.json(), bot.bot)
    except Exception:
        raise HTTPException(400, "Neplatná zpráva")
    await bot.update_queue.put(update)
    return {"ok": True}


# --- Webové demo -----------------------------------------------------------------------------

pocitadlo = {"den": date.today(), "pocet": 0}
posledni_z_ip = defaultdict(deque)


class Poptavka(BaseModel):
    text: str = Field(min_length=10, max_length=3000)


def zkontroluj_limity(ip):
    if pocitadlo["den"] != date.today():
        pocitadlo.update(den=date.today(), pocet=0)
    if pocitadlo["pocet"] >= DENNI_LIMIT:
        raise HTTPException(429, "Dnešní limit dema je vyčerpaný – zkuste to prosím zítra.")
    casy = posledni_z_ip[ip]
    while casy and time.time() - casy[0] > 60:
        casy.popleft()
    if len(casy) >= MAX_ZA_MINUTU_Z_IP:
        raise HTTPException(429, "Moc rychle za sebou – zkuste to za minutu.")
    casy.append(time.time())
    pocitadlo["pocet"] += 1


@app.post("/api/zpracuj")
async def zpracuj(poptavka: Poptavka, request: Request):
    ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0].strip()
    zkontroluj_limity(ip)
    z = await asyncio.to_thread(zpracuj_poptavku, poptavka.text)
    kroky = {k["krok"]: k for k in z["kroky"]}
    rozhodnuti = kroky["Rozhodnutí"]
    return {
        "udaje": {k: v for k, v in z["udaje"].items() if k != "chybejici_udaje"},
        "zasahy_kodu": kroky["Kontroly kódem"]["zasahy"],
        "akce": z["akce"],
        "duvody": rozhodnuti["duvody"],
        "cena": {"polozky": rozhodnuti.get("polozky"), "celkem": rozhodnuti.get("celkem")},
        "faq": kroky.get("Hledání v FAQ", {}).get("nalezeno", []),
        "odpoved": z["odpoved"],
        "k_rucni_uprave": z["k_rucni_uprave"],
        "doba_s": z["doba_s"],
        "zbyva_dnes": DENNI_LIMIT - pocitadlo["pocet"],
    }
