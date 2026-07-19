# Wupperverband Sensor Web für Home Assistant

Benutzerdefinierte Home-Assistant-Integration für ausgewählte Messreihen aus dem öffentlichen **OGC Sensor Observation Service (SOS) 2.0** des Wupperverbandes.

> **Wichtiger Rechtehinweis:** Die MIT-Lizenz dieses Repositorys gilt ausschließlich für den Programmcode. Die abgerufenen Messdaten sind nicht Bestandteil der MIT-Lizenz. Für Dienste und Daten gelten die Bedingungen des Wupperverbandes. Nach den veröffentlichten Bedingungen ist eine kommerzielle Nutzung nicht gestattet und es ist ein Quellenvermerk `© Wupperverband (Jahr)` anzubringen.

## Funktionen

- vollständige Einrichtung über die Home-Assistant-Oberfläche
- alphabetisch sortierte Auswahl der veröffentlichten FluGGS-Stationen
- anschließende Auswahl einer Messgröße und ihres Messverfahrens
- eindeutiger Abruf der gewählten Messreihe über ihre Sensor-Web-ID
- Maßeinheit und Messzeitpunkt aus dem SOS-Dokument
- konfigurierbares Aktualisierungsintervall, mindestens fünf Minuten
- konfigurierbare Erkennung veralteter Messwerte
- Quellenhinweis als Entitätsattribut
- deutsche und englische Übersetzung
- vorbereitet für HACS, Hassfest und HACS Action

## Installation über HACS (benutzerdefiniertes Repository)

Eine Aufnahme in den standardmäßigen HACS-Katalog ist nicht erforderlich:

1. In HACS oben rechts das Drei-Punkte-Menü öffnen und **Benutzerdefinierte Repositories** wählen.
2. `https://github.com/thilob/home-assistant-wupperverband-sensorweb` als Repository eintragen.
3. Als Kategorie **Integration** auswählen und das Repository hinzufügen.
4. **Wupperverband Sensor Web** in HACS herunterladen und Home Assistant neu starten.
5. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **Wupperverband Sensor Web** suchen.

Alternativ ist eine manuelle Installation möglich:

1. Den Ordner `custom_components/wupperverband_sensorweb` nach `/config/custom_components/` kopieren.
2. Home Assistant neu starten.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen** öffnen.
4. Nach **Wupperverband Sensor Web** suchen.
5. SOS-Endpunkt bestätigen, Messangebot und Messgröße auswählen.

Standard-Endpunkt:

```text
https://fluggs.wupperverband.de/sws5/service
```

## HACS-Kompatibilität

Das Repository erfüllt die Strukturvorgaben für ein benutzerdefiniertes HACS-Integrationsrepository. Es enthält `hacs.json`, eine semantische Versionsnummer im Manifest, ein lokales Brand-Icon sowie GitHub Actions für Hassfest und HACS-Validierung. Eine Aufnahme in den öffentlichen HACS-Standardkatalog ist derzeit nicht vorgesehen.

## Daten- und Nutzungsbedingungen

Datenquelle: **© Wupperverband 2026**

Die Integration ist ein unabhängiges Drittanbieterprojekt und weder vom Wupperverband entwickelt noch unterstützt. Messwerte können ungeprüft, verspätet, unvollständig oder zeitweise nicht verfügbar sein. Die Integration ist kein amtliches Warnsystem und darf nicht als alleinige Grundlage für sicherheitskritische oder hochwasserbezogene Entscheidungen verwendet werden.

Maßgeblich sind die jeweils aktuellen Bedingungen des Wupperverbandes:

- Sensor Observation Service: `https://fluggs.wupperverband.de/v2p/web/fluggs/sensor-observation-service`
- Nutzungsbedingungen digitale Dienste: `https://fluggs.wupperverband.de/v2p/web/fluggs/nutzungsbedingungen-digitale-dienste`

## Architektur

Jeder Konfigurationseintrag repräsentiert genau eine Station und Messreihe. Während der Einrichtung lädt die Integration zunächst die Stationsliste und danach nur die Messreihen der ausgewählten Station. Im laufenden Betrieb fragt sie ausschließlich den jüngsten Wert der gespeicherten Messreihen-ID ab.

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
