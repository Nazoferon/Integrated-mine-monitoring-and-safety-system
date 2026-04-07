import sys, json, random, math, requests, datetime, os, time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsScene, QGraphicsView, 
                             QGraphicsLineItem, QGraphicsRectItem, QGraphicsEllipseItem, 
                             QGraphicsSimpleTextItem, QToolBar, QLabel, QMessageBox, 
                             QFileDialog, QInputDialog, QDoubleSpinBox, QWidget, 
                             QVBoxLayout, QDockWidget, QGraphicsItemGroup, QGraphicsItem,
                             QFormLayout, QLineEdit, QGroupBox, QMenu, QSizePolicy, QSlider,
                             QSpinBox, QTabWidget, QPushButton, QHBoxLayout, QComboBox,
                             QCheckBox, QSplitter, QProgressBar, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QPointF, QLineF, QTimer, QRectF, QSettings, QStandardPaths
from PyQt6.QtGui import QPen, QColor, QBrush, QAction, QPainter, QFont, QPalette, QCursor, QMouseEvent

# --- 1. КОНСТАНТИ ---
SCALE = 10.0
GRID_STEP_M = 10 
TUNNEL_WIDTH_M = 4.0
TUNNEL_SNAP_DISTANCE = 20
SETTINGS_FILE = "minecad_settings.ini"
AUTOSAVE_FILENAME = "autosave_mine.json"

class MineItemType:
    TUNNEL = "tunnel"
    YARD = "yard"
    DEVICE = "device"
    MINER = "miner"
    RULER = "ruler"
    JUNCTION = "junction"

# --- НАЛАШТУВАНЯ ---
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Налаштування програми")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Група автозбереження
        autosave_group = QGroupBox("Автозбереження")
        autosave_layout = QVBoxLayout()
        
        self.autosave_checkbox = QCheckBox("Активувати автозбереження")
        autosave_layout.addWidget(self.autosave_checkbox)
        
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Інтервал автозбереження:"))
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(5, 120)  # 5 секунд до 2 хвилин
        self.interval_spinbox.setSuffix(" сек")
        interval_layout.addWidget(self.interval_spinbox)
        interval_layout.addStretch()
        autosave_layout.addLayout(interval_layout)
        
        self.save_on_exit_checkbox = QCheckBox("Запитувати при закритті, якщо проект не збережено")
        autosave_layout.addWidget(self.save_on_exit_checkbox)
        
        autosave_group.setLayout(autosave_layout)
        layout.addWidget(autosave_group)
        
        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def load_settings(self, settings):
        self.autosave_checkbox.setChecked(settings.get("autosave_enabled", False))
        self.interval_spinbox.setValue(settings.get("autosave_interval", 30))
        self.save_on_exit_checkbox.setChecked(settings.get("prompt_on_exit", True))
    
    def get_settings(self):
        return {
            "autosave_enabled": self.autosave_checkbox.isChecked(),
            "autosave_interval": self.interval_spinbox.value(),
            "prompt_on_exit": self.save_on_exit_checkbox.isChecked()
        }

# --- МАТЕМАТИЧНІ ДОПОМІЖНІ ФУНКЦІЇ ---
def nearest_point_on_line(line, point):
    """Знаходить найближчу точку на відрізку line до точки point"""
    x1, y1 = line.p1().x(), line.p1().y()
    x2, y2 = line.p2().x(), line.p2().y()
    x3, y3 = point.x(), point.y()
    
    px = x2 - x1
    py = y2 - y1
    norm = px*px + py*py
    
    if norm == 0: return line.p1()
    
    u = ((x3 - x1) * px + (y3 - y1) * py) / norm
    
    if u > 1: u = 1
    elif u < 0: u = 0
    
    x = x1 + u * px
    y = y1 + u * py
    
    return QPointF(x, y)

# --- ТЕМА ---
def apply_dark_theme(app):
    app.setStyle("Fusion")
    palette = QPalette()
    dark_gray = QColor(53, 53, 53)
    black = QColor(25, 25, 25)
    palette.setColor(QPalette.ColorRole.Window, dark_gray)
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, black)
    palette.setColor(QPalette.ColorRole.AlternateBase, dark_gray)
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, dark_gray)
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)

# --- 2. ГРАФІЧНІ ЕЛЕМЕНТИ ---
# [Тут без змін, все ті самі класи графічних елементів]
# ... (та ж сама реалізація InfiniteScene, JunctionPoint, WifiIconItem, TunnelGroup, YardItem, MinerItem, RulerItem)

class InfiniteScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-500000, -500000, 1000000, 1000000)
        self.grid_pen = QPen(QColor(60, 60, 60), 1)
        self.axis_pen = QPen(QColor(80, 150, 80), 2)
        self.snap_pen = QPen(QColor(255, 200, 0, 180), 2)
        self.snap_pen.setStyle(Qt.PenStyle.DashLine)

    def drawBackground(self, painter, rect):
        if not painter.isActive(): return
        painter.fillRect(rect, QColor("#1e1e1e"))
        step = GRID_STEP_M * SCALE
        l = int(rect.left()) - (int(rect.left()) % int(step))
        t = int(rect.top()) - (int(rect.top()) % int(step))
        lines = []
        max_lines = 300 
        x = l
        c = 0
        while x < rect.right() and c < max_lines:
            lines.append(QLineF(x, rect.top(), x, rect.bottom()))
            x += step
            c += 1
        y = t
        c = 0
        while y < rect.bottom() and c < max_lines:
            lines.append(QLineF(rect.left(), y, rect.right(), y))
            y += step
            c += 1
        painter.setPen(self.grid_pen)
        painter.drawLines(lines)
        if rect.contains(0, 0):
            painter.setPen(self.axis_pen)
            painter.drawLine(QLineF(0, -50, 0, 50))
            painter.drawLine(QLineF(-50, 0, 50, 0))

class JunctionPoint(QGraphicsEllipseItem):
    def __init__(self, x, y):
        super().__init__(-6, -6, 12, 12)
        self.setPos(x, y)
        self.setBrush(QBrush(QColor(255, 140, 0))) 
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        self.setZValue(150)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setData(0, MineItemType.JUNCTION)
        self.connected_tunnels = []
        
    def add_tunnel(self, tunnel):
        if tunnel not in self.connected_tunnels:
            self.connected_tunnels.append(tunnel)
            
    def remove_tunnel(self, tunnel):
        if tunnel in self.connected_tunnels:
            self.connected_tunnels.remove(tunnel)
            
    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QPen(QColor(0, 255, 255), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(-2,-2,2,2))

class WifiIconItem(QGraphicsItem):
    def __init__(self, uid, x, y):
        super().__init__()
        self.setPos(float(x), float(y))
        self.setZValue(300) 
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setData(0, MineItemType.DEVICE)
        self.uid = uid 
        self.show_range = False
        self.range_circle = QGraphicsEllipseItem(-300, -300, 600, 600, self)
        self.range_circle.setBrush(QBrush(QColor(0, 255, 0, 20)))
        self.range_circle.setPen(QPen(QColor(0, 255, 0, 80), 1, Qt.PenStyle.DashLine))
        self.range_circle.setVisible(False)
        self.circle = QGraphicsEllipseItem(-8, -8, 16, 16, self)
        if uid == "AP-MAIN":
            self.circle.setBrush(QBrush(QColor("#ff4444")))
        else:
            self.circle.setBrush(QBrush(QColor("yellow")))
        self.circle.setPen(QPen(Qt.GlobalColor.black, 2))
        self.label = QGraphicsSimpleTextItem(uid, self)
        font = QFont("Arial", 10, QFont.Weight.Bold)
        self.label.setFont(font)
        self.label.setBrush(QBrush(QColor("#00ffff")))
        self.label.setPos(-15, -25)
        self.hitbox = QGraphicsEllipseItem(-15, -15, 30, 30, self)
        self.hitbox.setBrush(QBrush(QColor(0,0,0,1)))
        self.hitbox.setPen(QPen(Qt.PenStyle.NoPen))

    def boundingRect(self):
        return QRectF(-20, -30, 40, 50)

    def paint(self, painter, option, widget):
        if self.isSelected():
            painter.setPen(QPen(QColor("#00ff00"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect())

    def set_label_text(self, text):
        self.uid = text
        self.label.setText(text)
        if text == "AP-MAIN":
            self.circle.setBrush(QBrush(QColor("#ff4444")))
        else:
            self.circle.setBrush(QBrush(QColor("yellow")))

    def toggle_range(self, visible):
        self.show_range = visible
        self.range_circle.setVisible(visible)
        
    def hoverEnterEvent(self, event):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.circle.setBrush(QBrush(QColor("#ffffaa")))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if self.uid == "AP-MAIN":
            self.circle.setBrush(QBrush(QColor("#ff4444")))
        else:
            self.circle.setBrush(QBrush(QColor("yellow")))
        super().hoverLeaveEvent(event)

class TunnelGroup(QGraphicsItemGroup):
    def __init__(self, line_geom, parent_scene=None):
        super().__init__()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setZValue(10) 
        self.setData(0, MineItemType.TUNNEL)
        self.line_geom = line_geom 
        self.length_m = line_geom.length() / SCALE
        self.tunnel_name = f"Штрек-{int(random.random()*1000)}"
        self.parent_scene = parent_scene
        self.junction_start = None
        self.junction_end = None
        
        self.bg = QGraphicsLineItem(line_geom)
        self.bg.setPen(QPen(QColor("#111"), (TUNNEL_WIDTH_M + 1.2) * SCALE, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        self.bg.setZValue(10)
        self.addToGroup(self.bg)

        self.main = QGraphicsLineItem(line_geom)
        self.main.setPen(QPen(QColor("#5a4d41"), TUNNEL_WIDTH_M * SCALE, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        self.main.setZValue(11) 
        self.addToGroup(self.main)

        self.supp = QGraphicsLineItem(line_geom)
        self.supp.setPen(QPen(QColor("#3e332a"), (TUNNEL_WIDTH_M - 1.0) * SCALE, Qt.PenStyle.DashLine))
        self.supp.setZValue(12) 
        self.addToGroup(self.supp)

    def update_length(self, new_length_m):
        current_angle = self.line_geom.angle()
        p1 = self.line_geom.p1()
        new_line = QLineF()
        new_line.setP1(p1)
        new_line.setAngle(current_angle)
        new_line.setLength(new_length_m * SCALE)
        self.line_geom = new_line
        self.length_m = new_length_m
        self.bg.setLine(new_line)
        self.main.setLine(new_line)
        self.supp.setLine(new_line)
        if self.junction_end:
            self.junction_end.setPos(new_line.p2())

    def paint(self, painter, option, widget):
        if self.isSelected():
            glow_pen = QPen(QColor(0, 255, 255, 100))
            glow_pen.setWidthF((TUNNEL_WIDTH_M + 4.0) * SCALE)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(glow_pen)
            painter.drawLine(self.line_geom)

class YardItem(QGraphicsRectItem):
    def __init__(self, x, y, w_m, h_m):
        self.w_m = w_m
        self.h_m = h_m
        w_px = w_m * SCALE
        h_px = h_m * SCALE
        super().__init__(-w_px/2, -h_px/2, w_px, h_px)
        self.setPos(float(x), float(y))
        self.setBrush(QBrush(QColor("#444")))
        self.setPen(QPen(QColor("#000"), 2))
        self.setZValue(5)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setData(0, MineItemType.YARD)
        self.yard_name = "Руддвір"
        self.shaft = QGraphicsEllipseItem(-20, -20, 40, 40, self)
        self.shaft.setBrush(QBrush(QColor("#000")))
        self.shaft.setPen(QPen(QColor("yellow"), 2, Qt.PenStyle.DashLine))
        self.label = QGraphicsSimpleTextItem(self.yard_name, self)
        self.label.setBrush(QBrush(Qt.GlobalColor.white))
        self.label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.label.setPos(-w_px/2 + 5, -h_px/2 + 5)

    def update_size(self, w_m, h_m):
        self.w_m = w_m
        self.h_m = h_m
        w_px = w_m * SCALE
        h_px = h_m * SCALE
        self.setRect(-w_px/2, -h_px/2, w_px, h_px)
        self.label.setPos(-w_px/2 + 5, -h_px/2 + 5)

    def update_name(self, name):
        self.yard_name = name
        self.label.setText(name)

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QPen(QColor(0, 255, 255, 200), 4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.rect())

class MinerItem(QGraphicsItem):
    def __init__(self, miner_id, name):
        super().__init__()
        self.setZValue(400)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setData(0, MineItemType.MINER)
        self.setAcceptHoverEvents(True)
        self.stats = {"id": miner_id, "name": name, "heart": 75, "bat": 100, "status": "OK"}
        self.path = []
        self.current_path_index = 0
        self.glow = QGraphicsEllipseItem(-15, -15, 30, 30, self)
        self.glow.setBrush(QBrush(QColor(255, 0, 0, 100)))
        self.glow.setPen(QPen(Qt.PenStyle.NoPen))
        self.body = QGraphicsEllipseItem(-8, -8, 16, 16, self)
        self.body.setBrush(QBrush(QColor("red")))
        self.body.setPen(QPen(Qt.GlobalColor.white, 2))
        self.lbl = QGraphicsSimpleTextItem(name, self)
        self.lbl.setBrush(QBrush(Qt.GlobalColor.white))
        self.lbl.setFont(QFont("Arial", 9))
        self.lbl.setPos(12, -12)

    def boundingRect(self):
        return QRectF(-20, -20, 100, 40)

    def paint(self, painter, option, widget):
        if self.isSelected():
            painter.setPen(QPen(QColor(0, 255, 255, 200), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(-16, -16, 32, 32)
            if self.path:
                painter.setPen(QPen(QColor(255, 255, 0, 100), 1, Qt.PenStyle.DashLine))
                for i in range(len(self.path)-1):
                    painter.drawLine(self.path[i], self.path[i+1])

    def update_name(self, text):
        self.stats["name"] = text
        self.lbl.setText(text)
        
    def set_path(self, path_points):
        self.path = path_points
        self.current_path_index = 0
        
    def move_along_path(self, speed):
        if not self.path or self.current_path_index >= len(self.path):
            return False
        target = self.path[self.current_path_index]
        current_pos = self.pos()
        dx = target.x() - current_pos.x()
        dy = target.y() - current_pos.y()
        distance = math.sqrt(dx*dx + dy*dy)
        if distance < speed:
            self.setPos(target)
            self.current_path_index += 1
            return True
        else:
            self.setPos(current_pos.x() + dx/distance * speed, 
                       current_pos.y() + dy/distance * speed)
            return True

class RulerItem(QGraphicsLineItem):
    def __init__(self, p1, p2):
        super().__init__(QLineF(p1, p2))
        self.setZValue(500)
        pen = QPen(QColor("#ff00ff"))
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.text = QGraphicsSimpleTextItem(self)
        self.text.setBrush(QBrush(QColor("#ff00ff")))
        self.text.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.update_text()

    def update_line(self, p2):
        l = self.line()
        l.setP2(p2)
        self.setLine(l)
        self.update_text()

    def update_text(self):
        l = self.line()
        dist = l.length() / SCALE
        self.text.setText(f"{dist:.2f} m")
        self.text.setPos((l.x1() + l.x2())/2, (l.y1() + l.y2())/2)

# --- 3. ПАНЕЛЬ ІНСПЕКТОРА ---
# [Тут без змін]
# ... (та ж сама реалізація InspectorPanel)

class InspectorPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.current_item = None
        
        self.header = QLabel("🔧 РЕДАКТОР")
        self.header.setStyleSheet("font-weight: bold; font-size: 14px; background: #2a2a2a; padding: 5px;")
        self.header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.header)
        
        self.selection_info = QLabel("Нічого не вибрано")
        self.selection_info.setStyleSheet("color: #aaa; padding: 5px;")
        self.layout.addWidget(self.selection_info)
        
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        self.tab_main = QWidget()
        form_main = QFormLayout()
        self.tab_main.setLayout(form_main)
        
        self.inp_name = QLineEdit()
        self.inp_name.textEdited.connect(self.on_name_change)
        
        self.spin_x = QDoubleSpinBox()
        self.spin_x.setRange(-99999, 99999)
        self.spin_x.valueChanged.connect(self.on_coords_change)
        self.spin_y = QDoubleSpinBox()
        self.spin_y.setRange(-99999, 99999)
        self.spin_y.valueChanged.connect(self.on_coords_change)
        
        form_main.addRow("Назва / ID:", self.inp_name)
        form_main.addRow("X:", self.spin_x)
        form_main.addRow("Y:", self.spin_y)
        self.btn_delete = QPushButton("🗑️ Видалити")
        self.btn_delete.setStyleSheet("background: #d32f2f; color: white; padding: 5px;")
        self.btn_delete.clicked.connect(self.delete_current)
        form_main.addRow(self.btn_delete)
        self.tabs.addTab(self.tab_main, "Властивості")
        
        self.tab_size = QWidget()
        form_size = QFormLayout()
        self.tab_size.setLayout(form_size)
        self.spin_w = QSpinBox()
        self.spin_w.setRange(5, 500)
        self.spin_w.valueChanged.connect(self.on_size_change)
        self.spin_h = QSpinBox()
        self.spin_h.setRange(5, 500)
        self.spin_h.valueChanged.connect(self.on_size_change)
        self.spin_len = QDoubleSpinBox()
        self.spin_len.setRange(1.0, 5000.0)
        self.spin_len.valueChanged.connect(self.on_tunnel_len_change)
        
        self.lbl_w = QLabel("Ширина:")
        self.lbl_h = QLabel("Висота:")
        self.lbl_len = QLabel("Довжина:")
        form_size.addRow(self.lbl_w, self.spin_w)
        form_size.addRow(self.lbl_h, self.spin_h)
        form_size.addRow(self.lbl_len, self.spin_len)
        self.tabs.addTab(self.tab_size, "Розміри")
        
        self.tab_live = QWidget()
        form_live = QFormLayout()
        self.tab_live.setLayout(form_live)
        self.lbl_heart = QLabel("-")
        self.lbl_bat = QLabel("-")
        self.lbl_status = QLabel("-")
        self.bar_heart = QProgressBar()
        self.bar_heart.setRange(0, 100)
        self.bar_heart.setStyleSheet("QProgressBar { border: 1px solid #555; border-radius: 3px; background: #333; text-align: center; } QProgressBar::chunk { background-color: #ff5555; }")
        self.bar_bat = QProgressBar()
        self.bar_bat.setRange(0, 100)
        self.bar_bat.setStyleSheet("QProgressBar { border: 1px solid #555; border-radius: 3px; background: #333; text-align: center; } QProgressBar::chunk { background-color: #55ff55; }")
        
        form_live.addRow("❤️ Пульс:", self.lbl_heart)
        form_live.addRow(self.bar_heart)
        form_live.addRow("🔋 Батарея:", self.lbl_bat)
        form_live.addRow(self.bar_bat)
        form_live.addRow("Статус:", self.lbl_status)
        self.btn_set_path = QPushButton("🎯 Маршрут")
        self.btn_set_path.clicked.connect(self.set_miner_path)
        form_live.addRow(self.btn_set_path)
        self.tabs.addTab(self.tab_live, "Моніторинг")
        self.layout.addStretch()

    def set_item(self, item):
        self.current_item = item
        self.block_signals(True)
        self.btn_delete.setEnabled(item is not None)
        self.btn_set_path.setVisible(False)
        self.spin_w.setVisible(False); self.lbl_w.setVisible(False)
        self.spin_h.setVisible(False); self.lbl_h.setVisible(False)
        self.spin_len.setVisible(False); self.lbl_len.setVisible(False)
        
        if not item:
            self.inp_name.setText("")
            self.inp_name.setEnabled(False)
            self.selection_info.setText("Нічого не вибрано")
            self.block_signals(False)
            return

        itype = item.data(0)
        if itype == MineItemType.TUNNEL:
            pos = item.line_geom.p1()
            info = f"Штрек: {item.tunnel_name}"
            self.spin_len.setVisible(True); self.lbl_len.setVisible(True)
            self.spin_len.setValue(item.length_m)
            self.tabs.setCurrentIndex(1)
        elif itype == MineItemType.DEVICE:
            pos = item.pos()
            info = f"Репітер: {item.uid}"
            self.tabs.setCurrentIndex(0)
        elif itype == MineItemType.YARD:
            pos = item.pos()
            info = f"Руддвір: {item.yard_name}"
            self.spin_w.setVisible(True); self.lbl_w.setVisible(True)
            self.spin_h.setVisible(True); self.lbl_h.setVisible(True)
            self.spin_w.setValue(item.w_m)
            self.spin_h.setValue(item.h_m)
            self.tabs.setCurrentIndex(1)
        elif itype == MineItemType.MINER:
            pos = item.pos()
            info = f"Шахтар: {item.stats['name']}"
            self.update_miner_ui(item)
            self.btn_set_path.setVisible(True)
            self.tabs.setCurrentIndex(2)
        else:
            pos = item.pos()
            info = "Об'єкт"
            
        self.inp_name.setEnabled(True)
        if itype == MineItemType.DEVICE: 
            self.inp_name.setText(item.uid)
            if item.uid == "AP-MAIN":
                self.inp_name.setEnabled(False)
                self.btn_delete.setEnabled(False)
        elif itype == MineItemType.TUNNEL: self.inp_name.setText(item.tunnel_name)
        elif itype == MineItemType.YARD: self.inp_name.setText(item.yard_name)
        elif itype == MineItemType.MINER: self.inp_name.setText(item.stats["name"])
        else: self.inp_name.setText("")
            
        self.selection_info.setText(info)
        self.spin_x.setValue(pos.x() / SCALE)
        self.spin_y.setValue(pos.y() / SCALE)
        self.block_signals(False)

    def block_signals(self, block):
        self.inp_name.blockSignals(block)
        self.spin_x.blockSignals(block)
        self.spin_y.blockSignals(block)
        self.spin_w.blockSignals(block)
        self.spin_h.blockSignals(block)
        self.spin_len.blockSignals(block)

    def on_name_change(self, text):
        if not self.current_item: return
        itype = self.current_item.data(0)
        if itype == MineItemType.DEVICE: self.current_item.set_label_text(text)
        elif itype == MineItemType.TUNNEL: self.current_item.tunnel_name = text
        elif itype == MineItemType.YARD: self.current_item.yard_name = text
        elif itype == MineItemType.MINER: self.current_item.update_name(text)

    def on_coords_change(self):
        if not self.current_item: return
        if self.current_item.data(0) == MineItemType.TUNNEL: return
        x = self.spin_x.value() * SCALE
        y = self.spin_y.value() * SCALE
        self.current_item.setPos(x, y)

    def on_size_change(self):
        if self.current_item and self.current_item.data(0) == MineItemType.YARD:
            self.current_item.update_size(self.spin_w.value(), self.spin_h.value())

    def on_tunnel_len_change(self):
        if self.current_item and self.current_item.data(0) == MineItemType.TUNNEL:
            self.current_item.update_length(self.spin_len.value())

    def update_miner_ui(self, item):
        heart = item.stats["heart"]
        bat = item.stats["bat"]
        self.lbl_heart.setText(f"{heart} уд/хв")
        self.lbl_bat.setText(f"{bat:.1f}%")
        self.lbl_status.setText(item.stats.get("status", "OK"))
        self.bar_heart.setValue(int(min(100, max(0, (heart-40)*100/100))))
        self.bar_bat.setValue(int(min(100, max(0, bat))))

    def delete_current(self):
        item = self.current_item
        if not item: return
        win = self.window()
        if hasattr(win, 'delete_single_item'):
            win.delete_single_item(item)
        self.set_item(None)

    def set_miner_path(self):
        if self.current_item and self.current_item.data(0) == MineItemType.MINER:
            win = self.window()
            if isinstance(win, MineCAD):
                win.set_miner_path_mode(self.current_item)

# --- 4. ПАНЕЛЬ КЕРУВАННЯ ---
class ControlPanel(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Додаємо кнопку налаштувань зверху
        self.settings_btn = QPushButton("⚙️ Налаштування")
        self.settings_btn.clicked.connect(self.parent.open_settings)
        self.settings_btn.setStyleSheet("padding: 8px; background: #2a5caa; color: white; font-weight: bold;")
        self.layout.addWidget(self.settings_btn)
        
        self.layout.addSpacing(10)
        
        self.add_btn("🖱️ Вибір", lambda: parent.set_mode("select"))
        self.add_btn("⛏️ Штрек", lambda: parent.set_mode("draw_tunnel"))
        self.add_btn("🏢 Руддвір", parent.add_yard)
        self.add_btn("👷 Шахтар", parent.spawn_miner)
        self.add_btn("📡 WiFi", self.add_wifi_point)
        
        self.layout.addSpacing(20)
        self.layout.addWidget(QLabel("Швидкість:"))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 100)
        self.slider.setValue(10)
        self.slider.valueChanged.connect(parent.update_speed)
        self.layout.addWidget(self.slider)
        
        self.cb_wifi = QCheckBox("WiFi зони")
        self.cb_wifi.stateChanged.connect(parent.toggle_wifi)
        self.layout.addWidget(self.cb_wifi)
        
        self.layout.addStretch()
        self.add_btn("💾 Експорт", parent.export_json)
        self.add_btn("📂 Імпорт", parent.import_json)
        self.add_btn("☁️ На Сервер", parent.upload_to_server)

    def add_btn(self, text, func):
        btn = QPushButton(text)
        btn.setStyleSheet("padding: 8px; text-align: left;")
        btn.clicked.connect(func)
        self.layout.addWidget(btn)

    def add_wifi_point(self):
        pos = self.parent.view.mapToScene(self.parent.view.viewport().rect().center())
        self.parent.add_repeater(pos.x(), pos.y())

# --- 5. ГОЛОВНЕ ВІКНО ---
class MineCAD(QMainWindow):
    def __init__(self):
        super().__init__()
        apply_dark_theme(QApplication.instance())
        self.setWindowTitle("MineCAD v25.0 - Налаштування & Автозбереження")
        self.setGeometry(100, 100, 1600, 900)
        
        # Налаштування
        self.settings = self.load_settings()
        self.project_saved = False
        self.current_project_file = None
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.perform_autosave)
        
        self.wifi_interval = 20.0
        self.repeater_count = 1
        self.mode = "select"
        self.temp_line = None
        self.start_pos = None
        self.pending_yard_size = (30, 15)
        self.show_wifi_ranges = False
        self.miner_speed_mult = 1.0
        self.junction_points = []
        self.miner_path_points = []
        self.current_miner_path = None
        
        self.scene = InfiniteScene()
        self.scene.selectionChanged.connect(self.on_select)
        
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setMouseTracking(True)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.viewport().installEventFilter(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.control = ControlPanel(self)
        splitter.addWidget(self.control)
        splitter.addWidget(self.view)
        splitter.setStretchFactor(1, 4)
        self.setCentralWidget(splitter)
        
        d = QDockWidget("Інспектор", self)
        d.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.inspector = InspectorPanel()
        d.setWidget(self.inspector)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, d)
        
        self.miners = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.sim_tick)
        self.timer.start(50)
        
        self.status = QLabel("Готовий")
        self.statusBar().addWidget(self.status)
        
        # Запуск автозбереження, якщо активовано
        if self.settings.get("autosave_enabled", False):
            self.start_autosave()
        
        # Спробуємо завантажити автозбереження, якщо воно є
        self.try_load_autosave()
    
    def load_settings(self):
        """Завантажити налаштування з файлу"""
        settings = QSettings(SETTINGS_FILE, QSettings.Format.IniFormat)
        return {
            "autosave_enabled": settings.value("autosave/enabled", False, type=bool),
            "autosave_interval": settings.value("autosave/interval", 30, type=int),
            "prompt_on_exit": settings.value("exit/prompt", True, type=bool)
        }
    
    def save_settings(self, settings_dict):
        """Зберегти налаштування у файл"""
        settings = QSettings(SETTINGS_FILE, QSettings.Format.IniFormat)
        settings.setValue("autosave/enabled", settings_dict["autosave_enabled"])
        settings.setValue("autosave/interval", settings_dict["autosave_interval"])
        settings.setValue("exit/prompt", settings_dict["prompt_on_exit"])
    
    def open_settings(self):
        """Відкрити діалог налаштувань"""
        dialog = SettingsDialog(self)
        dialog.load_settings(self.settings)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_settings = dialog.get_settings()
            self.save_settings(new_settings)
            self.settings = new_settings
            
            # Оновити автозбереження
            if new_settings["autosave_enabled"]:
                self.start_autosave()
            else:
                self.autosave_timer.stop()
            
            QMessageBox.information(self, "Налаштування", "Налаштування збережено!")
    
    def start_autosave(self):
        """Запустити таймер автозбереження"""
        interval = self.settings.get("autosave_interval", 30) * 1000  # Конвертуємо в мілісекунди
        self.autosave_timer.start(interval)
        self.statusBar().showMessage(f"Автозбереження активовано ({interval/1000} сек)", 3000)
    
    def perform_autosave(self):
        """Виконати автозбереження"""
        try:
            data = self.export_data()
            with open(AUTOSAVE_FILENAME, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Показуємо повідомлення в статусбарі
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            self.statusBar().showMessage(f"Автозбереження: {current_time}", 2000)
            
        except Exception as e:
            print(f"Помилка автозбереження: {e}")
    
    def try_load_autosave(self):
        """Спробувати завантажити автозбережений проект"""
        if os.path.exists(AUTOSAVE_FILENAME):
            reply = QMessageBox.question(
                self, 
                "Знайдено автозбереження", 
                "Знайдено автозбережений проект. Завантажити його?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    with open(AUTOSAVE_FILENAME, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self.import_data(data)
                    self.statusBar().showMessage("Автозбереження завантажено", 3000)
                except Exception as e:
                    QMessageBox.warning(self, "Помилка", f"Не вдалося завантажити автозбереження: {e}")
    
    def export_data(self):
        """Експортувати дані проекту у словник"""
        data = {
            "tunnels": [], 
            "yards": [], 
            "devices": [], 
            "miners": [], 
            "timestamp": str(datetime.datetime.now())
        }
        
        for item in self.scene.items():
            if item.data(0) == MineItemType.TUNNEL:
                l = item.line_geom
                data["tunnels"].append({
                    "name": item.tunnel_name,
                    "x1": round(l.x1()/SCALE, 2), 
                    "y1": round(l.y1()/SCALE, 2),
                    "x2": round(l.x2()/SCALE, 2), 
                    "y2": round(l.y2()/SCALE, 2)
                })
            elif item.data(0) == MineItemType.DEVICE:
                p = item.pos()
                data["devices"].append({
                    "id": item.uid, 
                    "x": round(p.x()/SCALE, 2), 
                    "y": round(p.y()/SCALE, 2)
                })
            elif item.data(0) == MineItemType.YARD:
                p = item.pos()
                data["yards"].append({
                    "name": item.yard_name, 
                    "x": round(p.x()/SCALE, 2), 
                    "y": round(p.y()/SCALE, 2), 
                    "w": item.w_m, 
                    "h": item.h_m
                })
            elif item.data(0) == MineItemType.MINER:
                p = item.pos()
                data["miners"].append({
                    "name": item.stats["name"],
                    "id": item.stats["id"],
                    "x": round(p.x()/SCALE, 2), 
                    "y": round(p.y()/SCALE, 2)
                })
        
        return data
    
    def import_data(self, data):
        """Імпортувати дані проекту зі словника"""
        self.scene.clear()
        self.junction_points = []
        self.miners = []
        self.repeater_count = 1
        
        for t in data.get("tunnels", []):
            line = QLineF(t["x1"]*SCALE, t["y1"]*SCALE, t["x2"]*SCALE, t["y2"]*SCALE)
            tunnel = TunnelGroup(line, self.scene)
            if "name" in t:
                tunnel.tunnel_name = t["name"]
            self.scene.addItem(tunnel)
            self.auto_create_junctions(tunnel)
        
        for d in data.get("devices", []):
            self.add_repeater(d["x"]*SCALE, d["y"]*SCALE, uid=d.get("id"))
        
        for y in data.get("yards", []):
            yard = YardItem(y["x"]*SCALE, y["y"]*SCALE, y["w"], y["h"])
            yard.update_name(y["name"])
            self.scene.addItem(yard)
        
        for m in data.get("miners", []):
            miner = MinerItem(m["id"], m["name"])
            miner.setPos(m["x"]*SCALE, m["y"]*SCALE)
            self.scene.addItem(miner)
            self.miners.append({"obj": miner, "target": None, "path": [], "idx": 0})
        
        self.project_saved = False
        self.current_project_file = None
    
    def closeEvent(self, event):
        """Обробка закриття вікна"""
        if self.settings.get("prompt_on_exit", True) and not self.project_saved:
            reply = QMessageBox.question(
                self, 
                "Підтвердження закриття",
                "Проєкт не збережено. Ви впевнені, що хочете закрити програму?\n\n"
                "Автозбереження буде збережено окремо.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self.export_json()
                event.accept()
            elif reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
                return
        
        # Зупинити таймери перед закриттям
        self.timer.stop()
        self.autosave_timer.stop()
        event.accept()
    
    def mark_project_saved(self, filename=None):
        """Позначити проект як збережений"""
        self.project_saved = True
        if filename:
            self.current_project_file = filename
            self.setWindowTitle(f"MineCAD v25.0 - {os.path.basename(filename)}")
    
    # [Інші методи залишаються без змін, тільки додаємо оновлення project_saved там, де потрібно]
    
    def export_json(self):
        data = self.export_data()
        fname, _ = QFileDialog.getSaveFileName(
            self, "Зберегти проект", "mine.json", "JSON (*.json)"
        )
        if fname:
            try:
                with open(fname, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self.mark_project_saved(fname)
                QMessageBox.information(self, "Збережено", "Проект успішно збережено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти: {e}")
    
    def import_json(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Відкрити проект", "", "JSON (*.json)"
        )
        if fname:
            try:
                with open(fname, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.import_data(data)
                self.mark_project_saved(fname)
                QMessageBox.information(self, "Завантажено", "Проект успішно завантажено!")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося завантажити: {e}")

    # [Решта методів залишаються без змін - set_mode, update_speed, toggle_wifi, add_yard, 
    # create_tunnel_logic, split_tunnel_at_point, find_or_create_junction, add_repeater, 
    # auto_create_junctions, spawn_miner, sim_tick, on_select, delete_single_item, 
    # set_miner_path_mode, get_snap, upload_to_server, eventFilter]

    def set_mode(self, m):
        self.mode = m
        if m == "select":
            self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.status.setText("Режим вибору")
        else:
            self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.status.setText(f"Режим: {m}")

    def update_speed(self, val):
        self.miner_speed_mult = val / 10.0

    def toggle_wifi(self, visible):
        self.show_wifi_ranges = visible
        for i in self.scene.items():
            if i.data(0) == MineItemType.DEVICE:
                i.toggle_range(visible)

    def add_yard(self):
        self.set_mode("place_yard")

    def create_tunnel_logic(self, line_geom):
        # 1. Перевіряємо, чи треба розрізати існуючі штреки
        p1 = line_geom.p1()
        p2 = line_geom.p2()
        
        # Спробуємо знайти штрек, на який лягла точка p1 або p2 (якщо це не кінець штреку)
        p1_junction = self.split_tunnel_at_point(p1)
        p2_junction = self.split_tunnel_at_point(p2)
        
        # Оновлюємо точки лінії, щоб вони починалися точно від junction, якщо такий був створений
        if p1_junction: p1 = p1_junction.pos()
        if p2_junction: p2 = p2_junction.pos()
        line_geom = QLineF(p1, p2)

        # 2. Створюємо новий штрек
        tunnel = TunnelGroup(line_geom, self.scene)
        self.scene.addItem(tunnel)
        self.auto_create_junctions(tunnel)
        
        # 3. Репітери
        length = line_geom.length()
        interval = self.wifi_interval * SCALE
        if length > 5 * SCALE:
            count = int(length // interval)
            if count == 0:
                self.add_repeater((p1.x()+p2.x())/2, (p1.y()+p2.y())/2)
            else:
                for i in range(1, count + 1):
                    r = (i * interval) / length
                    x = p1.x() + (p2.x()-p1.x())*r
                    y = p1.y() + (p2.y()-p1.y())*r
                    self.add_repeater(x, y)
        
        self.project_saved = False

    def split_tunnel_at_point(self, point):
        """
        Якщо точка лежить на штреку (не на кінцях), розрізає штрек на два.
        Повертає JunctionPoint або None.
        """
        for item in self.scene.items():
            if item.data(0) == MineItemType.TUNNEL:
                line = item.line_geom
                
                # Перевіряємо, чи точка близько до лінії
                nearest = nearest_point_on_line(line, point)
                dist_to_line = QLineF(nearest, point).length()
                
                if dist_to_line < 10: # Точка лежить на лінії
                    # Перевіряємо, чи це не один з кінців (з певним допуском)
                    dist_p1 = QLineF(line.p1(), nearest).length()
                    dist_p2 = QLineF(line.p2(), nearest).length()
                    
                    if dist_p1 > 20 and dist_p2 > 20: # Ми всередині лінії!
                        # 1. Видаляємо старий штрек
                        self.delete_single_item(item)
                        
                        # 2. Створюємо точку розгалуження
                        junction = JunctionPoint(nearest.x(), nearest.y())
                        self.scene.addItem(junction)
                        self.junction_points.append(junction)
                        
                        # 3. Створюємо два нових штреки
                        t1 = TunnelGroup(QLineF(line.p1(), nearest), self.scene)
                        t2 = TunnelGroup(QLineF(nearest, line.p2()), self.scene)
                        self.scene.addItem(t1)
                        self.scene.addItem(t2)
                        
                        self.auto_create_junctions(t1)
                        self.auto_create_junctions(t2)
                        
                        return junction
                        
                    # Якщо ми на кінці - повертаємо існуючий junction або створюємо новий
                    elif dist_p1 <= 20:
                        return self.find_or_create_junction(line.p1())
                    elif dist_p2 <= 20:
                        return self.find_or_create_junction(line.p2())
                        
        return None

    def find_or_create_junction(self, pos):
        for j in self.junction_points:
            if QLineF(j.pos(), pos).length() < 20:
                return j
        j = JunctionPoint(pos.x(), pos.y())
        self.scene.addItem(j)
        self.junction_points.append(j)
        return j

    def add_repeater(self, x, y, uid=None):
        if uid is None:
            uid = f"AP-{self.repeater_count}"
            self.repeater_count += 1
        dev = WifiIconItem(uid, x, y)
        if self.show_wifi_ranges: dev.toggle_range(True)
        self.scene.addItem(dev)
        self.project_saved = False
        return dev

    def auto_create_junctions(self, tunnel):
        for p in [tunnel.line_geom.p1(), tunnel.line_geom.p2()]:
            existing = None
            for j in self.junction_points:
                if QLineF(j.pos(), p).length() < 20:
                    existing = j
                    break
            if not existing:
                existing = JunctionPoint(p.x(), p.y())
                self.scene.addItem(existing)
                self.junction_points.append(existing)
            existing.add_tunnel(tunnel)
            
            # Прив'язуємо
            if QLineF(tunnel.line_geom.p1(), existing.pos()).length() < 5:
                tunnel.junction_start = existing
            else:
                tunnel.junction_end = existing

    def spawn_miner(self):
        if not self.junction_points:
            QMessageBox.warning(self, "Увага", "Спочатку створіть штреки!")
            return
        j = random.choice(self.junction_points)
        m = MinerItem(f"M-{len(self.miners)+1}", f"Шахтар {len(self.miners)+1}")
        m.setPos(j.pos())
        self.scene.addItem(m)
        self.miners.append({"obj": m, "target": None, "path": [], "idx": 0})
        self.project_saved = False

    def sim_tick(self):
        speed = 3.0 * self.miner_speed_mult
        for data in self.miners:
            miner = data["obj"]
            
            if random.random() < 0.05:
                miner.stats["heart"] = max(40, min(180, miner.stats["heart"] + random.randint(-5, 5)))
                miner.stats["bat"] = max(0, miner.stats["bat"] - 0.05)
                if self.inspector.current_item == miner:
                    self.inspector.update_miner_ui(miner)

            if miner.path:
                if miner.move_along_path(speed): continue
                else: miner.path = []
            
            # AI: Блукання
            if not miner.path and self.junction_points:
                curr = miner.pos()
                
                # Знаходимо найближчий junction
                nearest = None
                min_dist = 9999
                for j in self.junction_points:
                    d = QLineF(j.pos(), curr).length()
                    if d < min_dist:
                        min_dist = d
                        nearest = j
                
                if nearest and nearest.connected_tunnels:
                    # Вибрати штрек, але не той, звідки прийшли (якщо можливо)
                    available_tunnels = nearest.connected_tunnels[:]
                    if len(available_tunnels) > 1 and "last_tunnel" in data:
                      if data["last_tunnel"] in available_tunnels:
                          available_tunnels.remove(data["last_tunnel"])
                    
                    tun = random.choice(available_tunnels)
                    data["last_tunnel"] = tun
                    line = tun.line_geom
                    
                    p1, p2 = line.p1(), line.p2()
                    target = p2 if QLineF(curr, p1).length() < QLineF(curr, p2).length() else p1
                    
                    path = []
                    steps = int(line.length() / 50) + 1
                    for i in range(steps + 1):
                        r = i / steps
                        path.append(QPointF(line.x1() + (line.x2()-line.x1())*r, 
                                          line.y1() + (line.y2()-line.y1())*r))
                    if target == p1: path.reverse()
                    
                    miner.set_path(path)

    def on_select(self):
        try:
            sel = self.scene.selectedItems()
            self.inspector.set_item(sel[0] if sel else None)
        except: pass

    def delete_single_item(self, item):
        if item.data(0) == MineItemType.MINER:
            self.miners = [m for m in self.miners if m["obj"] != item]
        elif item.data(0) == MineItemType.JUNCTION:
            if item in self.junction_points: self.junction_points.remove(item)
        elif item.data(0) == MineItemType.TUNNEL:
            if hasattr(item, 'junction_start') and item.junction_start:
                item.junction_start.remove_tunnel(item)
            if hasattr(item, 'junction_end') and item.junction_end:
                item.junction_end.remove_tunnel(item)
        
        self.scene.removeItem(item)
        self.project_saved = False

    def set_miner_path_mode(self, miner):
        self.current_miner_path = miner
        self.miner_path_points = [miner.pos()]
        self.set_mode("set_miner_path")
        self.status.setText("Вкажіть точки маршруту. ПКМ - завершити")

    def get_snap(self, pos):
        """Розумне прилипання до точок АБО до ліній"""
        snap_dist = TUNNEL_SNAP_DISTANCE
        closest = None
        min_d = snap_dist
        
        # 1. Прилипання до точок (пріоритет)
        for item in self.scene.items():
            if item.data(0) == MineItemType.JUNCTION:
                d = QLineF(pos, item.pos()).length()
                if d < min_d:
                    min_d = d
                    closest = item.pos()
            elif item.data(0) == MineItemType.TUNNEL:
                l = item.line_geom
                for p in [l.p1(), l.p2()]:
                    d = QLineF(pos, p).length()
                    if d < min_d:
                        min_d = d
                        closest = p
        
        if closest: return closest

        # 2. Прилипання до тіла штреку (якщо не знайшли точку)
        for item in self.scene.items():
            if item.data(0) == MineItemType.TUNNEL:
                line = item.line_geom
                nearest = nearest_point_on_line(line, pos)
                dist = QLineF(pos, nearest).length()
                if dist < 15: # Відстань прилипання до лінії
                    return nearest
                    
        return None

    def upload_to_server(self):
      # 1. Формуємо дані так само, як для експорту в файл
      data = self.export_data()

      # 2. Питаємо адресу сервера (щоб не хардкодити)
      url, ok = QInputDialog.getText(self, "Upload", "Адреса сервера API:", text="https://bunb.pp.ua/diploma/api/upload-map/")

      if ok and url:
          try:
              headers = {"X-API-Key": os.environ.get("ESP32_API_KEY", "SecretMineKey2026")}
              response = requests.post(url, json=data, headers=headers, timeout=5)
              if response.status_code == 200:
                  res_json = response.json()
                  msg = res_json.get('message') or f"Синхронізовано {res_json.get('sync', 0)} репітерів."
                  QMessageBox.information(self, "Успіх", f"Дані відправлено. Сервер: {msg}")
              else:
                  QMessageBox.warning(self, "Помилка", f"Сервер повернув код {response.status_code}:\n{response.text}")
          except Exception as e:
              QMessageBox.critical(self, "Помилка з'єднання", str(e))
    
    def eventFilter(self, src, evt):
        if src == self.view.viewport():
            if evt.type() == evt.Type.Wheel:
                f = 1.15 if evt.angleDelta().y() > 0 else 1/1.15
                self.view.scale(f, f)
                return True
            
            if evt.type() == evt.Type.MouseButtonPress:
                if evt.buttons() & Qt.MouseButton.LeftButton:
                    if evt.modifiers() & Qt.KeyboardModifier.ControlModifier:
                        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                        fake = QMouseEvent(evt.type(), evt.position(), evt.globalPosition(), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
                        self.view.mousePressEvent(fake)
                        return True
                    
                    pos = self.view.mapToScene(evt.pos())
                    
                    if self.mode == "place_yard":
                        w, h = self.pending_yard_size
                        yard = YardItem(pos.x(), pos.y(), w, h)
                        self.scene.addItem(yard)
                    
                        # Автоматично створюємо центральний репітер у Руддворі
                        self.add_repeater(pos.x(), pos.y(), uid="AP-MAIN")
                    
                        self.set_mode("select")
                        self.project_saved = False
                        return True
                    
                    elif self.mode == "draw_tunnel":
                        snap = self.get_snap(pos)
                        self.start_pos = snap if snap else pos
                        self.temp_line = self.scene.addLine(QLineF(self.start_pos, self.start_pos), QPen(Qt.GlobalColor.yellow, 2, Qt.PenStyle.DashLine))
                        return True
                        
                    elif self.mode == "set_miner_path":
                        snap = self.get_snap(pos)
                        pt = snap if snap else pos
                        self.miner_path_points.append(pt)
                        if len(self.miner_path_points) > 1:
                            l = self.scene.addLine(QLineF(self.miner_path_points[-2], pt), 
                                                 QPen(QColor(255, 255, 0, 100), 2))
                            l.setZValue(500)
                        return True

                elif evt.button() == Qt.MouseButton.RightButton:
                    if self.mode == "set_miner_path" and self.current_miner_path:
                        self.current_miner_path.set_path(self.miner_path_points)
                        for i in self.scene.items():
                            if isinstance(i, QGraphicsLineItem) and i.zValue() == 500:
                                self.scene.removeItem(i)
                        self.set_mode("select")
                        return True
            
            if evt.type() == evt.Type.MouseButtonRelease:
                if self.view.dragMode() == QGraphicsView.DragMode.ScrollHandDrag:
                    self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag if self.mode == "select" else QGraphicsView.DragMode.NoDrag)
                    return True
                
                if evt.button() == Qt.MouseButton.LeftButton and self.mode == "draw_tunnel" and self.temp_line:
                    line = self.temp_line.line()
                    self.scene.removeItem(self.temp_line)
                    self.temp_line = None
                    if line.length() > 5:
                        self.create_tunnel_logic(line)
                    return True

            if evt.type() == evt.Type.MouseMove:
                pos = self.view.mapToScene(evt.pos())
                if self.mode == "draw_tunnel" and self.temp_line:
                    snap = self.get_snap(pos)
                    self.temp_line.setLine(QLineF(self.start_pos, snap if snap else pos))
                    return True

        return super().eventFilter(src, evt)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MineCAD()
    w.show()
    sys.exit(app.exec())