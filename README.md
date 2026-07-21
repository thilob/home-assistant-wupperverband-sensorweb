# Wupperverband Sensor Web für Home Assistant

Benutzerdefinierte Home-Assistant-Integration für ausgewählte Messreihen aus dem öffentlichen **OGC Sensor Observation Service (SOS) 2.0** des Wupperverbandes.

> **Wichtiger Rechtehinweis:** Die MIT-Lizenz dieses Repositorys gilt ausschließlich für den Programmcode. Die abgerufenen Messdaten sind nicht Bestandteil der MIT-Lizenz. Für Dienste und Daten gelten die Bedingungen des Wupperverbandes. Nach den veröffentlichten Bedingungen ist eine kommerzielle Nutzung nicht gestattet und es ist ein Quellenvermerk `© Wupperverband (Jahr)` anzubringen.

## Funktionen

- vollständige Einrichtung über die Home-Assistant-Oberfläche
- Abruf der verfügbaren SOS-Messangebote über `GetCapabilities`
- Auswahl einer Station beziehungsweise eines Offerings und einer Messgröße
- Abruf des jeweils neuesten Messwertes über `GetObservation`
- Maßeinheit und Messzeitpunkt aus dem SOS-Dokument
- konfigurierbares Aktualisierungsintervall, mindestens fünf Minuten
- konfigurierbare Erkennung veralteter Messwerte
- Quellenhinweis als Entitätsattribut
- deutsche und englische Übersetzung
- vorbereitet für HACS, Hassfest und HACS Action

## Installation zum lokalen Test

1. Den Ordner `custom_components/wupperverband_sensorweb` nach `/config/custom_components/` kopieren.
2. Home Assistant neu starten.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen** öffnen.
4. Nach **Wupperverband Sensor Web** suchen.
5. SOS-Endpunkt bestätigen, Messangebot und Messgröße auswählen.

Standard-Endpunkt:

```text
https://fluggs.wupperverband.de/sws5/service
```

## HACS-Vorbereitung

Das Repository enthält `hacs.json`, eine semantische Versionsnummer im Manifest sowie GitHub-Actions für Hassfest und HACS-Validierung. Vor einer Veröffentlichung müssen in `manifest.json` die Platzhalter `OWNER` durch den tatsächlichen GitHub-Namen ersetzt, ein öffentliches Repository angelegt und Releases mit Tags wie `v0.1.1` erstellt werden.

## Daten- und Nutzungsbedingungen

Datenquelle: **© Wupperverband 2026**

Die Integration ist ein unabhängiges Drittanbieterprojekt und weder vom Wupperverband entwickelt noch unterstützt. Messwerte können ungeprüft, verspätet, unvollständig oder zeitweise nicht verfügbar sein. Die Integration ist kein amtliches Warnsystem und darf nicht als alleinige Grundlage für sicherheitskritische oder hochwasserbezogene Entscheidungen verwendet werden.

Maßgeblich sind die jeweils aktuellen Bedingungen des Wupperverbandes:

- Sensor Observation Service: `https://fluggs.wupperverband.de/v2p/web/fluggs/sensor-observation-service`
- Nutzungsbedingungen digitale Dienste: `https://fluggs.wupperverband.de/v2p/web/fluggs/nutzungsbedingungen-digitale-dienste`

## Architektur

Jeder Konfigurationseintrag repräsentiert genau eine Kombination aus SOS-Offering und beobachteter Messgröße. Dies hält den Datenabruf klein und vermeidet einen lokalen Spiegel der gesamten Datenbank. Die Integration lädt die Angebotsliste nur während der Einrichtung und fragt danach ausschließlich den jüngsten Wert der ausgewählten Reihe ab.

## Entwicklung und Tests

```bash
python -m pip install -r requirements_test.txt
pytest
ruff check .
python -m compileall custom_components
```

Die enthaltenen Unit-Tests prüfen den XML-Parser mit SOS-2.0-Beispieldokumenten und benötigen keinen Zugriff auf den Produktivdienst.

## Lizenz

Programmcode: MIT. Siehe `LICENSE`.

Daten: gesonderte Nutzungsbedingungen des Wupperverbandes; insbesondere **nicht** unter MIT, CC BY oder einer anderen Open-Data-Lizenz weiterlizenziert.


## Verlauf und Diagnose

Die Integration setzt `force_update`, damit Home Assistant jeden erfolgreichen
Abruf an den Recorder weitergibt, auch wenn der vom SOS gelieferte Zahlenwert
gegenüber dem vorherigen Abruf identisch ist. Der Sensor stellt zusätzlich die
Attribute `measurement_time`, `measurement_age_minutes` und
`poll_interval_minutes` bereit. Damit lässt sich unterscheiden zwischen einem
tatsächlich konstanten Messwert und einer nicht fortgeschriebenen Quelle.

HTTP-Antworten für Messwerte werden mit `Cache-Control: no-cache, no-store`
angefordert, um veraltete Antworten eines vorgeschalteten Caches zu vermeiden.
