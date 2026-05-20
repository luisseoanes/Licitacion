"""
Módulo de detección de anomalías y fraude — Chernovia Health
Analiza el conjunto de solicitudes procesadas en busca de patrones sospechosos.
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd


class DetectorAnomalias:
    UMBRAL_ENTIDAD_BAJA_RECHAZO = 0.05   # < 5% rechazo en entidad = sospechoso
    UMBRAL_VALOR_ZSCORE = 3.0             # > 3σ del promedio del servicio = atípico
    MAX_ANOMALIAS_POR_TIPO = 50           # límite de filas devueltas por tipo

    # Servicios exclusivos de pediatría
    SERVICIOS_PEDIATRICOS = {
        "Pediatría general", "Neonatología", "Cirugía pediátrica",
        "Neurología pediátrica", "Cardiología pediátrica",
    }
    EDAD_MAX_PEDIATRICO = 18

    def detectar(self, df: pd.DataFrame) -> dict[str, Any]:
        df = df.copy()
        df = self._enriquecer(df)

        resultados: list[dict] = []
        resultados += self._duplicados(df)
        resultados += self._valor_atipico(df)
        resultados += self._entidad_sospechosa(df)
        resultados += self._incompatibilidad_edad(df)

        total = len(df)
        return {
            "total_solicitudes_analizadas": total,
            "total_anomalias": len(resultados),
            "tasa_anomalia_pct": round(len(resultados) / total * 100, 3) if total else 0.0,
            "resumen_por_tipo": self._resumen(resultados),
            "anomalias": resultados[:300],
        }

    # ── Enriquecimiento ──────────────────────────────────────────────────────

    def _enriquecer(self, df: pd.DataFrame) -> pd.DataFrame:
        if "glosa" in df.columns:
            df["_dno"] = df["glosa"].str.extract(r"DNO:\s*([^;]+)")[0].str.strip().fillna("")
            df["_edad"] = pd.to_numeric(
                df["glosa"].str.extract(r"Edad:\s*(\d+)")[0], errors="coerce"
            )
        else:
            df["_dno"] = ""
            df["_edad"] = float("nan")

        df["_fecha_dia"] = df["fecha_solicitud"].astype(str).str[:10]
        return df

    # ── Reglas de detección ──────────────────────────────────────────────────

    def _duplicados(self, df: pd.DataFrame) -> list[dict]:
        """Misma DNO + mismo servicio + mismo día más de una vez."""
        if "_dno" not in df.columns or "servicio_solicitado" not in df.columns:
            return []

        grp = (
            df[df["_dno"] != ""]
            .groupby(["_dno", "servicio_solicitado", "_fecha_dia"])
            .agg(count=("id_solicitud", "count"), ids=("id_solicitud", list))
            .reset_index()
        )
        dups = grp[grp["count"] > 1]

        anomalias = []
        for _, row in dups.head(self.MAX_ANOMALIAS_POR_TIPO).iterrows():
            anomalias.append({
                "tipo": "DUPLICADO",
                "codigo": "AN-DUP-001",
                "gravedad": "ALTA",
                "descripcion": (
                    f"DNO {row['_dno']} solicitó '{row['servicio_solicitado']}' "
                    f"{int(row['count'])} veces el {row['_fecha_dia']}"
                ),
                "ids_afectados": row["ids"][:5],
            })
        return anomalias

    def _valor_atipico(self, df: pd.DataFrame) -> list[dict]:
        """Valor del procedimiento > media + 3σ para ese tipo de servicio."""
        if "servicio_solicitado" not in df.columns or "valor_procedimiento" not in df.columns:
            return []

        df2 = df.copy()
        df2["valor_procedimiento"] = pd.to_numeric(df2["valor_procedimiento"], errors="coerce")
        stats = (
            df2.groupby("servicio_solicitado")["valor_procedimiento"]
            .agg(["mean", "std"])
            .reset_index()
        )
        stats["umbral"] = stats["mean"] + self.UMBRAL_VALOR_ZSCORE * stats["std"].fillna(0)
        merged = df2.merge(stats[["servicio_solicitado", "mean", "umbral"]], on="servicio_solicitado", how="left")
        atipicos = merged[(merged["valor_procedimiento"] > merged["umbral"]) & (merged["umbral"] > 0)]

        anomalias = []
        for _, row in atipicos.head(self.MAX_ANOMALIAS_POR_TIPO).iterrows():
            anomalias.append({
                "tipo": "VALOR_ATIPICO",
                "codigo": "AN-VAL-002",
                "gravedad": "MEDIA",
                "descripcion": (
                    f"Servicio '{row['servicio_solicitado']}': valor "
                    f"${row['valor_procedimiento']:,.0f} supera 3σ "
                    f"(promedio servicio: ${row['mean']:,.0f})"
                ),
                "ids_afectados": [row["id_solicitud"]],
            })
        return anomalias

    def _entidad_sospechosa(self, df: pd.DataFrame) -> list[dict]:
        """Entidad con tasa de rechazo < 5% sobre más de 10 solicitudes."""
        if "entidad_emisora" not in df.columns or "cubre" not in df.columns:
            return []

        grp = df.groupby("entidad_emisora").agg(
            total=("id_solicitud", "count"),
            cubiertos=("cubre", "sum"),
        ).reset_index()
        grp["tasa_rechazo"] = 1 - (grp["cubiertos"] / grp["total"])
        sospechosas = grp[
            (grp["tasa_rechazo"] < self.UMBRAL_ENTIDAD_BAJA_RECHAZO) & (grp["total"] > 10)
        ]

        anomalias = []
        for _, row in sospechosas.head(self.MAX_ANOMALIAS_POR_TIPO).iterrows():
            anomalias.append({
                "tipo": "ENTIDAD_SOSPECHOSA",
                "codigo": "AN-ENT-003",
                "gravedad": "MEDIA",
                "descripcion": (
                    f"Entidad '{row['entidad_emisora']}': tasa de rechazo "
                    f"{row['tasa_rechazo']*100:.1f}% (umbral: <5%) "
                    f"sobre {int(row['total'])} solicitudes"
                ),
                "ids_afectados": [],
            })
        return anomalias

    def _incompatibilidad_edad(self, df: pd.DataFrame) -> list[dict]:
        """Servicio pediátrico solicitado para paciente mayor de 18 años."""
        if "_edad" not in df.columns or "servicio_solicitado" not in df.columns:
            return []

        mask = (
            df["servicio_solicitado"].isin(self.SERVICIOS_PEDIATRICOS)
            & (df["_edad"] > self.EDAD_MAX_PEDIATRICO)
            & df["_edad"].notna()
        )

        anomalias = []
        for _, row in df[mask].head(self.MAX_ANOMALIAS_POR_TIPO).iterrows():
            anomalias.append({
                "tipo": "INCOMPATIBILIDAD_EDAD",
                "codigo": "AN-EDAD-004",
                "gravedad": "ALTA",
                "descripcion": (
                    f"Servicio pediátrico '{row['servicio_solicitado']}' "
                    f"solicitado para paciente de {int(row['_edad'])} años"
                ),
                "ids_afectados": [row["id_solicitud"]],
            })
        return anomalias

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _resumen(anomalias: list[dict]) -> list[dict]:
        counts: dict[str, dict] = {}
        for a in anomalias:
            t = a["tipo"]
            if t not in counts:
                counts[t] = {"tipo": t, "codigo": a["codigo"], "gravedad": a["gravedad"], "total": 0}
            counts[t]["total"] += 1
        return sorted(counts.values(), key=lambda x: -x["total"])
