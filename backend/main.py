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
from pydantic import BaseModel

from clasificador import ClasificadorChernovia
from clasificador_ml import ClasificadorML
from detector_anomalias import DetectorAnomalias
from generador_reporte import generar_pdf

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
        return
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida o ausente")


# ── Configuración AWS ────────────────────────────────────────────────────────
BUCKET = os.environ.get("S3_BUCKET", "")
RAW_PREFIX = "raw"
RESULTS_KEY = "results/resultado_clasificacion.parquet"
GLUE_JOB_NAME = os.environ.get("GLUE_JOB_NAME", "chernovia-clasificacion-batch")
TMP_DIR = os.environ.get("TMP_DIR", "/tmp/chernovia")

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

# ── Caché: stats pre-agregadas + muestra pequeña ─────────────────────────────
# We never hold the full 1.2M-row DataFrame in memory.
# Stats are computed incrementally (one parquet file at a time).
# Sample keeps 10K rows for /api/solicitudes pagination.
_cache: dict = {"stats": None, "sample": None, "valid": False}

# ── Modelo ML (carga lazy al primer uso) ─────────────────────────────────────
_ml_lock = threading.Lock()
_ml_model: Optional[ClasificadorML] = None


def get_ml_model() -> Optional[ClasificadorML]:
    global _ml_model
    if _ml_model is not None:
        return _ml_model
    if not BUCKET:
        return None
    with _ml_lock:
        if _ml_model is None:
            try:
                _ml_model = ClasificadorML(BUCKET, RAW_PREFIX)
            except Exception:
                return None
    return _ml_model


def get_state():
    with _state_lock:
        return dict(_state)


def set_state(**kwargs):
    with _state_lock:
        _state.update(kwargs)


_KEEP_COLS = [
    "id_solicitud", "fecha_solicitud", "medio_emisor", "valor_procedimiento",
    "entidad_emisora", "servicio_solicitado", "perfil_cobertura",
    "cubre", "porcentaje_cobertura", "valor_cubierto", "razon_decision",
]

_CATEGORY_COLS = [
    "perfil_cobertura", "medio_emisor", "servicio_solicitado",
    "entidad_emisora", "fecha_solicitud",
]


def _read_parquet_lean(source) -> pd.DataFrame:
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(source)
    available = [c for c in _KEEP_COLS if c in pf.schema_arrow.names]
    df = pf.read(columns=available).to_pandas()

    for col in ["valor_procedimiento", "valor_cubierto"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")
    if "porcentaje_cobertura" in df.columns:
        df["porcentaje_cobertura"] = pd.to_numeric(
            df["porcentaje_cobertura"], errors="coerce"
        ).fillna(0).astype("int16")
    if "cubre" in df.columns:
        df["cubre"] = df["cubre"].astype(bool)
    for col in _CATEGORY_COLS:
        if col in df.columns:
            df[col] = df[col].fillna("").astype("category")
    return df


def _load_stats_and_sample() -> bool:
    """
    Reads parquet files one at a time, accumulates aggregation dicts, discards each
    full DataFrame after processing. Peak RAM: ~45MB (one file) instead of 181MB.
    Keeps a 10K-row sample for /api/solicitudes pagination.
    """
    try:
        s3 = boto3.client("s3")
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=BUCKET, Prefix=RESULTS_KEY)
        keys = sorted(
            obj["Key"]
            for page in pages
            for obj in page.get("Contents", [])
            if obj["Key"].endswith(".parquet")
        )
        if not keys:
            return False

        total = 0
        cubiertos = 0
        valor_total = 0.0
        valor_cubierto_total = 0.0
        por_perfil: dict = {}
        por_servicio: dict = {}
        por_medio: dict = {}
        por_dia: dict = {}
        samples: list = []

        for key in keys:
            data = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
            df = _read_parquet_lean(io.BytesIO(data))

            total += len(df)
            cubiertos += int(df["cubre"].sum()) if "cubre" in df.columns else 0
            if "valor_procedimiento" in df.columns:
                valor_total += float(df["valor_procedimiento"].sum())
            if "valor_cubierto" in df.columns:
                valor_cubierto_total += float(df["valor_cubierto"].sum())

            if "perfil_cobertura" in df.columns:
                gp = df.groupby("perfil_cobertura", observed=True).agg(
                    cnt=("id_solicitud", "count"),
                    cub=("cubre", "sum"),
                    val=("valor_cubierto", "sum"),
                )
                for perfil, row in gp.iterrows():
                    if perfil not in por_perfil:
                        por_perfil[perfil] = {"total": 0, "cubiertos": 0, "valor_cubierto": 0.0}
                    por_perfil[perfil]["total"] += int(row["cnt"])
                    por_perfil[perfil]["cubiertos"] += int(row["cub"])
                    por_perfil[perfil]["valor_cubierto"] += float(row["val"])

            if "servicio_solicitado" in df.columns:
                gs = df.groupby("servicio_solicitado", observed=True).agg(
                    cnt=("id_solicitud", "count"),
                    cub=("cubre", "sum"),
                    val=("valor_cubierto", "sum"),
                )
                for serv, row in gs.iterrows():
                    if serv not in por_servicio:
                        por_servicio[serv] = {"total": 0, "cubiertos": 0, "valor_cubierto": 0.0}
                    por_servicio[serv]["total"] += int(row["cnt"])
                    por_servicio[serv]["cubiertos"] += int(row["cub"])
                    por_servicio[serv]["valor_cubierto"] += float(row["val"])

            if "medio_emisor" in df.columns:
                for medio, cnt in df["medio_emisor"].value_counts().items():
                    por_medio[medio] = por_medio.get(medio, 0) + int(cnt)

            if "fecha_solicitud" in df.columns:
                fechas = df["fecha_solicitud"].astype(str).str[:10]
                cubre_col = df["cubre"] if "cubre" in df.columns else pd.Series(False, index=df.index)
                id_col = df["id_solicitud"] if "id_solicitud" in df.columns else pd.Series(range(len(df)), index=df.index)
                tmp = pd.DataFrame({"fecha": fechas, "cubre": cubre_col, "id": id_col})
                gd = tmp.groupby("fecha").agg(cnt=("id", "count"), cub=("cubre", "sum"))
                for fecha, row in gd.iterrows():
                    if fecha not in por_dia:
                        por_dia[fecha] = {"total": 0, "cubiertos": 0}
                    por_dia[fecha]["total"] += int(row["cnt"])
                    por_dia[fecha]["cubiertos"] += int(row["cub"])

            # Keep 2500 rows per file (4 files → 10K sample total)
            samples.append(df.head(2500).copy())
            del df

        top_servicios = sorted(por_servicio.items(), key=lambda x: -x[1]["total"])[:15]
        top_medios = dict(sorted(por_medio.items(), key=lambda x: -x[1])[:10])

        stats = {
            "total": total,
            "cubiertos": cubiertos,
            "no_cubiertos": total - cubiertos,
            "tasa_cobertura": round(cubiertos / total * 100, 2) if total else 0.0,
            "valor_total": valor_total,
            "valor_cubierto_total": valor_cubierto_total,
            "por_perfil": [{"perfil_cobertura": k, **v} for k, v in por_perfil.items()],
            "por_dia": [{"fecha": k, **v} for k, v in sorted(por_dia.items())],
            "por_servicio": [{"servicio_solicitado": k, **v} for k, v in top_servicios],
            "por_medio": top_medios,
        }

        sample_df = pd.concat(samples, ignore_index=True)

        _cache["stats"] = stats
        _cache["sample"] = sample_df
        _cache["valid"] = True
        return True

    except Exception:
        return False


def _ensure_loaded() -> bool:
    if _cache["valid"]:
        return True
    return _load_stats_and_sample()


def invalidate_cache():
    _cache["valid"] = False
    _cache["stats"] = None
    _cache["sample"] = None


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
        glue = boto3.client("glue", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
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

            progreso_map = {"STARTING": 15, "RUNNING": 60, "STOPPING": 90}
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

    except Exception as exc:
        glue_error = str(exc)
        if "ConcurrentRuns" in glue_error or "concurrent" in glue_error.lower():
            set_state(
                estado="error",
                paso="Glue ya tiene un job en ejecución. Espera a que termine e inténtalo de nuevo.",
                error=glue_error,
                fin=datetime.now().isoformat(),
            )
            return
        set_state(
            paso=f"Glue no disponible → procesando localmente. Causa: {glue_error[:200]}",
            progreso=20,
            modo="local",
            error=glue_error,
        )
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
            glue = boto3.client("glue", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
            run = glue.get_job_run(JobName=GLUE_JOB_NAME, RunId=state["glue_run_id"])
            glue_status = run["JobRun"]["JobRunState"]
            elapsed = run["JobRun"].get("ExecutionTime", 0)
            set_state(paso=f"Glue: {glue_status} | Tiempo: {elapsed}s")
        except Exception:
            pass
    return get_state()


@app.get("/api/stats")
def get_stats(_: None = Depends(verify_api_key)):
    if not _ensure_loaded():
        return {"data": None}
    return {"data": _cache["stats"]}


@app.get("/api/solicitudes")
def get_solicitudes(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    perfil: str = Query(None),
    cubre: str = Query(None),
    search: str = Query(None),
    _: None = Depends(verify_api_key),
):
    if not _ensure_loaded() or _cache["sample"] is None:
        return {"data": [], "total": 0, "page": page, "limit": limit, "pages": 0}

    filtered = _cache["sample"]

    if perfil:
        filtered = filtered[filtered["perfil_cobertura"] == perfil]
    if cubre == "true":
        filtered = filtered[filtered["cubre"] == True]  # noqa: E712
    elif cubre == "false":
        filtered = filtered[filtered["cubre"] == False]  # noqa: E712
    if search:
        mask = (
            filtered["id_solicitud"].astype(str).str.contains(search, case=False, na=False)
            | filtered["servicio_solicitado"].astype(str).str.contains(search, case=False, na=False)
            | filtered["entidad_emisora"].astype(str).str.contains(search, case=False, na=False)
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
    if not _ensure_loaded() or _cache["sample"] is None:
        return {"error": "No hay resultados disponibles. Ejecute el procesamiento primero."}

    output = io.StringIO()
    _cache["sample"].to_csv(output, index=False)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=resultados_clasificacion.csv"},
    )


class ClasificarRequest(BaseModel):
    glosa: str
    valor_procedimiento: float = 0.0


@app.post("/api/classify")
def classify_single(body: ClasificarRequest, _: None = Depends(verify_api_key)):
    model = get_ml_model()
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Modelo ML no disponible. Verifica la configuración del bucket S3.",
        )
    result = model.clasificar_uno(body.glosa, body.valor_procedimiento)
    return result


@app.get("/api/quality")
def get_quality(_: None = Depends(verify_api_key)):
    if not _ensure_loaded() or _cache["sample"] is None:
        return {"data": None, "message": "No hay resultados procesados aún."}

    model = get_ml_model()
    if model is None:
        return {"data": None, "message": "Modelo ML no disponible."}

    metricas = model.metricas_calidad(_cache["sample"])
    return {"data": metricas}


@app.get("/api/glue/status")
def glue_status(_: None = Depends(verify_api_key)):
    if not GLUE_JOB_NAME:
        return {"available": False, "reason": "GLUE_JOB_NAME no configurado"}
    try:
        glue = boto3.client("glue", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        job = glue.get_job(JobName=GLUE_JOB_NAME)
        return {
            "available": True,
            "job_name": GLUE_JOB_NAME,
            "worker_type": job["Job"].get("WorkerType"),
            "max_capacity": job["Job"].get("MaxCapacity"),
        }
    except Exception as exc:
        return {"available": False, "reason": str(exc), "job_name": GLUE_JOB_NAME}


@app.get("/health")
def health():
    ml_ready = get_ml_model() is not None
    return {
        "status": "ok",
        "bucket": BUCKET,
        "glue_job": GLUE_JOB_NAME,
        "version": "2.0.0",
        "ml_model": "ready" if ml_ready else "not_loaded",
    }


# ── Anomalías ────────────────────────────────────────────────────────────────
@app.get("/api/anomalias")
def get_anomalias(_: None = Depends(verify_api_key)):
    """Detecta patrones sospechosos en la muestra de solicitudes procesadas."""
    if not _ensure_loaded() or _cache["sample"] is None:
        return {"data": None, "message": "No hay datos procesados aún."}
    detector = DetectorAnomalias()
    resultado = detector.detectar(_cache["sample"])
    return {"data": resultado}


# ── Simulador de política de cobertura ───────────────────────────────────────
class SimulateRequest(BaseModel):
    agregar_servicios: list[str] = []
    quitar_servicios: list[str] = []
    cambiar_perfiles: dict[str, int] = {}


@app.post("/api/simulate")
def simulate_policy(body: SimulateRequest, _: None = Depends(verify_api_key)):
    """Simula el impacto fiscal de cambios en la política de cobertura."""
    if not _ensure_loaded() or _cache["sample"] is None or _cache["stats"] is None:
        raise HTTPException(status_code=404, detail="No hay datos procesados. Ejecute el pipeline primero.")

    stats = _cache["stats"]
    sample = _cache["sample"]
    total = stats["total"]
    scale = total / len(sample) if len(sample) > 0 else 1.0

    cubiertos_actual = stats["cubiertos"]
    valor_cubierto_actual = stats["valor_cubierto_total"]
    tasa_actual = cubiertos_actual / total if total > 0 else 0.0

    perfiles_base = {"PRIORITARIO": 100, "ESTANDAR": 50, "COPAGO": 25}
    perfiles_nuevos = {**perfiles_base, **body.cambiar_perfiles}

    delta_cubiertos = 0
    delta_valor = 0.0
    detalle: list[dict] = []

    # Agregar servicios al catálogo
    for serv in body.agregar_servicios:
        mask = sample["servicio_solicitado"].str.strip().str.lower() == serv.strip().lower()
        mask &= sample["cubre"] == False  # noqa: E712
        filas = sample[mask]
        nuevas = int(len(filas) * scale)
        delta_cubiertos += nuevas
        val_serv = 0.0
        for perfil, pct in perfiles_nuevos.items():
            f_p = filas[filas["perfil_cobertura"] == perfil]
            val_serv += float(f_p["valor_procedimiento"].sum()) * scale * pct / 100
        delta_valor += val_serv
        detalle.append({
            "cambio": f"Agregar '{serv}' al catálogo cubierto",
            "solicitudes_nuevas_cubiertas": nuevas,
            "costo_adicional": round(val_serv, 2),
        })

    # Quitar servicios del catálogo
    for serv in body.quitar_servicios:
        mask = sample["servicio_solicitado"].str.strip().str.lower() == serv.strip().lower()
        mask &= sample["cubre"] == True  # noqa: E712
        filas = sample[mask]
        perdidas = int(len(filas) * scale)
        delta_cubiertos -= perdidas
        val_serv = float(filas["valor_cubierto"].sum()) * scale if "valor_cubierto" in filas.columns else 0.0
        delta_valor -= val_serv
        detalle.append({
            "cambio": f"Quitar '{serv}' del catálogo cubierto",
            "solicitudes_afectadas": perdidas,
            "ahorro": round(val_serv, 2),
        })

    # Cambiar porcentajes de perfiles
    for perfil, nuevo_pct in body.cambiar_perfiles.items():
        pct_actual = perfiles_base.get(perfil, 0)
        diff_pct = nuevo_pct - pct_actual
        if diff_pct == 0:
            continue
        mask = sample["cubre"] == True  # noqa: E712
        mask &= sample["perfil_cobertura"] == perfil
        filas = sample[mask]
        val_extra = float(filas["valor_procedimiento"].sum()) * scale * diff_pct / 100
        delta_valor += val_extra
        detalle.append({
            "cambio": f"Perfil '{perfil}': {pct_actual}% → {nuevo_pct}%",
            "solicitudes_afectadas": int(len(filas) * scale),
            "variacion_valor": round(val_extra, 2),
        })

    nuevos_cubiertos = cubiertos_actual + delta_cubiertos
    nueva_tasa = nuevos_cubiertos / total if total > 0 else 0.0

    return {
        "estado_actual": {
            "total_solicitudes": total,
            "cubiertos": cubiertos_actual,
            "tasa_cobertura_pct": round(tasa_actual * 100, 2),
            "valor_cubierto_total": round(valor_cubierto_actual, 2),
        },
        "impacto_proyectado": {
            "nuevos_cubiertos": delta_cubiertos,
            "total_cubiertos_nuevo": nuevos_cubiertos,
            "nueva_tasa_cobertura_pct": round(nueva_tasa * 100, 2),
            "variacion_tasa_pct": round((nueva_tasa - tasa_actual) * 100, 2),
            "delta_valor_cubierto": round(delta_valor, 2),
            "nuevo_valor_cubierto_total": round(valor_cubierto_actual + delta_valor, 2),
        },
        "detalle_cambios": detalle,
    }


# ── Reporte PDF ejecutivo ────────────────────────────────────────────────────
@app.get("/api/reporte")
def descargar_reporte(_: None = Depends(verify_api_key)):
    """Genera y descarga el reporte PDF ejecutivo del último procesamiento."""
    if not _ensure_loaded() or _cache["stats"] is None:
        raise HTTPException(status_code=404, detail="No hay datos procesados. Ejecute el pipeline primero.")

    detector = DetectorAnomalias()
    anomalias_data = detector.detectar(_cache["sample"]) if _cache["sample"] is not None else None

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    pdf_bytes = generar_pdf(
        stats=_cache["stats"],
        anomalias_data=anomalias_data,
        fecha_ejecucion=fecha,
    )
    filename = f"reporte_chernovia_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Gestión de catálogos ─────────────────────────────────────────────────────
SERVICIOS_CSV = "COIL_catalogo_servicios_cubiertos.csv"
PERFILES_CSV = "COIL_catalogo_perfiles_cobertura.csv"


def _leer_catalogo_s3(filename: str) -> pd.DataFrame:
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=BUCKET, Key=f"{RAW_PREFIX}/{filename}")
    return pd.read_csv(io.BytesIO(obj["Body"].read()))


def _guardar_catalogo_s3(df: pd.DataFrame, filename: str) -> None:
    s3 = boto3.client("s3")
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    s3.put_object(Bucket=BUCKET, Key=f"{RAW_PREFIX}/{filename}", Body=buf.getvalue())
    # Forzar recarga del modelo ML en la próxima solicitud
    global _ml_model
    with _ml_lock:
        _ml_model = None


@app.get("/api/catalogo/servicios")
def get_catalogo_servicios(_: None = Depends(verify_api_key)):
    if not BUCKET:
        raise HTTPException(status_code=503, detail="Bucket S3 no configurado.")
    df = _leer_catalogo_s3(SERVICIOS_CSV)
    return {"data": df.to_dict("records"), "total": len(df)}


class ServicioRequest(BaseModel):
    servicio: str
    cubre_sistema_publico: str  # "SI" o "NO"


@app.post("/api/catalogo/servicios")
def agregar_servicio(body: ServicioRequest, _: None = Depends(verify_api_key)):
    if body.cubre_sistema_publico not in ("SI", "NO"):
        raise HTTPException(status_code=422, detail="cubre_sistema_publico debe ser 'SI' o 'NO'.")
    if not BUCKET:
        raise HTTPException(status_code=503, detail="Bucket S3 no configurado.")
    df = _leer_catalogo_s3(SERVICIOS_CSV)
    nombre = body.servicio.strip()
    if nombre in df["servicio"].values:
        df.loc[df["servicio"] == nombre, "cubre_sistema_publico"] = body.cubre_sistema_publico
        msg = f"Servicio '{nombre}' actualizado a {body.cubre_sistema_publico}."
    else:
        nueva_fila = pd.DataFrame([{"servicio": nombre, "cubre_sistema_publico": body.cubre_sistema_publico}])
        df = pd.concat([df, nueva_fila], ignore_index=True)
        msg = f"Servicio '{nombre}' agregado con cobertura {body.cubre_sistema_publico}."
    _guardar_catalogo_s3(df, SERVICIOS_CSV)
    return {"message": msg, "total": len(df)}


@app.delete("/api/catalogo/servicios/{servicio}")
def eliminar_servicio(servicio: str, _: None = Depends(verify_api_key)):
    if not BUCKET:
        raise HTTPException(status_code=503, detail="Bucket S3 no configurado.")
    df = _leer_catalogo_s3(SERVICIOS_CSV)
    nombre = servicio.strip()
    if nombre not in df["servicio"].values:
        raise HTTPException(status_code=404, detail=f"Servicio '{nombre}' no encontrado.")
    df = df[df["servicio"] != nombre].reset_index(drop=True)
    _guardar_catalogo_s3(df, SERVICIOS_CSV)
    return {"message": f"Servicio '{nombre}' eliminado del catálogo.", "total": len(df)}


@app.get("/api/catalogo/perfiles")
def get_catalogo_perfiles(_: None = Depends(verify_api_key)):
    if not BUCKET:
        raise HTTPException(status_code=503, detail="Bucket S3 no configurado.")
    df = _leer_catalogo_s3(PERFILES_CSV)
    return {"data": df.to_dict("records"), "total": len(df)}


class PerfilRequest(BaseModel):
    porcentaje_cobertura_si_el_servicio_esta_cubierto: int


@app.put("/api/catalogo/perfiles/{perfil}")
def actualizar_perfil(perfil: str, body: PerfilRequest, _: None = Depends(verify_api_key)):
    if not BUCKET:
        raise HTTPException(status_code=503, detail="Bucket S3 no configurado.")
    if not (0 <= body.porcentaje_cobertura_si_el_servicio_esta_cubierto <= 100):
        raise HTTPException(status_code=422, detail="El porcentaje debe estar entre 0 y 100.")
    df = _leer_catalogo_s3(PERFILES_CSV)
    nombre = perfil.strip().upper()
    if nombre not in df["perfil_cobertura"].values:
        raise HTTPException(status_code=404, detail=f"Perfil '{nombre}' no encontrado.")
    df.loc[df["perfil_cobertura"] == nombre, "porcentaje_cobertura_si_el_servicio_esta_cubierto"] = (
        body.porcentaje_cobertura_si_el_servicio_esta_cubierto
    )
    _guardar_catalogo_s3(df, PERFILES_CSV)
    return {"message": f"Perfil '{nombre}' actualizado a {body.porcentaje_cobertura_si_el_servicio_esta_cubierto}%."}


STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
