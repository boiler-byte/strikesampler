# STRIKE 1.1.0 — Drum Sampler PWA

Eigenständiges HTML-Instrument, ohne Build, Backend oder externe Bibliotheken.

## Lokal starten

ZIP entpacken, in diesem Verzeichnis ein Terminal öffnen und ausführen:

```sh
python -m http.server 8080
```

Im Browser `http://localhost:8080/` öffnen. Alternativ auf einem statischen HTTPS-Webserver veröffentlichen. Das direkte Öffnen von `index.html` bleibt für den Sampler möglich, installiert aber keinen Service Worker. Bei einem Server im lokalen Netzwerk ist HTTPS für PWA-Funktionen erforderlich; die localhost-Ausnahme gilt nur auf dem jeweiligen Gerät.

## Installieren und offline verwenden

Einmal online öffnen, bis im Footer „Offline bereit“ erscheint. Je nach Browser über den angebotenen Installieren-Button, das Browsermenü oder auf iOS/Safari über Teilen → Zum Home-Bildschirm installieren. Der Offline-Cache enthält die komplette App. Eigene Audiodateien werden weiterhin lokal importiert; Projekte einschließlich Audio müssen wie zuvor ausdrücklich über „Speichern“ als JSON gesichert werden. Der Cache speichert die Anwendung, nicht automatisch offene Kits. Browser können Offline-Daten unter bestimmten Bedingungen entfernen.

Neue App-Versionen werden im Hintergrund vorbereitet; beim Schließen aller App-Fenster/Clients kann der wartende Worker aktiv werden. Kein automatischer Reload. Bei einem Update bitte aktuelle Projekte vor dem Schließen speichern.

## Boiler Room

Alle Dateien des veröffentlichten Pakets unter derselben App-Basis-URL ablegen (auch Unterpfade sind möglich). Die App-Basis-URL ist beispielsweise `https://example.org/apps/strike/`, die iframe-Einstiegsadresse `https://example.org/apps/strike/index.html` oder die Basis-URL (wenn der Server `index.html` ausliefert). Diese URLs sind Beispiele, keine bereits eingerichteten Deployments.

Die stabile PWA-Identität ist `/strike-drum-sampler` (originbezogen); Start-URL und Scope sind relativ zur Manifest-Datei. Die Identität bei Updates beibehalten.

Die drei öffentlichen Schnittstellen sind `manifest.webmanifest`, `boiler-room.json` und `sw.js`. Vorhandene Workspace-Konfigurationen bleiben unverändert. Der Server muss das Manifest als JSON/Manifest und `sw.js` als JavaScript ausliefern und die iframe-Einbettung zulassen. Ein Service Worker kann in einem fremd-originigen oder sandboxed iframe aufgrund von Browser- bzw. Workspace-Regeln blockiert werden; die Instrumentenlogik ist unabhängig davon. Die Installation sollte dann im direkt geöffneten App-Tab erfolgen. Die tatsächliche Boiler-Room-Umgebung ist separat zu testen.

`boiler-room.json`: Schema 2, technische Version 2, sichtbare Version 1.1.0. Die frühere sichtbare Version 1.0 wird rückwirkend der technischen Version 1 zugeordnet. Erstbereitstellung und aktuelle Bereitstellung in diesem Chat: 25.11.2026. Keine Lizenz- oder Autorenangaben ohne Nachweis. `offline.mode: full` gilt bei vollständig verfügbaren Ressourcen; die App braucht keine Internetdienste.

## Entwicklung und Test

`index.html` enthält die ursprüngliche Instrumentenlogik und UI; PWA-Integration ist separat am Dokumentende. Die Projektformat-Version bleibt 1. Bei Veröffentlichungen die technische Version in `boiler-room.json` und `RELEASE` in `sw.js`, die sichtbare Version im HTML und die Änderungshistorie aktualisieren. `files` an geänderte Offline-Abhängigkeiten anpassen. Ein eigenes Cache-Präfix pro App-Basis-URL verhindert die Löschung von Caches anderer Anwendungen.

Regressionstest (optional; benötigt Python-Pakete `jsonschema`, `playwright`, `Pillow` und Chromium):

```sh
python tests/check_pwa.py
```

Der Test verwendet einen temporären lokalen HTTP-Server und prüft Schema, Ressourcen, Manifest, Offline-Start und Kernfunktionen im Browser. Der Standard ist lokal in `boiler-room.schema.json` mitgeliefert.

Weitere isolierte Tests (ohne echten Service-Worker-Lebenszyklus):

```sh
node tests/check_worker.cjs
python tests/check_instrument.py
```

Prüfstand dieser Auslieferung: JSON-Schema mit Datumsprüfung, HTTP-Erreichbarkeit der gelisteten Dateien, JavaScript-Syntax, simulierter Service-Worker-Ablauf und Offline-Instrumententest in Chromium bestanden. Der vollständige Browser-Integrationstest wurde durch die lokale Browser-Administratorrichtlinie (`ERR_BLOCKED_BY_ADMINISTRATOR`) beim HTTP-Navigieren blockiert. Native PWA-Installation, echter Offline-Neustart mit Service Worker und Einbettung im tatsächlichen Boiler-Room-Workspace sind daher noch nicht verifiziert.
