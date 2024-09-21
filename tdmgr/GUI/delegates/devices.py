from dataclasses import dataclass
from typing import List, Optional, Union

from PyQt5.QtCore import QModelIndex, QPoint, QRect, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPalette, QPen, QPixmap
from PyQt5.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from tdmgr.GUI.common import (
    ARROW_DN,
    ARROW_UP,
    DARKGRAY,
    GAP,
    GREEN,
    ICON_SIZE,
    RECT_ADJUSTMENT,
    RECT_HALFSIZE,
    RECT_PADDING,
    RECT_SIZE,
    RECT_SPACING,
    ROW_HEIGHT,
    RSSI_FULL,
    RSSI_GOOD,
    RSSI_LOW,
    RSSI_MEDIUM,
    SizeMode,
)
from tdmgr.models.roles import DeviceRoles
from tdmgr.tasmota.common import TasmotaColor
from tdmgr.tasmota.device import Relay, Shutter


@dataclass
class RectSpacing:
    v: int = 3
    h: int = 3


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


class ControlsPainter:
    def __init__(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex,
        painter: QPainter,
        size_mode: SizeMode = SizeMode.FULL,
    ):
        self.option = option
        self.index = index
        self.p = painter
        self.size_mode = size_mode

        self.x = option.rect.right() - GAP
        self.y = option.rect.top() + (option.rect.height() - RECT_SIZE.height()) // 2

        self.relays = index.data(DeviceRoles.PowerRole)
        self.shutters = index.data(DeviceRoles.ShuttersRole)
        self.color = index.data(DeviceRoles.ColorRole)

        self.relays_rect = None
        self.shutters_rect = None

        palette = QPalette()
        self.hltext_pen = QPen(palette.color(QPalette.HighlightedText))

        self.calculate_rects()

    def calculate_rects(self):
        if self.relays:
            expand_width = 0
            if self.color and self.size_mode != SizeMode.MINIMAL:
                if self.color.SO68 == 1:
                    expand_width = RECT_HALFSIZE.width() * len(self.color.channels)
                else:
                    expand_width = RECT_HALFSIZE.width() * len(self.color.dimmers)

            self.relays_rect = self.calculate_control_rect(self.relays, expand_width=expand_width)

        if self.shutters:
            self.shutters_rect = self.calculate_control_rect(self.shutters, short_prefix="SHT")

    def get_item_name_width(self, name) -> int:
        bounding_width = self.option.fontMetrics.boundingRect(name).width() + RECT_PADDING
        if bounding_width < RECT_SIZE.width():
            return RECT_SIZE.width()
        return bounding_width

    def calculate_control_rect(
        self,
        controls: List[Union[Relay, Shutter]],
        short_prefix: str = "",
        expand_width: int = 0,
    ) -> QRect:
        if self.size_mode == SizeMode.MINIMAL:
            width = len(controls) * RECT_HALFSIZE.width()
        else:
            width = sum(
                [
                    self.get_item_name_width(
                        f"{short_prefix}{c.idx}" if self.size_mode == SizeMode.SHORT else c.name
                    )
                    for c in controls
                ]
            )
            width += expand_width
        width += RECT_SPACING.width() * (len(controls) - 1)

        x = self.x - (width + GAP)
        rect = QRect(QPoint(x, self.y), QSize(width, RECT_SIZE.height()))
        self.x = x
        return rect

    def draw_relay_rect(self, rect: QRect, relay: Relay):
        name_rect = QRect(rect)

        if self.color and self.size_mode != SizeMode.MINIMAL:
            name_rect.setWidth(name_rect.width() - RECT_HALFSIZE.width())
            color_rect = QRect(name_rect.topRight() + QPoint(1, 0), RECT_HALFSIZE)
            self.p.drawRect(color_rect)
            color_rect = color_rect.adjusted(*RECT_ADJUSTMENT)

            if self.color.SO68 == 1:
                channel_value = self.color.channels[relay.idx - 1]
                height = int(color_rect.height() / 100 * channel_value)
                color_rect.adjust(0, color_rect.height() - height, 0, 0)
                self.p.fillRect(color_rect, DARKGRAY)

            elif self.color.hsbcolor and relay.idx == 1:
                self.p.fillRect(color_rect, TasmotaColor.fromTasmotaHSB(self.color.hsbcolor))

            elif relay.idx == 2:
                dimmer_value = self.color.dimmers[relay.idx - 1]
                height = int(color_rect.height() / 100 * dimmer_value)
                color_rect.adjust(0, color_rect.height() - height, 0, 0)
                self.p.fillRect(color_rect, DARKGRAY)

        state_fill_rect = name_rect.adjusted(*RECT_ADJUSTMENT)

        self.p.save()
        if relay.state == "ON":
            self.p.setPen(self.hltext_pen)
            self.p.fillRect(state_fill_rect, GREEN)

        if relay.locked:
            padlock_px = QPixmap(":/padlock.png")
            padlock_rect = rect.adjusted(6, 6, -6, -6)
            self.p.drawPixmap(padlock_rect, padlock_px)
        else:
            if self.size_mode != SizeMode.MINIMAL:
                self.p.drawText(
                    name_rect,
                    Qt.AlignCenter,
                    f"{relay.idx}" if self.size_mode == SizeMode.SHORT else relay.name,
                )
        self.p.restore()

        self.p.drawRect(rect)

    def draw_relay_state(self):
        pos_x = self.relays_rect.topLeft()
        for relay in self.relays:
            if self.size_mode == SizeMode.MINIMAL:
                rect_size = RECT_HALFSIZE
            else:
                width = self.get_item_name_width(
                    f"{relay.idx}" if self.size_mode == SizeMode.SHORT else relay.name
                )
                if self.color and self.size_mode != SizeMode.MINIMAL:
                    if self.color.SO68 == 1 or relay.idx <= len(self.color.dimmers):
                        width += RECT_HALFSIZE.width()

                name_size = QSize(width, RECT_SIZE.height())
                rect_size = RECT_SIZE if name_size.width() < RECT_SIZE.width() else name_size

            rect = QRect(pos_x, rect_size)
            self.draw_relay_rect(rect, relay)
            pos_x.setX(pos_x.x() + rect_size.width() + RectSpacing.h)

    def draw_shutter_rect(self, rect: QRect, shutter: Shutter):
        state_rect = rect.adjusted(*RECT_ADJUSTMENT)
        position_rect = QRect(state_rect)

        self.p.save()

        if self.size_mode == SizeMode.MINIMAL:
            position_rect.setHeight(state_rect.height() * shutter.position // 100)
        else:
            position_rect.setWidth(state_rect.width() * shutter.position // 100)

        self.p.fillRect(state_rect, DARKGRAY)
        self.p.setPen(self.hltext_pen)
        if shutter.position > 0:
            self.p.fillRect(position_rect, GREEN)

        if self.size_mode != SizeMode.MINIMAL:
            if self.size_mode == SizeMode.FULL and shutter.direction != 0:
                direction = ARROW_DN if shutter.direction == -1 else ARROW_UP
                text = f"{direction} -> {shutter.target}%"
            else:
                text = f"SHT{shutter.idx}" if self.size_mode == SizeMode.SHORT else shutter.name
            self.p.drawText(rect, Qt.AlignCenter, text)

        self.p.restore()
        self.p.drawRect(rect)

    def draw_shutters_state(self):
        pos_x = self.shutters_rect.topLeft()
        for shutter in self.shutters:
            if self.size_mode == SizeMode.MINIMAL:
                rect_size = RECT_HALFSIZE
            else:
                width = self.get_item_name_width(
                    f"SHT{shutter.idx}" if self.size_mode == SizeMode.SHORT else shutter.name
                )
                name_size = QSize(width, RECT_SIZE.height())
                rect_size = RECT_SIZE if name_size.width() < RECT_SIZE.width() else name_size

            rect = QRect(pos_x, rect_size)
            self.draw_shutter_rect(rect, shutter)
            pos_x.setX(pos_x.x() + rect_size.width() + RectSpacing.h)

    def calculate_color_rect(self):
        if self.size_mode == SizeMode.MINIMAL:
            width = RECT_HALFSIZE.width()

        if self.size_mode == SizeMode.SHORT:
            width = RECT_SIZE.width()

        else:
            width = self.get_item_name_width("100%")

        x = self.x - (width + GAP)
        rect = QRect(QPoint(x, self.y), QSize(width, RECT_SIZE.height()))
        self.x = x
        return rect

    @property
    def width_needed(self) -> int:
        rects = list(filter(lambda c: c is not None, [self.relays_rect, self.shutters_rect]))
        if rects:
            return sum([r.width() for r in rects]) + GAP * (len(rects) - 1)
        return 0

    def paint(self):
        # reset x after rect calculation
        self.x = self.option.rect.right() - GAP

        # draw relay icons
        if self.relays:
            self.draw_relay_state()

        # draw shutter icons
        if self.shutters:
            self.draw_shutters_state()


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
        if self.get_column_name(index) == "Device":
            return QSize(10, ROW_HEIGHT)
        return QStyledItemDelegate().sizeHint(option, index)

    def get_used_width(self, option, index) -> int:
        return sum([self.get_devicename_width(option, index), self.get_alerts_width(option, index)])

    @staticmethod
    def get_devicename_width(option, index) -> int:
        return GAP + ICON_SIZE.width() + GAP + QStyledItemDelegate().sizeHint(option, index).width()

    def get_alerts_width(self, option, index) -> int:
        if alerts := self.get_alerts_text(index):
            return (
                GAP + option.fontMetrics.boundingRect(option.rect, Qt.AlignCenter, alerts).width()
            )
        return 0

    @staticmethod
    def get_alerts_text(index) -> Optional[str]:
        alerts = []
        if index.data(DeviceRoles.RestartReasonRole) == "Exception":
            alerts.append("Exception")
        if "minimal" in index.data(DeviceRoles.FirmwareRole).lower():
            alerts.append("Minimal")
        if alerts:
            return " | ".join(alerts)

    @staticmethod
    def get_column_name(index):
        return index.model().sourceModel().columns[index.column()]

    def paint(self, p: QPainter, option: QStyleOptionViewItem, index):
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

            device_rect = option.rect.adjusted(2 * GAP + ICON_SIZE.width(), 3, 0, 0)
            p.save()
            if not index.data(DeviceRoles.LWTRole):
                p.setFont(self.font_italic)
                p.setPen(self.mid_pen)

            p.drawText(device_rect, Qt.AlignVCenter | Qt.AlignLeft, index.data())
            p.restore()

            if alerts := self.get_alerts_text(index):
                p.save()

                alerts_width = self.get_alerts_width(option, index)

                exc_rect = QRect(
                    self.get_devicename_width(option, index), y, alerts_width, RECT_SIZE.height()
                )

                if selected:
                    pen = self.hltext_pen
                else:
                    pen = QPen(QColor("red"))
                p.setPen(pen)

                p.drawRect(exc_rect)
                p.drawText(exc_rect, Qt.AlignCenter, alerts)
                p.restore()

            c = None
            for size_mode in [SizeMode.FULL, SizeMode.SHORT, SizeMode.MINIMAL]:
                _c = ControlsPainter(option, index, p, size_mode)
                if option.rect.width() - self.get_used_width(option, index) - _c.width_needed > 0:
                    c = _c
                    break
            if c:
                c.paint()

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

        px_y = option.rect.y() + (option.rect.height() - ICON_SIZE.height()) // 2
        px_rect = QRect(QPoint(option.rect.x() + GAP, px_y), ICON_SIZE)
        p.drawPixmap(px_rect, px.scaled(ICON_SIZE))
        p.restore()

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
