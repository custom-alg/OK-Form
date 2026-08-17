# Průvodce: rozjet to na GitHubu

Postup prvního nastavení. Průběžný provoz a popis všech voleb je
v **PRIRUCKA-SPRAVCE.md**.

Psáno pro člověka, který GitHub zná, ale Actions dlouho neviděl. Nic
z toho nevyžaduje příkazovou řádku — všechno se dá naklikat v prohlížeči.

Počítejte s hodinou a půl, z toho většina padne na založení schránky.

---

## Co jsou GitHub Actions, v pěti větách

Actions je plánovač úloh, který GitHub nabízí ke každému repozitáři.
Úloha je textový soubor v `.github/workflows/`; GitHub ho sám najde a nabídne.
Každá úloha si při spuštění půjčí čistý virtuální počítač s Linuxem, stáhne
do něj obsah repozitáře, provede kroky, které jsou v souboru napsané, a stroj
zahodí. Spouštět se dá ručně tlačítkem, podle času, nebo při změně v repozitáři.
U veřejného repozitáře je to zdarma bez omezení.

V našem případě jsou úlohy čtyři a dělají tohle:

| Soubor | Kdy běží | Co dělá |
| --- | --- | --- |
| `rozeslat.yml` | tlačítkem | vygeneruje tokeny a rozešle pozvánky |
| `sber.yml` | každých 10 minut + tlačítkem | přečte schránku, zapíše lístky, přepíše sešit |
| `uzavrit.yml` | tlačítkem | uzamkne kolo a rozešle výsledky |
| `doplnit.yml` | tlačítkem | zapíše lístek, který se nepodařilo přečíst |

Tlačítka na ně jsou v `admin.html`, takže do Actions nemusíte chodit vůbec —
hodí se ale, když chcete vidět, co se stalo.

---

## 1. Nahrát soubory

Rozbalte balíček do kořene repozitáře a nahrajte. Přes web: **Add file →
Upload files**, přetáhnout, dole **Commit changes**. Adresář `.github`
web GitHubu při přetažení někdy zahodí, protože začíná tečkou — pokud se
workflow v záložce Actions neobjeví, založte ty čtyři soubory ručně přes
**Add file → Create new file** a do jména napište celou cestu
`.github/workflows/rozeslat.yml`; GitHub složky vytvoří sám.

Zkontrolujte, že v repozitáři jsou:

```
index.html  admin.html  config.js  support.js  _ds/  assets/
scripts/    .github/workflows/
```

---

## 2. Oprávnění k zápisu — nejspíš nic nedělejte

**Settings → Actions → General → Workflow permissions.**

Pokud jde přepnout na **Read and write permissions**, přepněte a uložte.
Pokud je volba zašedlá, drží ji nastavení organizace nebo enterprise —
co je omezené na vyšší úrovni, nejde povolit na nižší.

**Zašedlá volba nevadí.** Určuje jen výchozí oprávnění pro úlohy, které si
o žádné neřeknou. Všechny čtyři naše úlohy mají hned v hlavičce
`permissions: contents: write`, takže si zápis vyžádají samy. Pokračujte
dál a nic neřešte.

### Kdyby to přece jen selhalo

Pozná se to podle hlášky `403: Resource not accessible by integration`
nebo odmítnutého `git push` na konci běhu. Pak si obstarejte zápis
vlastním tokenem:

1. Vytvořte fine-grained token stejně jako v kroku 6, s právem
   **Contents: Read and write** na tento repozitář.
2. **Settings → Secrets and variables → Actions → New repository secret**,
   jméno `GH_PAT`, hodnota token.

Víc není potřeba — úlohy si ho vezmou samy, protože mají nastaveno
`token: ${{ secrets.GH_PAT || github.token }}`. Když secret neexistuje,
použijí běžný token; když existuje, zapisují pod ním.

---

## 3. Zapnout Pages

**Settings → Pages**. V *Source* zvolte **Deploy from a branch**, větev
`main`, složka `/ (root)`, **Save**. Za minutu se nahoře objeví adresa
tvaru `https://<vlastník>.github.io/<repo>`. Tu si poznamenejte, budete ji
potřebovat dvakrát.

Ještě založte v kořeni prázdný soubor `.nojekyll` (Add file → Create new
file, jméno `.nojekyll`, nic nepsat, commit). Bez něj GitHub ignoruje
složky začínající podtržítkem a nenačte se vám `_ds/` se styly.

---

## 4. Schránka pro sběr

Založte **novou schránku** jen pro tohle, ne osobní — úloha do ní sahá
a označuje zprávy jako přečtené.

Nejrychlejší je Gmail. Potřebujete z něj takzvané **heslo aplikace** —
šestnáctimístný kód, který se používá místo hesla k účtu. Běžné heslo
Google skriptům nepustí, proto to bez tohohle kroku nepůjde.

**a) Založte účet.** Na `gmail.com` vytvořte nový účet, například
`hlasovani.moneco@gmail.com`. Nepoužívejte svůj osobní.

**b) Zapněte dvoufázové ověření.** Bez něj se heslo aplikace vůbec
nenabídne. Jděte na `myaccount.google.com`, vlevo **Zabezpečení**,
najděte **Dvoufázové ověření** a projděte průvodce — vyžádá si telefonní
číslo a pošle na něj kód.

**c) Vytvořte heslo aplikace.** Otevřete přímo tuhle adresu:

    https://myaccount.google.com/apppasswords

V menu ji nehledejte, Google ji tam u většiny účtů nezobrazuje. Stránka
si nejspíš vyžádá znovu přihlášení. Pak jen do políčka s názvem napište
cokoli, podle čeho to poznáte (třeba `hlasovani vybor`), a klikněte na
**Vytvořit**.

**d) Zkopírujte kód.** Vyskočí okno se šestnácti znaky rozdělenými do
čtyř skupin po čtyřech, například `abcd efgh ijkl mnop`. **Mezery jsou
jen kosmetické, zapisujte kód bez nich** — tedy `abcdefghijklmnop`.
Google ho ukáže jednou a už nikdy; když okno zavřete, musíte vytvořit
nové. Tenhle kód půjde v kroku 5 do secrets `IMAP_PASS` a `SMTP_PASS`.

IMAP zapínat nemusíte, Gmail ho má zapnutý sám.

**Kdyby ta stránka hlásila, že heslo aplikace není k dispozici:** buď
ještě neběží dvoufázové ověření (vraťte se k bodu b), nebo jste
přihlášen pod firemním účtem, kde to správce zakázal. Proto ten nový,
soukromý účet.

Microsoft 365 tady nepoužijte. Přihlášení jménem a heslem k IMAP tam
Microsoft vypnul a hesla aplikací neexistují; potřebovali byste registraci
aplikace v Entra ID, tedy přesně to IT, kterému se vyhýbáme.

---

## 5. Vyplnit secrets

**Settings → Secrets and variables → Actions**. Jsou tam dvě záložky
a záleží na tom, do které co patří.

Do **Secrets** (New repository secret, jeden po druhém — vidí je jen
běžící úloha a už nikdy nikdo, ani vy):

| Jméno | Hodnota |
| --- | --- |
| `IMAP_HOST` | `imap.gmail.com` |
| `IMAP_USER` | adresa schránky |
| `IMAP_PASS` | heslo aplikace z kroku 4 |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | adresa schránky |
| `SMTP_PASS` | totéž heslo aplikace |
| `ADMIN_EMAIL` | vaše adresa — sem chodí hlášky a výsledky |

Do **Variables** (záložka vedle, tyhle jsou vidět běžně):

| Jméno | Hodnota |
| --- | --- |
| `PAGES_URL` | adresa z kroku 3, **bez lomítka na konci** |

Překlep v `PAGES_URL` je druhý nejčastější problém: pozvánky odejdou,
ale odkazy v nich nikam nevedou.

---

## 6. Token pro administraci

`admin.html` mluví s GitHubem přímo z prohlížeče a potřebuje k tomu token.

Klikněte na svůj avatar → **Settings** (tentokrát nastavení účtu, ne
repozitáře) → úplně dole **Developer settings** → **Personal access tokens
→ Fine-grained tokens** → **Generate new token**.

- *Repository access*: **Only select repositories**, vyberte tenhle jeden
- *Permissions → Repository permissions*: **Contents** na *Read and write*,
  **Actions** na *Read and write*
- platnost podle sebe, klidně rok

Token se ukáže jednou. Zkopírujte ho, otevřete `admin.html` na své Pages
adrese, vyplňte vlastníka, jméno repozitáře a token, **Připojit**. Uloží se
do prohlížeče, takže příště už jen otevřete stránku.

---

## 7. Zkušební kolo

Než pustíte pět lidí, vyzkoušejte to na sobě. V administraci → **Nastavení** dočasně
nechte v seznamu hlasujících jen sebe (vaše jméno a adresa), uložte a pak:

1. **Krok 2 → OK.** Do minuty vám má přijít pozvánka se třemi odkazy.
2. Otevřete odkaz, vyplňte lístek, **Odevzdat**, potom **Odeslat e-mailem**
   a zprávu odešlete beze změn.
3. **Krok 3 → Zkontrolovat schránku teď.** Do minuty přijde potvrzení
   „přijali jsme Vaši odpověď" a tabulka v administraci se přebarví.
4. **Krok 4 → Stáhnout výsledky.** Musí přijít sešit se třemi listy.

Když některý krok selže, jděte do záložky **Actions**, klikněte na poslední
běh a rozklikněte krok, který má červený křížek. Skripty píšou česky
a v *Summary* nahoře je tabulka, kdo co odevzdal.

Pak v administraci → **Nastavení** vraťte všech pět lidí a uložte.
Od téhle chvíle už `config.js` needitujte ručně — všechno se mění
v záložce Nastavení.

---

## Co dostanete místo patnácti souborů

Sběrač skládá lístky průběžně: pět odpovědí na jeden formulář je pět řádků
jedné tabulky, ne pět souborů. Po každém úspěšném sběru navíc přepíše
`data/kola/<kolo>/vysledky.xlsx` — jeden sešit, ve kterém je:

- list **Přehled** — kdo co odevzdal a kolik ještě chybí
- list na každý formulář — hlasující v řádcích, otázky ve sloupcích,
  zamrzlá hlavička a zapnuté filtry

Stáhnout ho jde kdykoli tlačítkem v kroku 4, i uprostřed sběru. Při uzávěrce
odejde e-mailem; zaškrtnutím políčka se pošle rovnou všem hlasujícím, takže
nemusíte nic přeposílat. CSV zůstávají v repozitáři, kdybyste je někdy
potřeboval do jiného nástroje.

---

## Na co si dát pozor

**Cron chodí pozdě.** `sber.yml` má naplánováno každých deset minut, ale
GitHub běh při zátěži odloží klidně o dvacet. Pro hlasování na několik dní
je to jedno; když chcete odpověď hned, klikněte na *Zkontrolovat schránku teď*.

**Naplánované úlohy po šedesáti dnech usnou.** Pokud se do repozitáře dva
měsíce nic nezapíše, GitHub cron vypne a napíše vám o tom. Stačí cokoli
commitnout, nebo úlohu ručně spustit. Mezi hlasováními se to stát může.

**Repozitář je veřejný.** Vidí ho kdokoli včetně jmen a adres v `config.js`,
nahraných podkladů i výsledků. Historie commitů ukazuje, kdy co přibylo, ale
úloha má právo zapisovat, takže to není důkaz proti dodatečné úpravě —
jako auditní záznam to neobstojí.

**Tokeny v pozvánkách platí do dalšího rozeslání.** Nové rozeslání staré
odkazy zneplatní. Kdo použije odkaz z předloňské pozvánky, dostane hlášku
o nerozpoznaném odkazu.

---

## Kam sáhnout, když něco nesedí

| Co vidíte | Kde je příčina |
| --- | --- |
| Úloha spadne hned v prvním kroku | chybí některý secret |
| `403: Resource not accessible by integration` | organizace nepouští zápis přes GITHUB_TOKEN — založte secret `GH_PAT` podle kroku 2 |
| Pozvánky nedorazily | *Summary* běhu vypíše konkrétní adresu i chybu SMTP |
| Odkazy v pozvánce nikam nevedou | špatná `PAGES_URL` |
| Stránka bez stylů | chybí `.nojekyll` |
| Lístek nedorazil do sešitu | *Summary* běhu `2 · Sběr odpovědí` — vypisuje každou zprávu i důvod odmítnutí |
| „neplatný token" | hlasující použil odkaz ze starší pozvánky |
| Administrace hlásí 403 | tokenu chybí oprávnění, nebo vypršel |
