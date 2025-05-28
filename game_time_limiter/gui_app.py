from __future__ import annotations

import json
import sys
from datetime import timedelta
from datetime import date      
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
    QStyle,
)

from game_time_limiter.monitor import Monitor, DEFAULT_LIMIT
from game_time_limiter.utils import parse_timedelta
from game_time_limiter.monitor import POLL_INTERVAL

# ------------------------------------------------------------------ #
# Configuración persistente
# ------------------------------------------------------------------ #
CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"

DEFAULT_CONF = {
    "hours": 2,
    "minutes": 0,
    "auto_start": False,
}

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return {**DEFAULT_CONF, **json.loads(CONFIG_FILE.read_text())}
        except json.JSONDecodeError:
            pass
    return DEFAULT_CONF.copy()

def save_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


# ------------------------------------------------------------------ #
# Hilo que ejecuta el Monitor sin bloquear la UI
# ------------------------------------------------------------------ #
class Worker(QThread):
    tick = Signal(int)  # segundos restantes

    def __init__(self, limit: timedelta):
        super().__init__()
        self.monitor = Monitor(limit)

    def run(self):
        while True:
            self.monitor.loop_step()
            remaining = int(
                self.monitor.limit.total_seconds() - self.monitor.usage[self.monitor.today]
            )
            self.tick.emit(max(remaining, 0))
            self.msleep(5000) 


# ------------------------------------------------------------------ #
# Ventana principal
# ------------------------------------------------------------------ #
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Time Limiter")
        self.cfg = load_config()

        # Widgets de configuración
        self.spin_hours = QSpinBox(); self.spin_hours.setRange(0, 12)
        self.spin_mins  = QSpinBox(); self.spin_mins.setRange(0, 55); self.spin_mins.setSingleStep(5)
        self.auto_cb    = QCheckBox("Auto-iniciar al abrir aplicación")

        self.spin_hours.setValue(self.cfg["hours"])
        self.spin_mins.setValue(self.cfg["minutes"])
        self.auto_cb.setChecked(self.cfg["auto_start"])

        form = QFormLayout()
        form.addRow("Horas:", self.spin_hours)
        form.addRow("Minutos:", self.spin_mins)
        form.addRow("", self.auto_cb)

        self.label  = QLabel("Tiempo restante: --:--:--", alignment=Qt.AlignCenter)
        self.button = QPushButton("Iniciar")
        self.button.clicked.connect(self.toggle)
        
        # --- crea el icono de bandeja ANTES de update_time ---
        self.tray = QSystemTrayIcon(
            self.style().standardIcon(QStyle.SP_ComputerIcon), self
        )
        self.tray.setToolTip("Game Time Limiter")
        self.tray.show()
        # ------------------------------------------------------------------
        #  ▼  NUEVO bloque – calcula y pinta el tiempo restante al arrancar
        # ------------------------------------------------------------------
        today_key = date.today().isoformat()                 # "2025-05-22"
        already_played = Monitor().usage.get(today_key, 0)   # segundos acumulados
        initial_remaining = int(DEFAULT_LIMIT.total_seconds() - already_played)
        self.update_time(initial_remaining)                  # muestra en la etiqueta
        

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.label)
        layout.addWidget(self.button)

        central = QWidget(); central.setLayout(layout)
        self.setCentralWidget(central)
        self.resize(320, 200)

        # Bandeja
        self.tray = QSystemTrayIcon(
            self.style().standardIcon(QStyle.SP_ComputerIcon), self
        )
        self.tray.setToolTip("Game Time Limiter")
        self.tray.show()

        self.worker: Worker | None = None

        # Auto-start si la casilla está marcada
        if self.auto_cb.isChecked():
            QTimer.singleShot(100, self.toggle)

    # ------------- lógica -------------
    def build_limit(self) -> timedelta:
        return timedelta(hours=self.spin_hours.value(),
                         minutes=self.spin_mins.value())

    def toggle(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker = None
            self.button.setText("Iniciar")
            return

        self.worker = Worker(self.build_limit())
        self.worker.tick.connect(self.update_time)
        self.worker.start()
        self.button.setText("Detener")

    @Slot(int)
    def update_time(self, seconds: int):
        h, m = divmod(seconds // 60, 60)
        s = seconds % 60
        text = f"{h:02}:{m:02}:{s:02}"
        self.label.setText(f"Tiempo restante: {text}")
        self.tray.setToolTip(f"Tiempo restante: {text}")

    # -------- persistencia al cerrar --------
    def closeEvent(self, event):
        self.cfg.update(
            hours=self.spin_hours.value(),
            minutes=self.spin_mins.value(),
            auto_start=self.auto_cb.isChecked(),
        )
        save_config(self.cfg)
        super().closeEvent(event)


# ------------------------------------------------------------------ #
def run():
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()