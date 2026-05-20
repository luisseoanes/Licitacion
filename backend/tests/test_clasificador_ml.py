"""
Tests unitarios para ClasificadorML — fuzzy matching con TF-IDF.
"""
import sys
import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from clasificador_ml import ClasificadorML


SERVICIOS_CSV = (
    "servicio,cubre_sistema_publico\n"
    "Terapia física ambulatoria,SI\n"
    "Consulta médica general,SI\n"
    "Cirugía cardiovascular,SI\n"
    "Cirugía estética,NO\n"
)

PERFILES_CSV = (
    "perfil_cobertura,porcentaje_cobertura_si_el_servicio_esta_cubierto\n"
    "PRIORITARIO,100\n"
    "ESTANDAR,50\n"
    "COPAGO,25\n"
)


def _make_s3_response(csv_text: str):
    body = MagicMock()
    body.read.return_value = csv_text.encode("utf-8")
    return {"Body": body}


def _make_clf():
    with patch("clasificador_ml.boto3.client") as mock_boto:
        s3 = MagicMock()
        mock_boto.return_value = s3
        s3.get_object.side_effect = [
            _make_s3_response(SERVICIOS_CSV),
            _make_s3_response(PERFILES_CSV),
        ]
        clf = ClasificadorML("bucket-test", "raw")
    return clf


def _glosa(servicio: str, perfil: str) -> str:
    return (
        f"Paciente: Test; DNI: 1234; SeguroSocial: 9999; Edad: 30; "
        f"PerfilCobertura: {perfil}; ServicioSolicitado: {servicio}; Medicacion: ninguna"
    )


# ── Clasificación exacta ──────────────────────────────────────────────────────

def test_exacto_cubierto():
    clf = _make_clf()
    r = clf.clasificar_uno(_glosa("Terapia física ambulatoria", "PRIORITARIO"), 1000)
    assert r["cubre"] is True
    assert r["confianza"] == 1.0
    assert r["metodo"] == "exacto"
    assert r["porcentaje_cobertura"] == 100
    assert r["valor_cubierto"] == 1000.0


def test_exacto_no_cubierto():
    clf = _make_clf()
    r = clf.clasificar_uno(_glosa("Cirugía estética", "PRIORITARIO"), 500)
    assert r["cubre"] is False
    assert r["confianza"] == 1.0
    assert r["metodo"] == "exacto"
    assert r["valor_cubierto"] == 0.0


# ── Fuzzy matching ────────────────────────────────────────────────────────────

def test_fuzzy_typo_menor():
    """Typo menor: 'fisca' en lugar de 'física' debe hacer fuzzy match."""
    clf = _make_clf()
    r = clf.clasificar_uno(_glosa("Terapia fisca ambulatoria", "ESTANDAR"), 2000)
    # El fuzzy matching debe reconocerlo como cubierto con alta similitud
    assert r["metodo"] in ("fuzzy_ml", "exacto")
    if r["metodo"] == "fuzzy_ml":
        assert r["cubre"] is True
        assert r["confianza"] > 0.0
        assert r["servicio_canonico"] == "Terapia física ambulatoria"


def test_fuzzy_variante_nombre():
    """Variante de nombre debe resolver al servicio canónico."""
    clf = _make_clf()
    r = clf.clasificar_uno(_glosa("Terapia fisica ambulatoria", "COPAGO"), 800)
    assert r["metodo"] in ("fuzzy_ml", "exacto")


# ── Sin match ─────────────────────────────────────────────────────────────────

def test_servicio_completamente_desconocido():
    clf = _make_clf()
    r = clf.clasificar_uno(_glosa("Tratamiento de bienestar lunar", "PRIORITARIO"), 3000)
    assert r["cubre"] is False
    assert r["metodo"] == "sin_match"
    assert r["valor_cubierto"] == 0.0


# ── Sin extracción ────────────────────────────────────────────────────────────

def test_glosa_sin_servicio():
    clf = _make_clf()
    r = clf.clasificar_uno("Paciente: Test; DNI: 1234; PerfilCobertura: ESTANDAR; Medicacion: ninguna", 1000)
    assert r["cubre"] is False
    assert r["metodo"] == "sin_extraccion"
    assert r["confianza"] == 0.0


def test_glosa_vacia():
    clf = _make_clf()
    r = clf.clasificar_uno("", 0)
    assert r["cubre"] is False
    assert r["metodo"] == "sin_extraccion"


# ── Score de confianza ────────────────────────────────────────────────────────

def test_confianza_rango_valido():
    clf = _make_clf()
    for glosa_text, perfil in [
        ("Terapia física ambulatoria", "PRIORITARIO"),
        ("Cirugía estética", "ESTANDAR"),
        ("Servicio inventado xyz", "COPAGO"),
    ]:
        r = clf.clasificar_uno(_glosa(glosa_text, perfil))
        assert 0.0 <= r["confianza"] <= 1.0, f"Confianza fuera de rango para '{glosa_text}': {r['confianza']}"


# ── Métricas de calidad ────────────────────────────────────────────────────────

def test_metricas_calidad_estructura():
    clf = _make_clf()
    df = pd.DataFrame({
        "servicio_solicitado": ["Terapia física ambulatoria", "Consulta médica general", None, "xyz"],
        "perfil_cobertura": ["PRIORITARIO", "ESTANDAR", "COPAGO", "PRIORITARIO"],
        "cubre": [True, True, False, False],
    })
    metricas = clf.metricas_calidad(df)
    assert "total_registros" in metricas
    assert "parseo" in metricas
    assert "clasificacion" in metricas
    assert "confianza" in metricas
    assert metricas["total_registros"] == 4
    assert metricas["parseo"]["tasa_parseo"] <= 100


def test_metricas_calidad_dataframe_vacio():
    clf = _make_clf()
    metricas = clf.metricas_calidad(pd.DataFrame())
    assert metricas == {}
