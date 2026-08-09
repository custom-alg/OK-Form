# -*- coding: utf-8 -*-
"""
Ruční doplnění odpovědi, kterou sběrač nezpracoval.

Dva režimy (podle toho, co administrátor vloží):
  A) KOD  – vložený text e-mailu nebo samotný kódový blok ##OKF/1/…##
  B) CSV  – obsah staženého souboru CSV + volba hlasujícího a formuláře

Zapisuje přesně stejnou cestou jako automatický sběr, takže výsledek
je nerozeznatelný – jen se v záznamu poznamená, že šlo o ruční vstup.
"""
from __future__ import annotations

import csv
import io
import os

import spolecne as s
from sber import nacti_zaznamy, uloz_zaznamy, zapis_log


def z_csv(text: str) -> list[list[str]]:
    text = text.lstrip("\ufeff")
    try:
        dialekt = csv.Sniffer().sniff(text.splitlines()[0], delimiters=";,\t")
        oddelovac = dialekt.delimiter
    except Exception:
        oddelovac = ";" if text.count(";") >= text.count(",") else ","
    radky = list(csv.reader(io.StringIO(text), delimiter=oddelovac))
    radky = [r for r in radky if any(b.strip() for b in r)]
    if len(radky) < 2:
        raise SystemExit("CSV musí mít řádek hlaviček a alespoň jeden řádek odpovědi.")
    hlavicky, hodnoty = radky[0], radky[1]
    return [[h, hodnoty[i] if i < len(hodnoty) else ""] for i, h in enumerate(hlavicky)]


def main() -> None:
    kolo = s.nacti_kolo()
    if not kolo:
        raise SystemExit("Žádné kolo neexistuje.")

    kod = (os.environ.get("KOD") or "").strip()
    csv_text = (os.environ.get("CSV") or "").strip()
    volba = (os.environ.get("HLASUJICI") or "").strip()
    formular = (os.environ.get("FORMULAR") or "").strip()

    hlasujici = None
    if volba:
        hlasujici = next((h for h in kolo["hlasujici"]
                          if h["jmeno"] == volba or str(h["i"]) == volba), None)
        if hlasujici is None:
            raise SystemExit(f"Hlasující „{volba}“ v tomto kole není.")

    if kod:
        payloady = s.najdi_payloady(kod)
        if not payloady:
            raise SystemExit("Ve vloženém textu není kódový blok ##OKF/1/…##.")
        data = payloady[0]
        formular = data["f"]
        pary = data["p"]
        if hlasujici is None:
            idx = s.index_z_tokenu(data["t"])
            hlasujici = next((h for h in kolo["hlasujici"] if h["i"] == idx), None)
            if hlasujici is None or s.hash_tokenu(data["t"]) != hlasujici["token_hash"]:
                raise SystemExit(
                    "Token ve vloženém kódu nesedí. Vyberte hlasujícího ručně."
                )
    elif csv_text:
        if not hlasujici or formular not in s.TYPY:
            raise SystemExit("U vloženého CSV je nutné vybrat hlasujícího i formulář.")
        pary = z_csv(csv_text)
    else:
        raise SystemExit("Vložte buď kód lístku, nebo obsah CSV.")

    slozka = s.slozka_kola(kolo)
    zaznamy = [z for z in nacti_zaznamy(slozka, formular) if z["i"] != hlasujici["i"]]
    zaznamy.append({
        "i": hlasujici["i"],
        "jmeno": hlasujici["jmeno"],
        "prijato": s.ted(),
        "odesilatel": "ručně doplněno administrátorem",
        "pary": pary,
    })
    uloz_zaznamy(slozka, formular, zaznamy)
    hlasujici.setdefault("odevzdal", {})[formular] = s.ted()
    s.uloz_kolo(kolo)

    popis = f"{hlasujici['jmeno']} – {s.NAZVY_TYPU[formular]} doplněno ručně"
    zapis_log(slozka, popis)
    s.commit(f"Ruční doplnění: {popis}", ["data"])
    s.shrnuti_do_summary(f"## Doplněno\n\n- {popis}")


if __name__ == "__main__":
    main()
