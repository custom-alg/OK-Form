# OK Forms — příručka správce

Kompletní popis toho, jak je systém složený, co kde běží a co s tím dělat.
Postup prvního nastavení krok za krokem je v **PRUVODCE-GITHUB.md**; tenhle
dokument je referenční a předpokládá, že už to jednou běželo.

---

## 1. Co to celé je

Statická webová aplikace na GitHub Pages, čtyři úlohy v GitHub Actions
a jedna poštovní schránka. Žádný server, žádná databáze, žádná měsíční platba.

Životní cyklus jednoho kola:

```
   admin.html                 e-mail                GitHub Actions
   ──────────                 ──────                ──────────────
1. Nastavení        ──────────────────────────────▶ config.js v repozitáři
2. Podklady         ──────────────────────────────▶ assets/*.png
3. „OK — rozeslat"  ──▶ pozvánka s odkazem ──▶ hlasující vyplní
                                                    │
4.                        lístek e-mailem ◀─────────┘
                                  │
                                  ▼
                        sber.yml každých 10 min
                                  │
                                  ▼
                    data/kola/<kolo>/*.json + *.csv + vysledky.xlsx
                                  │
5. „Ukončit sběr"  ──────────────▶ výsledky e-mailem
6.                        ručně: vložit do databaze.xlsx
```

Aplikace nemá vlastní přihlašování. Kdokoli s odkazem může lístek vyplnit;
identitu zajišťuje token v osobním odkazu z pozvánky. Pro pětičlenný výbor
je to přiměřené — pro cokoli právně závazného ne, viz oddíl 9.

---

## 2. Kde co je uložené

| Co | Kde | Kdo to mění |
| --- | --- | --- |
| Aplikace a nastavení | repozitář na GitHubu | vy přes `admin.html` |
| Publikovaná stránka | GitHub Pages | vzniká sama z repozitáře |
| Přístupová hesla | GitHub Secrets | vy, jednorázově |
| Pozvánky a lístky | poštovní schránka na Gmailu | úlohy |
| Nasbírané odpovědi | `data/` v repozitáři | úloha `sber.yml` |
| Přístupový token administrace | prohlížeč (localStorage) | vy |
| Archiv a výpočty | `databaze.xlsx` u vás na disku | vy ručně |

### Struktura repozitáře

```
index.html          hlasovací formulář (nechte být)
admin.html          administrace (nechte být)
config.js           VŠECHNA nastavení — mění se přes admin
support.js          běhové prostředí formuláře (nechte být)
_ds/                vzhled (nechte být)
assets/             podkladové obrázky — nahrávají se přes admin
data/               nasbírané odpovědi, zakládá se samo
  kolo.json         stav aktuálního kola
  kola/<datum>/     odpovědi, CSV, sešit, protokol
scripts/            čtyři skripty v Pythonu
.github/workflows/  čtyři úlohy
docs/               tato dokumentace
.nojekyll           bez něj Pages ignoruje složku _ds
```

Ručně needitujte nic kromě `docs/`. `config.js` sice upravit lze, ale při
dalším uložení z administrace se přepíše.

---

## 3. Administrace

Otevírá se na adrese `<vaše Pages adresa>/admin.html`. Je veřejně dostupná,
ale bez tokenu z ní nejde nic udělat — je to jen formulář, který mluví
s GitHub API pod vaším jménem.

### Připojení

Vyžaduje fine-grained token s právy **Contents: Read and write** a
**Actions: Read and write** na tenhle jeden repozitář. Ukládá se do
`localStorage` prohlížeče, takže příště stačí stránku otevřít. Na cizím
počítači po práci klikněte na *Odhlásit a smazat token*.

Token má platnost — až vyprší, administrace začne hlásit 401 nebo 403.
Vytvořte nový stejným postupem a znovu se připojte. Poznamenejte si datum
vypršení, ať vás to nepřekvapí den před hlasováním.

### Záložka Nastavení

Kompletní editor souboru `config.js`. Co která volba dělá:

**Chování aplikace**

| Volba | Význam |
| --- | --- |
| Sběrná adresa | kam míří tlačítko „Odeslat e-mailem" ve formuláři; musí to být schránka, kterou čte `sber.yml` |
| Režim sběru | `e-mailem` = normální provoz; `sdílená složka` = lístky se zapisují na disk (jen Chrome/Edge) |
| Odkaz na sdílenou složku | nepovinný; prázdné = tlačítko se skryje |
| Oddělovač CSV | středník pro český Excel, čárka pro anglický |
| Výchozí motiv | jak stránka vypadá při prvním otevření |
| Kontrola součtu | `blokovat` = nedosažitelné volby zešednou; `varovat` = klikat lze vše, odeslat ne |
| Přepínač světlý/tmavý | zda ho hlasující vidí |
| Netto skóre | zda se v hlavičce sekce ukazuje součet −3…+3 |

**Hlasující.** Jméno a e-mail. Pořadí určuje pořadí ve výsledcích.
Na adresy chodí pozvánky, takže překlep = lístek nedorazí. Odebrání
hlasujícího z běžícího kola neodstraní jeho už odevzdaný lístek.

**Pool témat.** Kolik témat je v poolu (`aktuálně`), kolik jich smí být
nejvýš (`max`) a nejméně (`min`). Z toho formulář počítá, kolik vyřazení
musí doprovázet zařazení. Je-li pool plný, zařazení bez vyřazení neprojde.

**Témata k prioritizaci.** Seznam, ze kterého se sestavuje pořadí.
Musí mít alespoň tolik položek, kolik je maximum priorit.

**Škála.** Sedm stupňů. První tři mají kontrolní hodnotu −1, prostřední 0,
poslední tři +1. **Zapisujte bez mezer** — přesně v tomto tvaru je čte
převodní tabulka v `databaze.xlsx`. Kdyby tam bylo „+ +", VLOOKUP v matici
nenajde shodu a hlas tiše propadne. Editor mezery odstraňuje sám.

**Sekce a řádky.** Každá sekce je jeden blok lístku. Identifikátory
u existujících řádků neměňte — podle nich se páruje rozepsaný koncept
v prohlížečích hlasujících. Nový řádek dostane vlastní id automaticky.

Než se uloží, projde nastavení kontrolou: neplatné e-maily, prázdná jména,
duplicitní identifikátory, škála jiná než sedmiprvková, pool s minimem větším
než maximum. Chyby uložení zastaví, upozornění se jen zeptají.

> **Pozor na model.** Přidáte-li řádek nebo sekci, přibude sloupec v CSV.
> `databaze.xlsx` má pevně dané sloupce, takže nové položky se do něj
> nepřenesou, dokud v něm neuděláte místo. Viz oddíl 7.

### Záložka Podklady

Nahrání čtyř obrázků. Stránka po zápisu čeká, až se soubor skutečně objeví
na publikované adrese, a teprve pak napíše *publikováno*. Řiďte se tou
hláškou, ne náhledem — prohlížeč umí držet starou verzi.

### Záložka Hlasování

Rozeslání lístků a tabulka, kdo odevzdal. Tlačítko *Zkontrolovat schránku
teď* spustí sběr okamžitě, místo čekání na desetiminutový cyklus.

### Záložka Výsledky

Stažení sešitu, uzávěrka a ruční doplnění lístků, které se nepodařilo přečíst.

---

## 4. Poštovní schránka

Účet: `ok.form.monecois@gmail.com` (nebo ten, který máte nastavený).
Úlohy k němu přistupují přes IMAP a SMTP pomocí **hesla aplikace** —
šestnáctimístného kódu, ne běžného hesla k účtu.

Heslo aplikace se vytváří na `myaccount.google.com/apppasswords` a vyžaduje
zapnuté dvoufázové ověření. Zapisuje se bez mezer.

**Kdy ho budete muset vytvořit znovu:** když změníte heslo k účtu Google,
heslo aplikace se automaticky zneplatní. Sběr pak začne padat na chybě
přihlášení. Vytvořte nové a přepište secrets `IMAP_PASS` a `SMTP_PASS`.

Schránku občas projděte — úlohy označují zprávy jako přečtené, ale nemažou
je, takže časem naroste. Nepřečtené zprávy jsou fronta ke zpracování;
označíte-li nějakou ručně jako nepřečtenou, sběr se ji pokusí zpracovat znovu.

---

## 5. Secrets a proměnné

**Settings → Secrets and variables → Actions.** Secrets nejdou po uložení
přečíst, jen přepsat.

| Secret | Co to je |
| --- | --- |
| `IMAP_HOST` | `imap.gmail.com` |
| `IMAP_PORT` | `993` (nepovinné) |
| `IMAP_USER` | adresa schránky |
| `IMAP_PASS` | heslo aplikace |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | adresa schránky |
| `SMTP_PASS` | heslo aplikace |
| `ADMIN_EMAIL` | kam chodí hlášky „X vyplnil Y" a výsledky |
| `GH_PAT` | jen když organizace nepouští zápis přes GITHUB_TOKEN |

| Variable | Co to je |
| --- | --- |
| `PAGES_URL` | adresa publikované stránky, bez lomítka na konci |
| `IMAP_FOLDER` | složka ve schránce (nepovinné, výchozí `INBOX`) |

---

## 6. Úlohy v GitHub Actions

| Soubor | Spouští | Co dělá |
| --- | --- | --- |
| `rozeslat.yml` | tlačítko OK | vygeneruje tokeny, založí kolo, rozešle pozvánky |
| `sber.yml` | cron á 10 min + tlačítko | přečte schránku, zapíše lístky, přegeneruje sešit |
| `uzavrit.yml` | tlačítko | uzamkne kolo, sestaví souhrn, rozešle výsledky |
| `doplnit.yml` | tlačítko | zapíše lístek vložený ručně |

Průběh každého běhu je v záložce **Actions**. Klikněte na běh a otevřete
*Summary* — je psaný česky a obsahuje tabulku, kdo co odevzdal, i důvod
u každé odmítnuté zprávy.

**Jak se lístek pozná.** Formulář vkládá do e-mailu blok
`##OKF/1/<délka>##…##/OKF##` s daty zakódovanými v base64. Sběrač z něj čte
obsah i délku, takže pozná zkrácenou nebo poškozenou zprávu. Funguje to
i přes citovanou odpověď a přes HTML poštu. Co přečíst nejde, skončí
v `data/kola/<kolo>/neprirazene/` a administrace to vypíše s odkazy.

**Tokeny.** V pozvánce je token tvaru `<pořadí>.<náhoda>`; v repozitáři
je uložený jen jeho otisk SHA-256, takže z veřejných dat odkaz nikdo
nesestaví. Nové rozeslání staré tokeny zneplatní.

---

## 7. Přenos do modelu databaze.xlsx

Automatizované to není záměrně — model zůstává ve vašich rukou.

Sešit `vysledky.xlsx` má list *Přehled* a tři listy pojmenované podle bloků.
Každý z nich používá **stejná písmena sloupců i stejná čísla řádků** jako
list „IMPORT HLASOVACÍCH LÍSTKŮ" v modelu. Postup:

1. V administraci → Výsledky stáhněte sešit.
2. Otevřete list, například *3 · Hlavní část*. Nad tabulkou je červeně
   uvedená přesná adresa oblasti.
3. Označte žlutě podbarvenou oblast a zkopírujte.
4. V modelu se přepněte na „IMPORT HLASOVACÍCH LÍSTKŮ" a vložte na tutéž
   adresu **jako hodnoty** (Ctrl+Shift+V).
5. Zopakujte pro zbylé dva listy.

Pořadí řádků nehraje roli, model hledá hlasující podle jména ve sloupci D.
U bloku priorit se kopíruje i sloupec A s pořadovým číslem — model z něj
vzorcem `COUNT($A$12:$A$16)` počítá, kolik lístků dorazilo.

**Omezení na pět řádků.** Vzorce v modelu mají pevné rozsahy
(`$D$3:$L$8`, `$E$12:$E$16`, `$D$21:$U$25`), takže se vejde právě pět
hlasujících. Kdyby jich přibylo, export to napíše do protokolu a přebývající
vynechá — pak je potřeba rozšířit rozsahy přímo v modelu.

**Sloupec U (FX EUR/USD)** v modelu existuje, ale formulář se na EUR/USD
neptá, takže zůstává prázdný. Chcete-li ho začít sbírat, přidejte řádek
do sekce FX v Nastavení.

**Chyby, které nejsou vaše chyba.** Model má i bez hlasování 17 buněk
s `#REF!` a `#N/A`. Když někdo neodevzdá, přibudou `#N/A` v odvozených
řádcích, protože do převodní tabulky vstoupí text „Lístek neodevzdán".
Ověřeno: archivní data prohnaná exportem a vložená zpět dají v MASTER MATICI
identických 461 buněk jako originál.

---

## 8. Běžný provoz — co dělat kdy

**Před každým kolem**
1. Nastavení → zkontrolovat pool, témata a seznam hlasujících, uložit.
2. Podklady → nahrát aktuální obrázky, počkat na *publikováno*.
3. Hlasování → název kola, termín, vybrat formuláře, **OK**.
4. Zkontrolovat, že pozvánky odešly (Summary běhu vypíše počet).

**Během sběru**
- Tabulka v záložce Hlasování se sama obnovuje jednou za minutu.
- Kdo nereaguje, má odkazy v původní pozvánce; není potřeba nic přeposílat.
- Objeví-li se červené hlášení o nezpracovaných zprávách, doplňte je
  v záložce Výsledky.

**Po uzávěrce**
1. Výsledky → *Ukončit sběr*; volitelně zaškrtnout rozeslání všem.
2. Stáhnout sešit a přenést do modelu podle oddílu 7.
3. Aktualizovat pool v Nastavení podle toho, co výbor schválil.

**Jednou za čas**
- Projít schránku a smazat staré zprávy.
- Hlídat platnost tokenu administrace.
- Pokud se do repozitáře dva měsíce nic nezapíše, GitHub naplánované úlohy
  uspí a napíše o tom. Stačí cokoli commitnout nebo úlohu ručně spustit.

---

## 9. Meze řešení

Tohle je vědomě zvolený kompromis, ne nedodělek. Za co systém neručí:

**Není to auditní záznam.** Historie commitů ukazuje, kdy co přibylo, ale
úloha má právo zapisovat, takže dodatečnou úpravu nevylučuje. Pro cokoli,
co by mělo něco doložit před regulátorem, je potřeba databáze s odděleným
zápisem.

**Repozitář je veřejný.** Vidí ho kdokoli — včetně jmen a adres hlasujících,
nahraných podkladů a výsledků. Chcete-li to skrýt, je nutné buď repozitář
zesoukromit (Pages ze soukromého repozitáře vyžaduje placený plán), nebo
oddělit data do druhého, soukromého repozitáře.

**Identita stojí na tokenu v odkazu.** Kdo odkaz získá, může hlasovat
za jeho majitele. E-mail navíc není těžké podvrhnout.

**Cron chodí pozdě.** GitHub běh při zátěži odloží i o dvacet minut.
Pro hlasování na dny to nevadí; kdo chce odpověď hned, klikne na
*Zkontrolovat schránku teď*.

**Délka zprávy.** Kód lístku u hlavní části je zhruba 1,8 kB, starší Outlook
zvládne `mailto:` do ~2 kB. Rezerva je asi na tři další řádky. Kdyby se
formulář rozrostl, klienti začnou zprávu ořezávat — sběrač to pozná
a napíše hlasujícímu, ať použije tlačítko *Zkopírovat kód*.

---

## 10. Když něco nefunguje

| Příznak | Příčina a řešení |
| --- | --- |
| Administrace hlásí 401 nebo 403 | vypršel token, nebo mu chybí oprávnění — vytvořte nový |
| `403: Resource not accessible by integration` v běhu | organizace nepouští zápis přes GITHUB_TOKEN — založte secret `GH_PAT` |
| Úloha spadne hned v prvním kroku | chybí některý secret |
| Pozvánky nedorazily | Summary běhu vypíše konkrétní adresu i chybu SMTP |
| Sběr hlásí chybu přihlášení | vypršelo nebo bylo zneplatněno heslo aplikace — vytvořte nové |
| Odkazy v pozvánce nikam nevedou | špatná `PAGES_URL` |
| Stránka bez stylů | chybí `.nojekyll` v kořeni |
| Lístek nedorazil do sešitu | Summary běhu `2 · Sběr odpovědí` vypisuje každou zprávu i důvod |
| „neplatný token" | hlasující použil odkaz ze starší pozvánky |
| Obrázek se nezmění | tvrdé obnovení stránky (Ctrl+Shift+R) |
| Uložení nastavení hlásí konflikt | soubor se mezitím změnil jinde — *Zahodit změny* a provést úpravu znovu |
| V matici chybí hlasy | zkontrolujte, že škála je bez mezer (`++`, ne `+ +`) |

Souhrn každého běhu najdete v **Actions** → konkrétní běh → *Summary*.
