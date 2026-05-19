import io

import boto3
import pandas as pd


class ClasificadorChernovia:
    def __init__(self, bucket: str, raw_prefix: str = "raw"):
        self.bucket = bucket
        self.raw_prefix = raw_prefix
        self._cargar_catalogos()

    def _leer_csv(self, filename: str) -> pd.DataFrame:
        s3 = boto3.client("s3")
        key = f"{self.raw_prefix}/{filename}"
        obj = s3.get_object(Bucket=self.bucket, Key=key)
        return pd.read_csv(io.BytesIO(obj["Body"].read()))

    def _cargar_catalogos(self):
        servicios_df = self._leer_csv("COIL_catalogo_servicios_cubiertos.csv")
        self.servicios_cubiertos = set(
            servicios_df[servicios_df["cubre_sistema_publico"] == "SI"]["servicio"].str.strip()
        )

        perfiles_df = self._leer_csv("COIL_catalogo_perfiles_cobertura.csv")
        self.perfiles = dict(
            zip(
                perfiles_df["perfil_cobertura"],
                perfiles_df["porcentaje_cobertura_si_el_servicio_esta_cubierto"],
            )
        )

    def procesar(self, on_step=None):
        if on_step:
            on_step("leyendo", 5)

        # Leer dataset principal desde S3 en chunks para eficiencia de memoria
        s3 = boto3.client("s3")
        key = f"{self.raw_prefix}/COIL_dataset_glosas_salud_1_2M.csv"
        obj = s3.get_object(Bucket=self.bucket, Key=key)

        chunks = []
        for chunk in pd.read_csv(io.BytesIO(obj["Body"].read()), chunksize=200_000):
            chunks.append(chunk)

        df = pd.concat(chunks, ignore_index=True)

        if on_step:
            on_step("extrayendo", 35)

        df["servicio_solicitado"] = (
            df["glosa"].str.extract(r"ServicioSolicitado:\s*([^;]+)")[0].str.strip()
        )
        df["perfil_cobertura"] = (
            df["glosa"].str.extract(r"PerfilCobertura:\s*([^;]+)")[0].str.strip()
        )

        if on_step:
            on_step("clasificando", 65)

        df["cubre"] = df["servicio_solicitado"].isin(self.servicios_cubiertos)
        df["porcentaje_cobertura"] = (
            df["perfil_cobertura"].map(self.perfiles).fillna(0).astype(int)
        )
        df.loc[~df["cubre"], "porcentaje_cobertura"] = 0
        df["valor_cubierto"] = df["valor_procedimiento"] * df["porcentaje_cobertura"] / 100

        if on_step:
            on_step("guardando", 90)

        return df[
            [
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
            ]
        ].copy()
