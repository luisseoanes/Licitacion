import io
import os
import threading
from datetime import datetime

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from clasificador import ClasificadorChernovia

app = FastAPI(title="Chernovia Health API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "datos")
RESULTS_DIR = os.path.join(BASE_DIR, "resultados")
RESULTS_PATH = os.path.join(RESULTS_DIR, "resultado_clasificacion.parquet")

os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Estado de procesamiento ──────────────────────────────────────────────────
_state_lock = threading.Lock()
_state = {"estado": "idle", "paso": "", "progreso": 0, "inicio": None, "fin": None, "total": 0, "error": None}

# ── Caché en memoria ─────────────────────────────────────────────────────────
_cache: dict = {"df": None, "valid": False}


def get_state():
    with _state_lock:
        return dict(_state)


def set_state(**kwargs):
    with _state_lock:
        _state.update(kwargs)


def get_df() -> pd.DataFrame | None:
    if _cache["valid"] and _cache["df"] is not None:
        return _cache["df"]
    if not os.path.exists(RESULTS_PATH):
        return None
    _cache["df"] = pd.read_parquet(RESULTS_PATH)
    _cache["valid"] = True
    return _cache["df"]


def invalidate_cache():
    _cache["valid"] = False
    _cache["df"] = None


# ── Procesamiento en background ──────────────────────────────────────────────
def _run_processing():
    set_state(estado="procesando", paso="Iniciando...", progreso=0,
              inicio=datetime.now().isoformat(), fin=None, error=None)
    try:
        def on_step(paso: str, progreso: int):
            pasos = {
                "leyendo": "Leyendo 1.2M registros...",
                "extrayendo": "Extrayendo datos de glosas...",
                "clasificando": "Clasificando solicitudes...",
                "guardando": "Guardando resultados...",
            }
            set_state(paso=pasos.get(paso, paso), progreso=progreso)

        clf = ClasificadorChernovia(DATA_DIR)
        resultado = clf.procesar(on_step=on_step)

        resultado.to_parquet(RESULTS_PATH, index=False)
        invalidate_cache()

        set_state(
            estado="completado",
            paso="¡Clasificación completada!",
            progreso=100,
            fin=datetime.now().isoformat(),
            total=len(resultado),
        )
    except Exception as exc:
        set_state(estado="error", paso="Error durante el procesamiento", error=str(exc),
                  fin=datetime.now().isoformat())


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.post("/api/process")
def start_process(background_tasks: BackgroundTasks):
    if get_state()["estado"] == "procesando":
        return {"message": "Ya hay un procesamiento en curso"}
    background_tasks.add_task(_run_processing)
    return {"message": "Procesamiento iniciado"}


@app.get("/api/process/status")
def process_status():
    return get_state()


@app.get("/api/stats")
def get_stats():
    df = get_df()
    if df is None:
        return {"data": None}

    total = len(df)
    cubiertos = int(df["cubre"].sum())
    no_cubiertos = total - cubiertos
    valor_total = float(df["valor_procedimiento"].sum())
    valor_cubierto_total = float(df["valor_cubierto"].sum())

    # Por perfil
    gp = (
        df.groupby("perfil_cobertura")
        .agg(total=("id_solicitud", "count"), cubiertos=("cubre", "sum"),
             valor_cubierto=("valor_cubierto", "sum"))
        .reset_index()
    )
    por_perfil = [
        {
            "perfil_cobertura": r["perfil_cobertura"],
            "total": int(r["total"]),
            "cubiertos": int(r["cubiertos"]),
            "valor_cubierto": float(r["valor_cubierto"]),
        }
        for _, r in gp.iterrows()
    ]

    # Por día
    df2 = df.copy()
    df2["fecha"] = pd.to_datetime(df2["fecha_solicitud"]).dt.strftime("%Y-%m-%d")
    gd = (
        df2.groupby("fecha")
        .agg(total=("id_solicitud", "count"), cubiertos=("cubre", "sum"))
        .reset_index()
        .sort_values("fecha")
    )
    por_dia = [
        {"fecha": r["fecha"], "total": int(r["total"]), "cubiertos": int(r["cubiertos"])}
        for _, r in gd.iterrows()
    ]

    # Top servicios
    gs = (
        df.groupby("servicio_solicitado")
        .agg(total=("id_solicitud", "count"), cubiertos=("cubre", "sum"),
             valor_cubierto=("valor_cubierto", "sum"))
        .reset_index()
        .sort_values("total", ascending=False)
        .head(15)
    )
    por_servicio = [
        {
            "servicio_solicitado": r["servicio_solicitado"],
            "total": int(r["total"]),
            "cubiertos": int(r["cubiertos"]),
            "valor_cubierto": float(r["valor_cubierto"]),
        }
        for _, r in gs.iterrows()
    ]

    # Por medio emisor
    por_medio = {k: int(v) for k, v in df["medio_emisor"].value_counts().head(10).items()}

    return {
        "data": {
            "total": total,
            "cubiertos": cubiertos,
            "no_cubiertos": no_cubiertos,
            "tasa_cobertura": round(cubiertos / total * 100, 2),
            "valor_total": valor_total,
            "valor_cubierto_total": valor_cubierto_total,
            "por_perfil": por_perfil,
            "por_dia": por_dia,
            "por_servicio": por_servicio,
            "por_medio": por_medio,
        }
    }


@app.get("/api/solicitudes")
def get_solicitudes(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    perfil: str = Query(None),
    cubre: str = Query(None),
    search: str = Query(None),
):
    df = get_df()
    if df is None:
        return {"data": [], "total": 0, "page": page, "limit": limit, "pages": 0}

    filtered = df.copy()

    if perfil:
        filtered = filtered[filtered["perfil_cobertura"] == perfil]
    if cubre == "true":
        filtered = filtered[filtered["cubre"] == True]  # noqa: E712
    elif cubre == "false":
        filtered = filtered[filtered["cubre"] == False]  # noqa: E712
    if search:
        mask = (
            filtered["id_solicitud"].str.contains(search, case=False, na=False)
            | filtered["servicio_solicitado"].str.contains(search, case=False, na=False)
            | filtered["entidad_emisora"].str.contains(search, case=False, na=False)
        )
        filtered = filtered[mask]

    total = len(filtered)
    start = (page - 1) * limit
    records = filtered.iloc[start : start + limit].copy()

    records["cubre"] = records["cubre"].astype(bool)
    records["valor_procedimiento"] = records["valor_procedimiento"].astype(float)
    records["valor_cubierto"] = records["valor_cubierto"].astype(float)
    records["porcentaje_cobertura"] = records["porcentaje_cobertura"].astype(int)

    return {
        "data": records.to_dict("records"),
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, -(-total // limit)),
    }


@app.get("/api/export")
def export_csv():
    df = get_df()
    if df is None:
        return {"error": "No hay resultados"}

    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=resultados_clasificacion.csv"},
    )
