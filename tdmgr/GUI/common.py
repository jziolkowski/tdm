from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor, QPainter, QPixmap

GREEN = QColor("#8BC34A")

RSSI_LOW = QColor("#e74c3c")
RSSI_MEDIUM = QColor("#ec8826")
RSSI_GOOD = QColor("#f1c40f")
RSSI_FULL = QColor("#8bc34a")

ARROW_UP = '▲'
ARROW_DN = '▼'

RECT_SIZE = QSize(24, 24)


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

    p.drawText(px_rect, Qt.AlignCenter, f'{label}')
    p.end()
    return px
