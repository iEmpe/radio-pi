"""Light radio player theme — 480×320 (Waveshare LCD)."""

SCREEN_W = 480
SCREEN_H = 320

# Background & surfaces
BG = "#FFFFFF"
BG_SOFT = "#F5F5F7"
BORDER = "#E8E8EC"
TEXT = "#1A1A1A"
TEXT_MUTED = "#333333"
TEXT_LIGHT = "#4A4A4A"
TEXT_DIM = "#555555"

# Accent gradient (equalizer panel)
GRAD_TOP = "#9B6DFF"
GRAD_BOT = "#E878C8"

# Network status
NET_ACTIVE = "#34C759"
NET_INACTIVE = "#1A1A1A"

# Controls
ACCENT = "#9B6DFF"
BTN_BG = "#F0F0F4"
BTN_HOVER = "#E4E4EA"

# Monospace UI — family name resolved at runtime from bundled .ttf (see app/ui/fonts.py)
FONT_UI = "JetBrains Mono"
FONT_MONO = FONT_UI

# Pixel-aligned sizes for 480×320 LCD (regular weight everywhere except clock)
FONT_SIZE_TINY = 9
FONT_SIZE_SMALL = 10
FONT_SIZE_MED = 11
FONT_SIZE_LARGE = 14
FONT_SIZE_CLOCK = 26
CLOCK_TRACKING = 3

HEADER_H = 62
STATION_ROW_H = 88
VOLUME_H = 34
CONTROLS_H = 44
EQUALIZER_H = SCREEN_H - HEADER_H - STATION_ROW_H - VOLUME_H - CONTROLS_H

# Legacy aliases (network overlay, keyboard)
IPOD_BG = BG_SOFT
IPOD_HEADER_TOP = "#E8E4F8"
IPOD_HEADER_BOT = BG
IPOD_SELECT = ACCENT
IPOD_TEXT = TEXT
IPOD_TEXT_SEL = "#FFFFFF"
IPOD_LINE = BORDER
BAR_TOP = BG_SOFT
BAR_BOT = BORDER
BAR_TEXT = TEXT
