# Hamburgs Haushalt 2027/2028

Eine unabhängige Auswertung des Haushaltsplan-Entwurfs 2027/2028 der Freien und Hansestadt Hamburg. Die Seite zeigt, wofür die Stadt ihr Geld ausgibt: nach Einzelplan, Aufgabenbereich, Produktgruppe, Produkt und Kostenart.

Live: https://haushalt-hamburg.vermittler.dev

Dieses Projekt ist kein Angebot der Freien und Hansestadt Hamburg.

## Daten

Alle Zahlen stammen aus den veröffentlichten Haushaltsplänen der Freien und Hansestadt Hamburg. Die Skripte lesen sie aus den PDF-Bänden aus. Die Angaben erfolgen ohne Gewähr. Bei Abweichungen gelten die Originaldokumente.

Die Werte liegen in Tsd. € oder Mio. € vor. Das Feld `meta` jeder Datei in `dashboard/` nennt Quelle, Einheit und Besonderheiten.

| Datei | Inhalt | Quelle |
| --- | --- | --- |
| `dashboard/eckwerte.json` | Eckwerte des Gesamthaushalts | Band Gesamthaushalt |
| `dashboard/einzelplaene.json` | Kosten, Erlöse und Investitionen je Einzelplan, 2026–2028 | Band Gesamthaushalt |
| `dashboard/produkte.json` | Kosten und Erlöse je Produkt (IPR-Produktbericht) | Band Gesamthaushalt |
| `dashboard/kostenarten.json` | Ergebnisplan je Produktgruppe nach Kostenart, 2024–2030 | Einzelplan-Bände |
| `dashboard/kennzahlen.json` | Kennzahlen je Produktgruppe, 2024–2030 | Einzelplan-Bände |
| `dashboard/finanzbericht.json` | Tabellen 2 und 3 des Finanzberichts | Finanzbericht 2027/2028 |

`data/` enthält die Zwischenergebnisse der Parser als CSV und JSON.

### Quellen

Die Finanzbehörde veröffentlicht alle Bände auf der Seite [Doppelhaushalt 2027/2028](https://www.hamburg.de/politik-und-verwaltung/behoerden/finanzbehoerde/themen/haushalt/doppelhaushalt-2027-2028-1207756).

- [Band Gesamthaushalt](https://dokumente.hamburg.de/resource/blob/1209006/4826cfb37eed8a34e15cfe17846fd0ac/finale-fassung-01-hhp-gesamthaushalt-data.pdf)
- [Finanzbericht 2027/2028](https://dokumente.hamburg.de/resource/blob/1209040/92adcb9cf30f6bb9520b9c1be3caa007/finanzbericht-2027-2028-data.pdf)
- Einzelplan-Bände:
  - [02: Einzelpläne 1.01 bis 1.1](https://dokumente.hamburg.de/resource/blob/1209008/63f30163f3eb2ba42aa87ff20a024a9b/finale-fassung-02-hhp-ep-1-01-1-1-data.pdf)
  - [04a: Einzelpläne 1.2 bis 1.5](https://dokumente.hamburg.de/resource/blob/1209012/2397bb897698734d9fd438f4b2f720f8/finale-fassung-04a-hhp-ep-1-2-1-5-data.pdf)
  - [04b: Einzelpläne 1.6 bis 1.8](https://dokumente.hamburg.de/resource/blob/1209014/18741df33912be7db6941ab71446a272/finale-fassung-04b-hhp-ep-1-6-1-8-data.pdf)
  - [05: Einzelplan 2](https://dokumente.hamburg.de/resource/blob/1209016/1791a2fe26c159e626cf5601d17bea5b/finale-fassung-05-hhp-ep-2-0-data.pdf)
  - [06: Einzelplan 3.1](https://dokumente.hamburg.de/resource/blob/1209018/ef8cc99dc8c155e6f73ba5d816784711/finale-fassung-06-hhp-ep-3-1-data.pdf)
  - [07: Einzelplan 3.2](https://dokumente.hamburg.de/resource/blob/1209020/d665cf3a5bf6fea292aafd4c25a666c9/finale-fassung-07-hhp-ep-3-2-data.pdf)
  - [08: Einzelplan 3.3](https://dokumente.hamburg.de/resource/blob/1209022/be9f8fa0d4040e010e2b63d005a65c46/finale-fassung-08-hhp-ep-3-3-data.pdf)
  - [09: Einzelplan 4](https://dokumente.hamburg.de/resource/blob/1209024/c7976d80c7dd6e3375dd8112fe737493/finale-fassung-09-hhp-ep-4-data.pdf)
  - [10: Einzelplan 6.1](https://dokumente.hamburg.de/resource/blob/1209026/6cc46f2978081cc9e9dabe4582805e03/finale-fassung-10-hhp-ep-6-1-data.pdf)
  - [11: Einzelplan 6.2](https://dokumente.hamburg.de/resource/blob/1209028/217eeaebdd18a9d386db495c1fe6a26c/finale-fassung-11-hhp-ep-6-2-data.pdf)
  - [12: Einzelplan 7](https://dokumente.hamburg.de/resource/blob/1209030/3efb232bca8d6a78e35825e27a799cbc/finale-fassung-12-hhp-ep-7-0-data.pdf)
  - [13: Einzelplan 7.1](https://dokumente.hamburg.de/resource/blob/1209032/822b231868e6c9c8a4d779d10d8c20ec/finale-fassung-13-hhp-ep-7-1-data.pdf)
  - [14: Einzelplan 8.1](https://dokumente.hamburg.de/resource/blob/1209034/6264320d9a4d9d7e48e6c40bb2ab78d0/finale-fassung-14-hhp-ep-8-1-data.pdf)
  - [15: Einzelplan 9.1](https://dokumente.hamburg.de/resource/blob/1209036/255abad32207a59da324ea0d94a4d0ef/finale-fassung-15-hhp-ep-9-1-data.pdf)
  - [16: Einzelplan 9.2](https://dokumente.hamburg.de/resource/blob/1209038/dd4dd9e6d167d1ad4ee151fbbb321b08/finale-fassung-16-hhp-ep-9-2-data.pdf)

Die PDFs liegen nicht in diesem Repository. Um die Daten neu zu erzeugen, laden Sie die Bände herunter und legen Sie sie so ab:

```text
raw/pdf/gesamthaushalt-2027-2028.pdf
raw/pdf/finanzbericht-2027-2028.pdf
raw/pdf/epl/finale-fassung-NN-….pdf
```

## Voraussetzungen

- Python 3.12
- `pdftotext` aus Poppler, zum Beispiel mit `brew install poppler`
- pandas für `build_dataset.py` und `validate.py`

```bash
python3 -m venv .venv
.venv/bin/pip install pandas
```

Alle Skripte laufen mit `python -I`. Dieser Schalter verhindert, dass Python Module aus dem aktuellen Verzeichnis lädt.

## Daten neu erzeugen

1. Gesamtpläne und Übersichten je Einzelplan auslesen:

   ```bash
   python3 -I scripts/parse_overviews.py raw/pdf/gesamthaushalt-2027-2028.pdf data
   ```

2. IPR-Produktbericht auslesen (Seiten 19 bis 121 des Bands Gesamthaushalt):

   ```bash
   python3 -I scripts/parse_ipr.py raw/pdf/gesamthaushalt-2027-2028.pdf 19 121 data
   ```

3. Kostenarten und Kennzahlen aus jedem Einzelplan-Band auslesen. Die Nummer des Bands bestimmt den Dateinamen:

   ```bash
   python3 -I scripts/parse_epl.py raw/pdf/epl/finale-fassung-06-hhp-ep-3-1-data.pdf data/epl_06.json
   ```

4. Die ausgelesenen Werte gegen die Summen in den PDFs prüfen:

   ```bash
   .venv/bin/python -I scripts/validate.py data
   ```

5. Den Datensatz bauen und die Dateien des Dashboards schreiben:

   ```bash
   .venv/bin/python -I scripts/build_dataset.py raw/pdf/gesamthaushalt-2027-2028.pdf data data/site.json
   ```

   ```bash
   .venv/bin/python -I scripts/export_dashboard.py data/site.json dashboard
   ```

6. Die Einzelplan-Bände gegen den Produktbericht prüfen:

   ```bash
   python3 -I scripts/validate_epl.py dashboard
   ```

## Seite bauen

`build_site.py` erzeugt aus `dashboard/` eine statische Seite in `site/`. Die Seite braucht keinen Server-Code. d3 liegt in `dashboard/vendor/` und wird mitkopiert.

```bash
python3 -I scripts/build_site.py dashboard site
```

Um die Seite lokal anzusehen, starten Sie einen Webserver im Ordner `site/`:

```bash
python3 -I -m http.server 8766 --bind 127.0.0.1 --directory site
```

## Deploy

`site/` ist eine Sammlung statischer Dateien. Jeder Webserver kann sie ausliefern. Um sie auf einen eigenen Server zu kopieren, tragen Sie Host und Benutzer in `~/.ssh/config` ein und nutzen Sie rsync:

```bash
rsync -az --delete site/ "$DEPLOY_HOST:$DEPLOY_PATH/"
```

Tragen Sie Server-Adressen und Benutzernamen nie in dieses Repository ein.

## Lizenz

- Code: MIT, siehe `LICENSE`
- d3 (`dashboard/vendor/d3.min.js`): ISC, siehe `dashboard/vendor/LICENSE-d3.txt`
- Daten: ausgelesen aus den Haushaltsplänen der Freien und Hansestadt Hamburg. Die Rechte an den Originaldokumenten liegen bei der Freien und Hansestadt Hamburg.
