# Usability & Design Review Roadmap

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

---

## 📋 Aufgabenübersicht: Weitere Seiten zur Usability-Prüfung

### 1. Artenverzeichnis & Suche
- [ ] **Globale Suche (`/search/`)**
  - Suchergebnisdarstellung (Kategorisierung nach Arten, Berichten, Futterdaten).
  - Autovervollständigung, Leere-Zustände und Tippfehler-Toleranz.

### 2. Futter-Datenbank
- [ ] **Futter-Übersicht (`/fooddb/`)**
  - Kategorisierung (Zuckerquellen, Proteine/Futtertiere, Körner/Samen).
  - Filterung und Eignungsbewertungen auf einen Blick.
- [ ] **Futter-Detailansicht**
  - Verdaulichkeit, Beliebtheit bei verschiedenen Gattungen, Nährwertübersicht.

### 3. Schwarmflug-Meldungen & Karten
- [ ] **Schwarmflug-Meldungen & Karte (`/flights/`)**
  - Karten-Usability (Zoom, Cluster, mobile Touch-Bedienung).
  - Melde-Formular: Einfachheit der Dateneingabe für Halter (Datum, Wetter, Fundort).
  - Feedback nach Absenden einer Meldung (Toasts / Bestätigung).

### 4. Halterbereich, Kolonien & Haltungstagebuch
- [ ] **Kolonie-Verwaltung (`/users/.../colonies/`)**
  - Anlegen und Bearbeiten einer Kolonie (Art, Fangdatum, Volksstärke).
  - Statusanzeigen (Gründung, aktiv, Winterruhe, verstorben).
- [ ] **Haltungstagebuch / Journal (`/users/.../journals/`)**
  - Schnelles Hinzufügen von Einträgen und Fotos.
  - Chronologische Timeline-Darstellung und Filterung nach Ereignissen (Fütterung, Schlupf, Umzug).
  - Teilen-Funktion (Social Share Modal, Share-Links).

### 5. Benutzerkonto & Allgemeine Seiten
- [ ] **Benutzerprofil & Einstellungen (`/users/...`)**
  - Sub-Navigation, Avatar-Upload, E-Mail-Einstellungen und Passwortänderung.
- [ ] **Kontakt & Rechtliches (`/contact/`, `/legal-notice/`, `/privacy-policy/`)**
  - Schnelles Kontaktformular mit Validierungsfeedback.
  - Lesbarkeit und Typografie auf mobilen Geräten.

---

## 🔍 Prüfkriterien für jede Seite

1. **Usability & UX:** Sind die Hauptaktionen sofort ersichtlich? Gibt es klare Rückmeldungen bei Aktionen?
2. **Mobile / Responsive:** Funktioniert die Bedienung mit Daumenbedienung, ohne seitliches Scrollen oder abgeschnittene Texte?
3. **Darkmode & Kontrast:** Sind alle Texte, Rahmen und Badges nach WCAG AA gut lesbar (keine dunklen Texte auf dunklem Grund)?
4. **Micro-Interactions & Feedback:** Lade-Spinner (HTMX), leere Zustände (Empty States) und Fehlermeldungen verständlich formuliert?
