from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  
import sys
from SOURCES.utils import INPUT_DIR, OUTPUT_DIR, PLOTS_DIR

DATOS_PATH  = INPUT_DIR / "datos_guardados.txt"
REPORT_PATH = OUTPUT_DIR / "DefaultReportFile.txt"


def load_report(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No se encuentra el report: {path}")

    # Leemos separado por espacios (uno o más)
    df = pd.read_csv(path, sep=r"\s+", engine="python")

    # Forzar a numérico y eliminar filas no numéricas (cabeceras repetidas, etc.)
    df = df.apply(pd.to_numeric, errors="coerce").dropna()

    if df.shape[1] < 7:
        raise ValueError(
            f"El report tiene {df.shape[1]} columnas, "
            "pero esperaba al menos 7 (t, X, Y, Z, VX, VY, VZ)."
        )

    return df


def leer_tiempos_burn(path: Path):
    """
    Intenta leer 'Tiempo burn' (en días) desde datos_guardados.txt.
    Devuelve una lista de floats [t_burn1, t_burn2, ...].
    Si no encuentra nada, devuelve [] y no rompe nada.
    """
    tiempos = []
    if not path.exists():
        return tiempos

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Ejemplos esperados:
            # "Tiempo burn 1: 0.3"
            # "Tiempo burn 2: 0.6"
            if line.lower().startswith("tiempo burn"):
                # Partimos por ":" y cogemos lo que hay a la derecha
                if ":" in line:
                    _, val = line.split(":", 1)
                    val = val.strip().replace(",", ".")
                    try:
                        t_b = float(val)
                        tiempos.append(t_b)
                    except ValueError:
                        pass
    return tiempos


def make_plots(df: pd.DataFrame):
    PLOTS_DIR.mkdir(exist_ok=True)

    cols = df.columns.tolist()
    t_col  = cols[0]
    x_col  = cols[1]
    y_col  = cols[2]
    z_col  = cols[3]
    vx_col = cols[4]
    vy_col = cols[5]
    vz_col = cols[6]

    t  = df[t_col].values
    x  = df[x_col].values
    y  = df[y_col].values
    z  = df[z_col].values
    vx = df[vx_col].values
    vy = df[vy_col].values
    vz = df[vz_col].values

    speed = np.sqrt(vx**2 + vy**2 + vz**2)
    r     = np.sqrt(x**2 + y**2 + z**2)

    # Intentamos leer los tiempos de burn (si existen)
    burn_times = leer_tiempos_burn(DATOS_PATH)
    print("Tiempos de burn leídos:", burn_times)

    # === 1) Trayectoria 3D ===
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(x, y, z)
    ax.set_xlabel("X [km]")
    ax.set_ylabel("Y [km]")
    ax.set_zlabel("Z [km]")
    ax.set_title("Trayectoria 3D")
    ax.set_box_aspect([1, 1, 1])  # ejes a la misma escala
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "trayectoria_3D.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # === 2) Órbita en plano XY ===
    fig, ax = plt.subplots()
    ax.plot(x, y)
    ax.set_xlabel("X [km]")
    ax.set_ylabel("Y [km]")
    ax.set_title("Órbita en el plano XY")
    ax.axis("equal")
    ax.grid(True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "orbita_XY.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # === 3) Componentes de velocidad vs tiempo ===
    fig, ax = plt.subplots()
    ax.plot(t, vx, label="Vx")
    ax.plot(t, vy, label="Vy")
    ax.plot(t, vz, label="Vz")

    # Marcar burns si existen
    for tb in burn_times:
        ax.axvline(tb, color="k", linestyle="--", alpha=0.7)

    ax.set_xlabel("Tiempo [días]")
    ax.set_ylabel("Velocidad [km/s]")
    ax.set_title("Componentes de velocidad vs tiempo")
    ax.grid(True)
    ax.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "velocidades_vs_tiempo.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # === 4) Módulo de la velocidad vs tiempo ===
    fig, ax = plt.subplots()
    ax.plot(t, speed, label="|V|")

    for tb in burn_times:
        ax.axvline(tb, color="k", linestyle="--", alpha=0.7)

    ax.set_xlabel("Tiempo [días]")
    ax.set_ylabel("|V| [km/s]")
    ax.set_title("Módulo de la velocidad vs tiempo")
    ax.grid(True)
    ax.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "velocidad_modulo_vs_tiempo.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # === 5) Distancia al cuerpo central r(t) ===
    fig, ax = plt.subplots()
    ax.plot(t, r, label="r")

    for tb in burn_times:
        ax.axvline(tb, color="k", linestyle="--", alpha=0.7)

    ax.set_xlabel("Tiempo [días]")
    ax.set_ylabel("r [km]")
    ax.set_title("Distancia al cuerpo central vs tiempo")
    ax.grid(True)
    ax.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "radio_vs_tiempo.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    print("✅ Gráficas guardadas en:", PLOTS_DIR)



