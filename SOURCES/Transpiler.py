from pathlib import Path
from datetime import datetime
import subprocess
import sys
from SOURCES.utils import INPUT_DIR, GMAT_DIR, OUTPUT_DIR


DATA_FILE   = INPUT_DIR / "datos_guardados.txt"
SCRIPT_PATH = GMAT_DIR / "demo.script"



def map_body(spanish_name: str) -> str:
    mapping = {
        "Tierra": "Earth",
        "Luna": "Luna",
        "Marte": "Mars",
        "Venus": "Venus",
        "Júpiter": "Jupiter",
        "Jupiter": "Jupiter",
        "Saturno": "Saturn",
        "Urano": "Uranus",
        "Neptuno": "Neptune",
        "Mercurio": "Mercury",
        "Sol": "Sun",
    }
    return mapping.get(spanish_name, "Earth")


def map_coord_system(central_body_en: str, sistema_ref: str) -> str:
    """Devuelve algo tipo 'EarthMJ2000Eq' o 'EarthMJ2000Ec' según referencia."""
    s = (sistema_ref or "").lower()
    if "eclip" in s:
        suffix = "MJ2000Ec"
    else:
        suffix = "MJ2000Eq"
    return f"{central_body_en}{suffix}"


def map_time_format(fmt: str) -> str:
    mapping = {
        "UTC": "UTCGregorian",
        "TAI": "TAIGregorian",
        "TT":  "TTGregorian",
    }
    return mapping.get(fmt, "UTCGregorian")


def to_float(value: str, default: float = 0.0) -> float:
    try:
        v = value.strip().replace(",", ".")
        return float(v)
    except Exception:
        return default
    
def positive_or_default(value: str, default: float) -> float:
    """Convierte a float y asegura que sea > 0, si no, usa el default."""
    v = to_float(value, default)
    if v <= 0:
        return default
    return v



def sanitize_name(name: str, default: str = "Sat") -> str:
    """Convierte 'Mi nave 1' en 'Mi_nave_1' y se asegura de que no quede vacío."""
    if not name:
        return default
    name = name.strip()
    if not name:
        return default
    name = name.replace(" ", "_")
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
    name = "".join(c for c in name if c in allowed)
    if not name:
        return default
    return name


def parse_gui_txt(path: Path) -> dict:
    """
    Lee datos_guardados.txt generado por la GUI y devuelve
    un diccionario con secciones:
      general, spacecraft, time, propagate, impulsive_burn, reportfile
    """
    config = {
        "general": {},
        "spacecraft": {},
        "time": {},
        "propagate": {},
        "impulsive_burn": {},
        "impulsive_burn_2": {},   #AGREGADOOOO
        "reportfile": {},
    }
    current_section = None

    if not path.exists():
        raise FileNotFoundError(f"No se encuentra {path}")

    # Si te vuelve a dar problemas de acentos, cambia utf-8 por "latin-1"
    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            # Detectar secciones por los "=== ... ==="
            if line.startswith("=== ") and line.endswith(" ==="):
                if "GENERAL" in line:
                    current_section = "general"
                elif "SPACECRAFT" in line:
                    current_section = "spacecraft"
                elif "TIEMPO" in line:
                    current_section = "time"
                elif "PROPAGATE" in line:
                    current_section = "propagate"
                elif "IMPULSIVE BURN 2" in line:          # AGREGADOOOO
                    current_section = "impulsive_burn_2"
                elif "IMPULSIVE BURN" in line:
                    current_section = "impulsive_burn"
                elif "REPORTFILE" in line:
                    current_section = "reportfile"
                else:
                    current_section = None
                continue

            # Clave: valor
            if ":" in line and current_section is not None:
                key, value = line.split(":", 1)
                config[current_section][key.strip()] = value.strip()

    return config

def map_report_variable(label: str, sat_name: str) -> str | None:
    """
    Convierte el texto de la GUI (en español) en el campo GMAT correspondiente.
    Devuelve None si no está soportado (de momento).
    """
    label = label.strip()

    # Tiempo
    if label == "Elapsed Days":
        return f"{sat_name}.ElapsedDays"
    if label == "Elapsed Seconds":
        return f"{sat_name}.ElapsedSecs"   # si da error, lo quitamos luego

    # Cartesianas
    if label == "Posicion X":
        return f"{sat_name}.X"
    if label == "Posicion Y":
        return f"{sat_name}.Y"
    if label == "Posicion Z":
        return f"{sat_name}.Z"
    if label == "Velocidad VX":
        return f"{sat_name}.VX"
    if label == "Velocidad VY":
        return f"{sat_name}.VY"
    if label == "Velocidad VZ":
        return f"{sat_name}.VZ"

    # Keplerianas
    if label == "Semieje mayor (SMA)":
        return f"{sat_name}.SMA"
    if label == "Excentricidad (ECC)":
        return f"{sat_name}.ECC"
    if label == "Inclinacion (INC)":
        return f"{sat_name}.INC"
    if label == "RAAN":
        return f"{sat_name}.RAAN"
    if label == "Argumento del periapsis (AOP)":
        return f"{sat_name}.AOP"
    if label == "Anomalia verdadera (TA)":
        return f"{sat_name}.TA"

    # Si no lo tenemos mapeado todavía, devolvemos None
    return None

def build_gmat_script(cfg: dict, script_path: Path):
    gen = cfg["general"]
    sc  = cfg["spacecraft"]
    tm  = cfg["time"]
    pr  = cfg["propagate"]
    ib1 = cfg["impulsive_burn"]
    ib2 = cfg.get("impulsive_burn_2", {})

    # ========== GENERAL ==========
    sat_name_raw = gen.get("Nombre nave", "").strip()
    sat_name = sanitize_name(sat_name_raw, default="Sat")

    central_es   = gen.get("Cuerpo central", "Tierra")
    central_en   = map_body(central_es)
    sistema_ref  = gen.get("Sistema de referencia", "Ecuatorial")
    coord_system = map_coord_system(central_en, sistema_ref)

    # Ejes (ecuatorial vs eclíptica) en GMAT
    if coord_system.endswith("MJ2000Ec"):
        axes_type = "MJ2000Ec"   # eclíptica
    else:
        axes_type = "MJ2000Eq"   # ecuatorial por defecto


    time_fmt    = gen.get("Formato de tiempo", "UTC")
    date_format = map_time_format(time_fmt)

    # ========== TIEMPO ==========

    start_raw = tm.get("Fecha inicio", "").strip()
    end_raw   = tm.get("Fecha final", "").strip()

    def normalize_epoch(epoch: str) -> str:
        """
        Convierte lo que viene de la GUI en un string tipo:
        '08 Dec 2024 12:00:00.000'
        Soporta:
        - '08 Dec 2024'
        - '08/12/2024'
        - '08 Dec 2024 10:30:00'
        - '08/12/2024 10:30:00'
        Si falla, devuelve una fecha por defecto.
        """
        s = epoch.strip()
        if not s:
            return "01 Jan 2030 12:00:00.000"

        # Caso con hora incluida
        if ":" in s:
            for fmt in ("%d %b %Y %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
                try:
                    dt = datetime.strptime(s, fmt)
                    return dt.strftime("%d %b %Y %H:%M:%S.000")
                except ValueError:
                    pass
            if not s.endswith(".000"):
                return s + ".000"
            return s

        # Solo fecha
        for fmt in ("%d %b %Y", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(s, fmt)
                return dt.strftime("%d %b %Y 12:00:00.000")
            except ValueError:
                pass

        return "01 Jan 2030 12:00:00.000"

    def parse_date_only(s: str):
        s = s.strip()
        if not s:
            return None
        for fmt in ("%d %b %Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                pass
        return None

    epoch_str = normalize_epoch(start_raw)

    start_dt = parse_date_only(start_raw)
    end_dt   = parse_date_only(end_raw)

    if start_dt and end_dt and end_dt > start_dt:
        dur_days = (end_dt - start_dt).total_seconds() / 86400.0
    else:
        dur_days = 1.0   # por defecto

    
    # ========== SPACECRAFT ==========

    coord_type = sc.get("Sistema de coordenadas", "Cartesianas").strip()

    # Cartesianas
    x  = to_float(sc.get("x",  "7000"), default=7000.0)
    y  = to_float(sc.get("y",  "0"),    default=0.0)
    z  = to_float(sc.get("z",  "0"),    default=0.0)
    vx = to_float(sc.get("vx", "0"),    default=0.0)
    vy = to_float(sc.get("vy", "7.5"),  default=7.5)
    vz = to_float(sc.get("vz", "0"),    default=0.0)

    # Keplerianas
    sma  = to_float(sc.get("SMA",  "7000"), default=7000.0)
    ecc  = to_float(sc.get("ECC",  "0.0"),  default=0.0)
    inc  = to_float(sc.get("INC",  "0.0"),  default=0.0)
    raan = to_float(sc.get("RAAN", "0.0"),  default=0.0)
    aop  = to_float(sc.get("AOP",  "0.0"),  default=0.0)
    ta   = to_float(sc.get("TA",   "0.0"),  default=0.0)

    # ========== PROPAGATE ==========
    integ_type = pr.get("Tipo de integrador", "RungeKutta89").strip() or "RungeKutta89"

    init_step = positive_or_default(pr.get("Tamano de paso inicial", "10"),   10.0)
    accuracy  = positive_or_default(pr.get("Precision (accuracy)", "1e-4"),   1e-4)
    min_step  = positive_or_default(pr.get("Paso minimo", "0.01"),            0.01)
    max_step  = positive_or_default(pr.get("Paso maximo", "300"),             300.0)

    max_step_attempts_str = pr.get("Intentos max. paso", "50")
    try:
        max_step_attempts = int(float(max_step_attempts_str.replace(",", ".")))
        if max_step_attempts <= 0:
            max_step_attempts = 50
    except Exception:
        max_step_attempts = 50

    fm_central_es = pr.get("Cuerpo central", gen.get("Cuerpo central", "Tierra"))
    fm_central_en = map_body(fm_central_es)

    # ========== IMPULSIVE BURN 1 ==========
    ib1_coord_raw = ib1.get("Sistema de coordenadas", "Local").strip()
    ib1_origin_es = ib1.get("Origen", central_es)
    ib1_axes      = ib1.get("Axes", "VNB").strip()

    dv1_1 = to_float(ib1.get("Delta V Element 1", "0"), 0.0)
    dv1_2 = to_float(ib1.get("Delta V Element 2", "0"), 0.0)
    dv1_3 = to_float(ib1.get("Delta V Element 3", "0"), 0.0)

    has_burn1 = (abs(dv1_1) + abs(dv1_2) + abs(dv1_3)) > 0.0

    ib1_burn_time_str = ib1.get("Tiempo burn", "").strip()
    t_burn1 = None
    if has_burn1 and ib1_burn_time_str != "":
        t_burn1 = to_float(ib1_burn_time_str, 0.0)
        # Acotamos entre 0 y dur_days
        if t_burn1 < 0.0:
            t_burn1 = 0.0
        if t_burn1 > dur_days:
            t_burn1 = dur_days

    if ib1_coord_raw == "Local":
        ib1_coord_gmat = coord_system
    else:
        ib1_coord_gmat = ib1_coord_raw

    ib1_origin_en = map_body(ib1_origin_es)

    # ========== IMPULSIVE BURN 2 ==========
    ib2_coord_raw = ib2.get("Sistema de coordenadas", "Local").strip()
    ib2_origin_es = ib2.get("Origen", central_es)
    ib2_axes      = ib2.get("Axes", "VNB").strip()

    dv2_1 = to_float(ib2.get("Delta V Element 1", "0"), 0.0)
    dv2_2 = to_float(ib2.get("Delta V Element 2", "0"), 0.0)
    dv2_3 = to_float(ib2.get("Delta V Element 3", "0"), 0.0)

    has_burn2 = (abs(dv2_1) + abs(dv2_2) + abs(dv2_3)) > 0.0

    ib2_burn_time_str = ib2.get("Tiempo burn", "").strip()
    t_burn2 = None
    if has_burn2 and ib2_burn_time_str != "":
        t_burn2 = to_float(ib2_burn_time_str, 0.0)
        if t_burn2 < 0.0:
            t_burn2 = 0.0
        if t_burn2 > dur_days:
            t_burn2 = dur_days

    if ib2_coord_raw == "Local":
        ib2_coord_gmat = coord_system
    else:
        ib2_coord_gmat = ib2_coord_raw

    ib2_origin_en = map_body(ib2_origin_es)


        # ========== CONSTRUIR SCRIPT ==========
    lines = []

    # --- CoordinateSystem SOLO si NO es la Tierra ---
    if central_en != "Earth":
        lines.append(f"Create CoordinateSystem {coord_system};")
        lines.append(f"{coord_system}.Origin = {central_en};")
        lines.append(f"{coord_system}.Axes   = {axes_type};")
        lines.append("")  # estética



    # Objetos
    lines.append(f"Create Spacecraft {sat_name};")
    lines.append("Create ForceModel FM;")
    lines.append("Create Propagator Prop;")
    if has_burn1:
        lines.append("Create ImpulsiveBurn ImpBurn1;")
    if has_burn2:
        lines.append("Create ImpulsiveBurn ImpBurn2;")
    lines.append("Create ReportFile DefaultReportFile;")
    lines.append("")
    

    # Spacecraft
    lines.append(f"{sat_name}.DateFormat = {date_format};")
    lines.append(f"{sat_name}.Epoch = '{epoch_str}';")
    lines.append(f"{sat_name}.CoordinateSystem = {coord_system};")

    if coord_type == "Cartesianas":
        lines.append(f"{sat_name}.DisplayStateType = Cartesian;")
        lines.append(f"{sat_name}.X  = {x};")
        lines.append(f"{sat_name}.Y  = {y};")
        lines.append(f"{sat_name}.Z  = {z};")
        lines.append(f"{sat_name}.VX = {vx};")
        lines.append(f"{sat_name}.VY = {vy};")
        lines.append(f"{sat_name}.VZ = {vz};")
    else:
        lines.append(f"{sat_name}.DisplayStateType = Keplerian;")
        lines.append(f"{sat_name}.SMA  = {sma};")
        lines.append(f"{sat_name}.ECC  = {ecc};")
        lines.append(f"{sat_name}.INC  = {inc};")
        lines.append(f"{sat_name}.RAAN = {raan};")
        lines.append(f"{sat_name}.AOP  = {aop};")
        lines.append(f"{sat_name}.TA   = {ta};")

    lines.append("")

    # ForceModel
    lines.append(f"FM.CentralBody   = {fm_central_en};")
    lines.append(f"FM.PrimaryBodies = {{{fm_central_en}}};")
    lines.append("FM.Drag = None;")
    lines.append("FM.SRP  = Off;")
    lines.append("")

    # Propagator
    lines.append(f"Prop.Type            = {integ_type};")
    lines.append("Prop.FM              = FM;")
    lines.append(f"Prop.InitialStepSize = {init_step};")
    lines.append(f"Prop.Accuracy        = {accuracy};")
    lines.append(f"Prop.MinStep         = {min_step};")
    lines.append(f"Prop.MaxStep         = {max_step};");
    lines.append(f"Prop.MaxStepAttempts = {max_step_attempts};")
    lines.append("")

    # ImpulsiveBurn 1
    if has_burn1:
        lines.append(f"ImpBurn1.CoordinateSystem = {ib1_coord_gmat};")
        lines.append(f"ImpBurn1.Origin          = {ib1_origin_en};")
        lines.append(f"ImpBurn1.Axes            = {ib1_axes};")
        lines.append(f"ImpBurn1.Element1        = {dv1_1};")
        lines.append(f"ImpBurn1.Element2        = {dv1_2};")
        lines.append(f"ImpBurn1.Element3        = {dv1_3};")
        lines.append("ImpBurn1.DecrementMass   = false;")
        lines.append("")

    # ImpulsiveBurn 2
    if has_burn2:
        lines.append(f"ImpBurn2.CoordinateSystem = {ib2_coord_gmat};")
        lines.append(f"ImpBurn2.Origin          = {ib2_origin_en};")
        lines.append(f"ImpBurn2.Axes            = {ib2_axes};")
        lines.append(f"ImpBurn2.Element1        = {dv2_1};")
        lines.append(f"ImpBurn2.Element2        = {dv2_2};")
        lines.append(f"ImpBurn2.Element3        = {dv2_3};")
        lines.append("ImpBurn2.DecrementMass   = false;")
        lines.append("")

    # ReportFile
    lines.append("DefaultReportFile.Filename = 'DefaultReportFile.txt';")
    lines.append("DefaultReportFile.WriteHeaders = true;")
    lines.append("DefaultReportFile.Precision = 16;")
    lines.append(
        f"DefaultReportFile.Add = "
        f"{{{sat_name}.ElapsedDays, {sat_name}.X, {sat_name}.Y, {sat_name}.Z, "
        f"{sat_name}.VX, {sat_name}.VY, {sat_name}.VZ}};"
    )
    lines.append("")


    # ========== MISSION SEQUENCE ==========
    lines.append("BeginMissionSequence;")

    report_fields = (
        f"{sat_name}.ElapsedDays {sat_name}.X {sat_name}.Y {sat_name}.Z "
        f"{sat_name}.VX {sat_name}.VY {sat_name}.VZ"
    )

    # Report inicial
    lines.append(f"Report DefaultReportFile {report_fields};")

    # Construimos lista de eventos (nombre del burn, tiempo)
    events = []
    if has_burn1 and t_burn1 is not None:
        events.append(("ImpBurn1", t_burn1))
    if has_burn2 and t_burn2 is not None:
        events.append(("ImpBurn2", t_burn2))

    current_t = 0.0

    # Ordenar por tiempo
    events.sort(key=lambda e: e[1])

    for burn_name, t in events:
        if dur_days <= 0.0:
            break

        t_clamped = max(0.0, min(dur_days, t))

        if t_clamped > current_t:
            lines.append(
                f"Propagate Prop({sat_name}) "
                f"{{{sat_name}.ElapsedDays = {t_clamped}}};"
            )
            lines.append(f"Report DefaultReportFile {report_fields};")

        lines.append(f"Maneuver {burn_name}({sat_name});")
        lines.append(f"Report DefaultReportFile {report_fields};")

        current_t = t_clamped

    # Propagación final
    if dur_days > current_t:
        lines.append(
            f"Propagate Prop({sat_name}) "
            f"{{{sat_name}.ElapsedDays = {dur_days}}};"
        )
        lines.append(f"Report DefaultReportFile {report_fields};")

    lines.append("")

    script_text = "\n".join(lines)
    script_path.write_text(script_text, encoding="utf-8")

    print(f"Script GMAT generado en: {script_path}")
    print("Contenido aproximado:")
    print("-----------------------------------------")
    print(script_text[:400] + "...\n")


def run_transpiler():
    cfg = parse_gui_txt(DATA_FILE)
    build_gmat_script(cfg, SCRIPT_PATH)
    return SCRIPT_PATH




