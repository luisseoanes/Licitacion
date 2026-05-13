import os
import pandas as pd


class ClasificadorChernovia:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self._cargar_catalogos()

    def _cargar_catalogos(self):
        servicios_df = pd.read_csv(
            os.path.join(self.data_dir, "COIL_catalogo_servicios_cubiertos.csv")
        )
        self.servicios_cubiertos = set(
            servicios_df[servicios_df["cubre_sistema_publico"] == "SI"]["servicio"].str.strip()
        )

        perfiles_df = pd.read_csv(
            os.path.join(self.data_dir, "COIL_catalogo_perfiles_cobertura.csv")
        )
        self.perfiles = dict(
            zip(
                perfiles_df["perfil_cobertura"],
                perfiles_df["porcentaje_cobertura_si_el_servicio_esta_cubierto"],
            )
        )

    def procesar(self, on_step=None):
        dataset_path = os.path.join(self.data_dir, "COIL_dataset_glosas_salud_1_2M.csv")

        if on_step:
            on_step("leyendo", 5)

        df = pd.read_csv(dataset_path)

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
