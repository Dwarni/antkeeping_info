# Usability & Design Review Roadmap (Archiv)

> [!NOTE]
> **Status:** Vollständig umgesetzt & abgeschlossen (Stand: 15. Oktober 2026)  
> **Archiviert am:** 26. Oktober 2026

Status- und Aufgabenübersicht für die Usability-, Design- und Barrierefreiheitsprüfung aller Seiten von **antkeeping.info** (sowohl Light- als auch Darkmode).

---

## ✅ Bereits abgeschlossen

- [x] **Landing Page (`/`)**
  - Modernes Hero-Design mit klarem Hobby-Fokus für private Ameisenhalter.
  - Dynamische Feature-Karten und Call-to-Actions.
- [x] **Navbar & Navigation**
  - Aufgeräumte Hauptnavigation mit optimierter Dropdown-Struktur und mobiler Bedienbarkeit.
  - Quick-Search und Theme-Toggle Integration.
- [x] **Nuptial Flight Table (`/ants/nuptial-flight-table/`)**
  - Sticky-Spalte für Artennamen mit nahtloser Eckrundung.
  - Optimierter Darkmode-Kontrast für Kopfzeile und Monatsspalten.
  - „Fliegt jetzt“-Schnellfilter, dezente Status-Pills und visuelle On-Screen-Legende.
- [x] **Arten-Katalog / Übersicht (`/ants/species/filter/` bzw. `/antdb/`)**
  - Erweiterte Filterbedienung (Region/Land, Unterfamilie, Gattung, Haltungsschwierigkeit, Winterruhe, Größe etc.).
  - Umschaltung zwischen responsiver Karten- (Grid) und kompakter Listenansicht.
  - Einklappbarer mobiler Filter mit Live-Zähler aktiver Filter.
  - WCAG AA-konforme Badges für Haltungsschwierigkeit & Status im Light- und Darkmode.
  - Ansprechender Leere-Zustand (Empty State) mit Reset-Option.
- [x] **Art-Detailseite / Haltungsbericht (`/ants/<slug>/`)**
  - Schnelle Übersicht der Kernparameter auf einen Blick („Quick Parameters“-Grid: Nest- und Arenaklima, Winterruhe, Gründung, Kolonieform, Kasten-Größen).
  - Modernes 2-Spalten-Layout (Desktop) mit ansprechender Thumbnail-Fotogalerie, Quellennachweisen und ansprechendem Placeholder für unbebilderte Arten.
  - Interaktive Größenvergleichs-Karten mit Darkmode-Kontrastfilter für Ameisensilhouetten (`ant.svg`).
  - Integrierter AntMaps.org-Direktlink und Live-Echtzeitfilter für weltweite Verbreitungsdaten.
  - Schwarmflugzeiten mit dynamischem, theme-adaptivem Chart.js-Diagramm (automatische Farbanpassung an Light- und Darkmode per Theme-Observer).
  - WCAG AA-konforme Futterakzeptanz- und Community-Schwierigkeitsbewertungen.
- [x] **Globale Suche (`/search/`)**
  - Schnelle Live-Autovervollständigung in der Navbar mit Tastaturnavigation (Pfeiltasten/Enter/Escape) und Kategorien-Vorschauen (Arten, Futter, Berichte, Regionen).
  - Umfassende Multi-Kategorien-Suche über Ameisenarten (inkl. Synonyme & Trivialnamen), Haltungsberichte (nur öffentliche Kolonien), Futter-Datenbank und Regionen.
  - Kategorie-Pills mit Zähler-Badges zur schnellen Filterung der Treffer.
  - Tippfehler-Toleranz mit „Meintest du: ...?“-Vorschlägen für Gattungen und Arten.
  - Leere-Zustände mit Vorschlägen beliebter Suchbegriffe und Hilfestellungen.
- [x] **Futter-Datenbank (`/fooddb/` & `/fooddb/<id>/`)**
  - **Futter-Übersicht (`/fooddb/`)**:
    - Kategorisierungs-Tabs (Proteine, Zucker/Kohlenhydrate, Körner/Samen, Blätter, Sonstiges) mit Farbschema, Icons und dynamischen Zähler-Badges.
    - Schnelle Client-Seitige Sofortsuche mit Live-Trefferzähler („X von Y Futtermitteln“) und informativem Leere-Zustand mit Zurücksetzen-Aktion.
    - WCAG AA-konforme Akzeptanz-Badges (Hohe/Mittlere/Geringe Akzeptanz in % mit Barrierefreiheitsfarben für Light- & Darkmode).
    - Theme-adaptive Platzhalter (`.food-placeholder-thumb`) ohne harte Weißtöne im Darkmode.
    - Direkte Stimmabgabe für angemeldete Nutzer und übersichtliche Aufklapp-Suche für weitere Arten.
  - **Futter-Detailansicht (`/fooddb/<id>/`)**:
    - Vollwertige Detailseite (`FoodItemDetailView`) mit Breadcrumb-Navigation, High-Res Fotogalerie und Quellnachweisen.
    - Kennzahlen-Kacheln: Akzeptanzrate (%), Netto-Score, Gesamtwertungen und Anzahl getesteter Arten.
    - Spezifischer Fütterungs- und Eignungsratgeber je nach Futterkategorie (Proteine: Larvenwachstum, Überbrühen/Einfrieren gegen Milben; Zucker: Energie, Ertrinkschutz mit Watte; Körner: Messor-Kornspeicher trocken halten; Blätter: frische Futterpflanzen ohne Pestizide).
    - **Beliebtheit nach Ameisengattung**: Aufschlüsselung der Akzeptanzwerte aggregiert nach Gattungen (*Lasius*, *Camponotus*, *Messor* etc.) mit visualisierten Prozent-Balken.
    - Vollständiges Arten-Ranking mit Direktverlinkung zu Haltungsberichten und Stimmen-Logs (`/fooddb/<id>/<slug>/ratings/`).
    - SEO-Integration: `FoodItemSitemap` und direkte Verknüpfung in der globalen Suche und Autocomplete.
- [x] **Schwarmflug-Archiv & Karten (`/flights/`)**
  - Readonly-Archivierung: Lokale Meldungen dauerhaft deaktiviert, klare Kennzeichnung als permanentes historisches Archiv.
  - Prominente AntScout-Integration: Verlinkung auf `https://antscout.com/flights` als primäre Plattform für Live-Meldungen und Schwarmflug-Tracking (Landingpage-Hero/Callout, Navbar-Dropdown und Banner auf der Kartenseite).
  - Modernisierte Kartenansicht mit Breadcrumbs, Filterleiste nach Jahren & Arten und WCAG AA Darkmode-Styling.
- [x] **Benutzerprofil & Einstellungen (`/users/...`)**
  - **Einheitliche Sub-Navigation**: Schnelles Wechseln zwischen Übersicht, Kolonien, Journalen, Futterbewertungen, Schwierigkeitsgraden und Einstellungen inklusive Zähler-Badges und responsivem Touch-Horizontal-Scroll auf mobilen Endgeräten.
  - **Avatar-Upload & System**: `UserProfile`-Erweiterung mit square Avatar-Upload, File-Größen- & Typ-Validierung, Live-Bildvorschau beim Upload und Fallback auf zentrierte Benutzer-Initialen (`{% user_avatar %}`).
  - **Avatar-Integration**: Durchgängige Anzeige in der Navbar, im Profil-Dashboard, in den Einstellungen und in Kommentaren des Community- und Haltungstagebuchs.
  - **Zentraler Einstellungs-Hub (`/users/profile/settings/`)**: Strukturierte Karten für Profildaten (Name, Bio, Standort), E-Mail-Adressen, Passwort/Sicherheit und verknüpfte Social Accounts (Discord, Google).
  - **Privatsphäre & Sichtbarkeitseinstellungen**: Voller Name ist standardmäßig öffentlich komplett ausgeblendet (nur Nickname @username sichtbar), mit konfigurierbaren Schaltern für Namen, Standort und Biografie.
  - **Allauth E-Mail- & Passwortseiten**: Modernisiertes Design für `/accounts/email/`, `/accounts/password/change/` und `/accounts/password/set/` mit Breadcrumbs, Sub-Navigation und WCAG AA-konformen Status-Badges im Light- und Darkmode.
- [x] **Kontakt & Rechtliches (`/contact/`, `/legal-notice/`, `/privacy-policy/`)**
  - **Kontaktformular (`/contact/`)**:
    - Übersichtliches 2-Spalten-Layout (Desktop) mit moderner Hauptformular-Karte und Sidebar für alternative Kontaktkanäle.
    - Schnelles Validierungsfeedback mit Bootstrap 5 Formvalidierung (`was-validated`), Live-Zeichenzähler (`X / 5000 Zeichen`) und animiertem Spinner-Button gegen versehentliche Mehrfachabsendungen.
    - Automatische Vorbelegung von Name und E-Mail für angemeldete Nutzer (`request.user`) inkl. dezentem Hinweis.
    - Mehrschichtiger Spamschutz: Honeypot-Felder (`phone`, `address`), zeitgesteuerter kryptografischer Token (`form_token`) und IP-basiertes Rate-Limiting.
    - Community- und Support-Karten: Discord-Server-CTA (`discord_url`), direkte E-Mail mit 1-Klick-Kopierfunktion und Quick-Links für Arten- & Futter-Fragen sowie GitHub-Fehlermeldungen.
  - **Impressum / Legal Notice (`/legal-notice/`)**:
    - Vollständige Angaben nach § 5 DDG (Verantwortlicher, Anschrift, Kontakt-E-Mail mit Mailto-Aktion).
    - Optimierte Typografie und mobile Lesbarkeit mit Zeilenbegrenzung, weichem Zeilenabstand und strukturierten Inhaltskarten.
    - Klebriges Inhaltsverzeichnis (Sticky-TOC) auf Desktop und horizontale Touch-Quick-Jump-Pills auf Smartphones (`#provider`, `#liability-content`, `#liability-links`, `#copyright`, `#credits`).
    - Urheberrechtshinweise (CC BY 4.0 Lizenz-Badge) und Open-Source-Danksagung für genutzte Icons (Solar Icons, Framework7 ant icon, Bootstrap Icons).
  - **Datenschutzerklärung (`/privacy-policy/`)**:
    - „Privacy at a Glance“-Highlightkarten (keine Tracking-Cookies/Google Analytics, ausschließlich essenzielle Session-/CSRF-Cookies, max. 14-tägige Serverlog-Aufbewahrung, DDoS-Schutz via Cloudflare).
    - Strukturierte Dokumentation der Serverlog-Daten, Cookie-Tabelle mit Verwendungszweck und Laufzeit.
    - DSGVO-Betroffenenrechte (Auskunft, Berichtigung, Löschung) mit direkter E-Mail-Anfrage-Aktion.
    - Vollständige i18n-Unterstützung (`{% load i18n %}` / `{% trans %}`) in Footer, Formularen und Vorlagen sowie Aufnahme in die `sitemap.xml`.

---

## 📋 Aufgabenübersicht: Weitere Seiten zur Usability-Prüfung

### 1. Artenverzeichnis & Suche
- [x] **Globale Suche (`/search/`)**
  - Suchergebnisdarstellung (Kategorisierung nach Arten, Berichten, Futterdaten).
  - Autovervollständigung, Leere-Zustände und Tippfehler-Toleranz.

### 2. Futter-Datenbank
- [x] **Futter-Übersicht (`/fooddb/`)**
  - Kategorisierung (Zuckerquellen, Proteine/Futtertiere, Körner/Samen).
  - Filterung und Eignungsbewertungen auf einen Blick.
- [x] **Futter-Detailansicht**
  - Verdaulichkeit, Beliebtheit bei verschiedenen Gattungen, Nährwertübersicht.

### 3. Schwarmflug-Meldungen & Archiv
- [x] **Schwarmflug-Archiv & Karten (`/flights/`)**
  - Readonly-Archivierung: Lokale Meldungen dauerhaft deaktiviert, klare Kennzeichnung als historisches Referenzarchiv.
  - Prominente AntScout-Integration: Verlinkung auf `https://antscout.com/flights` für Live-Schwarmflugtracking & neue Meldungen.
  - Kartenbedienung mit responsivem Jahres- & Artenfilter und WCAG AA Darkmode-Styling.

### 4. Halterbereich, Kolonien & Haltungstagebuch
- [x] **Kolonie-Verwaltung (`/users/.../colonies/`)**
  - Anlegen und Bearbeiten einer Kolonie (Art, Fang-/Kaufdatum, Volksstärke mit Initial-Zählung beim Erstellen).
  - Statusanzeigen mit WCAG-AA-konformen Badges & Icons (Gründung, aktiv, Winterruhe, verstorben, abgegeben).
  - Filter-Pills nach Koloniestatus mit Zähler-Badges auf der Übersichtsseite.
  - Automatische Berechnung und Anzeige der aktuellen Volksstärke (`1 👑 • 42 🐜`) auf Übersichtskarten.
  - Darkmode-Kontrast für Aktions- & Edit-Buttons optimiert (`btn-outline-secondary`) und Umbruch-Schutz (`flex-md-nowrap flex-shrink-0 text-nowrap`).
- [x] **Haltungstagebuch / Journal (`/users/.../journals/`, `/ants/colonies/.../journal/` & `/ants/colonies/community/`)**
  - Schnelles Hinzufügen von Einträgen und Fotos via Schnell-Eingabe-Modal und Drag-and-Drop / Clipboard (Ctrl+V).
  - Chronologische Timeline-Darstellung mit visueller Timeline-Leiste und farblich passenden Ereignis-Icons (Fütterung, Schlupf, Umzug, Winterruhe etc.).
  - 1-Klick-Filter-Pills nach Ereignissen (`FEEDING`, `FIRST_WORKER`, `NEST_MOVE`, `HIBERNATION_START`, `FOUNDING`, `ISSUE`).
  - Community Journal: Einklappbarer Filter in der mobilen Ansicht (standardmäßig eingeklappt) mit dynamischem Zähler für aktive Filter; voll ausgeklappt auf Desktop (`d-md-block`).
  - Teilen-Funktion (Social Share Modal für WhatsApp, Telegram, Reddit, X, E-Mail, Zwischenablage sowie native Web Share API).

### 5. Benutzerkonto & Allgemeine Seiten
- [x] **Benutzerprofil & Einstellungen (`/users/...`)**
  - Einheitliche Sub-Navigation (`profile_nav.html`) über Dashboard, Kolonien, Journale, Futterbewertungen, Schwierigkeit und Einstellungen mit dynamischen Zähler-Badges und barrierefreiem Touch-Scroll.
  - Avatar-Upload (`UserProfile` Model, File-Validierung bis 5 MB, Live-Vorschau per JS, Lösch-Aktion und SVG/Initialen-Fallback-Tag `{% user_avatar %}`).
  - Integration des Benutzer-Avatars in der Navbar, im Profil, in Einstellungen und bei Kommentaren im Haltungstagebuch.
  - Vollständiger Einstellungs-Hub (`/users/profile/settings/`): Profil-Details (Name, Bio, Standort), Avatar-Verwaltung, E-Mail-Status und Sicherheitsübersicht.
  - Privatsphäre & Sichtbarkeit: Standardmäßig strikter Schutz des Klarnamens (nur Nickname @username öffentlich), granulare Schalter für Name, Standort und Bio.
  - Überarbeitete Allauth-Templates für E-Mail-Einstellungen (`/accounts/email/`), Passwortänderung (`/accounts/password/change/`) und Passwort-Erstellung (`/accounts/password/set/`) im konsistenten Profil-Design mit WCAG AA-Kontrast.
- [x] **Kontakt & Rechtliches (`/contact/`, `/legal-notice/`, `/privacy-policy/`)**
  - **Kontaktformular (`/contact/`)**:
    - Schnelles 2-Spalten-Layout (Desktop) mit übersichtlicher Formular-Karte und Sidebar für alternative Kontaktwege.
    - Sofortiges Validierungsfeedback (HTML5 & Bootstrap 5 `was-validated`, Live-Zeichenzähler bis 5.000 Zeichen, animierter Spinner-Button zur Vermeidung von Mehrfachabsendungen).
    - Automatische Vorbelegung von Name und E-Mail für angemeldete Nutzer (`request.user`) inkl. dezentem Status-Hinweis.
    - Mehrschichtiger Spamschutz (Honeypot-Felder, kryptografisch signierter Zeitstempel-Token mit Mindestdauer, IP-basiertes Rate-Limiting).
    - Direkte Community-Integration (Discord-Einladungskarte mit Direktlink, 1-Klick-Kopierfunktion für die Kontakt-E-Mail, Schnell-FAQ zu Futter, Arten & Fehlerberichten).
  - **Rechtliches & Datenschutz (`/legal-notice/` & `/privacy-policy/`)**:
    - Ausgezeichnete Typografie und Lesbarkeit auf Mobil- und Desktop-Geräten (optimierte Zeilenbreite und -höhe, strukturierte Inhaltskarten mit konsistentem Spacing).
    - Horizontale Quick-Jump-Pills für Mobilgeräte (`.doc-mobile-toc` mit sanftem Touch-Scroll und `scroll-margin-top`) für 1-Tap-Sprung zu Abschnitten.
    - Klebrige Inhaltsverzeichnis-Sidebar (`sticky-top`) auf Desktop zur schnellen Orientierung.
    - Gesetzliche Angaben nach § 5 DDG (Verantwortlicher, Kontakt, Haftungsausschluss für Inhalte & Links, CC BY 4.0 Lizenz und Open-Source-Credits für Icons & Assets).
    - DSGVO-konforme Datenschutzerklärung mit „Privacy at a Glance“-Highlightkarten (keine Tracking-Cookies/Google Analytics, ausschließlich essenzielle Session-/CSRF-Cookies, 14-tägige Log-Löschung, Cloudflare-Sicherheits-CDN, Betroffenenrechte mit Mailvorlage).
    - Vollständige Mehrsprachigkeit (`{% load i18n %}` / `{% trans %}`) in Footer, Formularen und Vorlagen sowie Integration von `/legal-notice/` und `/privacy-policy/` in die `sitemap.xml`.

---

## 🔍 Prüfkriterien für jede Seite

1. **Usability & UX:** Sind die Hauptaktionen sofort ersichtlich? Gibt es klare Rückmeldungen bei Aktionen?
2. **Mobile / Responsive:** Funktioniert die Bedienung mit Daumenbedienung, ohne seitliches Scrollen oder abgeschnittene Texte?
3. **Darkmode & Kontrast:** Sind alle Texte, Rahmen und Badges nach WCAG AA gut lesbar (keine dunklen Texte auf dunklem Grund)?
4. **Micro-Interactions & Feedback:** Lade-Spinner (HTMX), leere Zustände (Empty States) und Fehlermeldungen verständlich formuliert?
