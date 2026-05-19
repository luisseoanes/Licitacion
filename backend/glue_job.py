"""
Chernovia Health - AWS Glue ETL Job (PySpark distribuido)
Procesa 1.2M solicitudes médicas desde S3 y guarda resultados en S3 Parquet.
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import BooleanType, DoubleType, IntegerType

args = getResolvedOptions(
    sys.argv,
    ["JOB_NAME", "BUCKET", "RAW_PREFIX", "RESULTS_KEY"],
)

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

BUCKET = args["BUCKET"]
RAW_PREFIX = args["RAW_PREFIX"]
RESULTS_KEY = args["RESULTS_KEY"]

# ── Cargar catálogos ─────────────────────────────────────────────────────────
servicios_df = spark.read.option("header", True).csv(
    f"s3://{BUCKET}/{RAW_PREFIX}/COIL_catalogo_servicios_cubiertos.csv"
)
servicios_cubiertos = set(
    row["servicio"].strip()
    for row in servicios_df.filter(F.col("cubre_sistema_publico") == "SI")
    .select("servicio")
    .collect()
)

perfiles_df = spark.read.option("header", True).csv(
    f"s3://{BUCKET}/{RAW_PREFIX}/COIL_catalogo_perfiles_cobertura.csv"
)
perfiles_map = {
    row["perfil_cobertura"]: int(row["porcentaje_cobertura_si_el_servicio_esta_cubierto"])
    for row in perfiles_df.collect()
}

# Broadcast para eficiencia en todos los workers
servicios_bc = sc.broadcast(servicios_cubiertos)
perfiles_bc = sc.broadcast(perfiles_map)

# ── Leer dataset principal (distribuido) ─────────────────────────────────────
df = spark.read.option("header", True).csv(
    f"s3://{BUCKET}/{RAW_PREFIX}/COIL_dataset_glosas_salud_1_2M.csv"
)

# ── Extracción de glosa ──────────────────────────────────────────────────────
df = df.withColumn(
    "servicio_solicitado",
    F.trim(F.regexp_extract(F.col("glosa"), r"ServicioSolicitado:\s*([^;]+)", 1)),
)
df = df.withColumn(
    "perfil_cobertura",
    F.trim(F.regexp_extract(F.col("glosa"), r"PerfilCobertura:\s*([^;]+)", 1)),
)

# ── Clasificación distribuida (UDFs con broadcast) ───────────────────────────
@F.udf(BooleanType())
def is_covered(servicio):
    return servicio in servicios_bc.value if servicio else False


@F.udf(IntegerType())
def get_percentage(perfil, cubre):
    if not cubre:
        return 0
    return perfiles_bc.value.get(perfil, 0) if perfil else 0


df = df.withColumn("cubre", is_covered(F.col("servicio_solicitado")))
df = df.withColumn("porcentaje_cobertura", get_percentage(F.col("perfil_cobertura"), F.col("cubre")))
df = df.withColumn("valor_procedimiento", F.col("valor_procedimiento").cast(DoubleType()))
df = df.withColumn(
    "valor_cubierto",
    F.col("valor_procedimiento") * F.col("porcentaje_cobertura") / 100,
)

# ── Resultado final ──────────────────────────────────────────────────────────
result = df.select(
    "id_solicitud",
    "fecha_solicitud",
    "medio_emisor",
    "valor_procedimiento",
    "entidad_emisora",
    "servicio_solicitado",
    "perfil_cobertura",
    "cubre",
    "porcentaje_cobertura",
    "valor_cubierto",
)

# Guardar como Parquet particionado por fecha (optimiza consultas)
result.write.mode("overwrite").parquet(f"s3://{BUCKET}/{RESULTS_KEY}")

job.commit()
