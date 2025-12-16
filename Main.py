from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, QThread, Signal
import sys

from SOURCES.GUI import MainWindow
from SOURCES.Transpiler import run_transpiler
from SOURCES.GMAT_exec import run_gmat
from SOURCES.plot_results import load_report, make_plots
from SOURCES.utils import ensure_dirs, OUTPUT_DIR


class PipelineWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def run(self):
        try:
            print("▶ Ejecutando Transpiler...")
            script_path = run_transpiler()

            print("▶ Ejecutando GMAT...")
            run_gmat(script_path)

            print("▶ Generando plots...")
            report = OUTPUT_DIR / "DefaultReportFile.txt"
            df = load_report(report)
            make_plots(df)

            print("✅ Pipeline completo")
            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))


def ejecutar_pipeline_async(window):
    window.pipeline_thread = QThread()
    window.pipeline_worker = PipelineWorker()

    window.pipeline_worker.moveToThread(window.pipeline_thread)

    window.pipeline_thread.started.connect(window.pipeline_worker.run)

    window.pipeline_worker.finished.connect(window.pipeline_thread.quit)
    window.pipeline_worker.finished.connect(window.pipeline_worker.deleteLater)
    window.pipeline_thread.finished.connect(window.pipeline_thread.deleteLater)

    window.pipeline_worker.error.connect(
        lambda e: print("❌ Error en pipeline:", e)
    )

    window.pipeline_thread.start()




def main():
    ensure_dirs()

    app = QApplication(sys.argv)
    window = MainWindow()

    window.datos_guardados.connect(lambda: ejecutar_pipeline_async(window))

    window.show()
    sys.exit(app.exec())



if __name__ == "__main__":
    main()
