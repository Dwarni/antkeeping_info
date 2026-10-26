# Projektrichtlinien & Best Practices

## Modularitaet & DRY-Prinzip (Don't Repeat Yourself)
* **Wiederverwendbare Snippets:** Komponenten, HTML-Fragmente oder UI-Elemente, die an mehreren Stellen vorkommen (z. B. Galerien, Aktionsleisten, Modals, Buttons, Badges), muessen modular als eigene Snippets (z. B. unter `ants/templates/ants/snippets/` oder `templates/`) implementiert werden.
* **Redundanzen vermeiden & erkennen:** Vor einer Implementierung oder bei Aenderungen pruefen, ob vergleichbare Logik oder UI-Elemente bereits existieren. Redundanter Copy-Paste-Code soll vermieden bzw. aktiv durch wiederverwendbare Fragmente ersetzt werden.
* **Konfigurierbare Parameter:** Snippets sollen flexibel ueber Kontext-Parameter gesteuert werden (z. B. `with entry=entry thumb_size="140x140" gallery_prefix="xyz"`), anstatt separate fast identische Templates anzulegen.

## Django Templates & JavaScript
* **JavaScript-Einbindung:** Die Basis-Vorlage `layout.html` nutzt `{% block script %}` am Ende des Body-Tags. Kind-Templates muessen JavaScript-Dateien und Scripts in `{% block script %}` einbetten (nicht `{% block js %}` oder `{% block scripts %}`).
* **Bootstrap Modals & Event-Delegation:** JavaScript fuer interaktive Elemente (wie Lightboxen oder Share-Modals) soll Event-Delegation nutzen, damit dynamisch oder via HTMX nachgeladene Inhalte ohne Neuinitialisierung funktionieren.

## Tests & Qualitaetssicherung
* Nach Aenderungen an Templates oder Views stets relevante Tests ausfuehren (`python manage.py test <app>.tests...`).
* Bei neuen Snippets oder UI-Features sicherstellen, dass die Einbindung in Views ueber entsprechende Assertions (`assertContains`) abgesichert ist.

## Roadmaps & Aufgabenplanung
* **Verzeichnis `roadmaps/`:** Alle Roadmaps liegen im Verzeichnis `roadmaps/`.
* **Aktive Roadmap:** Die derzeit gültige Roadmap liegt unter `roadmaps/ROADMAP.md`.
* **Archivierung abgeschlossener Roadmaps:** Vollständig umgesetzte Roadmaps werden mit Datumspräfix (z. B. `roadmaps/archive/YYYY-MM-DD_<thema>.md`) archiviert und in `roadmaps/ROADMAP.md` im Abschnitt Archiv verlinkt.
