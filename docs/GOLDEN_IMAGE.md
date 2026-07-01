# Obraz złoty (golden image) — Radio Pi

Gotowy obraz karty SD z pełnym systemem: Raspberry Pi OS Bullseye, LCD Waveshare, Radio Pi, VLC, WiFi/BT, stacje i ustawienia.

## Generowanie obrazu (na działającym Pi)

**Wymagania:** pendrive ≥ 16 GB sformatowany (exFAT/FAT32) zamontowany w `/media/pi/NAZWA`

```bash
# Na Raspberry Pi (przez SSH)
sudo OUTPUT_DIR=/media/pi/USB /opt/radio-pi/build/export-golden-image.sh
```

Skrypt:
1. Zatrzymuje `radio-ui` na chwilę (sync plików)
2. Robi `dd` całej karty `/dev/mmcblk0`
3. Kompresuje do `radio-pi-golden-YYYYMMDD-HHMM.img.xz`
4. Tworzy plik `.manifest.txt` ze SHA256 i opisem
5. Uruchamia radio ponownie

**Czas na Pi 3:** ok. 30–90 minut (zależy od pendrive i rozmiaru karty).

## Pobranie na Mac

```bash
scp pi@192.168.0.81:~/radio-pi-images/radio-pi-golden-*.img.xz .
scp pi@192.168.0.81:~/radio-pi-images/radio-pi-golden-*.manifest.txt .
```

## Flash na nową kartę SD

1. **Raspberry Pi Imager** → *Choose OS* → **Use custom**
2. Wybierz plik `.img.xz` (Imager rozpakuje automatycznie)
3. Wybierz kartę SD → *Write*
4. Włóż do Pi 3 + LCD, zasilanie

## Zawartość obrazu (stan docelowy)

| Komponent | Opis |
|-----------|------|
| OS | Raspberry Pi OS Legacy Bullseye 32-bit + desktop |
| LCD | Waveshare 3.2" (`waveshare32b`, 480×320) |
| Radio Pi | `/opt/radio-pi`, autostart `radio-ui.service` |
| Stacje | 27 stacji DnB + PL + międzynarodowe |
| VLC | Pełne kodeki + skrót pendrive na pulpicie |
| Sieć | NetworkManager, WiFi 2.4 GHz, Bluetooth |
| Pamięć | Ostatnia stacja (`last_station.json`) |

## Bezpieczeństwo

Obraz złoty **może zawierać**:
- Hasło WiFi zapisane w NetworkManager
- Klucze SSH użytkownika `pi`
- Ostatnio graną stację

Po sklonowaniu na nowe urządzenie:
```bash
passwd
# opcjonalnie: zmień WiFi w UI lub nmcli
```

## Weryfikacja checksum

```bash
shasum -a 256 radio-pi-golden-*.img.xz
# porównaj z wartością w pliku .manifest.txt
```

## Uwaga

Pliki `.img.xz` **nie są** w repozytorium Git (za duże). Generuj lokalnie skryptem `build/export-golden-image.sh`.
