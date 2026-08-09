# -*- coding: utf-8 -*-
"""
Otevře nové kolo hlasování: vygeneruje tokeny, uloží stav a rozešle pozvánky.
Spouští se tlačítkem „OK“ v admin.html (workflow_dispatch nad rozeslat.yml).
"""
from __future__ import annotations

import os
import secrets
import sys
from datetime import date

import spolecne as s


def id_kola() -> str:
    zaklad = date.today().isoformat()
    existujici = (s.DATA / "kola")
    if not (existujici / zaklad).exists():
        return zaklad
    n = 2
    while (existujici / f"{zaklad}-{n}").exists():
        n += 1
    return f"{zaklad}-{n}"


def telo_pozvanky(jmeno: str, odkazy: list[tuple[str, str]], nazev: str,
                  termin: str, poznamka: str) -> str:
    radky = [
        f"Dobrý den, {jmeno.split()[0] if jmeno else ''},".strip().rstrip(","),
        "",
        f"otevřeli jsme hlasování: {nazev}.",
    ]
    if termin:
        radky.append(f"Prosíme o vyplnění do {termin}.")
    if poznamka:
        radky += ["", poznamka]
    radky += ["", "Vaše osobní odkazy (nesdílejte je, identifikují Vás):", ""]
    for popis, url in odkazy:
        radky += [f"  {popis}:", f"  {url}", ""]
    radky += [
        "Postup: formulář vyplňte, klikněte na „Odevzdat lístek“ a potom",
        "na „Odeslat e-mailem“. Otevře se Vám rozepsaná zpráva – jen ji odešlete.",
        "Text v kódovém bloku na konci zprávy prosím neupravujte, čte ho",
        "automat, který odpovědi sbírá. Přijetí Vám potvrdíme zpět e-mailem.",
        "",
        "Děkujeme.",
    ]
    return "\n".join(radky)


def main() -> None:
    nazev = os.environ.get("NAZEV") or "Hlasování investičního výboru"
    termin = (os.environ.get("TERMIN") or "").strip()
    poznamka = (os.environ.get("POZNAMKA") or "").strip()
    formulare = [t.strip() for t in (os.environ.get("FORMULARE") or "navrhy,priority,hlavni").split(",")]
    formulare = [t for t in formulare if t in s.TYPY]
    zakladni_url = (os.environ.get("PAGES_URL") or "").rstrip("/")

    if not formulare:
        raise SystemExit("Nebyl vybrán žádný formulář.")
    if not zakladni_url:
        raise SystemExit("Chybí proměnná PAGES_URL (adresa publikované stránky).")

    stare = s.nacti_kolo()
    if stare and stare.get("stav") == "otevreno" and os.environ.get("PREPSAT") != "true":
        raise SystemExit(
            f"Kolo {stare['id']} je stále otevřené. Nejdřív ho ukončete, "
            "nebo zvolte volbu „přepsat běžící kolo“."
        )

    lide = s.hlasujici_z_configu()
    kolo = {
        "id": id_kola(),
        "nazev": nazev,
        "stav": "otevreno",
        "otevreno": s.ted(),
        "uzavreno": None,
        "termin": termin,
        "formulare": formulare,
        "hlasujici": [],
    }

    hash_url = {"navrhy": "#/temata-navrhy", "priority": "#/temata-priority", "hlavni": "#/hlavni-cast"}
    odeslano, chyby = [], []

    for clovek in lide:
        token = f"{clovek['i']}.{secrets.token_urlsafe(24)}"
        kolo["hlasujici"].append({
            "i": clovek["i"],
            "jmeno": clovek["jmeno"],
            "token_hash": s.hash_tokenu(token),
            "odevzdal": {t: None for t in formulare},
        })
        odkazy = [
            (s.NAZVY_TYPU[t], f"{zakladni_url}/?t={token}{hash_url[t]}")
            for t in formulare
        ]
        try:
            s.posli_mail(
                clovek["email"],
                f"[{kolo['id']}] {nazev} – prosíme o vyplnění",
                telo_pozvanky(clovek["jmeno"], odkazy, nazev, termin, poznamka),
            )
            odeslano.append(clovek["jmeno"])
        except Exception as e:
            chyby.append(f"{clovek['jmeno']} <{clovek['email']}>: {e}")

    s.uloz_kolo(kolo)
    slozka = s.slozka_kola(kolo)
    (slozka / "log.md").write_text(
        f"# {kolo['nazev']} ({kolo['id']})\n\n"
        f"- {s.lidsky(kolo['otevreno'])} – kolo otevřeno, "
        f"pozvánky odeslány {len(odeslano)} hlasujícím\n",
        encoding="utf-8",
    )
    s.commit(f"Otevřeno kolo {kolo['id']}: {nazev}", ["data"])

    prehled = [
        f"## Kolo `{kolo['id']}` otevřeno",
        "",
        f"- **Název:** {nazev}",
        f"- **Formuláře:** {', '.join(s.NAZVY_TYPU[t] for t in formulare)}",
        f"- **Termín:** {termin or '–'}",
        f"- **Pozvánky odeslány:** {len(odeslano)} / {len(lide)}",
    ]
    if chyby:
        prehled += ["", "### Neodesláno", ""] + [f"- {c}" for c in chyby]
    s.shrnuti_do_summary("\n".join(prehled))

    if chyby:
        sys.exit(1)


if __name__ == "__main__":
    main()
