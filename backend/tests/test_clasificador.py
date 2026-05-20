"""
Tests unitarios para ClasificadorChernovia.
Usan mocks de S3 para no requerir credenciales AWS.
"""
import io
import sys
import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from clasificador import ClasificadorChernovia


# ── Fixtures ──────────────────────────────────────────────────────────────────

SERVICIOS_CSV = (
    "servicio,cubre_sistema_publico\n"
    "Terapia física ambulatoria,SI\n"
    "Consulta médica general,SI\n"
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


def _make_clasificador():
    with patch("clasificador.boto3.client") as mock_boto:
        s3 = MagicMock()
        mock_boto.return_value = s3
        s3.get_object.side_effect = [
            _make_s3_response(SERVICIOS_CSV),
            _make_s3_response(PERFILES_CSV),
        ]
        clf = ClasificadorChernovia("bucket-test", "raw")
    return clf


def _make_glosa(servicio: str, perfil: str) -> str:
    return (
        f"Paciente: Test; DNI: 1234; SeguroSocial: 9999; Edad: 30; "
        f"PerfilCobertura: {perfil}; ServicioSolicitado: {servicio}; Medicacion: ninguna"
    )


def _make_dataset(rows: list[dict]) -> str:
    lines = ["id_solicitud,fecha_solicitud,medio_emisor,valor_procedimiento,entidad_emisora,glosa"]
    for i, r in enumerate(rows):
        glosa = _make_glosa(r["servicio"], r["perfil"])
        lines.append(f"CHV-{i:07d},2024-01-01,Portal,{r['valor']},HospitalTest,\"{glosa}\"")
    return "\n".join(lines)


# ── Tests de catálogos ────────────────────────────────────────────────────────

def test_carga_servicios_cubiertos():
    clf = _make_clasificador()
    assert "Terapia física ambulatoria" in clf.servicios_cubiertos
    assert "Consulta médica general" in clf.servicios_cubiertos
    assert "Cirugía estética" not in clf.servicios_cubiertos


def test_carga_perfiles():
    clf = _make_clasificador()
    assert clf.perfiles["PRIORITARIO"] == 100
    assert clf.perfiles["ESTANDAR"] == 50
    assert clf.perfiles["COPAGO"] == 25


# ── Tests de clasificación ────────────────────────────────────────────────────

@pytest.mark.parametrize("perfil,valor,esperado_pct,esperado_cubierto", [
    ("PRIORITARIO", 1000, 100, 1000.0),
    ("ESTANDAR",    1000, 50,  500.0),
    ("COPAGO",      1000, 25,  250.0),
])
def test_servicio_cubierto_segun_perfil(perfil, valor, esperado_pct, esperado_cubierto):
    clf = _make_clasificador()
    dataset_csv = _make_dataset([{"servicio": "Terapia física ambulatoria", "perfil": perfil, "valor": valor}])

    with patch("clasificador.boto3.client") as mock_boto:
        s3 = MagicMock()
        mock_boto.return_value = s3
        s3.get_object.return_value = _make_s3_response(dataset_csv)

        result = clf.procesar()

    assert len(result) == 1
    row = result.iloc[0]
    assert row["cubre"] is True or row["cubre"] == True  # noqa: E712
    assert row["porcentaje_cobertura"] == esperado_pct
    assert abs(row["valor_cubierto"] - esperado_cubierto) < 0.01


def test_servicio_no_cubierto():
    clf = _make_clasificador()
    dataset_csv = _make_dataset([{"servicio": "Cirugía estética", "perfil": "PRIORITARIO", "valor": 5000}])

    with patch("clasificador.boto3.client") as mock_boto:
        s3 = MagicMock()
        mock_boto.return_value = s3
        s3.get_object.return_value = _make_s3_response(dataset_csv)

        result = clf.procesar()

    row = result.iloc[0]
    assert row["cubre"] is False or row["cubre"] == False  # noqa: E712
    assert row["porcentaje_cobertura"] == 0
    assert row["valor_cubierto"] == 0.0


def test_servicio_desconocido_no_cubierto():
    clf = _make_clasificador()
    dataset_csv = _make_dataset([{"servicio": "Procedimiento no existente", "perfil": "ESTANDAR", "valor": 2000}])

    with patch("clasificador.boto3.client") as mock_boto:
        s3 = MagicMock()
        mock_boto.return_value = s3
        s3.get_object.return_value = _make_s3_response(dataset_csv)

        result = clf.procesar()

    row = result.iloc[0]
    assert row["cubre"] is False or row["cubre"] == False  # noqa: E712
    assert row["valor_cubierto"] == 0.0


def test_multiples_registros_columnas_correctas():
    clf = _make_clasificador()
    rows = [
        {"servicio": "Terapia física ambulatoria", "perfil": "PRIORITARIO", "valor": 1000},
        {"servicio": "Consulta médica general",    "perfil": "ESTANDAR",    "valor": 800},
        {"servicio": "Cirugía estética",           "perfil": "COPAGO",      "valor": 3000},
    ]
    dataset_csv = _make_dataset(rows)

    with patch("clasificador.boto3.client") as mock_boto:
        s3 = MagicMock()
        mock_boto.return_value = s3
        s3.get_object.return_value = _make_s3_response(dataset_csv)

        result = clf.procesar()

    assert len(result) == 3
    expected_cols = {
        "id_solicitud", "fecha_solicitud", "medio_emisor", "valor_procedimiento",
        "entidad_emisora", "servicio_solicitado", "perfil_cobertura",
        "cubre", "porcentaje_cobertura", "valor_cubierto",
    }
    assert expected_cols.issubset(set(result.columns))


def test_on_step_callback_es_llamado():
    clf = _make_clasificador()
    dataset_csv = _make_dataset([{"servicio": "Consulta médica general", "perfil": "ESTANDAR", "valor": 500}])
    pasos_registrados = []

    def on_step(paso, progreso):
        pasos_registrados.append((paso, progreso))

    with patch("clasificador.boto3.client") as mock_boto:
        s3 = MagicMock()
        mock_boto.return_value = s3
        s3.get_object.return_value = _make_s3_response(dataset_csv)
        clf.procesar(on_step=on_step)

    assert len(pasos_registrados) > 0
    pasos = [p for p, _ in pasos_registrados]
    assert "leyendo" in pasos
    assert "clasificando" in pasos
