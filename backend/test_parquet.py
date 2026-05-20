import time, boto3, io, pyarrow.parquet as pq, pandas as pd

BUCKET = "chernovia-health-licitacion-213238636264"
KEEP = ["id_solicitud","fecha_solicitud","medio_emisor","valor_procedimiento",
        "entidad_emisora","servicio_solicitado","perfil_cobertura",
        "cubre","porcentaje_cobertura","valor_cubierto"]
CAT = ["perfil_cobertura","medio_emisor","servicio_solicitado","entidad_emisora","fecha_solicitud"]

s3 = boto3.client("s3")
t0 = time.time()

r = s3.list_objects_v2(Bucket=BUCKET, Prefix="results/resultado_clasificacion.parquet/")
keys = [x["Key"] for x in r.get("Contents",[]) if x["Key"].endswith(".parquet")]
print(f"Found {len(keys)} parquet files")

frames = []
for k in sorted(keys):
    t1 = time.time()
    data = s3.get_object(Bucket=BUCKET, Key=k)["Body"].read()
    t2 = time.time()
    pf = pq.ParquetFile(io.BytesIO(data))
    available = [c for c in KEEP if c in pf.schema_arrow.names]
    df = pf.read(columns=available).to_pandas()
    for col in ["valor_procedimiento","valor_cubierto"]:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")
    if "porcentaje_cobertura" in df.columns:
        df["porcentaje_cobertura"] = pd.to_numeric(df["porcentaje_cobertura"], errors="coerce").fillna(0).astype("int16")
    if "cubre" in df.columns: df["cubre"] = df["cubre"].astype(bool)
    for col in CAT:
        if col in df.columns: df[col] = df[col].fillna("").astype("category")
    mem = df.memory_usage(deep=True).sum() // 1024 // 1024
    t3 = time.time()
    print(f"  {k.split('/')[-1]}: rows={len(df)} mem={mem}MB dl={t2-t1:.1f}s parse={t3-t2:.1f}s")
    frames.append(df)

full = pd.concat(frames, ignore_index=True)
mem_total = full.memory_usage(deep=True).sum() // 1024 // 1024
print(f"\nTotal rows: {len(full)}  Total mem: {mem_total}MB  Time: {time.time()-t0:.1f}s")
print(f"Cobertura: {full['cubre'].sum()} / {len(full)}")
print("OK")
