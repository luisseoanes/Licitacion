"""
Motor de clasificación ML — Chernovia Health
Extiende la clasificación por reglas con fuzzy matching via TF-IDF + cosine similarity.
Permite clasificar glosas con errores ortográficos o variantes de nombre de servicio.
"""
from __future__ import annotations

import io
import re

import boto3
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

THRESHOLD_FUZZY = 0.72   # similitud mínima para considerar fuzzy match
THRESHOLD_RECHAZO = 0.40  # por debajo de esto, clasificamos "no cubre" con alta confianza


class ClasificadorML:
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
        self.servicios_no_cubiertos = set(
            servicios_df[servicios_df["cubre_sistema_publico"] == "NO"]["servicio"].str.strip()
        )
        self.todos_servicios = list(self.servicios_cubiertos | self.servicios_no_cubiertos)
        self._cobertura_map = {
            **{s: True for s in self.servicios_cubiertos},
            **{s: False for s in self.servicios_no_cubiertos},
        }

        perfiles_df = self._leer_csv("COIL_catalogo_perfiles_cobertura.csv")
        self.perfiles = dict(
            zip(
                perfiles_df["perfil_cobertura"],
                perfiles_df["porcentaje_cobertura_si_el_servicio_esta_cubierto"].astype(int),
            )
        )

        # TF-IDF sobre n-gramas de caracteres (2-4): robusto ante errores tipográficos
        self._vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 4),
            sublinear_tf=True,
        )
        self._catalogo_matrix = self._vectorizer.fit_transform(
            [s.lower() for s in self.todos_servicios]
        )

    # ── Clasificación individual ────────────────────────────────────────────

    def clasificar_uno(self, glosa: str, valor_procedimiento: float = 0.0) -> dict:
        """
        Clasifica una sola glosa en tiempo real.
        Retorna resultado con score de confianza y método usado (exacto | fuzzy_ml | sin_match).
        """
        servicio_raw, perfil = self._extraer_campos(glosa)

        if not servicio_raw:
            return self._resultado(
                servicio_raw=None,
                perfil=perfil,
                cubre=False,
                confianza=0.0,
                metodo="sin_extraccion",
                servicio_canonico=None,
                valor_procedimiento=valor_procedimiento,
            )

        # 1. Exacto
        if servicio_raw in self._cobertura_map:
            cubre = self._cobertura_map[servicio_raw]
            return self._resultado(
                servicio_raw=servicio_raw,
                perfil=perfil,
                cubre=cubre,
                confianza=1.0,
                metodo="exacto",
                servicio_canonico=servicio_raw,
                valor_procedimiento=valor_procedimiento,
            )

        # 2. Fuzzy ML
        query_vec = self._vectorizer.transform([servicio_raw.lower()])
        sims = cosine_similarity(query_vec, self._catalogo_matrix)[0]
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])
        servicio_canonico = self.todos_servicios[best_idx]

        if best_sim >= THRESHOLD_FUZZY:
            cubre = self._cobertura_map[servicio_canonico]
            return self._resultado(
                servicio_raw=servicio_raw,
                perfil=perfil,
                cubre=cubre,
                confianza=round(best_sim, 4),
                metodo="fuzzy_ml",
                servicio_canonico=servicio_canonico,
                valor_procedimiento=valor_procedimiento,
            )

        # 3. Sin match
        return self._resultado(
            servicio_raw=servicio_raw,
            perfil=perfil,
            cubre=False,
            confianza=round(max(0.0, 1.0 - best_sim), 4),
            metodo="sin_match",
            servicio_canonico=None,
            valor_procedimiento=valor_procedimiento,
        )

    # ── Procesamiento batch con scores de confianza ─────────────────────────

    def enriquecer_con_confianza(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Dado un DataFrame ya clasificado (con 'servicio_solicitado' y 'cubre'),
        agrega columnas 'confianza' y 'metodo' calculadas con el motor ML.
        Se usa sobre el resultado del Glue job para enriquecer los datos.
        """
        df = df.copy()

        servicios = df["servicio_solicitado"].fillna("").tolist()
        if not servicios:
            df["confianza"] = 1.0
            df["metodo"] = "exacto"
            return df

        query_matrix = self._vectorizer.transform([s.lower() for s in servicios])
        sims_matrix = cosine_similarity(query_matrix, self._catalogo_matrix)

        best_sims = sims_matrix.max(axis=1)

        metodos = []
        confianzas = []
        for s, sim in zip(servicios, best_sims):
            if not s:
                metodos.append("sin_extraccion")
                confianzas.append(0.0)
            elif s in self._cobertura_map:
                metodos.append("exacto")
                confianzas.append(1.0)
            elif sim >= THRESHOLD_FUZZY:
                metodos.append("fuzzy_ml")
                confianzas.append(round(float(sim), 4))
            else:
                metodos.append("sin_match")
                confianzas.append(round(max(0.0, 1.0 - float(sim)), 4))

        df["confianza"] = confianzas
        df["metodo"] = metodos
        return df

    # ── Métricas de calidad ─────────────────────────────────────────────────

    def metricas_calidad(self, df: pd.DataFrame) -> dict:
        total = len(df)
        if total == 0:
            return {}

        sin_servicio = int(df["servicio_solicitado"].isna().sum() + (df["servicio_solicitado"] == "").sum())
        sin_perfil = int(df["perfil_cobertura"].isna().sum() + (df["perfil_cobertura"] == "").sum())

        df_ml = self.enriquecer_con_confianza(df)
        conteo_metodo = df_ml["metodo"].value_counts().to_dict()

        confianza_media = float(df_ml["confianza"].mean())
        alta_confianza = int((df_ml["confianza"] >= 0.90).sum())
        baja_confianza = int((df_ml["confianza"] < 0.70).sum())

        return {
            "total_registros": total,
            "parseo": {
                "exitoso": total - sin_servicio,
                "sin_servicio": sin_servicio,
                "sin_perfil": sin_perfil,
                "tasa_parseo": round((total - sin_servicio) / total * 100, 2),
            },
            "clasificacion": {
                "exacto": conteo_metodo.get("exacto", 0),
                "fuzzy_ml": conteo_metodo.get("fuzzy_ml", 0),
                "sin_match": conteo_metodo.get("sin_match", 0),
                "sin_extraccion": conteo_metodo.get("sin_extraccion", 0),
            },
            "confianza": {
                "media": round(confianza_media, 4),
                "alta_confianza_pct": round(alta_confianza / total * 100, 2),
                "baja_confianza_pct": round(baja_confianza / total * 100, 2),
            },
        }

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _extraer_campos(glosa: str) -> tuple[str | None, str]:
        servicio_m = re.search(r"ServicioSolicitado:\s*([^;]+)", glosa or "")
        perfil_m = re.search(r"PerfilCobertura:\s*([^;]+)", glosa or "")
        servicio = servicio_m.group(1).strip() if servicio_m else None
        perfil = perfil_m.group(1).strip() if perfil_m else "DESCONOCIDO"
        return servicio, perfil

    def _resultado(
        self,
        servicio_raw,
        perfil,
        cubre,
        confianza,
        metodo,
        servicio_canonico,
        valor_procedimiento,
    ) -> dict:
        porcentaje = int(self.perfiles.get(perfil, 0)) if cubre else 0
        valor_cubierto = round(valor_procedimiento * porcentaje / 100, 2)
        razon = self._generar_razon(cubre, metodo, servicio_raw, servicio_canonico, perfil, porcentaje, confianza)
        return {
            "servicio_solicitado": servicio_raw,
            "servicio_canonico": servicio_canonico,
            "perfil_cobertura": perfil,
            "cubre": cubre,
            "porcentaje_cobertura": porcentaje,
            "valor_procedimiento": valor_procedimiento,
            "valor_cubierto": valor_cubierto,
            "confianza": confianza,
            "metodo": metodo,
            "razon_decision": razon,
        }

    @staticmethod
    def _generar_razon(cubre, metodo, servicio_raw, servicio_canonico, perfil, porcentaje, confianza) -> str:
        pct_str = f"{round(confianza * 100):.0f}%"
        if metodo == "sin_extraccion":
            return "No se pudo extraer el campo ServicioSolicitado de la glosa médica."
        if metodo == "sin_match":
            return (
                f"Servicio '{servicio_raw}' no fue identificado en el catálogo "
                f"(similitud máxima: {pct_str}). Cobertura pública: 0%."
            )
        if cubre:
            if metodo == "fuzzy_ml":
                return (
                    f"Servicio corregido por ML: '{servicio_raw}' → '{servicio_canonico}' "
                    f"(confianza {pct_str}). Incluido en catálogo DS-2024-001. "
                    f"Perfil {perfil}: {porcentaje}% reconocido."
                )
            return (
                f"Servicio '{servicio_canonico}' incluido en catálogo DS-2024-001. "
                f"Perfil {perfil}: {porcentaje}% reconocido por el sistema público."
            )
        if metodo == "fuzzy_ml":
            return (
                f"Servicio '{servicio_raw}' identificado como '{servicio_canonico}' por ML "
                f"(confianza {pct_str}), pero no figura en el catálogo de servicios cubiertos."
            )
        return (
            f"Servicio '{servicio_raw}' no figura en el catálogo de servicios cubiertos "
            f"(Resolución DS-2024-001). Cobertura pública: 0%."
        )
