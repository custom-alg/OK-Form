# -*- coding: utf-8 -*-
"""
Sběr odpovědí ze schránky.

Běží periodicky (cron) i na vyžádání. Postup pro každou nepřečtenou zprávu:
  1. přečti tělo, najdi kódový blok ##OKF/1/…##
  2. ověř token proti data/kolo.json (v repozitáři je jen jeho otisk)
  3. zapiš odpověď do data/kola/<id>/<typ>.json a přegeneruj <typ>.csv
  4. potvrď odesílateli, upozorni administrátora („X vyplnil Y“)
Co nelze přiřadit, skončí v data/kola/<id>/neprirazene/ k ručnímu doplnění.
"""
from __future__ import annotations

import csv
import email
import email.policy
import imaplib
import io
import json
import os
import re
from email.header import decode_header, make_header
from pathlib import Path

import spolecne as s

MAX_ZPRAV = 60


# --------------------------------------------------------------------------
# Ukládání odpovědí
# --------------------------------------------------------------------------
def oddelovac() -> str:
    zdroj = s.CONFIG_JS.read_text(encoding="utf-8")
    m = re.search(r"csvDelimiter\s*:\s*[\"']([^\"'])[\"']", zdroj)
    return m.group(1) if m else ";"


def nacti_zaznamy(slozka: Path, typ: str) -> list[dict]:
    f = slozka / f"{typ}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def uloz_zaznamy(slozka: Path, typ: str, zaznamy: list[dict]) -> None:
    zaznamy.sort(key=lambda z: z["i"])
    (slozka / f"{typ}.json").write_text(
        json.dumps(zaznamy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # CSV se vždy generuje znovu z JSON – je to odvozený soubor.
    sloupce: list[str] = []
    for z in zaznamy:
        for hlavicka, _ in z["pary"]:
            if hlavicka not in sloupce:
                sloupce.append(hlavicka)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=sloupce, delimiter=oddelovac(),
                       lineterminator="\r\n", extrasaction="ignore")
    w.writeheader()
    for z in zaznamy:
        w.writerow({h: v for h, v in z["pary"]})
    (slozka / f"{typ}.csv").write_text("\ufeff" + buf.getvalue(), encoding="utf-8")


def zapis_odpoved(kolo: dict, slozka: Path, hlasujici: dict, data: dict,
                  odesilatel: str) -> bool:
    """Vrací True, pokud šlo o přepis dřívější odpovědi."""
    typ = data["f"]
    zaznamy = nacti_zaznamy(slozka, typ)
    prepsano = any(z["i"] == hlasujici["i"] for z in zaznamy)
    zaznamy = [z for z in zaznamy if z["i"] != hlasujici["i"]]
    zaznamy.append({
        "i": hlasujici["i"],
        "jmeno": hlasujici["jmeno"],
        "prijato": s.ted(),
        "odesilatel": odesilatel,
        "pary": data["p"],
    })
    uloz_zaznamy(slozka, typ, zaznamy)
    hlasujici.setdefault("odevzdal", {})[typ] = s.ted()
    s.uloz_kolo(kolo)
    return prepsano


def zapis_log(slozka: Path, radek: str) -> None:
    with open(slozka / "log.md", "a", encoding="utf-8") as f:
        f.write(f"- {s.lidsky(s.ted())} – {radek}\n")


# --------------------------------------------------------------------------
# Práce s poštou
# --------------------------------------------------------------------------
def dekoduj(hodnota: str | None) -> str:
    if not hodnota:
        return ""
    try:
        return str(make_header(decode_header(hodnota)))
    except Exception:
        return hodnota


def telo_zpravy(zprava) -> str:
    casti = []
    for cast in zprava.walk():
        if cast.get_content_maintype() == "multipart":
            continue
        if cast.get_content_disposition() == "attachment":
            continue
        if cast.get_content_type() in ("text/plain", "text/html"):
            try:
                casti.append(cast.get_content())
            except Exception:
                syrove = cast.get_payload(decode=True) or b""
                casti.append(syrove.decode(cast.get_content_charset() or "utf-8", "replace"))
    text = "\n".join(casti)
    # HTML pošta: značky pryč, ať zbude čitelný text s kódovým blokem
    text = re.sub(r"<br\s*/?>|</p>|</div>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return (text.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">"))


def prilohy_csv(zprava) -> list[tuple[str, bytes]]:
    out = []
    for cast in zprava.walk():
        nazev = dekoduj(cast.get_filename())
        if nazev and nazev.lower().endswith((".csv", ".txt", ".okf")):
            out.append((nazev, cast.get_payload(decode=True) or b""))
    return out


def je_automat(zprava, vlastni: set[str], odesilatel: str) -> bool:
    if odesilatel.lower() in vlastni:
        return True
    auto = (zprava.get("Auto-Submitted") or "").lower()
    if auto and auto != "no":
        return True
    if zprava.get("X-Autoreply") or zprava.get("X-Autorespond"):
        return True
    if (zprava.get("Precedence") or "").lower() in ("bulk", "auto_reply", "list"):
        return True
    return False


def adresa(hlavicka: str | None) -> str:
    m = re.search(r"[\w.!#$%&'*+/=?^`{|}~-]+@[\w-]+(?:\.[\w-]+)+", hlavicka or "")
    return m.group(0) if m else ""


# --------------------------------------------------------------------------
# Texty odpovědí
# --------------------------------------------------------------------------
def potvrzeni(jmeno: str, typ: str, kolo: dict, prepsano: bool) -> str:
    hotove = [t for t in kolo["formulare"]
              if next((h for h in kolo["hlasujici"] if h["jmeno"] == jmeno), {}).get("odevzdal", {}).get(t)]
    zbyva = [s.NAZVY_TYPU[t] for t in kolo["formulare"] if t not in hotove]
    radky = [
        f"Dobrý den,",
        "",
        ("přijali jsme Vaši opravenou odpověď" if prepsano else "přijali jsme Vaši odpověď")
        + f" – {s.NAZVY_TYPU[typ]} ({len(hotove)}/{len(kolo['formulare'])}).",
    ]
    if zbyva:
        radky += ["", "Ještě zbývá vyplnit: " + ", ".join(zbyva) + ".",
                  "Odkazy najdete v původní pozvánce."]
    else:
        radky += ["", "Máte hotovo, děkujeme."]
    return "\n".join(radky)


def vada(jmeno: str, duvod: str) -> str:
    return "\n".join([
        "Dobrý den,",
        "",
        f"Vaši odpověď se nepodařilo automaticky zpracovat: {duvod}.",
        "",
        "Zkuste prosím ve formuláři znovu kliknout na „Odeslat e-mailem“ a zprávu",
        "odeslat beze změn – kódový blok na konci nesmí být upravený ani zkrácený.",
        "Pokud to nepomůže, přepošlete prosím stažený soubor CSV; doplníme ho ručně.",
    ])


# --------------------------------------------------------------------------
# Hlavní běh
# --------------------------------------------------------------------------
def main() -> None:
    kolo = s.nacti_kolo()
    if not kolo:
        s.shrnuti_do_summary("Žádné kolo není založené – není co sbírat.")
        return

    vlastni = {a.lower() for a in (
        os.environ.get("SMTP_USER", ""), os.environ.get("MAIL_FROM", ""),
        os.environ.get("IMAP_USER", "")) if a}
    znami = {c["email"].lower(): c for c in s.hlasujici_z_configu()}

    hostitel = os.environ.get("IMAP_HOST")
    if not hostitel:
        raise SystemExit("Chybí secret IMAP_HOST.")
    M = imaplib.IMAP4_SSL(hostitel, int(os.environ.get("IMAP_PORT", "993")))
    M.login(os.environ["IMAP_USER"], os.environ["IMAP_PASS"])
    M.select(os.environ.get("IMAP_FOLDER", "INBOX"))

    typ_hledani, cisla = M.search(None, "UNSEEN")
    ids = cisla[0].split()[:MAX_ZPRAV] if typ_hledani == "OK" and cisla[0] else []
    s.vypis(f"Nepřečtených zpráv ke zpracování: {len(ids)}")

    slozka = s.slozka_kola(kolo)
    prijato, odmitnuto, preskoceno = [], [], 0
    neprirazene = slozka / "neprirazene"

    for cislo in ids:
        typ_fetch, data = M.fetch(cislo, "(RFC822)")
        if typ_fetch != "OK" or not data or not isinstance(data[0], tuple):
            continue
        zprava = email.message_from_bytes(data[0][1], policy=email.policy.default)
        odesilatel = adresa(zprava.get("From"))
        predmet = dekoduj(zprava.get("Subject"))
        msgid = zprava.get("Message-ID")

        M.store(cislo, "+FLAGS", "\\Seen")  # zpracované už nechceme znovu

        if je_automat(zprava, vlastni, odesilatel):
            preskoceno += 1
            continue

        text = telo_zpravy(zprava)
        znamy = znami.get(odesilatel.lower())

        try:
            payloady = s.najdi_payloady(text)
        except s.ChybnyPayload as e:
            s.vypis(f"  ✗ {odesilatel}: {e}")
            if znamy:
                s.posli_mail(odesilatel, f"Re: {predmet}", vada(znamy["jmeno"], str(e)),
                             odpoved_na=msgid)
            odmitnuto.append(f"{odesilatel} – {e}")
            uloz_neprirazenou(neprirazene, zprava, odesilatel, predmet, str(e))
            continue

        if not payloady:
            if znamy or prilohy_csv(zprava):
                s.vypis(f"  ? {odesilatel}: zpráva bez kódu lístku")
                odmitnuto.append(f"{odesilatel} – zpráva neobsahuje kód lístku")
                uloz_neprirazenou(neprirazene, zprava, odesilatel, predmet,
                                  "chybí kódový blok")
                if znamy:
                    s.posli_mail(odesilatel, f"Re: {predmet}",
                                 vada(znamy["jmeno"], "zpráva neobsahovala kód lístku"),
                                 odpoved_na=msgid)
            else:
                preskoceno += 1
            continue

        for payload in payloady:
            zpracuj(kolo, slozka, payload, odesilatel, predmet, msgid,
                    prijato, odmitnuto, neprirazene, zprava)

    M.close()
    M.logout()

    zmeny = bool(prijato or odmitnuto)
    if prijato:
        try:
            import vystup
            vystup.sestav(s.nacti_kolo(), slozka)
        except Exception as e:
            s.vypis(f"Sešit se nepodařilo sestavit: {e}")
    if zmeny:
        s.commit(
            f"Sběr {kolo['id']}: {len(prijato)} přijato"
            + (f", {len(odmitnuto)} k ručnímu doplnění" if odmitnuto else ""),
            ["data"],
        )
        oznam_adminovi(kolo, prijato, odmitnuto)

    prehled = [f"## Sběr kola `{kolo['id']}`", "",
               f"- Zpracováno zpráv: {len(ids)} (přeskočeno automatických: {preskoceno})",
               f"- Přijato odpovědí: {len(prijato)}"]
    for p in prijato:
        prehled.append(f"  - {p}")
    if odmitnuto:
        prehled += ["", "### K ručnímu doplnění", ""] + [f"- {o}" for o in odmitnuto]
    prehled += ["", stav_tabulka(kolo)]
    s.shrnuti_do_summary("\n".join(prehled))


def zpracuj(kolo, slozka, payload, odesilatel, predmet, msgid,
            prijato, odmitnuto, neprirazene, zprava) -> None:
    if kolo.get("stav") != "otevreno":
        s.posli_mail(odesilatel, f"Re: {predmet}",
                     vada("", "sběr odpovědí už byl uzavřen"), odpoved_na=msgid)
        odmitnuto.append(f"{odesilatel} – kolo je uzavřené")
        uloz_neprirazenou(neprirazene, zprava, odesilatel, predmet, "kolo uzavřeno")
        return

    if payload["k"] != kolo["id"]:
        odmitnuto.append(f"{odesilatel} – lístek z jiného kola ({payload['k']})")
        uloz_neprirazenou(neprirazene, zprava, odesilatel, predmet,
                          f"lístek z kola {payload['k']}")
        return

    idx = s.index_z_tokenu(payload["t"])
    hlasujici = next((h for h in kolo["hlasujici"] if h["i"] == idx), None)
    if hlasujici is None or s.hash_tokenu(payload["t"]) != hlasujici["token_hash"]:
        s.vypis(f"  ✗ {odesilatel}: neplatný token")
        odmitnuto.append(f"{odesilatel} – neplatný token")
        uloz_neprirazenou(neprirazene, zprava, odesilatel, predmet, "neplatný token")
        return

    if payload["f"] not in kolo["formulare"]:
        odmitnuto.append(f"{hlasujici['jmeno']} – formulář {payload['f']} není v tomto kole")
        return

    prepsano = zapis_odpoved(kolo, slozka, hlasujici, payload, odesilatel)
    popis = f"{hlasujici['jmeno']} vyplnil {s.NAZVY_TYPU[payload['f']]}"
    if prepsano:
        popis += " (oprava dřívější odpovědi)"
    zapis_log(slozka, popis)
    prijato.append(popis)
    s.vypis(f"  ✓ {popis}")
    s.posli_mail(odesilatel, f"Re: {predmet}",
                 potvrzeni(hlasujici["jmeno"], payload["f"], kolo, prepsano),
                 odpoved_na=msgid)


def uloz_neprirazenou(slozka: Path, zprava, odesilatel: str, predmet: str,
                      duvod: str) -> None:
    slozka.mkdir(parents=True, exist_ok=True)
    znacka = re.sub(r"[^A-Za-z0-9]+", "-", f"{s.ted()}-{odesilatel}")[:80]
    (slozka / f"{znacka}.txt").write_text(
        f"Od: {odesilatel}\nPředmět: {predmet}\nDůvod: {duvod}\n"
        f"Přijato: {s.ted()}\n\n{'-' * 60}\n{telo_zpravy(zprava)}\n",
        encoding="utf-8",
    )
    for nazev, obsah in prilohy_csv(zprava):
        (slozka / f"{znacka}--{re.sub(r'[^A-Za-z0-9._-]+', '_', nazev)}").write_bytes(obsah)


def stav_tabulka(kolo: dict) -> str:
    hlavicka = "| Hlasující | " + " | ".join(s.NAZVY_TYPU[t] for t in kolo["formulare"]) + " |"
    delici = "| --- | " + " | ".join("---" for _ in kolo["formulare"]) + " |"
    radky = [hlavicka, delici]
    for h in kolo["hlasujici"]:
        bunky = ["✓" if h.get("odevzdal", {}).get(t) else "–" for t in kolo["formulare"]]
        radky.append(f"| {h['jmeno']} | " + " | ".join(bunky) + " |")
    return "\n".join(radky)


def oznam_adminovi(kolo: dict, prijato: list[str], odmitnuto: list[str]) -> None:
    komu = s.admin_mail()
    if not komu:
        return
    celkem = sum(1 for h in kolo["hlasujici"] for t in kolo["formulare"]
                 if h.get("odevzdal", {}).get(t))
    ocekavano = len(kolo["hlasujici"]) * len(kolo["formulare"])
    radky = [f"Kolo {kolo['id']} – {kolo['nazev']}", "",
             f"Hotovo {celkem} z {ocekavano} lístků.", ""]
    if prijato:
        radky += ["Nově přijato:"] + [f"  • {p}" for p in prijato] + [""]
    if odmitnuto:
        radky += ["Vyžaduje ruční doplnění:"] + [f"  • {o}" for o in odmitnuto] + [""]
    radky += [stav_tabulka(kolo).replace("|", " ")]
    try:
        s.posli_mail(komu, f"[{kolo['id']}] {celkem}/{ocekavano} lístků", "\n".join(radky))
    except Exception as e:
        s.vypis(f"Upozornění administrátorovi se nepodařilo odeslat: {e}")


if __name__ == "__main__":
    main()
