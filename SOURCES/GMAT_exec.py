import subprocess
from pathlib import Path
from shutil import copy2

from SOURCES.utils import OUTPUT_DIR


def find_gmat():
    posibles = [
        Path(r"C:\Program Files (x86)\GMAT-R2019aBeta-Windows-x64-public\bin\GmatConsole.exe"),
        Path(r"C:\Program Files\GMAT-R2019aBeta-Windows-x64-public\bin\GmatConsole.exe"),
    ]

    for p in posibles:
        if p.exists():
            return p

    raise FileNotFoundError("GMAT R2019aBeta Console no encontrado")


def run_gmat(script_path: Path):

    gmat_exe = find_gmat()
    gmat_bin = gmat_exe.parent

    script_path = script_path.resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"No existe el script de GMAT: {script_path}")

    #Ejecutar GMAT
    subprocess.run(
        [str(gmat_exe), str(script_path)],
        check=True
    )

    #Copiar el ReportFile desde GMAT/bin al proyecto
    src = gmat_bin.parent / "output" / "DefaultReportFile.txt"
    if not src.exists():
        raise FileNotFoundError(
            f"GMAT terminó pero no se generó el report file: {src}"
        )

    dst = OUTPUT_DIR / "DefaultReportFile.txt"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    copy2(src, dst)

    print("✅ ReportFile copiado a:", dst)
