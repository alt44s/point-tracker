import sys
import sqlite3
import os
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QToolBar, QAction, QMenu, QDialog, QComboBox, QDialogButtonBox, QSpinBox, QFontComboBox, QFrame)
from PyQt5.QtCore import Qt, QRect, QTimer, QSettings
from PyQt5.QtGui import QPainter, QColor, QFont
import json

VERSION = "1.0.0"

def initialize_database():
    if not os.path.exists('points.db'):
        conn = sqlite3.connect('points.db')
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS points (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            points INTEGER NOT NULL
        )
        ''')
        conn.commit()
        conn.close()

def check_database_integrity():
    if not os.path.exists('points.db'):
        return False, "Database file does not exist."

    try:
        conn = sqlite3.connect('points.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='points';")
        if not cursor.fetchone():
            return False, "Table 'points' does not exist."

        cursor.execute("SELECT COUNT(*) FROM points;")
        count = cursor.fetchone()[0]
        if count == 0:
            return False, "The 'points' table is empty."

        cursor.execute("PRAGMA table_info(points);")
        columns = [column[1] for column in cursor.fetchall()]
        required_fields = ['id', 'date', 'points']
        for field in required_fields:
            if field not in columns:
                return False, f"Required field '{field}' is missing."

        return True, "Database integrity check passed."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        conn.close()

def is_valid_date(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def load_settings():
    defaults = {"theme": "dark", "points_per_day": 10, "font": "Arial"}
    
    if os.path.exists('settings.json'):
        try:
            with open('settings.json', 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading settings: {e}. Clearing settings.")
            return defaults
    return defaults

def save_settings(settings):
    with open('settings.json', 'w') as f:
        json.dump(settings, f)

class PreferencesDialog(QDialog):
    def __init__(self, current_theme, current_points_per_day, current_font, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        
        self.theme_combo = QComboBox(self)
        self.theme_combo.addItems(["Light Theme", "Dark Theme"])
        if current_theme == "light":
            self.theme_combo.setCurrentIndex(0)
        else:
            self.theme_combo.setCurrentIndex(1)

        self.points_spinbox = QSpinBox(self)
        self.points_spinbox.setMinimum(0)
        self.points_spinbox.setMaximum(10000)
        self.points_spinbox.setValue(current_points_per_day)

        self.font_combo = QFontComboBox(self)
        self.font_combo.setCurrentFont(current_font)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select Theme:"))
        layout.addWidget(self.theme_combo)
        layout.addWidget(QLabel("Select Font:"))
        layout.addWidget(self.font_combo)
        layout.addWidget(QLabel("Points per Day:"))
        layout.addWidget(self.points_spinbox)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)
        self.setLayout(layout)

    def get_selected_theme(self):
        return "light" if self.theme_combo.currentIndex() == 0 else "dark"

    def get_points_per_day(self):
        return self.points_spinbox.value()

    def get_selected_font(self):
        return self.font_combo.currentFont()

class CustomTooltip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("font-size: 10pt;")

        self.label = QLabel(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.setContentsMargins(0, 0, 0, 0)

    def set_text(self, text):
        self.label.setText(text)
        self.adjustSize()

class HeatmapCalendar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points_data = {}
        self.setMouseTracking(True)
        self.setMinimumSize(350, 40)
        self.default_color = QColor(30, 30, 30)
        self.hovered_square = -1
        self.highlight_opacity = 0
        self.fade_in_timer = QTimer(self)
        self.fade_in_timer.timeout.connect(self.fade_in)
        self.current_week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        self.tooltip = CustomTooltip(self)
        self.parent = parent

    def set_points_data(self, points_data):
        self.points_data = points_data
        self.update()
        
    def set_target_points_per_day(self, target_points):
        self.target_points_per_day = target_points
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        size = min(self.width() // 6, self.height() - 5)

        painter.setPen(Qt.transparent)
        
        spacing = 5
        
        total_width = size * 7 + spacing * 6
        start_x = (self.width() - total_width) // 2
        y = (self.height() - size) // 4

        for i in range(7):
            date = (self.current_week_start + timedelta(days=i)).strftime("%Y-%m-%d")
            points = self.points_data.get(date, 0)

            x = start_x + i * (size + spacing)

            painter.setBrush(self.default_color)
            painter.drawRoundedRect(QRect(x, y, size, size), 5, 5)

            if points > 0:
                if self.target_points_per_day > 0:
                    self.color_value = min(155, int((points / self.target_points_per_day) * 155))
                else:
                    self.color_value = 0
                color = QColor(0, self.color_value, 0, self.color_value)
                painter.setBrush(color)
                painter.drawRoundedRect(QRect(x, y, size, size), 5, 5)

            if i == self.hovered_square and points > 0:
                highlight_color = QColor(0, self.color_value + 10, 0, self.highlight_opacity)
                painter.setBrush(highlight_color)
                painter.drawRoundedRect(QRect(x, y, size, size), 5, 5)

    def mouseMoveEvent(self, event):
        size = min(self.width() // 6, self.height() - 5)
        spacing = 5

        adjusted_width = size + spacing
        start_x = (self.width() - (size * 7 + spacing * 6)) // 2
        y = (self.height() - size) // 4

        x = event.x() - start_x

        if 0 <= y <= event.y() < y + size:
            square_index = x // adjusted_width
            if 0 <= square_index < 7:
                date = (self.current_week_start + timedelta(days=square_index)).strftime("%Y-%m-%d")
                points = self.points_data.get(date, 0)
                tooltip_text = f"Date: {date}\nPoints: {points}"
                self.tooltip.set_text(tooltip_text)
                
                tooltip_x = event.globalX() + 10
                tooltip_y = event.globalY() + 10
                self.tooltip.move(tooltip_x, tooltip_y)
                self.tooltip.show()

                if self.hovered_square != square_index:
                    self.hovered_square = square_index
                    self.highlight_opacity = 0
                    if points > 0:
                        self.fade_in_timer.start(30)
            else:
                self.hovered_square = -1
                self.highlight_opacity = 0
                self.fade_in_timer.stop()
        else:
            self.tooltip.hide()
            self.hovered_square = -1
            self.highlight_opacity = 0
            self.fade_in_timer.stop()

        self.update()
        
    def mousePressEvent(self, event):
        size = min(self.width() // 6, self.height() - 5)
        spacing = 5

        adjusted_width = size + spacing
        start_x = (self.width() - (size * 7 + spacing * 6)) // 2
        y = (self.height() - size) // 4

        x = event.x() - start_x
        
        if 0 <= y <= event.y() < y + size:
            square_index = x // adjusted_width
            if 0 <= square_index < 7:
                date = (self.current_week_start + timedelta(days=square_index)).strftime("%Y-%m-%d")
                if event.modifiers() and Qt.ControlModifier:
                    if event.button() == Qt.RightButton:
                        self.parent.update_points(-1, date)
                    else:
                        self.parent.update_points(1, date)
                else:
                    self.parent.set_date(date)

        super().mousePressEvent(event)
        
    def fade_in(self):
        self.highlight_opacity += 30
        if self.highlight_opacity > 255:
            self.highlight_opacity = 255
        self.update()

    def set_week_start(self, week_start):
        self.current_week_start = week_start
        self.update()

class PointsTracker(QMainWindow):
    def __init__(self):
        initialize_database()
        settings = load_settings()
        super().__init__()
        self.current_theme = settings.get("theme", "dark")
        self.font_name = settings.get("font", "Arial")
        self.current_font = QFont(self.font_name, 12)
        self.points_per_day = settings.get("points_per_day", 0)
        self.init_ui()
        self.update_points_display()
        self.apply_theme(self.current_font)
        self.load_geometry()

    def init_ui(self):
        self.setWindowTitle("Points Tracker")
        self.setGeometry(100, 100, 300, 300)

        toolbar = QToolBar("Toolbar", self)
        toolbar.setObjectName("Points Toolbar")
        toolbar.setStyleSheet("font-size: 9pt;")
        self.addToolBar(toolbar)

        edit_menu = QMenu("Edit", self)
        edit_menu.setStyleSheet("font-size: 9pt;")

        edit_button = QPushButton("Edit", self)
        edit_button.setMenu(edit_menu)
        edit_button.setFixedWidth(50)
        toolbar.addWidget(edit_button)
        
        preferences = QAction("Preferences", self)
        preferences.triggered.connect(self.open_preferences)
        edit_menu.addAction(preferences)
        
        help_menu = QMenu("Help", self)
        help_menu.setStyleSheet("font-size: 9pt;")

        help_button = QPushButton("Help", self)
        help_button.setMenu(help_menu)
        help_button.setFixedWidth(50)
        toolbar.addWidget(help_button)
        
        help = QAction("Info", self)
        help.triggered.connect(self.show_help_dialog)
        help_menu.addAction(help)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        self.background_frame = QFrame(self)
        self.background_frame.setFixedWidth(250)
        background_layout = QVBoxLayout(self.background_frame)

        self.date_label = QLabel("Date (YYYY-MM-DD):", self)
        background_layout.addWidget(self.date_label, alignment=Qt.AlignCenter)

        self.date_entry = QLineEdit(self)
        self.date_entry.setFixedWidth(150)
        background_layout.addWidget(self.date_entry, alignment=Qt.AlignCenter)

        self.set_date()

        self.points_label = QLabel("Points:", self)
        background_layout.addWidget(self.points_label, alignment=Qt.AlignCenter)

        self.points_entry = QSpinBox(self)
        self.points_entry.setMinimum(0)
        self.points_entry.setMaximum(10000)
        self.points_entry.setValue(0)
        self.points_entry.setFixedWidth(150)
        
        background_layout.addWidget(self.points_entry, alignment=Qt.AlignCenter)

        layout.addWidget(self.background_frame, alignment=Qt.AlignCenter)

        layout.addSpacing(10)

        self.add_button = QPushButton("Add Points", self)
        self.add_button.setFixedWidth(140)
        self.add_button.clicked.connect(lambda: self.update_points(1))
        
        self.remove_button = QPushButton("Remove Points", self)
        self.remove_button.setFixedWidth(140)
        self.remove_button.clicked.connect(lambda: self.update_points(-1))
        
        self.add_button.setStyleSheet("""
            background-color: #4CAF50; 
            color: white; 
            font-size: 10pt; 
            border-radius: 7px; 
            padding: 7px;
        """)
        self.remove_button.setStyleSheet("""
            background-color: #F44336; 
            color: white; 
            font-size: 10pt; 
            border-radius: 7px; 
            padding: 7px;
        """)
        
        adrem_button_layout = QHBoxLayout()
        adrem_button_layout.addWidget(self.add_button)
        adrem_button_layout.addWidget(self.remove_button)
        
        layout.addLayout(adrem_button_layout)

        layout.addSpacing(20)

        self.heatmap_calendar = HeatmapCalendar(self)
        layout.addWidget(self.heatmap_calendar, alignment=Qt.AlignCenter)
        
        layout.addSpacing(10)
        
        self.prev_week_button = QPushButton("<")
        self.prev_week_button.setFixedWidth(50)
        self.prev_week_button.clicked.connect(self.show_previous_week)

        self.next_week_button = QPushButton(">")
        self.next_week_button.setFixedWidth(50)
        self.next_week_button.clicked.connect(self.show_next_week)
        
        prevnext_button_layout = QHBoxLayout()
        prevnext_button_layout.addWidget(self.prev_week_button)
        prevnext_button_layout.addWidget(self.next_week_button)
        
        layout.addLayout(prevnext_button_layout)

        central_widget.setLayout(layout)
        
    def closeEvent(self, event):
        self.save_geometry()
        event.accept()

    def save_geometry(self):
        settings = QSettings("Points Tracker")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def load_geometry(self):
        settings = QSettings("Points Tracker")
        geometry = settings.value("geometry")
        window_state = settings.value("windowState")

        if geometry:
            self.restoreGeometry(geometry)
        if window_state:
            self.restoreState(window_state)
        
    def show_previous_week(self):
        new_week_start = self.heatmap_calendar.current_week_start - timedelta(weeks=1)
        self.heatmap_calendar.set_week_start(new_week_start)
        self.update_points_display()

    def show_next_week(self):
        new_week_start = self.heatmap_calendar.current_week_start + timedelta(weeks=1)
        self.heatmap_calendar.set_week_start(new_week_start)
        self.update_points_display()
        
    def show_help_dialog(self):
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Information")
        help_dialog.setFixedSize(300, 200)

        layout = QVBoxLayout()

        help_label = QLabel(
            'Points Tracker developed by <a href="https://github.com/alt44s">alt4s</a><br><br>'
            'You can use this application to track arbitrary points.<br>'
            'Enter the date and the points you want to add or remove.<br><br>'
            'Hold down CTRL and left-click to add points or right-click to remove points on the heatmap; without CTRL, clicking selects the date of the square.',
            self
        )
        help_label.setOpenExternalLinks(True)
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        version_label = QLabel(f"Version: {VERSION}", self)
        layout.addWidget(version_label)

        close_button = QPushButton("Close", self)
        close_button.clicked.connect(help_dialog.close)
        layout.addWidget(close_button)

        help_dialog.setLayout(layout)
        help_dialog.exec_()

    def apply_font_to_all_widgets(self, font):
        for widget in self.findChildren(QWidget):
            widget.setFont(font)

    def apply_theme(self, font=None):
        if font is not None:
            self.apply_font_to_all_widgets(font)
        
        if self.current_theme == "light":
            self.setStyleSheet("background-color: #FFFFFF; color: black;")
            self.background_frame.setStyleSheet("background-color: #DEDEDE; border-radius: 10px; padding: 5px;")
            self.date_label.setStyleSheet("color: black; font-size: 10pt;")
            self.points_label.setStyleSheet("color: black; font-size: 10pt;")
            self.date_entry.setStyleSheet("background-color: #F0F0F0; color: black; font-size: 12pt; border-radius: 2px; padding: 4px;")
            self.points_entry.setStyleSheet("background-color: #F0F0F0; color: black; font-size: 12pt; border-radius: 2px; padding: 4px;")
            self.prev_week_button.setStyleSheet("background-color: #F0F0F0; border-radius: 2px; padding: 4px;")
            self.next_week_button.setStyleSheet("background-color: #F0F0F0; border-radius: 2px; padding: 4px;")
            self.heatmap_calendar.default_color = QColor(120, 120, 120)
            self.heatmap_calendar.tooltip.label.setStyleSheet("background-color: #F0F0F0; color: black; padding: 5px; border-radius: 5px;")
        else:
            self.setStyleSheet("background-color: #2E2E2E; color: white;")
            self.background_frame.setStyleSheet("background-color: #333; border-radius: 10px; padding: 5px;")
            self.date_label.setStyleSheet("color: white; font-size: 10pt;")
            self.points_label.setStyleSheet("color: white; font-size: 10pt;")
            self.date_entry.setStyleSheet("background-color: #4A4A4A; color: white; font-size: 12pt; border-radius: 2px; padding: 4px;")
            self.points_entry.setStyleSheet("background-color: #4A4A4A; color: white; font-size: 12pt; border-radius: 2px; padding: 4px;")
            self.prev_week_button.setStyleSheet("background-color: #1E1E1E; border-radius: 2px; padding: 4px;")
            self.next_week_button.setStyleSheet("background-color: #1E1E1E; border-radius: 2px; padding: 4px;")
            self.heatmap_calendar.default_color = QColor(30, 30, 30)
            self.heatmap_calendar.tooltip.label.setStyleSheet("background-color: #1E1E1E; color: white; padding: 5px; border-radius: 5px;")

    def open_preferences(self):
        dialog = PreferencesDialog(self.current_theme, self.points_per_day, self.current_font, self)
        if dialog.exec_() == QDialog.Accepted:
            selected_theme = dialog.get_selected_theme()
            selected_font = dialog.get_selected_font()
            self.points_per_day = dialog.get_points_per_day()
            
            if selected_theme != self.current_theme:
                self.current_theme = selected_theme
                
            self.current_font = selected_font
            self.apply_theme(selected_font)
                
            save_settings({"theme": self.current_theme, "points_per_day": self.points_per_day, "font": selected_font.family()})
            
    def set_date(self, date=None):
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        self.date_entry.setText(date)

    def update_points(self, operation, date=None):
        if not date:
            date = self.date_entry.text()
        points = self.points_entry.text()

        if not is_valid_date(date):
            QMessageBox.critical(self, "Error", "Please enter a valid date in YYYY-MM-DD format.")
            return

        if points.isdigit():
            try:
                conn = sqlite3.connect('points.db')
                cursor = conn.cursor()

                cursor.execute("SELECT points FROM points WHERE date = ?", (date,))
                existing_row = cursor.fetchone()

                if existing_row:
                    if operation == 1:
                        new_points = existing_row[0] + int(points)
                        cursor.execute("UPDATE points SET points = ? WHERE date = ?", (new_points, date))
                        QMessageBox.information(self, "Success", f"Updated points for {date}. Total points: {new_points}")
                    elif operation == -1:
                        new_points = existing_row[0] - int(points)
                        if new_points <= 0:
                            cursor.execute("DELETE FROM points WHERE date = ?", (date,))
                            QMessageBox.information(self, "Success", f"Points for {date} have been deleted.")
                        else:
                            cursor.execute("UPDATE points SET points = ? WHERE date = ?", (new_points, date))
                            QMessageBox.information(self, "Success", f"Updated points for {date}. Total points: {new_points}")
                else:
                    if operation == 1:
                        cursor.execute("INSERT INTO points (date, points) VALUES (?, ?)", (date, int(points)))
                        QMessageBox.information(self, "Success", f"Points added successfully! Total points: {points}")
                    else:
                        QMessageBox.warning(self, "Warning", "No points recorded for this date.")

                conn.commit()
                self.update_points_display()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Error", f"An error occurred: {e}")
            finally:
                conn.close()
        else:
            QMessageBox.critical(self, "Error", "Please enter a valid number of points.")

    def update_points_display(self):
        conn = sqlite3.connect('points.db')
        cursor = conn.cursor()
        cursor.execute("SELECT date, points FROM points")
        rows = cursor.fetchall()
        conn.close()

        points_data = {row[0]: row[1] for row in rows}
        self.heatmap_calendar.set_points_data(points_data)
        self.heatmap_calendar.set_target_points_per_day(self.points_per_day)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    tracker = PointsTracker()
    tracker.show()
    sys.exit(app.exec_())