from dataclasses import dataclass
from typing import Tuple

from PyQt5.QtCore import QPoint, QRect, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPalette, QPen, QPixmap
from PyQt5.QtWidgets import QStyle, QStyledItemDelegate

from tdmgr.GUI.common import (
    ARROW_DN,
    ARROW_UP,
    GREEN,
    RECT_SIZE,
    RSSI_FULL,
    RSSI_GOOD,
    RSSI_LOW,
    RSSI_MEDIUM,
)
from tdmgr.models.roles import DeviceRoles


@dataclass
class RectSpacing:
    v: int = 3
    h: int = 3


RECT_ADJUSTMENT = (2, 2, -1, -1)
SHUTTER_RECT_SIZE = QSize(RECT_SIZE.width() * 2 + RectSpacing.h * 2, RECT_SIZE.height())


def get_pixmap_for_rssi(rssi: int) -> QPixmap:
    PIXMAP_LOW = QPixmap(":/signal1.png")
    PIXMAP_MEDIUM = QPixmap(":/signal2.png")
    PIXMAP_GOOD = QPixmap(":/signal3.png")
    PIXMAP_FULL = QPixmap(":/signal4.png")

    if 0 < rssi < 35:
        return PIXMAP_LOW
    if rssi < 50:
        return PIXMAP_MEDIUM
    if rssi < 85:
        return PIXMAP_GOOD
    if rssi >= 85:
        return PIXMAP_FULL


class DeviceDelegate(QStyledItemDelegate):
    def __init__(self):
        super(DeviceDelegate, self).__init__()

        self.font_8pt = QFont()
        self.font_8pt.setPointSize(8)

        self.font_italic = QFont()
        self.font_italic.setItalic(True)

        self.devicename_rect_h = 0

        palette = QPalette()
        self.mid_pen = QPen(palette.color(QPalette.Mid))
        self.text_pen = QPen(palette.color(QPalette.Text))
        self.hltext_pen = QPen(palette.color(QPalette.HighlightedText))

        self.rssi_offline = QPixmap(":/signal0.png")

    def sizeHint(self, option, index):
        if self.get_column_name(index) in ('Device', 'Power'):

            def get_relays_height():
                if relay_data := index.data(DeviceRoles.PowerRole):
                    return 6 + self.get_relays_rect_size(relay_data).height()
                return 0

            hint_height = max(28, get_relays_height())
            return QSize(QStyledItemDelegate().sizeHint(option, index).width(), hint_height)
        return QStyledItemDelegate().sizeHint(option, index)

    @staticmethod
    def get_layout(data, max_cols=8) -> Tuple[int, int]:
        key_count = len(data.keys())
        rows = key_count // max_cols if key_count % max_cols == 0 else key_count // max_cols + 1
        cols = key_count // rows
        return cols, rows

    def get_relays_rect_size(self, relay_data) -> QSize:
        cols, rows = self.get_layout(relay_data)
        return QSize(
            cols * RECT_SIZE.width() + (cols - 1) * RectSpacing.h,
            rows * RECT_SIZE.height() + (rows - 1) * RectSpacing.v,
        )

    @staticmethod
    def get_shutters_rect_size(shutter_data) -> QSize:
        cols = len(shutter_data.keys())
        return QSize(
            cols * SHUTTER_RECT_SIZE.width() + (cols - 1) * RectSpacing.h,
            SHUTTER_RECT_SIZE.height(),
        )

    @staticmethod
    def get_column_name(index):
        return index.model().sourceModel().columns[index.column()]

    def draw_relay_rect(self, p: QPainter, rect: QRect, relay: int, state: str):
        inner_rect = rect.adjusted(*RECT_ADJUSTMENT)

        p.save()
        if state == "ON":
            p.setPen(self.hltext_pen)
            p.fillRect(inner_rect, GREEN)

        p.drawText(rect, Qt.AlignCenter, f'{relay}')
        p.restore()

        p.drawRect(rect)

    @staticmethod
    def get_item_rect(option, x_pos, size: QSize):
        return QRect(
            QPoint(
                x_pos - size.width(),
                option.rect.top() + (option.rect.height() - size.height()) // 2,
            ),
            size,
        )

    def paint(self, p: QPainter, option, index):
        y = option.rect.y() + (option.rect.height() - RECT_SIZE.height()) // 2
        selected = option.state & QStyle.State_Selected

        if selected:
            color = option.palette.highlight()
            pen = self.hltext_pen
        else:
            color = option.palette.alternateBase() if index.row() % 2 else option.palette.base()
            pen = self.text_pen
        p.fillRect(option.rect, color)
        p.setPen(pen)

        col_name = self.get_column_name(index)

        if col_name == "Device":
            # draw signal strength icon
            self.draw_rssi_pixmap(index, option, p)

            device_rect = option.rect.adjusted(30, 2, 0, 0)
            p.save()
            if not index.data(DeviceRoles.LWTRole):
                p.setFont(self.font_italic)
                p.setPen(self.mid_pen)

            p.drawText(device_rect, Qt.AlignVCenter | Qt.AlignLeft, index.data())
            p.restore()

            alerts = []
            if index.data(DeviceRoles.RestartReasonRole) == "Exception":
                alerts.append("Exception")

            if "minimal" in index.data(DeviceRoles.FirmwareRole).lower():
                alerts.append("Minimal")

            if alerts:
                message = " | ".join(alerts)
                p.save()

                alerts_width = p.boundingRect(option.rect, Qt.AlignCenter, message).width() + 8
                device_name_width = (
                    40 + p.boundingRect(option.rect, Qt.AlignCenter, index.data()).width()
                )

                exc_rect = QRect(device_name_width, y, alerts_width, RECT_SIZE.height())
                if selected:
                    pen = self.hltext_pen
                else:
                    pen = QPen(QColor("red"))
                p.setPen(pen)

                p.drawRect(exc_rect)
                p.drawText(exc_rect, Qt.AlignCenter, message)
                p.restore()

            # draw relay icons
            x_pos = option.rect.right() - 5
            if relay_data := index.data(DeviceRoles.PowerRole):
                relays_rect_size = self.get_relays_rect_size(relay_data)
                relays_rect = self.get_item_rect(option, x_pos, relays_rect_size)
                self.draw_relay_state(p, relays_rect, relay_data)
                x_pos = relays_rect.left() - 5

            if shutter_data := index.data(DeviceRoles.ShuttersRole):
                shutter_rect_size = self.get_shutters_rect_size(shutter_data)
                shutters_rect = self.get_item_rect(option, x_pos, shutter_rect_size)

                if shutter_pos_data := index.data(DeviceRoles.ShutterPositionsRole):
                    self.draw_shutters_state(p, shutters_rect, shutter_pos_data)
                x_pos = shutters_rect.left() - 5

            # draw color frame
            if color_data := index.data(DeviceRoles.ColorRole):
                if (color := color_data.get("Color")) and not color_data.get(68):
                    rect = QRect(x_pos - 53, y, 50, RECT_SIZE.height())

                    inner_rect = rect.adjusted(*RECT_ADJUSTMENT)
                    p.fillRect(inner_rect, QColor(f"#{color[:6]}"))
                    p.drawRect(rect)

                    if dimmer := color_data.get("Dimmer"):
                        p.drawText(rect, Qt.AlignCenter, f"{dimmer}")

        elif col_name == "RSSI":
            self.draw_rssi_rect(p, option.rect, index)

        else:
            QStyledItemDelegate.paint(self, p, option, index)

    def draw_rssi_pixmap(self, index, option, p):
        p.save()
        px = self.rssi_offline
        if index.data(DeviceRoles.LWTRole):
            rssi = index.data(DeviceRoles.RSSIRole)
            px = get_pixmap_for_rssi(rssi)

        px_y = option.rect.y() + (option.rect.height() - 24) // 2
        px_rect = QRect(option.rect.x() + 2, px_y, 24, 24)
        p.drawPixmap(px_rect, px.scaled(24, 24))
        p.restore()

    def draw_relay_state(self, p: QPainter, target_rect: QRect, relay_data: dict):
        cols, _ = self.get_layout(relay_data)
        relay_row, relay_col = 0, 0
        for relay, relay_state in relay_data.items():
            rect = QRect(self.get_point(target_rect, RECT_SIZE, relay_col, relay_row), RECT_SIZE)
            self.draw_relay_rect(p, rect, relay, relay_state)
            relay_col += 1
            if relay_col == cols:
                relay_row += 1
                relay_col = 0

    @staticmethod
    def get_point(target_rect: QRect, item_size: QSize, col: int, row: int = 0):
        return QPoint(
            target_rect.x() + (item_size.width() + RectSpacing.h) * col,
            target_rect.y() + RectSpacing.v * row + row * item_size.height(),
        )

    def draw_shutters_state(self, p: QPainter, target_rect: QRect, shutter_pos_data: dict):
        cols, _ = self.get_layout(shutter_pos_data)
        shutter_col = 0
        for shutter, shutter_state in shutter_pos_data.items():
            rect = QRect(
                self.get_point(target_rect, SHUTTER_RECT_SIZE, shutter_col), SHUTTER_RECT_SIZE
            )
            title_rect = QRect(rect)
            title_rect.setHeight(RECT_SIZE.height())

            direction = shutter_state['Direction']
            arrow_direction = {-1: ARROW_DN, 1: ARROW_UP}

            position = (
                'CLS'
                if shutter_state['Position'] == 0
                else 'OPN' if shutter_state['Position'] == 100 else shutter_state['Position']
            )

            if direction != 0:
                p.save()
                p.setPen(self.hltext_pen)
                p.fillRect(title_rect, GREEN)
                p.drawText(title_rect, Qt.AlignCenter, f"{arrow_direction[direction]}  {position}")
                p.restore()
            else:
                p.drawText(title_rect, Qt.AlignCenter, f'SHT{shutter} {position}')
            for r in [title_rect, rect]:
                p.drawRect(r)

            shutter_col += 1

    def draw_rssi_rect(self, p: QPainter, rect, index):
        if index.data():
            rect = rect.adjusted(*RECT_ADJUSTMENT)
            rssi = index.data(DeviceRoles.RSSIRole)
            pen = QPen(p.pen())

            p.save()

            if 0 < rssi < 35:
                color = RSSI_LOW

            elif rssi < 50:
                color = RSSI_MEDIUM

            elif rssi < 85:
                color = RSSI_GOOD

            elif rssi >= 85:
                color = RSSI_FULL

            p.fillRect(rect.adjusted(*RECT_ADJUSTMENT), color)
            p.drawText(rect, Qt.AlignCenter, str(rssi))

            pen.setColor(QColor("#cccccc"))
            p.setPen(pen)
            p.drawRect(rect)
            p.restore()
