from enum import Enum, auto

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor, QPainter, QPixmap

GREEN = QColor("#8BC34A")
DARKGRAY = QColor("darkgray")

COLD = QColor("#eeffff")  # 6500k in RGB (White)
WARM = QColor("#ff8811")  # 2500k in RGB (Warm Yellow)

RSSI_LOW = QColor("#e74c3c")
RSSI_MEDIUM = QColor("#ec8826")
RSSI_GOOD = QColor("#f1c40f")
RSSI_FULL = QColor("#8bc34a")

ARROW_UP = "▲"
ARROW_DN = "▼"

GAP = 2
ICON_SIZE = QSize(24, 24)
RECT_ADJUSTMENT = (2, 2, -1, -1)
RECT_PADDING = 10
RECT_SIZE = QSize(24, 24)
RECT_HALFSIZE = QSize(12, 24)
RECT_SPACING = QSize(3, 3)
ROW_HEIGHT = RECT_SIZE.height() + 2 * GAP + 1


class SizeMode(Enum):
    FULL = auto()
    SHORT = auto()
    MINIMAL = auto()


def make_relay_pixmap(label, filled=True):
    px = QPixmap(RECT_SIZE)
    px_rect = px.rect()
    p = QPainter(px)

    if filled:
        pen_color = Qt.white
        fill_color = GREEN
    else:
        pen_color = GREEN
        fill_color = Qt.white
    p.setPen(pen_color)
    p.fillRect(px_rect, fill_color)

    if not filled:
        p.drawRect(px_rect.adjusted(0, 0, -1, -1))

    p.drawText(px_rect, Qt.AlignCenter, f"{label}")
    p.end()
    return px
