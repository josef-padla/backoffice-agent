"""Telegram bot: člověk schvaluje návrhy odpovědí („AI navrhuje, člověk rozhoduje").

Jak to funguje (demo):
  1. Pošleš botovi text poptávky (jako by přišel e-mailem).
  2. Bot ho pošle agentovi (pipeline.zpracuj_poptavku).
  3. Návrh odpovědi ti přijde zpět s tlačítky ✅ Odeslat / ✏️ Upravit / ❌ Zahodit.
  4. U „Upravit" napíšeš pokyn (např. „buď stručnější") a AI návrh přepíše.
  E-mail se v demu reálně neodesílá – jen se zaznamená rozhodnutí.

Spuštění:  uv run python -m backoffice_agent.telegram_bot
"""
import asyncio
import os
import uuid

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

from backoffice_agent.odpoved import uprav_odpoved, zkontroluj_odpoved
from backoffice_agent.pipeline import PISATEL_VYCHOZI, zpracuj_poptavku

load_dotenv()
TOKEN = os.environ["TELEGRAM_TOKEN"]
# Bot smí používat jen majitel. Jinak by kdokoli, kdo bota najde, mohl utrácet kredity za API.
POVOLENY_CHAT = os.environ.get("TELEGRAM_CHAT_ID")

NAZVY_AKCI = {
    "nabidka": "💰 Cenová nabídka",
    "doptat": "❓ Doptání na chybějící údaje",
    "predat_cloveku": "🙋 Předat člověku",
    "bez_odpovedi": "🚫 Bez odpovědi (spam / nabídka)",
}

# Návrhy čekající na rozhodnutí: krátké id -> záznam. (Zatím jen v paměti – po restartu zmizí.)
cekajici = {}


def je_majitel(update: Update) -> bool:
    return POVOLENY_CHAT is not None and str(update.effective_chat.id) == POVOLENY_CHAT


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if POVOLENY_CHAT is None:
        await update.message.reply_text(
            f"Tvoje chat ID je: {chat_id}\n\n"
            f"Ulož ho do .env jako řádek:\nTELEGRAM_CHAT_ID={chat_id}\n"
            f"a bota restartuj.")
    elif je_majitel(update):
        await update.message.reply_text("Ahoj! Pošli mi text poptávky a já připravím návrh odpovědi.")
    else:
        await update.message.reply_text("Tenhle bot je soukromý.")


async def posli_navrh(message, zaznam, nadpis):
    """Pošle návrh odpovědi s tlačítky a uloží ho mezi čekající."""
    id_navrhu = uuid.uuid4().hex[:8]
    cekajici[id_navrhu] = zaznam
    varovani = "\n⚠️ Kód našel problém – zkontroluj před odesláním!" if zaznam["k_rucni_uprave"] else ""
    tlacitka = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Odeslat", callback_data=f"ok:{id_navrhu}"),
        InlineKeyboardButton("✏️ Upravit", callback_data=f"edit:{id_navrhu}"),
        InlineKeyboardButton("❌ Zahodit", callback_data=f"x:{id_navrhu}"),
    ]])
    await message.reply_text(
        f"{nadpis}{varovani}\n\n——— NÁVRH ODPOVĚDI ———\n\n{zaznam['odpoved']}",
        reply_markup=tlacitka)


async def zprava(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Každá textová zpráva je buď pokyn k úpravě (když zrovna upravuješ), nebo nová poptávka."""
    if not je_majitel(update):
        await update.message.reply_text("Tenhle bot je soukromý.")
        return
    id_upravy = context.user_data.pop("upravuji", None)
    if id_upravy and id_upravy in cekajici:
        await uprava(update, cekajici.pop(id_upravy))
    else:
        await nova_poptavka(update)


async def nova_poptavka(update: Update):
    await update.message.reply_text("⏳ Zpracovávám poptávku…")
    # Agent běží pár sekund a není „async" – pustíme ho bokem, ať bot mezitím nezamrzne.
    zaznam = await asyncio.to_thread(zpracuj_poptavku, update.message.text)

    akce = NAZVY_AKCI.get(zaznam["akce"], zaznam["akce"])
    if zaznam["odpoved"] is None:
        await update.message.reply_text(f"{akce}\n\nAgent na tohle neodpovídá. Nic není potřeba schvalovat.")
        return
    await posli_navrh(update.message, zaznam, akce)


async def uprava(update: Update, zaznam):
    """AI přepíše návrh podle pokynu. Kód pak znovu zkontroluje částky a dosadí cenu."""
    await update.message.reply_text("⏳ Upravuji návrh…")
    navrh, _ = await asyncio.to_thread(
        uprav_odpoved, zaznam["poptavka"], zaznam["navrh"], update.message.text, PISATEL_VYCHOZI)
    hotova, problemy = zkontroluj_odpoved(navrh, zaznam["akce"], zaznam["rozpis"])
    zaznam = {**zaznam, "navrh": navrh, "odpoved": hotova, "k_rucni_uprave": bool(problemy)}
    await posli_navrh(update.message, zaznam, "✏️ Upravený návrh")


async def tlacitko(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dotaz = update.callback_query
    await dotaz.answer()  # Telegram chce potvrzení, jinak se tlačítko „točí"
    if not je_majitel(update):
        return

    volba, id_navrhu = dotaz.data.split(":")
    if volba == "edit" and id_navrhu in cekajici:
        # Návrh zatím necháme mezi čekajícími – další zpráva od tebe bude pokyn k úpravě.
        context.user_data["upravuji"] = id_navrhu
        await dotaz.edit_message_text(dotaz.message.text + "\n\n✏️ UPRAVUJE SE – nová verze přijde níž.")
        await dotaz.message.reply_text("Napiš, co mám změnit (např. „buď stručnější“ nebo „přidej, že termín potvrdíme zítra“).")
        return
    zaznam = cekajici.pop(id_navrhu, None)
    if zaznam is None:
        await dotaz.edit_message_reply_markup(None)
        await dotaz.message.reply_text("Tenhle návrh už je vyřízený (nebo se bot mezitím restartoval).")
        return

    if volba == "ok":
        stav = "✅ SCHVÁLENO – v ostrém provozu by se teď e-mail odeslal zákazníkovi."
    else:
        stav = "❌ ZAHOZENO – zákazníkovi nic nepůjde."
    # Tlačítka zmizí, ať nejde kliknout dvakrát, a pod návrh se dopíše rozhodnutí.
    await dotaz.edit_message_text(dotaz.message.text + f"\n\n{stav}")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, zprava))
    app.add_handler(CallbackQueryHandler(tlacitko))
    print("Bot běží. Zastavíš ho Ctrl+C.")
    app.run_polling()


if __name__ == "__main__":
    main()
