# -*- coding: utf-8 -*-
"""
Ukončí sběr: uzamkne kolo, vyrobí souhrn a pošle výsledky administrátorovi.
Po uzavření sběrač nové odpovědi nepřijímá a odesílateli to napíše.
"""
from __future__ import annotations

import os

import spolecne as s


def main() -> None:
    kolo = s.nacti_kolo()
    if not kolo:
        raise SystemExit("Žádné kolo neexistuje.")
    if kolo.get("stav") != "otevreno" and os.environ.get("ZNOVU") != "true":
        raise SystemExit(f"Kolo {kolo['id']} už je uzavřené ({s.lidsky(kolo.get('uzavreno'))}).")

    kolo["stav"] = "uzavreno"
    kolo["uzavreno"] = s.ted()
    s.uloz_kolo(kolo)

    slozka = s.slozka_kola(kolo)
    chybejici = []
    for h in kolo["hlasujici"]:
        prazdne = [s.NAZVY_TYPU[t] for t in kolo["formulare"]
                   if not h.get("odevzdal", {}).get(t)]
        if prazdne:
            chybejici.append(f"{h['jmeno']}: {', '.join(prazdne)}")

    neprirazene = sorted((slozka / "neprirazene").glob("*.txt")) \
        if (slozka / "neprirazene").exists() else []

    radky = [
        f"# Souhrn kola {kolo['id']} – {kolo['nazev']}",
        "",
        f"- Otevřeno: {s.lidsky(kolo['otevreno'])}",
        f"- Uzavřeno: {s.lidsky(kolo['uzavreno'])}",
        f"- Hlasujících: {len(kolo['hlasujici'])}",
        f"- Formuláře: {', '.join(s.NAZVY_TYPU[t] for t in kolo['formulare'])}",
        "",
        "## Odevzdání",
        "",
    ]
    hlavicka = "| Hlasující | " + " | ".join(s.NAZVY_TYPU[t] for t in kolo["formulare"]) + " |"
    radky += [hlavicka, "| --- | " + " | ".join("---" for _ in kolo["formulare"]) + " |"]
    for h in kolo["hlasujici"]:
        bunky = ["✓" if h.get("odevzdal", {}).get(t) else "chybí" for t in kolo["formulare"]]
        radky.append(f"| {h['jmeno']} | " + " | ".join(bunky) + " |")

    if chybejici:
        radky += ["", "## Nevyplněno", ""] + [f"- {c}" for c in chybejici]
    if neprirazene:
        radky += ["", "## Nezpracované zprávy k ručnímu doplnění", ""]
        radky += [f"- `data/kola/{kolo['id']}/neprirazene/{p.name}`" for p in neprirazene]

    (slozka / "souhrn.md").write_text("\n".join(radky) + "\n", encoding="utf-8")
    with open(slozka / "log.md", "a", encoding="utf-8") as f:
        f.write(f"- {s.lidsky(kolo['uzavreno'])} – sběr uzavřen\n")

    s.commit(f"Uzavřeno kolo {kolo['id']}", ["data"])

    try:
        import vystup
        sesit = vystup.sestav(kolo, slozka)
    except Exception as e:
        sesit = None
        s.vypis(f"Sešit se nepodařilo sestavit: {e}")

    prijemci = []
    if s.admin_mail():
        prijemci.append(s.admin_mail())
    if os.environ.get("VSEM") == "true":
        prijemci += [c["email"] for c in s.hlasujici_z_configu()
                     if c["email"] != s.admin_mail()]

    for komu in prijemci:
        prilohy = []
        if sesit and sesit.exists():
            prilohy.append((f"{kolo['id']}-vysledky.xlsx", sesit.read_bytes()))
        for t in kolo["formulare"]:
            soubor = slozka / f"{t}.csv"
            if soubor.exists():
                prilohy.append((f"{kolo['id']}-{t}.csv", soubor.read_bytes()))
        telo = ["Dobrý den,", "", f"sběr kola {kolo['id']} ({kolo['nazev']}) je uzavřen.",
                "V příloze je sešit vysledky.xlsx – list Přehled ukazuje, kdo odevzdal,",
                "další listy obsahují lístky po formulářích. CSV přikládáme také.", ""]
        if chybejici:
            telo += ["Nevyplnili:"] + [f"  • {c}" for c in chybejici] + [""]
        if neprirazene:
            telo += [f"Pozor: {len(neprirazene)} zpráv se nepodařilo automaticky "
                     "zpracovat, doplňte je prosím ručně v administraci.", ""]
        try:
            s.posli_mail(komu, f"[{kolo['id']}] Výsledky hlasování", "\n".join(telo), prilohy)
            s.vypis(f"Výsledky odeslány: {komu}")
        except Exception as e:
            s.vypis(f"Výsledky se nepodařilo odeslat na {komu}: {e}")

    s.shrnuti_do_summary("\n".join(radky))


if __name__ == "__main__":
    main()
