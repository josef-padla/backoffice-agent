"""Eval vyhledávání ve FAQ (bez AI, zdarma, běží za vteřinu).
Měří: našel hledač správnou otázku na 1. místě? A u e-mailů bez dotazu – nenašel zbytečně nic?
Použití: uv run evaly/eval_rag.py
"""
import json
from pathlib import Path

from backoffice_agent.rag import najdi_v_faq

otazky = json.loads((Path(__file__).parent / "faq_otazky.json").read_text(encoding="utf-8"))
prvni = top3 = spravne_nic = celkem_s_cilem = celkem_bez = 0
for o in otazky:
    nalezene = najdi_v_faq(o["dotaz"])
    nazvy = [n["otazka"] for n in nalezene]
    if o["cil"] is None:
        celkem_bez += 1
        ok = not nalezene
        spravne_nic += ok
        print(f"{'✅' if ok else '⚠️ '} (nemá najít nic) {o['dotaz'][:50]}  ->  {nazvy}")
        continue
    celkem_s_cilem += 1
    na_prvnim = bool(nazvy) and nazvy[0] == o["cil"]
    prvni += na_prvnim
    top3 += o["cil"] in nazvy
    znacka = "✅" if na_prvnim else ("🟡" if o["cil"] in nazvy else "❌")
    print(f"{znacka} {o['dotaz'][:50]}  ->  {nazvy[0] if nazvy else 'NIC'}")

print(f"\nSprávná odpověď na 1. místě: {prvni}/{celkem_s_cilem}")
print(f"Správná odpověď mezi top 3:  {top3}/{celkem_s_cilem}")
print(f"E-maily bez dotazu, kde správně nenašel nic: {spravne_nic}/{celkem_bez}")
