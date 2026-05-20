import io
import os
import threading
from datetime import datetime
from typing import Optional

import boto3
import pandas as pd
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security.api_key import APIKeyHeader
from fastapi.staticfiles import StaticFiles

from clasificador import ClasificadorChernovia

load_dotenv()

app = FastAPI(title="Chernovia Health API", version="2.0.0")

# ── CORS ──────────────────────────────────────────────────────────────────────
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# ── Autenticación por API Key ─────────────────────────────────────────────────
API_KEY = os.environ.get("API_KEY", "")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(key: str = Security(_api_key_header)):
    if not API_KEY:
        # Sin API_KEY configurada, se permite acceso (modo desarrollo)
        return
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida o ausente")


# ── Configuración AWS ────────────────────────────────────────────────────────
BUCKET = os.environ.get("S3_BUCKET", "")
RAW_PREFIX = "raw"
RESULTS_KEY = "results/resultado_clasificacion.parquet"
GLUE_JOB_NAME = os.environ.get("GLUE_JOB_NAME", "chernovia-clasificacion-batch")
TMP_DIR = os.environ.get("TMP_DIR", "/tmp/chernovia")
TMP_RESULTS = os.path.join(TMP_DIR, "resultado_clasificacion.parquet")

os.makedirs(TMP_DIR, exist_ok=True)

# ── Estado de procesamiento ──────────────────────────────────────────────────
_state_lock = threading.Lock()
_state = {
    "estado": "idle",
    "paso": "",
    "progreso": 0,
    "inicio": None,
    "fin": None,
    "total": 0,
    "error": None,
    "glue_run_id": None,
    "modo": None,
}

# ── Caché en memoria ─────────────────────────────────────────────────────────
_cache: dict = {"df": None, "valid": False}


def get_state():
    with _state_lock:
        return dict(_state)


def set_state(**kwargs):
    with _state_lock:
        _state.update(kwargs)


def get_df() -> Optional[pd.DataFrame]:
    if _cache["valid"] and _cache["df"] is not None:
        return _cache["df"]

    if os.path.exists(TMP_RESULTS):
        _cache["df"] = pd.read_parquet(TMP_RESULTS)
        _cache["valid"] = True
        return _cache["df"]

    try:
        s3 = boto3.client("s3")
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=BUCKET, Prefix=RESULTS_KEY)
        keys = [obj["Key"] for page in pages for obj in page.get("Contents", [])]

        if not keys:
            return None

        frames = []
        for key in keys:
            if key.endswith(".parquet"):
                obj = s3.get_object(Bucket=BUCKET, Key=key)
                frames.append(pd.read_parquet(io.BytesIO(obj["Body"].read())))

        if not frames:
            return None

        df = pd.concat(frames, ignore_index=True)
        _cache["df"] = df
        _cache["valid"] = True
        df.to_parquet(TMP_RESULTS, index=False)
        return df
    except Exception:
        return None


def invalidate_cache():
    _cache["valid"] = False
    _cache["df"] = None
    if os.path.exists(TMP_RESULTS):
        os.remove(TMP_RESULTS)


# ── Procesamiento vía AWS Glue (distribuido) ─────────────────────────────────
def _trigger_glue():
    set_state(
        estado="procesando",
        paso="Iniciando job distribuido en AWS Glue (PySpark)...",
        progreso=5,
        inicio=datetime.now().isoformat(),
        fin=None,
        error=None,
        glue_run_id=None,
        modo="glue",
    )
    try:
        glue = boto3.client("glue")
        response = glue.start_job_run(
            JobName=GLUE_JOB_NAME,
            Arguments={
                "--BUCKET": BUCKET,
                "--RAW_PREFIX": RAW_PREFIX,
                "--RESULTS_KEY": RESULTS_KEY,
            },
        )
        run_id = response["JobRunId"]
        set_state(glue_run_id=run_id, paso=f"Job Glue en ejecución: {run_id}", progreso=10)

        while True:
            import time
            time.sleep(15)
            run = glue.get_job_run(JobName=GLUE_JOB_NAME, RunId=run_id)
            status = run["JobRun"]["JobRunState"]

            progreso_map = {
                "STARTING": 15,
                "RUNNING": 60,
                "STOPPING": 90,
            }
            if status in progreso_map:
                set_state(
                    paso=f"Procesando en Glue ({status})... Workers PySpark activos",
                    progreso=progreso_map[status],
                )
            elif status == "SUCCEEDED":
                invalidate_cache()
                set_state(
                    estado="completado",
                    paso="¡Clasificación distribuida completada en AWS Glue!",
                    progreso=100,
                    fin=datetime.now().isoformat(),
                )
                break
            elif status in ("FAILED", "ERROR", "TIMEOUT"):
                error_msg = run["JobRun"].get("ErrorMessage", status)
                set_state(
                    estado="error",
                    paso=f"Glue job falló: {status}",
                    error=error_msg,
                    fin=datetime.now().isoformat(),
                )
                break

    except Exception:
        set_state(paso="Glue no disponible, procesando localmente...", progreso=20, modo="local")
        _run_local()


# ── Procesamiento local (fallback) ────────────────────────────────────────────
def _run_local():
    try:
        def on_step(paso: str, progreso: int):
            pasos = {
                "leyendo": "Leyendo 1.2M registros desde S3...",
                "extrayendo": "Extrayendo datos de glosas...",
                "clasificando": "Clasificando solicitudes...",
                "guardando": "Guardando resultados...",
            }
            set_state(paso=pasos.get(paso, paso), progreso=progreso)

        clf = ClasificadorChernovia(BUCKET, RAW_PREFIX)
        resultado = clf.procesar(on_step=on_step)

        resultado.to_parquet(TMP_RESULTS, index=False)

        set_state(paso="Subiendo resultados a S3...", progreso=95)
        s3 = boto3.client("s3")
        buf = io.BytesIO()
        resultado.to_parquet(buf, index=False)
        buf.seek(0)
        s3.put_object(Bucket=BUCKET, Key=RESULTS_KEY, Body=buf.getvalue())

        invalidate_cache()
        set_state(
            estado="completado",
            paso="¡Clasificación completada y guardada en S3!",
            progreso=100,
            fin=datetime.now().isoformat(),
            total=len(resultado),
        )
    except Exception as exc:
        set_state(
            estado="error",
            paso="Error durante el procesamiento",
            error=str(exc),
            fin=datetime.now().isoformat(),
        )


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.post("/api/process")
def start_process(
    background_tasks: BackgroundTasks,
    modo: str = Query("glue"),
    _: None = Depends(verify_api_key),
):
    if get_state()["estado"] == "procesando":
        return {"message": "Ya hay un procesamiento en curso"}
    if modo == "local":
        set_state(estado="procesando", paso="Iniciando procesamiento local...", progreso=0,
                  inicio=datetime.now().isoformat(), fin=None, error=None, modo="local")
        background_tasks.add_task(_run_local)
    else:
        background_tasks.add_task(_trigger_glue)
    return {"message": f"Procesamiento iniciado (modo={modo})"}


@app.get("/api/process/status")
def process_status(_: None = Depends(verify_api_key)):
    state = get_state()
    if state.get("estado") == "procesando" and state.get("glue_run_id"):
        try:
            glue = boto3.client("glue")
            run = glue.get_job_run(JobName=GLUE_JOB_NAME, RunId=state["glue_run_id"])
            glue_status = run["JobRun"]["JobRunState"]
            elapsed = run["JobRun"].get("ExecutionTime", 0)
            set_state(paso=f"Glue: {glue_status} | Tiempo: {elapsed}s")
        except Exception:
            pass
    return get_state()


@app.get("/api/stats")
def get_stats(_: None = Depends(verify_api_key)):
    df = get_df()
    if df is None:
        return {"data": None}

    total = len(df)
    cubiertos = int(df["cubre"].sum())
    no_cubiertos = total - cubiertos
    valor_total = float(df["valor_procedimiento"].sum())
    valor_cubierto_total = float(df["valor_cubierto"].sum())

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
    _: None = Depends(verify_api_key),
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
def export_csv(_: None = Depends(verify_api_key)):
    df = get_df()
    if df is None:
        return {"error": "No hay resultados disponibles. Ejecute el procesamiento primero."}

    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=resultados_clasificacion.csv"},
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "bucket": BUCKET,
        "glue_job": GLUE_JOB_NAME,
        "version": "2.0.0",
    }


STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
