# Roadmap — Antkeeping.info

Strategische Roadmap und Aufgabenübersicht für die Weiterentwicklung von **antkeeping.info**.

---

## 🔔 1. Benachrichtigungssystem & Social Features

Ziel: Schnelle und anpassbare Benachrichtigungen für Interaktionen (Likes, Kommentare, Antworten, @Erwähnungen, Moderation, Folgen).

### Phase 1: In-App Benachrichtigungen & Glocke
- [x] **Datenmodell & Architektur (`notifications/`)**
  - Kernmodell `Notification` mit gezielten ForeignKeys (`entry`, `comment`, `colony`), `group_key` und Zeitstempeln.
  - Granulare Nutzereinstellungen `NotificationPreference` pro Event und Kanal (`in_app`, `email`, `push`).
  - Thread-Abonnements `EntrySubscription` mit Stummschalt-Funktion (`muted=True`).
- [x] **Service-Schicht (`notifications.services`)**
  - Zentrale `notify()`-Funktion mit Selbst-Check (keine Eigen-Alerts) und Privatsphäre-Filter für private Kolonien.
  - Automatische Gruppierung von Likes pro Journal-Eintrag (inkl. Actor-Entfernung bei Unlike).
  - Mentions-Parser für `@username`-Erwähnungen in Kommentaren.
  - Thread-Teilnehmer-Benachrichtigung für vorangegangene Kommentatoren.
  - Moderations-Meldungen (Kommentar entfernt, Kolonie von Staff privat gesetzt).
- [x] **UI & Frontend-Integration**
  - Glocken-Symbol in der Navbar (Desktop & Mobile) mit rotem Ungelesen-Badge (`99+`).
  - HTMX-Live-Polling (alle 60 s sowie bei Tab-Fokus via `visibilitychange`).
  - Schnelles Dropdown mit den letzten 10 Benachrichtigungen, relativer Zeit, Avataren und 1-Klick-Zielen.
  - Vollständige Benachrichtigungs-Inbox (`/notifications/`) mit Tabs (*Alle*, *Ungelesen*, *Erwähnungen*), Paginierung und Lösch-/Stummschalt-Optionen.
  - Einstellungs-Hub (`/notifications/settings/`) mit Matrix-Tabelle und sofortiger HTMX-Live-Speicherung.
  - 15 automatisierte Unit- & Integrationstests.

### Phase 2: E-Mail-Benachrichtigungen & Hintergrundverarbeitung
- [ ] **Task-Queue Setup (`django-tasks`)**
  - Einrichtung von `django-tasks` mit DatabaseBackend für asynchrone Verarbeitung ohne schweren Server-Stack.
  - `systemd`-Service für den `manage.py db_worker`.
- [ ] **Sofort-Mails mit Bündelung**
  - 5-Minuten-Bündelung für Sofort-Mails (verhindert E-Mail-Spam bei schnellen Kommentarwechseln).
  - Ausschluss bereits in-app gelesener Benachrichtigungen vor dem Mailversand.
  - Prüfung auf verifizierte E-Mail-Adressen (`allauth.EmailAddress.verified`).
- [ ] **Digest-Mails (Zusammenfassungen)**
  - Tägliche und wöchentliche Zusammenfassungen via `manage.py send_notification_digests`.
  - Cronjob-Einrichtung für täglichen und wöchentlichen Versand.
- [ ] **E-Mail-Templates & Abmeldung**
  - Responsive HTML- & Text-Templates im CI-Design von antkeeping.info.
  - RFC 8058 One-Click-Unsubscribe (`List-Unsubscribe` Header mit kryptografisch signiertem Token).
- [ ] **Datenschutzerklärung**
  - Aktualisierung der Datenschutzerklärung bezüglich E-Mail-Verarbeitung und Zustellung.

### Phase 3: Community & Folgen-Feature (Follows)
- [ ] **Folgen-Modell (`Follow`)**
  - Kolonien und Haltern direkt folgen (`follower`, `colony` oder `followed_user`).
  - Zähler für Follower auf öffentlichen Profilen und Kolonie-Karten.
- [ ] **Interaktionen & Hooks**
  - Wiederverwendbares „Folgen / Entfolgen“-Button-Snippet für Kolonie-Detail, Profil und Journal.
  - Benachrichtigung bei neuen Followern (`NEW_FOLLOWER`).
  - Benachrichtigung bei neuen Haltungsberichten gefolgter Kolonien (`FOLLOWED_NEW_ENTRY`).
- [ ] **Verwaltung gefolgter Kolonien**
  - Eigener Bereich in den Profileinstellungen zur Verwaltung aktiver Abonnements.

### Phase 4: Web Push (PWA)
- [ ] **PWA & Service Worker**
  - Vervollständigung von `manifest.json` (`start_url`, `display: standalone`, 512px- und Maskable-Icons).
  - Service Worker (`/sw.js`) am Root-Scope für `push`- und `notificationclick`-Events.
- [ ] **Web Push Backend (`pywebpush`)**
  - VAPID-Schlüsselverwaltung und Subscription-Endpunkte.
  - Automatische Bereinigung abgelaufener Subscriptions (HTTP 404/410).
- [ ] **Opt-In UI**
  - Sanfte Einladung in den Benachrichtigungseinstellungen (kein störender nativer Browser-Prompt beim ersten Seitenaufruf).
  - iOS-Hinweis: Installation zum Home-Bildschirm für Push-Empfang.
- [ ] **Datenschutz**
  - Ergänzung der Datenschutzerklärung bezüglich Push-Gateway-Diensten (Google, Apple, Mozilla).

---

## 📦 2. Historie & Archiv

Frühere, bereits abgeschlossene Meilensteine (z. B. das vollständige Usability-, Design- & Darkmode-Review aller bestehenden Seiten) sind im [2026-10-15 Usability & Design Review](archive/2026-10-15_usability_and_design_review.md) dokumentiert.
