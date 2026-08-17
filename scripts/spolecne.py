# -*- coding: utf-8 -*-
"""
Sdílené funkce pro workflow skripty (rozeslat / sber / uzavrit / doplnit).

Zdroj pravdy:
  config.js          – jména a e-maily hlasujících (needituje se skriptem)
  data/kolo.json     – stav aktuálního kola (vytváří rozeslat.py, aktualizuje sber.py)
  data/kola/<id>/    – nasbírané odpovědi jednoho kola
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import smtplib
import ssl
import subprocess
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
DATA = KOREN / "data"
KOLO_JSON = DATA / "kolo.json"
CONFIG_JS = KOREN / "config.js"

TYPY = ["navrhy", "priority", "hlavni"]
NAZVY_TYPU = {
    "navrhy": "Témata – návrhy",
    "priority": "Témata – priority",
    "hlavni": "Hlavní část",
}


# --------------------------------------------------------------------------
# Čas
# --------------------------------------------------------------------------
def ted() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def lidsky(iso: str | None) -> str:
    if not iso:
        return "–"
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return d.strftime("%d.%m.%Y %H:%M UTC")
    except Exception:
        return iso


# --------------------------------------------------------------------------
# config.js – vytáhneme seznamy hlasujících bez spouštění JS
# --------------------------------------------------------------------------
def _pole_retezcu(zdroj: str, klic: str) -> list[str]:
    m = re.search(klic + r"\s*:\s*\[(.*?)\]", zdroj, re.S)
    if not m:
        raise SystemExit(f"config.js: nenalezen klíč {klic}")
    return [s for s in re.findall(r'"([^"]*)"|\'([^\']*)\'', m.group(1)) for s in s if s]


def hlasujici_z_configu() -> list[dict]:
    zdroj = CONFIG_JS.read_text(encoding="utf-8")
    jmena = _pole_retezcu(zdroj, "clenoveJmeno")
    maily = _pole_retezcu(zdroj, "clenoveMail")
    if len(jmena) != len(maily):
        raise SystemExit(
            f"config.js: clenoveJmeno ({len(jmena)}) a clenoveMail ({len(maily)}) "
            "mají různý počet položek."
        )
    if not jmena:
        raise SystemExit("config.js: seznam hlasujících je prázdný.")
    return [{"i": i, "jmeno": j, "email": m} for i, (j, m) in enumerate(zip(jmena, maily))]


# --------------------------------------------------------------------------
# Tokeny
# --------------------------------------------------------------------------
def hash_tokenu(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def index_z_tokenu(token: str) -> int | None:
    """Token má tvar '<index>.<náhodný řetězec>'."""
    m = re.match(r"^(\d+)\.[A-Za-z0-9_-]{16,}$", token or "")
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------
# Stav kola
# --------------------------------------------------------------------------
def nacti_kolo() -> dict | None:
    if not KOLO_JSON.exists():
        return None
    return json.loads(KOLO_JSON.read_text(encoding="utf-8"))


def uloz_kolo(kolo: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    KOLO_JSON.write_text(
        json.dumps(kolo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def slozka_kola(kolo: dict) -> Path:
    p = DATA / "kola" / kolo["id"]
    p.mkdir(parents=True, exist_ok=True)
    return p


# --------------------------------------------------------------------------
# Payload z e-mailu
#   ##OKF/1/<délka base64>##
#   <base64url bez paddingu, zalomený na řádky>
#   ##/OKF##
# --------------------------------------------------------------------------
ZACATEK = re.compile(r"##OKF/1/(\d+)##(.*?)##/OKF##", re.S)
POVOLENE = re.compile(r"[^A-Za-z0-9_-]")


class ChybnyPayload(Exception):
    pass


def najdi_payloady(text: str) -> list[dict]:
    """Vrátí všechny dekódované payloady z těla mailu. Chyby hlásí výjimkou."""
    out = []
    for m in ZACATEK.finditer(text or ""):
        ocekavana_delka = int(m.group(1))
        cisty = POVOLENE.sub("", m.group(2))
        if len(cisty) != ocekavana_delka:
            raise ChybnyPayload(
                f"kód lístku je poškozený nebo zkrácený "
                f"(očekáváno {ocekavana_delka} znaků, nalezeno {len(cisty)})"
            )
        try:
            syrove = base64.urlsafe_b64decode(cisty + "=" * (-len(cisty) % 4))
            data = json.loads(syrove.decode("utf-8"))
        except Exception as e:
            raise ChybnyPayload(f"kód lístku se nepodařilo přečíst ({e})")
        zkontroluj_payload(data)
        out.append(data)
    return out


def zkontroluj_payload(d: dict) -> None:
    if not isinstance(d, dict) or d.get("v") != 1:
        raise ChybnyPayload("neznámá verze kódu lístku")
    for klic in ("k", "f", "t", "p"):
        if klic not in d:
            raise ChybnyPayload(f"v kódu lístku chybí položka '{klic}'")
    if d["f"] not in TYPY:
        raise ChybnyPayload(f"neznámý typ formuláře '{d['f']}'")
    if not isinstance(d["p"], list) or not d["p"]:
        raise ChybnyPayload("kód lístku neobsahuje žádná data")


# --------------------------------------------------------------------------
# Čtení proměnných prostředí
#
# Pozor: workflow předává secrets vždy, i když neexistují – pak dorazí
# prázdný řetězec, na který se výchozí hodnota v os.environ.get() nechytí.
# Proto se všechny nepovinné hodnoty čtou přes tyhle dvě funkce.
# --------------------------------------------------------------------------
def text_z_prostredi(klic: str, vychozi: str) -> str:
    return (os.environ.get(klic) or "").strip() or vychozi


def cislo_z_prostredi(klic: str, vychozi: int) -> int:
    hodnota = (os.environ.get(klic) or "").strip()
    if not hodnota:
        return vychozi
    try:
        return int(hodnota)
    except ValueError:
        raise SystemExit(
            f"Secret {klic} musí být číslo, ale obsahuje {hodnota!r}. "
            f"Buď ho opravte, nebo smažte – pak se použije výchozí {vychozi}."
        )


# --------------------------------------------------------------------------
# Odesílání pošty
# --------------------------------------------------------------------------
def _smtp_nastaveni() -> dict:
    chybi = [k for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS") if not os.environ.get(k)]
    if chybi:
        raise SystemExit("Chybí secrets: " + ", ".join(chybi))
    return {
        "host": os.environ["SMTP_HOST"],
        "port": cislo_z_prostredi("SMTP_PORT", 587),
        "user": os.environ["SMTP_USER"],
        "pass": os.environ["SMTP_PASS"],
        "from": os.environ.get("MAIL_FROM") or os.environ["SMTP_USER"],
    }


def posli_mail(komu: str, predmet: str, telo: str, prilohy: list[tuple[str, bytes]] | None = None,
               odpoved_na: str | None = None) -> None:
    n = _smtp_nastaveni()
    zprava = EmailMessage()
    zprava["From"] = n["from"]
    zprava["To"] = komu
    zprava["Subject"] = predmet
    zprava["Auto-Submitted"] = "auto-generated"
    if odpoved_na:
        zprava["In-Reply-To"] = odpoved_na
        zprava["References"] = odpoved_na
    zprava.set_content(telo)
    for nazev, obsah in prilohy or []:
        if nazev.lower().endswith(".xlsx"):
            hlavni, pod = "application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            hlavni, pod = "text", "csv"
        zprava.add_attachment(obsah, maintype=hlavni, subtype=pod, filename=nazev)

    kontext = ssl.create_default_context()
    if n["port"] == 465:
        with smtplib.SMTP_SSL(n["host"], n["port"], context=kontext, timeout=45) as s:
            s.login(n["user"], n["pass"])
            s.send_message(zprava)
    else:
        with smtplib.SMTP(n["host"], n["port"], timeout=45) as s:
            s.ehlo()
            s.starttls(context=kontext)
            s.login(n["user"], n["pass"])
            s.send_message(zprava)


def admin_mail() -> str | None:
    return os.environ.get("ADMIN_EMAIL") or None


# --------------------------------------------------------------------------
# Git
# --------------------------------------------------------------------------
def commit(zprava: str, cesty: list[str]) -> bool:
    """Zapíše změny do repozitáře. Vrací True, pokud opravdu něco commitla."""
    subprocess.run(["git", "config", "user.name", "ok-form-bot"], cwd=KOREN, check=True)
    subprocess.run(
        ["git", "config", "user.email", "ok-form-bot@users.noreply.github.com"],
        cwd=KOREN, check=True,
    )
    subprocess.run(["git", "add", "--"] + _cesty_ok(cesty), cwd=KOREN, check=True)
    stav = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=KOREN
    )
    if stav.returncode == 0:
        print("Žádné změny ke commitu.")
        return False
    subprocess.run(["git", "commit", "-m", zprava], cwd=KOREN, check=True)
    for pokus in range(3):
        subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=KOREN, check=False)
        if subprocess.run(["git", "push"], cwd=KOREN).returncode == 0:
            return True
        print(f"push selhal, pokus {pokus + 1}/3")
    raise SystemExit("Nepodařilo se odeslat změny do repozitáře.")


def _cesty_ok(cesty: list[str]) -> list[str]:
    return [c for c in cesty if c]


def vypis(*a):
    print(*a, flush=True)


def shrnuti_do_summary(text: str) -> None:
    """Zapíše přehled do souhrnu běhu v GitHubu (záložka Actions)."""
    cesta = os.environ.get("GITHUB_STEP_SUMMARY")
    if cesta:
        with open(cesta, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    sys.stdout.write(text + "\n")
