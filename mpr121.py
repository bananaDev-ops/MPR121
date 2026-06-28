"""
mpr121.py — Eigenständiger MPR121 Touch-Sensor-Treiber für den Raspberry Pi.

Direkter I²C-Registerzugriff über smbus2 — keine fertige MPR121-Library nötig.
Liest die 12 kapazitiven Elektroden, mit konfigurierbaren Touch/Release-Schwellen
und schneller Baseline-Rekalibrierung (damit dauerhaft angeschlossene leitfähige
Objekte nicht als Dauer-Touch zählen).

Banana-Feature: Hängt man ein leitfähiges Objekt (z.B. eine Banane) an eine
Elektrode, wird es nach kurzer Zeit zur neuen Ruhe-Baseline — nur aktives
Berühren löst dann aus.

------------------------------------------------------------------------------
Copyright (C) 2026  BananaDev
Lizenziert unter der BANANA PUBLIC LICENSE v1.0 (siehe LICENSE).
Kurz:  - kommerzielle Nutzung -> Issue mit Foto von 7 nummerierten Bananen
       - private/edu Nutzung   -> eine gezeichnete Banane
Dieses Programm wird OHNE JEGLICHE GARANTIE bereitgestellt.
------------------------------------------------------------------------------

Abhängigkeit:  smbus2  (MIT-Lizenz)   ->  pip install smbus2
Hardware:      Raspberry Pi mit aktiviertem I²C, MPR121 an Bus 1.
Verkabelung:   VCC->3,3V | GND->GND | SDA->GPIO2 (Pin3) | SCL->GPIO3 (Pin5)
"""

import time

try:
    import smbus2
    _HAS_SMBUS = True
except ImportError:
    _HAS_SMBUS = False


# --- MPR121-Register (aus dem NXP/Freescale-Datenblatt) ---
_TOUCH_STATUS   = 0x00   # 2 Bytes: Bit 0-11 = Touch-Status der Elektroden
_THRESH_TOUCH   = 0x41   # Touch-Schwelle Elektrode 0 (danach je +2 pro Elektrode)
_THRESH_RELEASE = 0x42   # Release-Schwelle Elektrode 0
_ELE_CFG        = 0x5E   # Electrode Config: aktive Elektroden + Run/Calibration
_SOFT_RESET     = 0x80


class MPR121:
    """MPR121 kapazitiver Touch-Controller über I²C.

    Beispiel:
        sensor = MPR121()                 # Standard: Adresse 0x5A, Bus 1
        while True:
            print(sensor.touched())       # z.B. {0, 3}
            time.sleep(0.05)
    """

    def __init__(self, address=0x5A, bus_num=1,
                 touch_threshold=20, release_threshold=10,
                 fast_recalibration=True):
        """
        address            : I²C-Adresse (0x5A Standard bei offenem ADD-Pin;
                             0x5B/0x5C/0x5D je nach ADD-Verdrahtung)
        bus_num            : I²C-Bus (auf dem Pi üblicherweise 1)
        touch_threshold    : Schwelle ab der eine Berührung erkannt wird (höher
                             = unempfindlicher; gut gegen "Objekt = Dauer-Touch")
        release_threshold  : Schwelle für Loslassen (< touch_threshold = Hysterese)
        fast_recalibration : True -> Baseline folgt angeschlossenen Objekten zügig
        """
        if not _HAS_SMBUS:
            raise RuntimeError("smbus2 fehlt — bitte 'pip install smbus2'")
        self.address = address
        self.touch_threshold = touch_threshold
        self.release_threshold = release_threshold
        self.fast_recalibration = fast_recalibration
        self._bus = smbus2.SMBus(bus_num)
        self._init_sensor()

    def _w(self, reg, val):
        self._bus.write_byte_data(self.address, reg, val)

    def _init_sensor(self):
        # 1) Soft-Reset
        self._w(_SOFT_RESET, 0x63)
        time.sleep(0.01)
        # 2) Stop-Modus (ELE_CFG = 0), nur dann darf konfiguriert werden
        self._w(_ELE_CFG, 0x00)

        # 3) Baseline-Filter (MHD/NHD/NCL/FDL), Abschnitte:
        #    Rising  (Sektion A) = Baseline steigt, wenn Objekt/Finger weg geht
        #    Falling (Sektion B) = Baseline fällt, wenn Kapazität dazukommt
        #    Touched (Sektion C) = Verhalten während Berührung
        if self.fast_recalibration:
            # Falling schnell -> dauerhaft angeschlossenes Objekt wird zügig
            # zur neuen Ruhe-Baseline (kein Dauer-Touch durch Objekt-Anwesenheit).
            cfg = [
                (0x2B, 0x01), (0x2C, 0x01), (0x2D, 0x10), (0x2E, 0x20),  # rising
                (0x2F, 0x01), (0x30, 0x05), (0x31, 0x02), (0x32, 0x00),  # falling
                (0x33, 0x00), (0x34, 0x00), (0x35, 0x00),                # touched
            ]
        else:
            cfg = [
                (0x2B, 0x01), (0x2C, 0x01), (0x2D, 0x00), (0x2E, 0x00),
                (0x2F, 0x01), (0x30, 0x01), (0x31, 0xFF), (0x32, 0x02),
                (0x33, 0x00), (0x34, 0x00), (0x35, 0x00),
            ]
        for reg, val in cfg:
            self._w(reg, val)

        # 4) Touch/Release-Schwellen für alle 12 Elektroden
        for e in range(12):
            self._w(_THRESH_TOUCH + e * 2, self.touch_threshold)
            self._w(_THRESH_RELEASE + e * 2, self.release_threshold)

        # 5) Globale Filter-Config (Standardwerte aus dem Datenblatt)
        self._w(0x5C, 0x10)
        self._w(0x5D, 0x20)

        # 6) Run-Modus: 12 Elektroden aktiv (0x0C) + Auto-Baseline-Tracking (0x80)
        self._w(_ELE_CFG, 0x8C)
        time.sleep(0.01)

    def recalibrate(self):
        """Neu initialisieren -> aktuelle Kapazität (mit angeschlossenen Objekten)
        wird zur neuen Ruhe-Baseline. Nützlich, falls eine Elektrode 'klebt'."""
        self._init_sensor()

    def touched(self):
        """Set der aktuell berührten Elektroden (0-11). Leer, wenn keine."""
        lsb = self._bus.read_byte_data(self.address, _TOUCH_STATUS)
        msb = self._bus.read_byte_data(self.address, _TOUCH_STATUS + 1)
        bits = (msb << 8) | lsb
        return {e for e in range(12) if bits & (1 << e)}

    def is_touched(self, electrode):
        """True, wenn die angegebene Elektrode (0-11) gerade berührt wird."""
        return electrode in self.touched()

    def close(self):
        """I²C-Bus schließen."""
        self._bus.close()


# Minimal-Demo, wenn direkt ausgeführt: python3 mpr121.py
if __name__ == "__main__":
    sensor = MPR121()
    print("MPR121 bereit. Elektroden berühren (Strg+C zum Beenden)...")
    try:
        prev = set()
        while True:
            now = sensor.touched()
            if now != prev:
                print("berührt:", sorted(now) if now else "—")
                prev = now
            time.sleep(0.03)
    except KeyboardInterrupt:
        sensor.close()
        print("\nTschüss! 🍌")
