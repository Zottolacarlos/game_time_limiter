from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel,
    QPushButton, QVBoxLayout, QWidget, QSystemTrayIcon, QMenu, QAction
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from game_time_limiter.monitor import Monitor, DEFAULT_LIMIT
from pathlib import Path

class Worker(QThread):
    tick = Signal(int)           # segundos restantes

    def __init__(self, limit):
        super().__init__()
        self._monitor = Monitor(limit)

    def run(self):
        while not self.isInterruptionRequested():   # ← ① salir si la GUI lo pide
            self.monitor.loop_step()
            remaining = int(
                self.monitor.limit.total_seconds()
                - self.monitor.usage[self.monitor.today]
            )
            self.tick.emit(max(remaining, 0))
            self.msleep(5000)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Time Limiter")
        self.label = QLabel("Tiempo restante: --:--:--", alignment=Qt.AlignCenter)
        self.btn = QPushButton("Iniciar")
        self.btn.clicked.connect(self.toggle)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.btn)
        central = QWidget(); central.setLayout(layout)
        self.setCentralWidget(central)

        # Tray
        tray_icon = QSystemTrayIcon(self)
        tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        menu = QMenu()
        quit_act = QAction("Salir"); quit_act.triggered.connect(QApplication.quit)
        menu.addAction(quit_act)
        tray_icon.setContextMenu(menu)
        tray_icon.show()
        self.tray = tray_icon

        self.worker = None

    def toggle(self):
        # ---------- Detener ----------
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()   # ① pedimos que acabe el while
            self.worker.wait(1000)              # ② esperamos hasta 1 s
            self.worker = None
            self.button.setText("Iniciar")
            return

        # ---------- Iniciar ----------
        limit = timedelta(hours=self.spin_hours.value(),
                        minutes=self.spin_mins.value())
        self.worker = Worker(limit)
        self.worker.tick.connect(self.update_time)
        self.worker.start()
        self.button.setText("Detener")

    @Slot(int)
    def update_time(self, seconds):
        hh, mm = divmod(seconds//60, 60)
        ss = seconds % 60
        text = f"{hh:02}:{mm:02}:{ss:02}"
        self.label.setText(f"Tiempo restante: {text}")
        self.tray.setToolTip(f"Tiempo restante: {text}")

def run():
    #import qdarktheme
    import qdarkstyle

    app = QApplication([])
    #qdarktheme.setup_theme()
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    mw = MainWindow(); mw.resize(300, 150); mw.show()
    app.exec()

if __name__ == "__main__":
    run()