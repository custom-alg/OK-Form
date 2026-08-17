# Nasazení a provoz (referenční přehled)

> Tři dokumenty a k čemu jsou:
> **PRUVODCE-GITHUB.md** — první nastavení krok za krokem.
> **PRIRUCKA-SPRAVCE.md** — provoz, všechny volby, řešení potíží.
> **NASAZENI.md** (tento) — stručný technický přehled.

> Jdete-li na to poprvé (nebo po delší pauze), začněte souborem
> **PRUVODCE-GITHUB.md** — je to naklikaný postup krok za krokem.
> Tenhle soubor je referenční popis, ne návod.

Statický frontend na GitHub Pages. Žádný server, žádná databáze.
Sběr do sdílené složky v **Nextcloudu** přes jeho desktop klienta.

**Lístky se sbírají do sdílené složky.** Hlasující si jednou vybere složku
synchronizovanou Nextcloudem (nebo čímkoli jiným — aplikaci je to jedno,
vidí obyčejný adresář na disku) a odevzdané lístky
se do ní zapisují samy. Administrace pak tutéž složku otevře, lístky sloučí
a vyexportuje souhrnné CSV.

Zápis do složky umí **Chrome a Edge na počítači**, ne Firefox, Safari ani
telefon. Kdo takový prohlížeč nemá, lístek se mu stáhne a uloží ho do složky
ručně — nebo použije záložní cestu e-mailem (oddíl 2).

---

## 0. Rychlý start s Nextcloudem

Pokud vystačíte se sdílenou složkou, přeskočte oddíl 2 a nic nenastavujte:

1. V Nextcloudu založte složku a nasdílejte ji všem pěti hlasujícím.
   Každý ať má nainstalovaného **Nextcloud desktop klienta** a složku
   synchronizovanou do počítače — aplikace pak pracuje s obyčejným adresářem
   na disku a o Nextcloudu vůbec neví.
2. Rozešlete odkaz na aplikaci (stačí obyčejný e-mail všem).
3. Každý si na rozcestníku klikne na **Vybrat složku** a ukáže na ni. Jednou.
4. Od té chvíle tlačítko říká *Odevzdat lístek do složky* a soubor tam rovnou
   spadne. Jméno souboru je stálé, takže opravený lístek přepíše původní.
5. Vy v `admin.html` otevřete tutéž složku, dáte **Načíst znovu** a vidíte
   tabulku, kdo odevzdal. Souhrnné CSV si stáhnete, nebo uložíte zpět do složky.

Kroky 1–3 v repozitáři nic nenastavují a nepotřebují token ani IT.

### Záložní odkaz pro ostatní prohlížeče

Na téže složce vytvořte v Nextcloudu **sdílený odkaz** s právem nahrávat
(volba *File drop* nahraje bez zobrazení obsahu, *Allow upload and editing*
ukáže i vložené lístky) a vložte ho v `config.js` do `nextcloudOdkaz`.
Komu prohlížeč zápis do složky neumožní, tomu se lístek stáhne a tlačítkem
**Nahrát do Nextcloudu** otevře přesně tuhle stránku, kam soubor přetáhne.
Pošta pak není potřeba vůbec. Necháte-li klíč prázdný, tlačítko se skryje.

### Proč se nezapisuje do Nextcloudu přímo

Nabízelo by se posílat lístek rovnou na WebDAV a nepotřebovat sync klienta.
Nejde to: Nextcloud k WebDAV neposílá CORS hlavičky, takže prohlížeč požadavek
z cizí domény zablokuje. Řeší to serverová aplikace **WebAppPassword**, kterou
správce Nextcloudu nainstaluje a povolí v ní doménu s aplikací. Kdyby k tomu
někdy došlo, dá se zápis přes WebDAV doplnit a odpadne omezení na Chrome
i nutnost synchronizace — je to jediná věc, kterou by stálo za to po IT chtít.

> **Rozmyslete si viditelnost.** Ve složce, kam mají přístup všichni, uvidí
> každý lístky ostatních a může je přepsat nebo smazat. Pokud má být hlasování
> navzájem neveřejné, nasdílejte každému vlastní podsložku, nebo zůstaňte
> u pošty.

---

## 1. Co kam nakopírovat

Do kořene existujícího repozitáře:

```
index.html              ← nahradit (přibyla práce s tokenem a kódem lístku)
admin.html              ← nové, ovládací panel
scripts/                ← nové, čtyři skripty v Pythonu
.github/workflows/      ← nové, čtyři úlohy
data/                   ← vznikne samo při prvním rozeslání
```

`config.js`, `support.js`, `_ds/` a `assets/` zůstávají beze změny.
`config.js` je i nadále jediné místo, kde se mění hlasující, témata a pool.

---

## 2. Poštovní schránka

Při sběru přes GitHub Actions (`sberRezim: "email"` v `config.js`) je povinná. Vynechat ji jde jen v režimu `"slozka"` podle oddílu 0.

Použijte **vlastní schránku**, ne osobní. Skripty do ní sahají přes IMAP
a označují zprávy jako přečtené.

Nastavte v repozitáři **Settings → Secrets and variables → Actions**:

| Secret | Příklad | Poznámka |
| --- | --- | --- |
| `IMAP_HOST` | `imap.gmail.com` | |
| `IMAP_PORT` | `993` | nepovinné, výchozí 993 |
| `IMAP_USER` | `hlasovani@…` | |
| `IMAP_PASS` | heslo aplikace | ne běžné heslo |
| `SMTP_HOST` | `smtp.gmail.com` | |
| `SMTP_PORT` | `587` | 465 = SSL, jinak STARTTLS |
| `SMTP_USER` / `SMTP_PASS` | | zpravidla stejné jako IMAP |
| `MAIL_FROM` | `hlasovani@moneco.cz` | nepovinné, jinak `SMTP_USER` |
| `ADMIN_EMAIL` | váš e-mail | sem chodí „X vyplnil Y“ a výsledky |

A ve stejném okně v záložce **Variables**:

| Variable | Hodnota |
| --- | --- |
| `PAGES_URL` | `https://<vlastník>.github.io/<repo>` — bez lomítka na konci |
| `IMAP_FOLDER` | nepovinné, výchozí `INBOX` |

> **Pozor na Microsoft 365.** Přihlášení jménem a heslem k IMAP je tam vypnuté;
> heslo aplikace neexistuje. Buď použijte schránku u poskytovatele, který
> běžné IMAP přihlášení umí (Gmail s heslem aplikace, Seznam, vlastní server),
> nebo počítejte s přepsáním `sber.py` na Microsoft Graph s registrací aplikace
> v Entra ID. To je práce navíc zhruba na půl dne.

K **Settings → Actions → General → Workflow permissions**: pokud jde přepnout
na *Read and write permissions*, přepněte. Pokud je volba zašedlá kvůli politice
organizace, nevadí — úlohy si oprávnění vyžádají klíčem `permissions` samy.
Kdyby přesto zápis selhal (`403: Resource not accessible by integration`),
založte secret `GH_PAT` s fine-grained tokenem, který má na tento repozitář
*Contents: Read and write*; úlohy ho použijí automaticky.

---

## 3. Token pro administraci

`admin.html` mluví s GitHubem přímo z prohlížeče, potřebuje tedy token.
Vytvořte **fine-grained personal access token** omezený na tento jediný
repozitář, s oprávněními:

- **Contents** → Read and write (zápis obrázků a dat)
- **Actions** → Read and write (spouštění úloh)

Token se ukládá do `localStorage` vašeho prohlížeče. Na cizím počítači po
práci klikněte na *Odhlásit a smazat token*. Kdokoli může `admin.html`
otevřít, ale bez tokenu z ní nic neudělá.

---

## 4. Jak kolo probíhá

1. **Podklady** — v administraci nahrajete čtyři obrázky. Stránka počká, až se
   soubor opravdu objeví na publikované adrese, a teprve pak napíše
   *publikováno*. Nespoléhejte na náhled, spoléhejte na tu hlášku.
2. **OK** — vyplníte název a termín, zvolíte formuláře, stisknete tlačítko.
   Každý hlasující dostane e-mail s odkazy tvaru `…/?t=3.xY7…#/hlavni-cast`.
   Token je v odkazu; v repozitáři je uložený jen jeho otisk (SHA-256), takže
   z veřejných dat se odkaz zpětně sestavit nedá.
3. **Sběr** — úloha běží každých 10 minut a po stisku *Zkontrolovat schránku
   teď*. Přečte nepřečtené zprávy, najde v nich kódový blok, ověří token,
   zapíše řádek do CSV, odesílateli potvrdí přijetí a vám pošle „X vyplnil Y“.
   Tabulka v administraci se sama obnovuje.
4. **Uzávěrka** — kolo se zamkne, vznikne `souhrn.md` a výsledná CSV vám
   přijdou e-mailem. Kdo pošle lístek později, dostane zprávu, že už je zavřeno.

Kdykoli mezitím si můžete stáhnout průběžné CSV.

---

## 5. Kde to má hrany

**Zpoždění synchronizace.** Mezi zápisem lístku a tím, než ho uvidíte ve své
kopii složky, stojí sync klient cloudu — obvykle sekundy, při větším souboru
i minuta. Když někdo tvrdí, že odevzdal, a vy ho nevidíte, dejte *Načíst znovu*
až po doběhnutí synchronizace.

**Podpora prohlížečů.** Zápis do složky je postavený na File System Access API,
které mají jen prohlížeče postavené na Chromiu, a to na počítači. Aplikace to
sama pozná a takovému uživateli nabídne stažení souboru; administrace v jiném
prohlížeči složku vůbec neotevře.

**Zpoždění pošty.** Cron v GitHub Actions není přesný; při zátěži se běh odkládá
i o dvacet minut. Týká se to jen záložní cesty e-mailem.

**Délka zprávy.** Kód lístku u hlavní části vychází na zhruba 1,8 kB.
Starší Outlook zvládne odkaz `mailto:` do ~2 kB, takže je rezerva asi na tři
další řádky v `sekceHlavni`. Kdyby se formulář rozrostl, klienti začnou
zprávu ořezávat — sběrač to pozná podle délky a napíše hlasujícímu, ať
použije tlačítko *Zkopírovat kód* na stránce „Lístek odevzdán“. Ta cesta
funguje vždy.

**Ruční doplnění.** Co se nepovede přiřadit, skončí v
`data/kola/<kolo>/neprirazene/` a administrace to vypíše i s odkazy.
V kroku 4 vložíte text e-mailu (kód se v něm najde sám) nebo obsah CSV
s výběrem hlasujícího — zápis pak proběhne stejnou cestou jako automatický.

**Veřejnost dat.** Ve veřejném repozitáři jsou veřejné i podklady a výsledky,
včetně jmen a e-mailů v `config.js`. Pokud to nevyhovuje, jsou dvě cesty:
repozitář zesoukromit (Pages ze soukromého repozitáře vyžaduje placený plán),
nebo nechat veřejný jen web a data zapisovat do druhého, soukromého
repozitáře — pak `scripts/` a workflow přesuňte tam a doplňte token pro zápis.

**Auditní záznam.** Historie commitů ukazuje, kdy co přibylo, ale bot má
právo zapisovat, takže to není důkaz proti úpravě. Pokud výsledky někdy budou
muset něco doložit, tohle řešení na to nestačí.

---

## 6. Když se něco pokazí

| Příznak | Kde hledat |
| --- | --- |
| Úloha spadne hned | chybí secret, nebo `Workflow permissions` nejsou na *Read and write* |
| Pozvánky neodešly | souhrn běhu vypíše konkrétní adresy a chybu SMTP |
| Odpověď nedorazila do CSV | souhrn běhu *2 · Sběr odpovědí* — vypisuje každou zprávu i důvod odmítnutí |
| „neplatný token“ | hlasující použil odkaz ze starší pozvánky; rozesláním vzniknou nové tokeny a staré přestanou platit |
| Obrázek se nezmění | tvrdé obnovení stránky; administrace přidává k adrese `?cb=…`, prohlížeč s otevřenou stránkou ale může držet starou verzi |

Souhrn každého běhu najdete v záložce **Actions** → konkrétní běh → *Summary*.
Je psaný česky a obsahuje tabulku, kdo co odevzdal.
