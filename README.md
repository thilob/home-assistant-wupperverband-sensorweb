# Wupperverband Sensor Web für Home Assistant

Benutzerdefinierte Home-Assistant-Integration für ausgewählte Messreihen aus dem öffentlichen Sensor Web des Wupperverbandes. Die Einrichtung orientiert sich am Sensor-Web-Workflow `Ort -> Messgröße`; der eigentliche Datenabruf erfolgt je nach Eintrag über die passende Zeitreihe im Hintergrund.

> **Wichtiger Rechtehinweis:** Die MIT-Lizenz dieses Repositorys gilt ausschließlich für den Programmcode. Die abgerufenen Messdaten sind nicht Bestandteil der MIT-Lizenz. Für Dienste und Daten gelten die Bedingungen des Wupperverbandes. Nach den veröffentlichten Bedingungen ist eine kommerzielle Nutzung nicht gestattet und es ist ein Quellenvermerk `© Wupperverband (Jahr)` anzubringen.

## Funktionen

- vollständige Einrichtung über die Home-Assistant-Oberfläche
- Auswahl über `Ort -> Messgröße`, analog zum Wupperverband-Sensorweb
- Zwischenschritt-freie Zuordnung auf die passende interne Zeitreihe
- Abruf des jeweils neuesten Messwertes
- Maßeinheit, Messzeitpunkt und Ergebniszeit
- konfigurierbares Aktualisierungsintervall, mindestens fünf Minuten
- Standard-Aktualisierungsintervall für neue Einträge: 30 Minuten
- Standard-Schwelle für veraltete Daten bei neuen Einträgen: 24 Stunden
- Quellenhinweis als Entitätsattribut
- Diagnose-Entität für den letzten erfolgreichen Abruf
- deutsche und englische Übersetzung
- vorbereitet für HACS, Hassfest und HACS Action

## Aktueller Stand

- Veraltete Quelldaten setzen die Entität nicht mehr auf `unavailable`.
- `data_stale` und `stale_after_minutes` kennzeichnen alte Messwerte separat.
- `last_successful_fetch` zeigt den letzten erfolgreichen Abruf.
- Die Diagnose-Entität für `last successful fetch` wird über Neustarts hinweg wiederhergestellt.
- `result_time` wird getrennt vom eigentlichen Messzeitpunkt ausgewertet.
- Zeitstempel werden konsequent nach UTC normalisiert.
- Die Auswahl des neuesten Messwerts funktioniert auch bei gemischten Zeitzonenangaben.
- Jeder erfolgreiche Poll wird mit `force_update` an den Recorder weitergegeben.
- Debug-Protokollierung enthält Wert, Einheit, Messzeit und Ergebniszeit.

## Installation zum lokalen Test

1. Den Ordner `custom_components/wupperverband_sensorweb` nach `/config/custom_components/` kopieren.
2. Home Assistant neu starten.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen** öffnen.
4. Nach **Wupperverband Sensor Web** suchen.
5. Sensor-Web-Endpunkt bestätigen, Ort und Messgröße auswählen.
6. Optional Intervall und Veraltet-Schwelle in den Optionen anpassen.

Standard-Endpunkt:

```text
https://fluggs.wupperverband.de/sws5/service
```

## HACS

Das Repository enthält `hacs.json`, eine semantische Versionsnummer im Manifest sowie GitHub-Actions für Hassfest und HACS-Validierung. Für HACS-Releases sollten Git-Tags passend zur Manifest-Version erstellt werden, z. B. `v0.2.2`.

## Daten- und Nutzungsbedingungen

Datenquelle: **© Wupperverband 2026**

Die Integration ist ein unabhängiges Drittanbieterprojekt und weder vom Wupperverband entwickelt noch unterstützt. Messwerte können ungeprüft, verspätet, unvollständig oder zeitweise nicht verfügbar sein. Die Integration ist kein amtliches Warnsystem und darf nicht als alleinige Grundlage für sicherheitskritische oder hochwasserbezogene Entscheidungen verwendet werden.

Maßgeblich sind die jeweils aktuellen Bedingungen des Wupperverbandes:

- Sensor Observation Service: `https://fluggs.wupperverband.de/v2p/web/fluggs/sensor-observation-service`
- Nutzungsbedingungen digitale Dienste: `https://fluggs.wupperverband.de/v2p/web/fluggs/nutzungsbedingungen-digitale-dienste`

## Architektur

Jeder Konfigurationseintrag repräsentiert genau eine Kombination aus Ort und Messgröße. Während der Einrichtung lädt die Integration die Orte und zugehörigen Zeitreihen aus dem Sensor Web, verdichtet diese für die Auswahl auf sichtbare Messgrößen und speichert intern die passende Zeitreihen-ID. Bestehende ältere SOS-basierte Einträge bleiben weiter lesbar.

## Entwicklung und Tests

```bash
python -m pip install -r requirements_test.txt
pytest
ruff check .
python -m compileall custom_components
```

Die enthaltenen Unit-Tests prüfen sowohl den SOS-Parser als auch die Caching-/Zuordnungslogik und benötigen keinen Zugriff auf den Produktivdienst.

## Lizenz

Programmcode: MIT. Siehe `LICENSE`.

Daten: gesonderte Nutzungsbedingungen des Wupperverbandes; insbesondere **nicht** unter MIT, CC BY oder einer anderen Open-Data-Lizenz weiterlizenziert.


## Verlauf und Diagnose

Die Integration setzt `force_update`, damit Home Assistant jeden erfolgreichen
Abruf an den Recorder weitergibt, auch wenn der gelieferte Zahlenwert gegenüber
dem vorherigen Abruf identisch ist. Der Sensor stellt zusätzlich die Attribute
`measurement_time`, `measurement_age_minutes`, `poll_interval_minutes` und
`last_successful_fetch` bereit. Zusätzlich gibt es eine eigene Diagnose-Entität
für den letzten erfolgreichen Abruf. Damit lässt sich unterscheiden zwischen
einem tatsächlich konstanten Messwert, einer nicht fortgeschriebenen Quelle und
einem Abrufproblem.

HTTP-Antworten für Messwerte und Sensor-Web-Metadaten werden mit
`Cache-Control: no-cache, no-store` angefordert, um veraltete Antworten eines
vorgeschalteten Caches zu vermeiden.
