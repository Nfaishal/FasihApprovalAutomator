#!/usr/bin/env python3
"""
FASIH-SM Approval Automator
================================================================
Requirements:
    pip install PyQt6 playwright
    playwright install chromium
"""

import sys, threading, time, math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QGraphicsDropShadowEffect, QComboBox
)
from PyQt6.QtCore  import Qt, QTimer, QRectF, QPointF, pyqtSignal, pyqtSlot
from PyQt6.QtGui   import (
    QPainter, QColor, QLinearGradient, QRadialGradient,
    QPen, QBrush, QFont, QPainterPath, QPalette,
)
from playwright.sync_api import sync_playwright

_DISPLAY = "Segoe UI Variable Display"
_TEXT    = "Segoe UI Variable Text"
_FB      = "Segoe UI"
_MONO    = "Cascadia Code"
_MONO_FB = "Consolas"

def F(fam, fb, sz, bold=False, italic=False):
    f = QFont(fam, sz)
    if not f.exactMatch(): f = QFont(fb, sz)
    f.setBold(bold); f.setItalic(italic)
    return f

def FD(sz, bold=False, italic=False): return F(_DISPLAY, _FB, sz, bold, italic)
def FT(sz, bold=False, italic=False): return F(_TEXT,    _FB, sz, bold, italic)
def FM(sz):                            return F(_MONO, _MONO_FB, sz)

# Light-mode palette
class G:
    # Backgrounds
    BG_WIN   = QColor(245, 246, 250)   
    BG_PANEL = QColor(255, 255, 255)  

    # Text
    TEXT     = QColor( 22,  24,  35)   
    SUB_TEXT = QColor(110, 115, 135)  

    # Semantic
    ACCENT   = QColor( 37, 99,  235)   # blue-600
    OK       = QColor( 22, 163,  74)   # green-600
    ERR      = QColor(220,  38,  38)   # red-600
    WARN     = QColor(202, 138,   4)   # amber-600
    INFO     = QColor( 37,  99, 235)   # same as accent

    GLASS_BASE  = (255, 255, 255, 145)   
    GLASS_HI    = (255, 255, 255, 210)  
    GLASS_EDGE  = (200, 210, 230,  90)  
    GLASS_INNER = (230, 235, 245,  55)  

    # Aurora blobs pastel / washed out for light bg
    BLOBS = [
        (0.10, 0.12, 0.55,  99, 149, 255,  55, 2.8e-4, 2.1e-4),   
        (0.88, 0.08, 0.48,  99, 217, 200,  42, 2.3e-4, 3.2e-4), 
        (0.50, 0.88, 0.52, 167, 139, 255,  38, 2.0e-4, 2.6e-4),   
        (0.80, 0.78, 0.40, 255, 178, 120,  32, 3.0e-4, 2.0e-4),   
        (0.30, 0.50, 0.38, 120, 200, 255,  28, 2.6e-4, 2.9e-4),  
    ]


# Aurora Background
class AuroraBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def _tick(self): self._t += 1; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        # White base
        p.fillRect(self.rect(), QColor(248, 249, 253))

        t = self._t
        for i, (bx, by, br, r, g, b, a, fx, fy) in enumerate(G.BLOBS):
            cx  = (bx + math.sin(t * fx + i * 1.4) * 0.13) * W
            cy  = (by + math.cos(t * fy + i * 1.0) * 0.10) * H
            rad = br * max(W, H)
            grd = QRadialGradient(cx, cy, rad)
            grd.setColorAt(0.00, QColor(r, g, b, a))
            grd.setColorAt(0.50, QColor(r, g, b, a // 3))
            grd.setColorAt(1.00, QColor(r, g, b, 0))
            p.setBrush(QBrush(grd))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), rad, rad)

        # Subtle bright overlay to keep things airy
        veil = QLinearGradient(0, 0, 0, H)
        veil.setColorAt(0, QColor(255, 255, 255, 80))
        veil.setColorAt(1, QColor(240, 242, 250, 40))
        p.setBrush(QBrush(veil)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect())
        p.end()


# Liquid Glass Panel
class GlassPanel(QWidget):
    def __init__(self, parent=None, radius=18):
        super().__init__(parent)
        self._r = radius
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        r    = QRectF(0.5, 0.5, W - 1, H - 1)
        rad  = float(self._r)

        clip = QPainterPath()
        clip.addRoundedRect(r, rad, rad)
        p.setClipPath(clip)

        # 1 Frosted white base
        p.setBrush(QColor(*G.GLASS_BASE))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, rad, rad)

        # 2 Specular top highlight
        hi = QLinearGradient(0, r.top(), 0, r.top() + H * 0.48)
        hi.setColorAt(0.00, QColor(*G.GLASS_HI))
        hi.setColorAt(0.12, QColor(255, 255, 255, 120))
        hi.setColorAt(0.40, QColor(255, 255, 255,  30))
        hi.setColorAt(1.00, QColor(255, 255, 255,   0))
        p.setBrush(QBrush(hi)); p.drawRect(r)

        # 3 Inner tint (cool grey cast depth cue)
        it = QLinearGradient(0, H * 0.45, 0, H)
        it.setColorAt(0, QColor(*G.GLASS_INNER))
        it.setColorAt(1, QColor(215, 222, 238,  70))
        p.setBrush(QBrush(it)); p.drawRect(r)

        # 4 Left micro-highlight
        le = QLinearGradient(r.left(), 0, r.left() + 10, 0)
        le.setColorAt(0, QColor(255, 255, 255, 160))
        le.setColorAt(1, QColor(255, 255, 255,   0))
        p.setBrush(QBrush(le))
        p.drawRect(QRectF(r.left(), r.top(), 10, r.height()))

        p.setClipping(False)

        # 5 Rim border cool grey, no harsh lines
        p.setPen(QPen(QColor(*G.GLASS_EDGE), 0.9))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(0.45, 0.45, -0.45, -0.45), rad, rad)
        p.end()


# Glass Button
class GlassButton(QPushButton):
    def __init__(self, text, parent=None, accent=True):
        super().__init__(text, parent)
        self._accent  = accent
        self._hov     = False
        self._pressed = False
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(FT(14, bold=True))
        self.setMinimumHeight(50)

    def enterEvent(self, e):       self._hov = True;     self.update()
    def leaveEvent(self, e):       self._hov = False;    self.update()
    def mousePressEvent(self, e):  self._pressed = True;  self.update(); super().mousePressEvent(e)
    def mouseReleaseEvent(self, e):self._pressed = False; self.update(); super().mouseReleaseEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H  = self.width(), self.height()
        r     = QRectF(0.5, 0.5, W - 1, H - 1)
        rad   = H / 2.0
        en    = self.isEnabled()

        clip = QPainterPath(); clip.addRoundedRect(r, rad, rad)
        p.setClipPath(clip)

        if self._accent and en:
            # Solid blue with glass sheen on top
            base_a = 200 if self._pressed else (230 if self._hov else 215)
            gr = QLinearGradient(0, 0, 0, H)
            gr.setColorAt(0, QColor( 59, 120, 246, base_a))
            gr.setColorAt(1, QColor( 29,  78, 216, base_a - 20))
            p.setBrush(gr); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(r, rad, rad)

            sh = QLinearGradient(0, 0, 0, H * 0.48)
            sh.setColorAt(0, QColor(255, 255, 255, 68 if not self._pressed else 18))
            sh.setColorAt(1, QColor(255, 255, 255,  0))
            p.setBrush(QBrush(sh)); p.drawRect(QRectF(0, 0, W, H * 0.48))

            p.setClipping(False)
            p.setPen(QPen(QColor(29, 78, 216, 80), 0.8))
        else:
            a = 12 if not en else (32 if self._hov else 18)
            p.setBrush(QColor(0, 0, 0, a)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(r, rad, rad)
            p.setClipping(False)
            p.setPen(QPen(QColor(0, 0, 0, 35), 0.8))

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(0.4, 0.4, -0.4, -0.4), rad, rad)

        # Label
        if self._accent and en:
            p.setPen(QColor(255, 255, 255, 238))
        else:
            p.setPen(QColor(G.TEXT.red(), G.TEXT.green(), G.TEXT.blue(), 180 if en else 60))
        p.setFont(self.font())
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text())
        p.end()


# Glass Progress Bar
class GlassProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._v   = 0.0
        self._col = G.ACCENT
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.setFixedHeight(12)

    def set_value(self, v):  self._v = max(0.0, min(1.0, v)); self.update()
    def set_color(self, c):  self._col = c; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        rad  = H / 2.0

        # Track light grey
        p.setBrush(QColor(0, 0, 0, 14))
        p.setPen(QPen(QColor(0, 0, 0, 22), 0.5))
        p.drawRoundedRect(QRectF(0, 0, W, H), rad, rad)

        if self._v > 0.002:
            fw  = max(H, W * self._v)
            c   = self._col

            clip = QPainterPath()
            clip.addRoundedRect(QRectF(0, 0, W, H), rad, rad)
            p.setClipPath(clip)

            gr = QLinearGradient(0, 0, fw, 0)
            gr.setColorAt(0, c.lighter(118))
            gr.setColorAt(1, c)
            p.setBrush(gr); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(0, 0, fw, H), rad, rad)

            sh = QLinearGradient(0, 0, 0, H)
            sh.setColorAt(0.0, QColor(255, 255, 255, 110))
            sh.setColorAt(0.5, QColor(255, 255, 255,   0))
            p.setBrush(QBrush(sh)); p.drawRect(QRectF(0, 0, fw, H))

            p.setClipping(False)

            glow = QRadialGradient(fw, H / 2, H * 1.2)
            glow.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), 60))
            glow.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(),  0))
            p.setBrush(QBrush(glow)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(fw, H / 2), H * 1.2, H * 1.2)

        p.end()


# Status Chip
class Chip(QWidget):
    def __init__(self, text, color: QColor, parent=None):
        super().__init__(parent)
        self._text  = text
        self._color = color
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.setFont(FT(10, bold=True))
        self.setFixedHeight(25)
        self._rw()

    def _rw(self): self.setMinimumWidth(self.fontMetrics().horizontalAdvance(self._text) + 28)

    def update_text(self, t): self._text = t; self._rw(); self.update()
    def set_color(self, c):   self._color = c; self.update()

    def paintEvent(self, _):
        p   = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r   = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        rad = r.height() / 2
        c   = self._color

        clip = QPainterPath(); clip.addRoundedRect(r, rad, rad)
        p.setClipPath(clip)

        # Light tinted fill
        p.setBrush(QColor(c.red(), c.green(), c.blue(), 22))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, rad, rad)

        # Top sheen
        sh = QLinearGradient(0, 0, 0, r.height() * 0.5)
        sh.setColorAt(0, QColor(255, 255, 255, 130))
        sh.setColorAt(1, QColor(255, 255, 255,   0))
        p.setBrush(sh); p.drawRect(QRectF(r.x(), r.y(), r.width(), r.height() * 0.5))
        p.setClipping(False)

        p.setPen(QPen(QColor(c.red(), c.green(), c.blue(), 70), 0.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(0.4, 0.4, -0.4, -0.4), rad, rad)

        p.setPen(QColor(c.red(), c.green(), c.blue(), 210))
        p.setFont(self.font()); p.drawText(r, Qt.AlignmentFlag.AlignCenter, self._text)
        p.end()


# Title Bar
class TitleBar(QWidget):
    def __init__(self, win: QMainWindow, parent=None):
        super().__init__(parent)
        self._win  = win
        self._drag = None
        self.setFixedHeight(52)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 10, 0)
        lay.setSpacing(0)

        title = QLabel("FASIH-SM Approval Automator")
        title.setFont(FD(16, bold=True, italic=True))
        title.setStyleSheet(f"color: {G.TEXT.name()}; background: transparent;")
        lay.addWidget(title)

        badge = QLabel("  BPS Kabupaten Lampung Tengah  ")
        badge.setFont(FT(9, bold=True))
        badge.setStyleSheet("""
            color: #1d60e8;
            background: rgba(37,99,235,0.10);
            border: 0.8px solid rgba(37,99,235,0.35);
            border-radius: 4px;
            padding: 2px 6px;
            margin-left: 10px;
        """)
        lay.addWidget(badge)
        lay.addStretch()

        # Windows 11 control buttons
        for sym, tip, slot in [
            ("─", "Minimize", win.showMinimized),
            ("□", "Restore",  win.showNormal),
            ("✕", "Close",    win.close),
        ]:
            btn = QPushButton(sym)
            btn.setToolTip(tip)
            btn.setFont(FT(11))
            btn.setFixedSize(44, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            is_close = sym == "✕"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {G.SUB_TEXT.name()};
                    border: none; border-radius: 6px;
                }}
                QPushButton:hover {{
                    background: {'rgba(196,32,28,0.88)' if is_close else 'rgba(0,0,0,0.08)'};
                    color: {'white' if is_close else G.TEXT.name()};
                }}
                QPushButton:pressed {{
                    background: {'rgba(196,32,28,1.0)' if is_close else 'rgba(0,0,0,0.14)'};
                }}
            """)
            btn.clicked.connect(slot)
            lay.addWidget(btn)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self._win.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() == Qt.MouseButton.LeftButton:
            self._win.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e): self._drag = None

    def paintEvent(self, _):
        p = QPainter(self)
        W, H = self.width(), self.height()
        # Frosted white top band
        gr = QLinearGradient(0, 0, 0, H)
        gr.setColorAt(0, QColor(255, 255, 255, 200))
        gr.setColorAt(0.5, QColor(255, 255, 255, 120))
        gr.setColorAt(1,   QColor(255, 255, 255,  40))
        p.fillRect(self.rect(), QBrush(gr))
        # Bottom separator
        p.setPen(QPen(QColor(200, 205, 215, 140), 0.5))
        p.drawLine(0, H - 1, W, H - 1)
        p.end()


# Glass Line Edit
class GlassLineEdit(QLineEdit):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFont(FT(13))
        self.setMinimumHeight(44)
        self.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.72);
                border: 0.8px solid rgba(0, 0, 0, 0.10);
                border-radius: 11px;
                color: #161823;
                padding: 0px 14px;
                selection-background-color: rgba(37, 99, 235, 0.25);
            }
            QLineEdit:focus {
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid rgba(37, 99, 235, 0.55);
            }
        """)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.PlaceholderText, G.SUB_TEXT)
        self.setPalette(pal)

# Glass Combo Box (Dropdown)
class GlassComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(FT(13))
        self.setMinimumHeight(44)
        self.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.72);
                border: 0.8px solid rgba(0, 0, 0, 0.10);
                border-radius: 11px;
                color: #161823;
                padding: 0px 14px;
            }
            QComboBox:focus {
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid rgba(37, 99, 235, 0.55);
            }
            QComboBox::drop-down {
                border: none;
                width: 34px;
            }
            QComboBox QAbstractItemView {
                background: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(0, 0, 0, 0.10);
                border-radius: 8px;
                selection-background-color: rgba(37, 99, 235, 0.25);
                selection-color: #161823;
                outline: none;
            }
        """)

# Main Window
class FasihApp(QMainWindow):
    sig_log      = pyqtSignal(str, str)
    sig_progress = pyqtSignal(int, int, int, int)
    sig_finish   = pyqtSignal(int, int)
    sig_unlock   = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FASIH-SM Approval Automator")
        self.setFixedSize(760, 860)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build()
        self.sig_log.connect(self._on_log)
        self.sig_progress.connect(self._on_progress)
        self.sig_finish.connect(self._on_finish)
        self.sig_unlock.connect(self._unlock)

    # Build
    def _build(self):
        shell = QWidget(self)
        shell.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        sl = QVBoxLayout(shell)
        sl.setContentsMargins(18, 18, 18, 18)
        self.setCentralWidget(shell)

        self._bg = AuroraBackground(shell)

        shad = QGraphicsDropShadowEffect(self)
        shad.setBlurRadius(50)
        shad.setOffset(0, 12)
        shad.setColor(QColor(0, 0, 0, 55))   # softer shadow for light mode
        self._bg.setGraphicsEffect(shad)
        sl.addWidget(self._bg)

        main = QVBoxLayout(self._bg)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        self._tbar = TitleBar(self, self._bg)
        main.addWidget(self._tbar)

        body = QWidget(self._bg)
        body.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        blay = QVBoxLayout(body)
        blay.setContentsMargins(22, 8, 22, 22)
        blay.setSpacing(12)
        main.addWidget(body)

        # Subtitle
        sub = QLabel("Survey Collection  ·  Automated PML Approval")
        sub.setFont(FT(12))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color: {G.SUB_TEXT.name()}; background: transparent;")
        blay.addWidget(sub)
        blay.addSpacing(4)

        # Input panel 
        ip = GlassPanel(self._bg, radius=18)
        il = QVBoxLayout(ip)
        il.setContentsMargins(20, 16, 20, 18)
        il.setSpacing(6)

        for cap, attr, hint in [
            ("NAMA SURVEI",          "input_survei", "contoh:  SAKERNAS FEB 2026 - PENDATAAN (copy dari Fasih-SM)"),
            ("JUMLAH DATA YANG DITARIK", "input_jumlah", "contoh:  100"),
        ]:
            lbl = QLabel(cap)
            lbl.setFont(FT(9, bold=True))
            lbl.setStyleSheet(f"color:{G.SUB_TEXT.name()};letter-spacing:1.2px;background:transparent;")
            il.addWidget(lbl)
            e = GlassLineEdit(hint)
            setattr(self, attr, e)
            il.addWidget(e)
            il.addSpacing(16)

        # Tambahan Dropdown Status Data
        lbl_status = QLabel("STATUS DATA")
        lbl_status.setFont(FT(9, bold=True))
        lbl_status.setStyleSheet(f"color:{G.SUB_TEXT.name()};letter-spacing:1.2px;background:transparent;")
        il.addWidget(lbl_status)
        
        self.input_status = GlassComboBox()
        self.input_status.addItems([
            "SUBMITTED BY Pencacah",
            "APPROVED BY PML",
            "APPROVED BY Pengawas",
            "EDITED BY Admin Kabupaten"
        ])
        il.addWidget(self.input_status)
        il.addSpacing(16)

        # Tambahan Dropdown Urutan Data
        lbl_sort = QLabel("URUTAN TARIK DATA")
        lbl_sort.setFont(FT(9, bold=True))
        lbl_sort.setStyleSheet(f"color:{G.SUB_TEXT.name()};letter-spacing:1.2px;background:transparent;")
        il.addWidget(lbl_sort)
        
        self.input_sort = GlassComboBox()
        self.input_sort.addItems([
            "Ascending (Terlama / Atas)",
            "Descending (Terbaru / Bawah)"
        ])
        il.addWidget(self.input_sort)
        il.addSpacing(4)

        # Masukin panelnya ke layout utama (blay) di bagian paling akhir
        blay.addWidget(ip)

        # Run button
        self.btn_run = GlassButton("▶   Mulai Login & Automasi", accent=True)
        self.btn_run.clicked.connect(self._on_run)
        blay.addWidget(self.btn_run)

        # Progress panel
        pp = GlassPanel(self._bg, radius=18)
        pl = QVBoxLayout(pp)
        pl.setContentsMargins(20, 14, 20, 16)
        pl.setSpacing(10)

        hr = QHBoxLayout(); hr.setContentsMargins(0, 0, 0, 0)
        lp = QLabel("PROGRESS APPROVAL")
        lp.setFont(FT(9, bold=True))
        lp.setStyleSheet(f"color:{G.SUB_TEXT.name()};letter-spacing:1.2px;background:transparent;")
        hr.addWidget(lp); hr.addStretch()
        self.lbl_counter = QLabel("0 / 0")
        self.lbl_counter.setFont(FD(13, bold=True))
        self.lbl_counter.setStyleSheet(f"color:{G.ACCENT.name()};background:transparent;")
        hr.addWidget(self.lbl_counter)
        pl.addLayout(hr)

        self.pbar = GlassProgressBar(pp)
        pl.addWidget(self.pbar)

        cr = QHBoxLayout(); cr.setContentsMargins(0, 0, 0, 0); cr.setSpacing(8)
        self.chip_ok   = Chip("✓  Berhasil: 0", G.OK)
        self.chip_err  = Chip("✗  Gagal: 0",    G.ERR)
        self.chip_stat = Chip("●  Idle",         G.SUB_TEXT)
        for c in (self.chip_ok, self.chip_err, self.chip_stat): cr.addWidget(c)
        cr.addStretch()
        pl.addLayout(cr)
        blay.addWidget(pp)

        # Log panel
        lp2 = GlassPanel(self._bg, radius=18)
        ll  = QVBoxLayout(lp2)
        ll.setContentsMargins(0, 0, 0, 0)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFont(FM(11))
        self.log_box.setFixedHeight(130)
        self.log_box.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.log_box.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                color: #2a2d3e;
                padding: 14px 18px;
            }
            QScrollBar:vertical {
                background: rgba(0,0,0,0.04);
                width: 5px; border-radius: 2px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(0,0,0,0.18);
                border-radius: 2px; min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        ll.addWidget(self.log_box)
        blay.addWidget(lp2)

        # Footer Credit
        footer = QLabel("© M Naufal Faishal - 1805")
        footer.setFont(FT(10, bold=True))
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color: {G.SUB_TEXT.name()}; background: transparent; margin-top: 6px;")
        blay.addWidget(footer)

    # Slots
    @pyqtSlot(str, str)
    def _on_log(self, msg, tag):
        COLOR = {
            "ok":   G.OK.name(),
            "err":  G.ERR.name(),
            "warn": G.WARN.name(),
            "info": G.ACCENT.name(),
        }
        col = COLOR.get(tag, G.TEXT.name())
        self.log_box.append(
            f'<span style="color:{col};">{msg}</span>'
        )
        sb = self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    @pyqtSlot(int, int, int, int)
    def _on_progress(self, done, total, ok, err):
        r = done / total if total else 0
        self.pbar.set_value(r)
        self.lbl_counter.setText(f"{done} / {total}")
        self.chip_ok.update_text(f"✓  Berhasil: {ok}")
        self.chip_err.update_text(f"✗  Gagal: {err}")
        col = G.OK if err == 0 else G.WARN
        self.chip_stat.set_color(col)
        self.chip_stat.update_text(f"●  Running {int(r * 100)}%")

    @pyqtSlot(int, int)
    def _on_finish(self, ok, err):
        self.pbar.set_value(1.0)
        col = G.OK if err == 0 else (G.WARN if ok > 0 else G.ERR)
        self.pbar.set_color(col)
        self.chip_stat.set_color(col)
        self.chip_stat.update_text("●  Selesai")
        self._unlock()

    @pyqtSlot()
    def _unlock(self):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("▶   Mulai Login & Automasi")
        self.btn_run.update()

    # Run
    def _on_run(self):
        nama   = self.input_survei.text().strip()
        jumlah = self.input_jumlah.text().strip()
        status_data = self.input_status.currentText()
        
        # Tangkap nilai urutan dan ubah ke format API
        sort_pilihan = self.input_sort.currentText()
        sort_dir = "desc" if "Descending" in sort_pilihan else "asc"

        if not nama or not jumlah:
            self.sig_log.emit("[ERROR]  Nama survei dan jumlah data wajib diisi!", "err"); return
        try:    jml = int(jumlah)
        except: self.sig_log.emit("[ERROR]  Jumlah data harus berupa angka!", "err"); return

        self.btn_run.setEnabled(False)
        self.btn_run.setText("⏳  Running…")
        self.btn_run.update()
        self.log_box.clear()
        self.pbar.set_value(0); self.pbar.set_color(G.ACCENT)
        self.lbl_counter.setText("0 / 0")
        self.chip_ok.update_text("✓  Berhasil: 0")
        self.chip_err.update_text("✗  Gagal: 0")
        self.chip_stat.set_color(G.SUB_TEXT)
        self.chip_stat.update_text("●  Idle")

        threading.Thread(target=self._automate, args=(nama, jml, status_data, sort_dir), daemon=True).start()

    # Automation worker
    def log(self, msg, tag="default"): self.sig_log.emit(msg, tag)

    def _automate(self, nama_survei, jumlah_data, status_data, sort_dir):
        self.log("⬡  Membuka browser… Silakan login SSO & masukkan OTP.", "info")

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False, channel="chrome")
            ctx     = browser.new_context()
            page    = ctx.new_page()

            page.goto("https://fasih-sm.bps.go.id/login")
            self.log("⬡  Menunggu login selesai…", "info")

            try:
                page.wait_for_url("**/survey-collection/survey*", timeout=0)
                self.log("✓  Login berhasil terdeteksi!", "ok")
            except Exception as e:
                self.log(f"✗  Gagal: {e}", "err")
                browser.close(); self.sig_unlock.emit(); return

            try:
                csrf = page.locator('input[name="_csrf"]').get_attribute('value', timeout=5000)
                self.log("✓  CSRF Token diekstrak.", "ok")
            except:
                self.log("✗  CSRF Token tidak ditemukan.", "err")
                browser.close(); self.sig_unlock.emit(); return

            hdrs = {"x-xsrf-token": csrf, "Content-Type": "application/json"}

            self.log("Menunggu Daftar Survei Muncul", "ok")
            time.sleep(5)

            self.log(f"⬡  Mencari survei: {nama_survei}", "info")
            resp = ctx.request.post(
                "https://fasih-sm.bps.go.id/survey/api/v1/surveys/datatable?surveyType=Pencacahan",
                data=dict(pageNumber=0, pageSize=10, sortBy="CREATED_AT",
                          sortDirection="DESC", keywordSearch=nama_survei),
                headers=hdrs
            )

            time.sleep(3)

            if not resp.ok:
                self.log("✗  Gagal mengambil daftar survei.", "err"); browser.close(); self.sig_unlock.emit(); return

            resp_data = resp.json().get("data", {})
            content_list = resp_data.get("content", [])
            num_elements = resp_data.get("numberOfElements", 0)

            # Logika baru: Kalau hasil pencarian cuma 1, langsung comot ID-nya
            if num_elements == 1 and content_list:
                sid = content_list[0]["id"]
            else:
                sid = next((i["id"] for i in content_list if i.get("name") == nama_survei), None)

            if not sid:
                self.log(f"✗  Survei '{nama_survei}' tidak ditemukan. Cek huruf kapital/spasi.", "err")
                browser.close()
                self.sig_unlock.emit()
                return
            
            self.log(f"✓  Survey ID: {sid}", "ok")

            rp = ctx.request.get(
                f"https://fasih-sm.bps.go.id/survey/api/v1/survey-periods/my?surveyId={sid}",
                headers=hdrs
            )
            try:
                pid = rp.json()["data"][0]["id"]
                self.log(f"✓  Period ID: {pid}", "ok")
            except:
                self.log("✗  Periode aktif tidak ditemukan.", "err"); browser.close(); self.sig_unlock.emit(); return

            self.log(f"⬡  Menarik antrean untuk status: {status_data} ({sort_dir})…", "info")
            rt = ctx.request.post(
                "https://fasih-sm.bps.go.id/analytic/api/v2/assignment/datatable-all-user-survey-periode",
                data=dict(draw=2, columns=[], order=[{"column": 3, "dir": sort_dir}],
                          start=0, length=jumlah_data,
                          search={"value": "", "regex": False},
                          assignmentExtraParam=dict(surveyPeriodId=pid,
                              assignmentErrorStatusType=-1, filterTargetType="TARGET_ONLY", assignmentStatusAlias=status_data)),
                headers=hdrs
            )
            
            # Update filter berdasarkan status_data
            queue = [i for i in rt.json().get("searchData", [])
                     if i.get("assignmentStatusAlias") == status_data]

            if not queue:
                self.log(f"⬡  Tidak ada antrean '{status_data}' saat ini.", "warn")
                browser.close(); self.sig_unlock.emit(); return

            total = len(queue)
            self.log(f"✓  {total} data ditemukan. Memulai approval…\n", "ok")

            ok = err = 0
            for idx, task in enumerate(queue, 1):
                ra   = ctx.request.post(
                    "https://fasih-sm.bps.go.id/assignment-approval/api/v2/approval",
                    data=dict(assignmentId=task["id"], statusApproval=True),
                    headers=hdrs
                )
                code = task.get("codeIdentity", "?")
                if ra.ok:
                    self.log(f"  [{idx:>3}/{total}]  {code}  →  BERHASIL", "ok"); ok  += 1
                else:
                    self.log(f"  [{idx:>3}/{total}]  {code}  →  GAGAL ({ra.status})", "err"); err += 1
                self.sig_progress.emit(idx, total, ok, err)

            self.log(f"\n{'=' * 44}", "default")
            self.log(f"  SELESAI  ·  Berhasil: {ok}  ·  Gagal: {err}",
                     "ok" if err == 0 else "warn")
            self.log(f"{'=' * 44}\n", "default")
            self.sig_finish.emit(ok, err)
            time.sleep(2)
            browser.close()


# Entry
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = FasihApp()
    win.show()
    sys.exit(app.exec())