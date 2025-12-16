from PySide6.QtWidgets import (
    QWidget, QLineEdit, QComboBox,
    QTabWidget, QVBoxLayout, QFormLayout, QPushButton, QSizePolicy
)
from PySide6.QtCore import Signal

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT

from SOURCES.utils import INPUT_DIR, OUTPUT_DIR
from PySide6.QtWidgets import QLabel, QHBoxLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


DARK_BG = "#121212"


def style_dark_2d(ax, fig):
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)

    ax.tick_params(colors="white")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    ax.title.set_color("white")

    for spine in ax.spines.values():
        spine.set_color("white")

    ax.grid(True, alpha=0.25)


def style_dark_3d(ax, fig):
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)

    ax.tick_params(colors="white")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    ax.zaxis.label.set_color("white")
    ax.title.set_color("white")

    try:
        ax.xaxis.pane.set_facecolor((0.07, 0.07, 0.07, 1.0))
        ax.yaxis.pane.set_facecolor((0.07, 0.07, 0.07, 1.0))
        ax.zaxis.pane.set_facecolor((0.07, 0.07, 0.07, 1.0))
        ax.xaxis.pane.set_edgecolor("white")
        ax.yaxis.pane.set_edgecolor("white")
        ax.zaxis.pane.set_edgecolor("white")
    except Exception:
        pass


def load_report(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No se encuentra el report: {path}")

    df = pd.read_csv(path, sep=r"\s+", engine="python")
    df = df.apply(pd.to_numeric, errors="coerce").dropna()

    if df.shape[1] < 7:
        raise ValueError(
            f"El report tiene {df.shape[1]} columnas, pero se esperaban al menos 7."
        )

    return df


def leer_tiempos_burn(datos_path: Path):
    tiempos = []
    if not datos_path.exists():
        return tiempos

    with datos_path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip().lower()
            if s.startswith("tiempo burn"):
                if ":" in s:
                    _, val = s.split(":", 1)
                    val = val.strip().replace(",", ".")
                    try:
                        tiempos.append(float(val))
                    except ValueError:
                        pass
    return tiempos


def make_figures(df: pd.DataFrame, datos_path: Path):
    plt.close("all")

    cols = df.columns.tolist()
    t = df[cols[0]].values
    x = df[cols[1]].values
    y = df[cols[2]].values
    z = df[cols[3]].values
    vx = df[cols[4]].values
    vy = df[cols[5]].values
    vz = df[cols[6]].values

    speed = np.sqrt(vx**2 + vy**2 + vz**2)
    r = np.sqrt(x**2 + y**2 + z**2)

    burn_times = leer_tiempos_burn(datos_path)

    figures = []

    # 1) Trayectoria 3D
    fig1 = plt.figure()
    ax1 = fig1.add_subplot(111, projection="3d")
    ax1.plot(x, y, z, color="cyan")
    ax1.set_title("Trayectoria 3D")
    ax1.set_xlabel("X [km]")
    ax1.set_ylabel("Y [km]")
    ax1.set_zlabel("Z [km]")
    ax1.set_box_aspect([1, 1, 1])
    style_dark_3d(ax1, fig1)
    figures.append(fig1)

    # 2) Órbita XY
    fig2, ax2 = plt.subplots()
    ax2.plot(x, y, color="cyan")
    ax2.set_title("Órbita en el plano XY")
    ax2.set_xlabel("X [km]")
    ax2.set_ylabel("Y [km]")
    ax2.axis("equal")
    style_dark_2d(ax2, fig2)
    figures.append(fig2)

    # 3) Componentes velocidad vs tiempo
    fig3, ax3 = plt.subplots()
    ax3.plot(t, vx, label="Vx", color="cyan")
    ax3.plot(t, vy, label="Vy", color="orange")
    ax3.plot(t, vz, label="Vz", color="lime")
    for tb in burn_times:
        ax3.axvline(tb, color="white", linestyle="--", alpha=0.6)
    ax3.set_title("Componentes de velocidad vs Tiempo")
    ax3.set_xlabel("Tiempo [días]")
    ax3.set_ylabel("Velocidad [km/s]")
    ax3.legend()
    style_dark_2d(ax3, fig3)
    figures.append(fig3)

    # 4) |V| vs tiempo
    fig4, ax4 = plt.subplots()
    ax4.plot(t, speed, label="|V|", color="cyan")
    for tb in burn_times:
        ax4.axvline(tb, color="white", linestyle="--", alpha=0.6)
    ax4.set_title("Módulo de la velocidad vs Tiempo")
    ax4.set_xlabel("Tiempo [días]")
    ax4.set_ylabel("|V| [km/s]")
    ax4.legend()
    style_dark_2d(ax4, fig4)
    figures.append(fig4)

    # 5) r vs tiempo
    fig5, ax5 = plt.subplots()
    ax5.plot(t, r, label="r", color="cyan")
    for tb in burn_times:
        ax5.axvline(tb, color="white", linestyle="--", alpha=0.6)
    ax5.set_title("Distancia al cuerpo central vs Tiempo")
    ax5.set_xlabel("Tiempo [días]")
    ax5.set_ylabel("r [km]")
    ax5.legend()
    style_dark_2d(ax5, fig5)
    figures.append(fig5)

    return figures


class PlotsWindow(QWidget):
    def __init__(self, figures, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resultados de la simulación")
        self.resize(1100, 800)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        tab_names = [
            "Trayectoria 3D",
            "Órbita XY",
            "Velocidades",
            "|V| vs tiempo",
            "Distancia r",
        ]

        self._canvases = []
        self._hover_ann = {}

        for fig, name in zip(figures, tab_names):
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)

            canvas = FigureCanvas(fig)
            toolbar = NavigationToolbar2QT(canvas, self)

            tab_layout.addWidget(toolbar)
            tab_layout.addWidget(canvas)
            self.tabs.addTab(tab, name)

            self._canvases.append(canvas)
            self._enable_hover(canvas)

            canvas.draw()

    def _enable_hover(self, canvas: FigureCanvas):
        fig = canvas.figure
        axes = fig.get_axes()
        if not axes:
            return
        ax = axes[0]

        if ax.name == "3d":
            return

        ann = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(10, 10),
            textcoords="offset points",
            color="white",
            bbox=dict(boxstyle="round", fc="black", ec="white", alpha=0.7),
        )
        ann.set_visible(False)
        self._hover_ann[canvas] = ann

        def on_move(event):
            if event.inaxes != ax:
                ann.set_visible(False)
                canvas.draw_idle()
                return

            for line in ax.lines:
                if hasattr(line.get_xdata(), "size") and line.get_xdata().size <= 2 and line.get_linestyle() == "--":
                    continue

                contains, info = line.contains(event)
                if contains:
                    idx = info["ind"][0]
                    xd = line.get_xdata()
                    yd = line.get_ydata()
                    if idx < len(xd) and idx < len(yd):
                        x0 = float(xd[idx])
                        y0 = float(yd[idx])
                        ann.xy = (x0, y0)
                        ann.set_text(f"x={x0:.4g}\ny={y0:.4g}")
                        ann.set_visible(True)
                        canvas.draw_idle()
                        return

            ann.set_visible(False)
            canvas.draw_idle()

        canvas.mpl_connect("motion_notify_event", on_move)



# Main Window
class MainWindow(QWidget):
    datos_guardados = Signal()

    def create_header(self):
        header = QWidget()
        # header.setFixedHeight(140)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)

        ROOT_DIR = Path(__file__).resolve().parents[1]
        images_dir = ROOT_DIR / "MISCELANEA"

        logo_upm = QLabel()
        logo_etsi = QLabel()
        logo_muse = QLabel()

        pix_upm = QPixmap(str(images_dir / "upm.png"))
        pix_etsi = QPixmap(str(images_dir / "etsiae.png"))
        pix_muse = QPixmap(str(images_dir / "muse.png"))

        logo_h = 90

        logo_upm.setPixmap(pix_upm.scaledToHeight(logo_h, Qt.SmoothTransformation))
        logo_etsi.setPixmap(pix_etsi.scaledToHeight(logo_h, Qt.SmoothTransformation))
        logo_muse.setPixmap(pix_muse.scaledToHeight(logo_h, Qt.SmoothTransformation))


        for lbl in (logo_upm, logo_etsi, logo_muse):
            lbl.setAlignment(Qt.AlignHCenter | Qt.AlignTop)     
            lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)


        layout.addWidget(logo_upm, 1)
        layout.addWidget(logo_etsi, 2)
        layout.addWidget(logo_muse, 1)

        return header

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interfaz Orbital")

        layout = QVBoxLayout()
        tabs = QTabWidget()
        layout.addWidget(self.create_header())


        # General
        tab_general = QWidget()
        form_general = QFormLayout()

        self.nombre_nave = QLineEdit()
        self.Cuerpo_central = QComboBox()
        self.Cuerpo_central.addItems(
            ["Tierra", "Luna", "Marte", "Venus", "Júpiter",
             "Saturno", "Urano", "Neptuno", "Mercurio", "Sol"]
        )

        self.Sistema_de_referencia = QComboBox()
        self.Sistema_de_referencia.addItems(["Ecliptico", "Ecuatorial"])

        self.formato_tiempo = QComboBox()
        self.formato_tiempo.addItems(["UTC", "TAI", "TT"])
        self.formato_tiempo.currentTextChanged.connect(
            lambda _: self.actualizar_formato_tiempo()
        )

        form_general.addRow("Nombre de la nave:", self.nombre_nave)
        form_general.addRow("Cuerpo central:", self.Cuerpo_central)
        form_general.addRow("Sistema de referencia:", self.Sistema_de_referencia)
        form_general.addRow("Formato de tiempo:", self.formato_tiempo)

        tab_general.setLayout(form_general)

        
        # Spacecraft
        tab_spacecraft = QWidget()
        self.form_spacecraft = QFormLayout()
        tab_spacecraft.setLayout(self.form_spacecraft)

        self.coordinates = QComboBox()
        self.coordinates.addItems(["Cartesianas", "Keplerianas"])
        self.coordinates.currentIndexChanged.connect(self.update_spacecraft_fields)
        self.form_spacecraft.addRow("Sistema de coordenadas:", self.coordinates)
        self.update_spacecraft_fields()

        # Time
        tab_time = QWidget()
        form_time = QFormLayout()

        self.fecha_inicio = QLineEdit()
        self.fecha_final = QLineEdit()

        form_time.addRow("Fecha de inicio:", self.fecha_inicio)
        form_time.addRow("Fecha final:", self.fecha_final)

        tab_time.setLayout(form_time)
        self.actualizar_formato_tiempo()

        # Propagate
        tab_propagate = QWidget()
        form_propagate = QFormLayout()

        self.tipo_integrador = QComboBox()
        self.tipo_integrador.addItems([
            "RungeKutta89", "PrinceDormand78", "PrinceDormand45",
            "RungeKutta68", "RungeKutta56", "AdamsBashforthMoulton",
            "SPK", "Code500", "STK", "CCSDS-OEM",
            "PrinceDormand853", "RungeKutta4", "SPICESGP4"
        ])

        self.initial_step_size = QLineEdit()
        self.accuracy = QLineEdit()
        self.min_step_size = QLineEdit()
        self.max_step_size = QLineEdit()
        self.mas_step_attemps = QLineEdit()

        self.central_body = QComboBox()
        self.central_body.addItems(
            ["Tierra", "Luna", "Marte", "Venus", "Júpiter",
             "Saturno", "Urano", "Neptuno", "Mercurio", "Sol"]
        )

        self.primary_body = QComboBox()
        self.primary_body.addItems(
            ["Tierra", "Luna", "Marte", "Venus", "Júpiter",
             "Saturno", "Urano", "Neptuno", "Mercurio", "Sol"]
        )

        self.gmodel = QComboBox()
        self.gmodel.addItems(["JGM-2", "JGM-3", "EGM-96", "None"])

        self.gdegree = QLineEdit()
        self.gorder = QLineEdit()
        self.gSTMLimit = QLineEdit()

        self.drag_atmosphere_model = QComboBox()
        self.drag_atmosphere_model.addItems(["None", "Jacchia Roberts", "MSISE90"])

        self.drag_model = QComboBox()
        self.drag_model.addItems(["Spherical", "SPADFile"])
        self.drag_model.setEnabled(False)
        self.drag_model.hide()

        self.drag_atmosphere_model.currentTextChanged.connect(self.on_atmosphere_changed)

        form_propagate.addRow("Integrador:", self.tipo_integrador)
        form_propagate.addRow("Size paso inicial:", self.initial_step_size)
        form_propagate.addRow("Precisión (accuracy):", self.accuracy)
        form_propagate.addRow("Paso mínimo:", self.min_step_size)
        form_propagate.addRow("Paso máximo:", self.max_step_size)
        form_propagate.addRow("Intentos máx. paso:", self.mas_step_attemps)

        form_propagate.addRow("Cuerpo central:", self.central_body)
        form_propagate.addRow("Cuerpo primario:", self.primary_body)
        form_propagate.addRow("Modelo gravitatorio:", self.gmodel)
        form_propagate.addRow("Grado:", self.gdegree)
        form_propagate.addRow("Orden:", self.gorder)
        form_propagate.addRow("STM Limit:", self.gSTMLimit)
        form_propagate.addRow("Atmósfera:", self.drag_atmosphere_model)
        form_propagate.addRow("Modelo de arrastre:", self.drag_model)

        tab_propagate.setLayout(form_propagate)

    
        # Impulsive Burn         
        tab_impulsive_burn = QWidget()
        form_impulsive_burn = QFormLayout()

        self.coordinate_system = QComboBox()
        self.coordinate_system.addItems(["Local", "EarthMJ2000Eq", "EarthMJ2000Ec", "EarthFixed", "EarthICRF"])

        self.origin = QComboBox()
        self.origin.addItems(["Tierra", "Luna", "Marte", "Venus", "Júpiter", "Saturno", "Urano", "Neptuno", "Mercurio", "Sol"])

        self.axes = QComboBox()
        self.axes.addItems(["VNB", "LVLH", "MJ2000Eq", "SpacecraftBody"])

        self.DV_element1 = QLineEdit()
        self.DV_element2 = QLineEdit()
        self.DV_element3 = QLineEdit()
        self.burn_time1 = QLineEdit()
        self.burn_time1.setPlaceholderText("Días desde inicio (ej. 0.5)")

        form_impulsive_burn.addRow("Sistema de coordenadas:", self.coordinate_system)
        form_impulsive_burn.addRow("Origen:", self.origin)
        form_impulsive_burn.addRow("Axes:", self.axes)
        form_impulsive_burn.addRow("Delta V Element 1:", self.DV_element1)
        form_impulsive_burn.addRow("Delta V Element 2:", self.DV_element2)
        form_impulsive_burn.addRow("Delta V Element 3:", self.DV_element3)
        form_impulsive_burn.addRow("Tiempo burn [días]:", self.burn_time1)

        tab_impulsive_burn.setLayout(form_impulsive_burn)

        
        # Impulsive Burn 2
        tab_impulsive_burn2 = QWidget()
        form_impulsive_burn2 = QFormLayout()

        self.coordinate_system2 = QComboBox()
        self.coordinate_system2.addItems(["Local", "EarthMJ2000Eq", "EarthMJ2000Ec", "EarthFixed", "EarthICRF"])

        self.origin2 = QComboBox()
        self.origin2.addItems(["Tierra", "Luna", "Marte", "Venus", "Júpiter", "Saturno", "Urano", "Neptuno", "Mercurio", "Sol"])

        self.axes2 = QComboBox()
        self.axes2.addItems(["VNB", "LVLH", "MJ2000Eq", "SpacecraftBody"])

        self.DV_element1_2 = QLineEdit()
        self.DV_element2_2 = QLineEdit()
        self.DV_element3_2 = QLineEdit()
        self.burn_time2 = QLineEdit()
        self.burn_time2.setPlaceholderText("Días desde inicio (ej. 1.2)")

        form_impulsive_burn2.addRow("Sistema de coordenadas:", self.coordinate_system2)
        form_impulsive_burn2.addRow("Origen:", self.origin2)
        form_impulsive_burn2.addRow("Axes:", self.axes2)
        form_impulsive_burn2.addRow("Delta V Element 1:", self.DV_element1_2)
        form_impulsive_burn2.addRow("Delta V Element 2:", self.DV_element2_2)
        form_impulsive_burn2.addRow("Delta V Element 3:", self.DV_element3_2)
        form_impulsive_burn2.addRow("Tiempo burn [días]:", self.burn_time2)

        tab_impulsive_burn2.setLayout(form_impulsive_burn2)

        tabs.addTab(tab_general, "General")
        tabs.addTab(tab_spacecraft, "Spacecraft")
        tabs.addTab(tab_time, "Time")
        tabs.addTab(tab_propagate, "Propagate")
        tabs.addTab(tab_impulsive_burn, "Impulsive Burn")
        tabs.addTab(tab_impulsive_burn2, "Impulsive Burn 2")

        
        # Botones
        self.btn_guardar = QPushButton("Guardar datos y ejecutar")
        self.btn_guardar.clicked.connect(self.guardar_datos)

        self.btn_plots = QPushButton("Ver gráficas")
        self.btn_plots.clicked.connect(self.mostrar_graficas)

        layout.addWidget(tabs)
        layout.addWidget(self.btn_guardar)
        layout.addWidget(self.btn_plots)
        self.setLayout(layout)

        self.plots_window = None


    def actualizar_formato_tiempo(self):
        self.fecha_inicio.clear()
        self.fecha_final.clear()
        if self.formato_tiempo.currentText() == "UTC":
            self.fecha_inicio.setPlaceholderText("DD/MM/AAAA HH:MM:SS")
            self.fecha_final.setPlaceholderText("DD/MM/AAAA HH:MM:SS")
        else:
            self.fecha_inicio.setPlaceholderText("Días desde t0")
            self.fecha_final.setPlaceholderText("Días desde t0")

    def update_spacecraft_fields(self):
        while self.form_spacecraft.rowCount() > 1:
            self.form_spacecraft.removeRow(1)

        if self.coordinates.currentText() == "Cartesianas":
            self.x_input = QLineEdit()
            self.y_input = QLineEdit()
            self.z_input = QLineEdit()
            self.vx_input = QLineEdit()
            self.vy_input = QLineEdit()
            self.vz_input = QLineEdit()
            self.dry_mass_input = QLineEdit()
            self.fuel_mass_input = QLineEdit()
            self.epoch_input = QComboBox()
            self.epoch_input.addItems(["UTC", "Julian Dates"])

            self.form_spacecraft.addRow("x:", self.x_input)
            self.form_spacecraft.addRow("y:", self.y_input)
            self.form_spacecraft.addRow("z:", self.z_input)
            self.form_spacecraft.addRow("vx:", self.vx_input)
            self.form_spacecraft.addRow("vy:", self.vy_input)
            self.form_spacecraft.addRow("vz:", self.vz_input)
            self.form_spacecraft.addRow("Masa en seco [kg]:", self.dry_mass_input)
            self.form_spacecraft.addRow("Masa de combustible [kg]:", self.fuel_mass_input)
            self.form_spacecraft.addRow("Formato de fecha:", self.epoch_input)
        else:
            self.SMA_input = QLineEdit()
            self.ECC_input = QLineEdit()
            self.INC_input = QLineEdit()
            self.RAAN_input = QLineEdit()
            self.AOP_input = QLineEdit()
            self.TA_input = QLineEdit()
            self.dry_mass_input = QLineEdit()
            self.fuel_mass_input = QLineEdit()
            self.epoch_input = QComboBox()
            self.epoch_input.addItems(["UTC", "Julian Dates"])

            self.form_spacecraft.addRow("Semi-major axis (SMA):", self.SMA_input)
            self.form_spacecraft.addRow("Eccentricity (ECC):", self.ECC_input)
            self.form_spacecraft.addRow("Inclination (INC):", self.INC_input)
            self.form_spacecraft.addRow("RAAN:", self.RAAN_input)
            self.form_spacecraft.addRow("AOP:", self.AOP_input)
            self.form_spacecraft.addRow("True Anomaly (TA):", self.TA_input)
            self.form_spacecraft.addRow("Masa en seco [kg]:", self.dry_mass_input)
            self.form_spacecraft.addRow("Masa de combustible [kg]:", self.fuel_mass_input)
            self.form_spacecraft.addRow("Formato de fecha:", self.epoch_input)

    def on_atmosphere_changed(self, text):
        if text != "None":
            self.drag_model.setEnabled(True)
            self.drag_model.show()
        else:
            self.drag_model.setEnabled(False)
            self.drag_model.hide()

    
    # Guardar Datos
    def guardar_datos(self):
        datos = []

        datos.append("=== GENERAL ===")
        datos.append(f"Nombre nave: {self.nombre_nave.text()}")
        datos.append(f"Cuerpo central: {self.Cuerpo_central.currentText()}")
        datos.append(f"Sistema de referencia: {self.Sistema_de_referencia.currentText()}")
        datos.append(f"Formato de tiempo: {self.formato_tiempo.currentText()}")

        datos.append("\n=== SPACECRAFT ===")
        datos.append(f"Sistema de coordenadas: {self.coordinates.currentText()}")

        if self.coordinates.currentText() == "Cartesianas":
            datos.append(f"x: {self.x_input.text()}")
            datos.append(f"y: {self.y_input.text()}")
            datos.append(f"z: {self.z_input.text()}")
            datos.append(f"vx: {self.vx_input.text()}")
            datos.append(f"vy: {self.vy_input.text()}")
            datos.append(f"vz: {self.vz_input.text()}")
        else:
            datos.append(f"SMA: {self.SMA_input.text()}")
            datos.append(f"ECC: {self.ECC_input.text()}")
            datos.append(f"INC: {self.INC_input.text()}")
            datos.append(f"RAAN: {self.RAAN_input.text()}")
            datos.append(f"AOP: {self.AOP_input.text()}")
            datos.append(f"TA: {self.TA_input.text()}")

        datos.append(f"Masa seca: {self.dry_mass_input.text()}")
        datos.append(f"Masa combustible: {self.fuel_mass_input.text()}")
        datos.append(f"Formato epoch: {self.epoch_input.currentText()}")

        datos.append("\n=== TIEMPO ===")
        datos.append(f"Fecha inicio: {self.fecha_inicio.text()}")
        datos.append(f"Fecha final: {self.fecha_final.text()}")

        datos.append("\n=== PROPAGATE ===")
        datos.append(f"Tipo de integrador: {self.tipo_integrador.currentText()}")
        datos.append(f"Tamano de paso inicial: {self.initial_step_size.text()}")
        datos.append(f"Precision (accuracy): {self.accuracy.text()}")
        datos.append(f"Paso minimo: {self.min_step_size.text()}")
        datos.append(f"Paso maximo: {self.max_step_size.text()}")
        datos.append(f"Intentos max. paso: {self.mas_step_attemps.text()}")
        datos.append(f"Cuerpo central: {self.central_body.currentText()}")
        datos.append(f"Cuerpo primario: {self.primary_body.currentText()}")
        datos.append(f"Modelo gravitatorio: {self.gmodel.currentText()}")
        datos.append(f"Grado: {self.gdegree.text()}")
        datos.append(f"Orden: {self.gorder.text()}")
        datos.append(f"STM Limit: {self.gSTMLimit.text()}")
        datos.append(f"Atmosfera: {self.drag_atmosphere_model.currentText()}")
        datos.append(f"Modelo de arrastre: {self.drag_model.currentText()}")

        datos.append("\n=== IMPULSIVE BURN ===")
        datos.append(f"Sistema de coordenadas: {self.coordinate_system.currentText()}")
        datos.append(f"Origen: {self.origin.currentText()}")
        datos.append(f"Axes: {self.axes.currentText()}")
        datos.append(f"Delta V Element 1: {self.DV_element1.text()}")
        datos.append(f"Delta V Element 2: {self.DV_element2.text()}")
        datos.append(f"Delta V Element 3: {self.DV_element3.text()}")
        datos.append(f"Tiempo burn: {self.burn_time1.text()}")

        datos.append("\n=== IMPULSIVE BURN 2 ===")
        datos.append(f"Sistema de coordenadas: {self.coordinate_system2.currentText()}")
        datos.append(f"Origen: {self.origin2.currentText()}")
        datos.append(f"Axes: {self.axes2.currentText()}")
        datos.append(f"Delta V Element 1: {self.DV_element1_2.text()}")
        datos.append(f"Delta V Element 2: {self.DV_element2_2.text()}")
        datos.append(f"Delta V Element 3: {self.DV_element3_2.text()}")
        datos.append(f"Tiempo burn: {self.burn_time2.text()}")

        datos.append("\n=== REPORTFILE ===")
        datos.append("Nombre del archivo de reporte: ReportFile")

        ruta = INPUT_DIR / "datos_guardados.txt"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("\n".join(datos))

        print("✅ Datos guardados en:", ruta)

        self.datos_guardados.emit()


    # Gráficas
    def mostrar_graficas(self):
        report_path = OUTPUT_DIR / "DefaultReportFile.txt"
        datos_path = INPUT_DIR / "datos_guardados.txt"

        if not report_path.exists():
            print("❌ El report de GMAT no existe todavía:", report_path)
            return

        try:
            df = load_report(report_path)
            figures = make_figures(df, datos_path)
        except Exception as e:
            print("❌ Error generando figuras:", e)
            return

        self.plots_window = PlotsWindow(figures, parent=None)
        self.plots_window.show()
