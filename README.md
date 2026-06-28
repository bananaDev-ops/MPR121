# 🍌 mpr121-pi-driver

Ein eigenständiger, leichtgewichtiger **MPR121**-Touch-Sensor-Treiber für den
**Raspberry Pi** — direkter I²C-Registerzugriff über `smbus2`, ohne fertige
MPR121-Library.

Entstanden für ein Bastelprojekt („Touch Arcade" — Spiele, die man mit Bananen
statt Tasten steuert). Der Clou: **angeschlossene leitfähige Objekte** (Obst,
Münzen, Knete) werden automatisch zur Ruhe-Baseline — nur aktives Berühren
löst aus.

## Features

- 12 kapazitive Elektroden auslesen (`touched()` → Set der berührten Pads)
- Konfigurierbare **Touch/Release-Schwellen** (mit Hysterese)
- **Schnelle Baseline-Rekalibrierung**: ein dauerhaft angeschlossenes Objekt
  wird zügig zur neuen „Ruhe" → kein Dauer-Touch durch bloße Anwesenheit
- `recalibrate()` als Notnagel, falls eine Elektrode „klebt"
- Keine schweren Abhängigkeiten — nur `smbus2`

## Installation

```bash
# I²C am Pi aktivieren (einmalig)
sudo raspi-config nonint do_i2c 0

# Abhängigkeit
pip install smbus2

# Treiber: einfach mpr121.py ins Projekt kopieren
```

## Verkabelung (MPR121 → Raspberry Pi)

| MPR121 | Raspberry Pi |
|--------|--------------|
| VCC    | 3,3V         |
| GND    | GND          |
| SDA    | GPIO2 (Pin 3)|
| SCL    | GPIO3 (Pin 5)|

> ⚠️ VCC an **3,3V**, NICHT 5V — der Pi-I²C verträgt nur 3,3V.

Prüfen, ob der Sensor erkannt wird:
```bash
sudo i2cdetect -y 1     # sollte 0x5a zeigen
```

## Benutzung

```python
from mpr121 import MPR121
import time

sensor = MPR121()                 # Adresse 0x5A, Bus 1, sinnvolle Defaults

while True:
    pads = sensor.touched()       # z.B. {0, 3}
    if pads:
        print("berührt:", sorted(pads))
    time.sleep(0.05)
```

Oder direkt als Demo:
```bash
python3 mpr121.py
```

### Parameter

```python
MPR121(
    address=0x5A,            # 0x5B/0x5C/0x5D je nach ADD-Pin
    bus_num=1,
    touch_threshold=20,      # höher = unempfindlicher
    release_threshold=10,    # < touch_threshold (Hysterese)
    fast_recalibration=True, # Objekte werden zur Baseline
)
```

## 🍌 Lizenz — BANANA PUBLIC LICENSE v1.0

Dieses Projekt steht unter der **Banana Public License** (eine GPL-artige
Copyleft-Lizenz mit Frucht-Pflicht). Kurzfassung — bei Nutzung gilt:

- **Kommerzielle Nutzung:** Erstelle ein Issue mit einem **Foto von 7 echten
  Bananen**, jede einzeln mit Zetteln/Aufklebern **von 1 bis 7 nummeriert**.
- **Private / Bildungs-Nutzung:** Statt der 7 Bananen reicht **eine
  selbstgezeichnete Banane** (als Issue, im Fork-README oder bei den Dateien).

Außerdem (Copyleft): Abgeleitete Werke müssen wieder unter der Banana Public
License stehen und den Quellcode offenlegen.

Volltext siehe [LICENSE](LICENSE). Bereitgestellt ohne jegliche Garantie.

## Abhängigkeiten & deren Lizenzen

| Paket   | Lizenz | Zweck            |
|---------|--------|------------------|
| smbus2  | MIT    | I²C-Transport    |

Keine weiteren Laufzeit-Abhängigkeiten.
