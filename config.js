// ================================================================
// KONFIGURACE APLIKACE - vše, co spravuje administrátor, je zde.
// Soubor vzniká z administrace (admin.html → Nastavení → Uložit).
// Ruční úpravy jsou možné, ale při dalším uložení z administrace
// se přepíšou.
// ================================================================
export default {
  // --- Obecné ---
  vysledkyEmail: "ok.form.monecois@gmail.com",   // kam směřuje tlačítko „Odeslat e-mailem"
  sberRezim: "email",                            // "email" = lístky chodí do sběrné schránky (GitHub Actions)
  nextcloudOdkaz: "",                            // nepovinný odkaz na sdílenou složku; prázdné = tlačítko skryto
  csvDelimiter: ";",                             // oddělovač CSV: "," nebo ";"
  darkLightMode: true,                           // false = přepínač tmavého režimu se skryje
  defaultTheme: "light",                         // "light" | "dark"
  validaceRezim: "block",                        // "block" = nedosažitelné volby zešednou a nejdou stisknout
                                                 // "warning" = vše lze klikat, ale lístek se součtem != 0 nelze odeslat
  nettoSkore: true,                              // true = v hlavičce sekce se ukazuje netto skóre (-3 az +3)

  // --- Cesty k obrázkům (admin je přepisuje soubory se stejným názvem) ---
  obrazky: {
    temataAktualni:   "assets/temata-aktualni.png",
    akciePrehled:     "assets/akcie-prehled.png",
    dluhopisyPrehled: "assets/dluhopisy-prehled.png",
    poolSchvaleny:    "assets/pool-schvaleny.png",
  },

  // --- Hlasující ---
  clenoveJmeno: ["Petr Budinský", "Jiří Mikeš", "Ondřej Pěška", "Petr Šimčák", "Jiří Šindelář"],
  clenoveMail: ["petr.budinsky@monecois.cz", "jiri.mikes@monecois.cz", "ondrej.peska@monecois.cz", "petr.simcak@monecois.cz", "jiri.sindelar@monecois.cz"],

  // --- Lístek 1: stav poolu témat (určuje, kolik vyřazení musí doprovázet zařazení) ---
  pool: {
    akcie:     { aktualne: 5, max: 5, min: 2 },
    dluhopisy: { aktualne: 4, max: 5, min: 2 },
  },

  // --- Lístek 2: dostupná témata k prioritizaci ---
  temataAkcie: ["Polovodiče", "Obrana", "Indie", "Umělá inteligence", "Inovace ve zdravotnictví", "Nukleární energie"],
  temataDluhopisy: ["Global Enhanced", "Absolute return", "Konvertibilní dluhopisy", "ABS"],
  maxPriorit: 5,

  // --- Lístek 3: škála a sekce ---
  // Škála: index 0-2 = kontrolní hodnota -1, index 3 = 0, index 4-6 = +1.
  skala: ["---", "--", "-", "N", "+", "++", "+++"],   // bez mezer: přesně tak je čte převodní tabulka v matici
  // pravidlo: true = součet kontrolních hodnot sekce musí být 0.
  sekceHlavni: [
    { id: "tridy", nazev: "TŘÍDY AKTIV", pravidlo: true, radky: [
      { id: "t_penezni", nazev: "Peněžní trh" },
      { id: "t_akcie", nazev: "Akcie" },
      { id: "t_dluhopisy", nazev: "Dluhopisy" },
      { id: "t_alternativy", nazev: "Alternativy" } ] },
    { id: "akcie", nazev: "AKCIE", pravidlo: true, radky: [
      { id: "a_us", nazev: "Americké akcie" },
      { id: "a_eu", nazev: "Evropské akcie" },
      { id: "a_em", nazev: "Akcie rozvíjejících se trhů" },
      { id: "a_temata", nazev: "Témata / ostatní akciové pozice" } ] },
    { id: "dluhopisy", nazev: "DLUHOPISY", pravidlo: true, radky: [
      { id: "d_cz", nazev: "České státní dluhopisy" },
      { id: "d_us", nazev: "Americké státní dluhopisy" },
      { id: "d_eu", nazev: "Evropské státní dluhopisy" },
      { id: "d_ig", nazev: "Korpo. dluhopisy - investiční stupeň" },
      { id: "d_hy", nazev: "Korpo. dluhopisy - spekulativní stupeň" },
      { id: "d_ost", nazev: "Ostatní dluhopisové pozice" } ] },
    { id: "fx", nazev: "FX", poznamka: "Kontrolní pravidlo se zde neuplatňuje.", pravidlo: false, radky: [
      { id: "fx_eur", nazev: "EUR/CZK" },
      { id: "fx_usd", nazev: "USD/CZK" } ] },
  ],
};
