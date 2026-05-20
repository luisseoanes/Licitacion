"""
Generador de reportes PDF ejecutivos — Chernovia Health
Produce un informe diario post-ejecución con estadísticas, distribución y anomalías.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm

AZUL = colors.HexColor("#1e40af")
AZUL_CLARO = colors.HexColor("#dbeafe")
VERDE = colors.HexColor("#166534")
VERDE_CLARO = colors.HexColor("#dcfce7")
ROJO = colors.HexColor("#991b1b")
ROJO_CLARO = colors.HexColor("#fee2e2")
GRIS = colors.HexColor("#6b7280")
GRIS_CLARO = colors.HexColor("#f3f4f6")


def _estilos():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("titulo",     parent=s["Title"],   fontSize=18, textColor=AZUL,  spaceAfter=4))
    s.add(ParagraphStyle("subtitulo",  parent=s["Heading2"],fontSize=12, textColor=AZUL,  spaceAfter=6))
    s.add(ParagraphStyle("normal_ch",  parent=s["Normal"],  fontSize=9,  leading=13))
    s.add(ParagraphStyle("pie",        parent=s["Normal"],  fontSize=7,  textColor=GRIS))
    s.add(ParagraphStyle("kpi_label",  parent=s["Normal"],  fontSize=8,  textColor=GRIS))
    s.add(ParagraphStyle("kpi_valor",  parent=s["Normal"],  fontSize=22, textColor=AZUL,  fontName="Helvetica-Bold"))
    return s


def _tabla_kpis(stats: dict, s) -> Table:
    total = stats.get("total", 0)
    cubiertos = stats.get("cubiertos", 0)
    tasa = stats.get("tasa_cobertura", 0)
    valor_cubierto = stats.get("valor_cubierto_total", 0)

    filas = [
        [
            _kpi_cell(f"{total:,}", "Total solicitudes", s),
            _kpi_cell(f"{cubiertos:,}", "Cubiertas", s),
            _kpi_cell(f"{tasa:.1f}%", "Tasa de cobertura", s),
            _kpi_cell(f"${valor_cubierto:,.0f}", "Valor fiscal total", s),
        ]
    ]
    t = Table(filas, colWidths=[(PAGE_W - 2 * MARGIN) / 4] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL_CLARO),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [AZUL_CLARO]),
        ("BOX", (0, 0), (-1, -1), 0.5, AZUL),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return t


def _kpi_cell(valor: str, label: str, s) -> list:
    return [Paragraph(valor, s["kpi_valor"]), Paragraph(label, s["kpi_label"])]


def _tabla_perfiles(por_perfil: list[dict], s) -> Table:
    cabecera = [["Perfil", "Total", "Cubiertos", "% Cobertura", "Valor cubierto ($)"]]
    filas = cabecera + [
        [
            p.get("perfil_cobertura", "—"),
            f"{p.get('total', 0):,}",
            f"{p.get('cubiertos', 0):,}",
            f"{p['cubiertos']/p['total']*100:.1f}%" if p.get("total") else "—",
            f"${p.get('valor_cubierto', 0):,.0f}",
        ]
        for p in por_perfil
    ]
    anchos = [4 * cm, 3 * cm, 3 * cm, 3.5 * cm, 4 * cm]
    t = Table(filas, colWidths=anchos)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLARO]),
        ("GRID",  (0, 0), (-1, -1), 0.3, GRIS),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    return t


def _tabla_top_servicios(por_servicio: list[dict], s) -> Table:
    cabecera = [["#", "Servicio", "Total solicitudes", "Cubiertos", "Valor cubierto ($)"]]
    filas = cabecera + [
        [
            str(i + 1),
            sv.get("servicio_solicitado", "—")[:45],
            f"{sv.get('total', 0):,}",
            f"{sv.get('cubiertos', 0):,}",
            f"${sv.get('valor_cubierto', 0):,.0f}",
        ]
        for i, sv in enumerate(por_servicio[:10])
    ]
    anchos = [1 * cm, 7.5 * cm, 3 * cm, 2.5 * cm, 3.5 * cm]
    t = Table(filas, colWidths=anchos)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLARO]),
        ("GRID",  (0, 0), (-1, -1), 0.3, GRIS),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    return t


def _tabla_anomalias(resumen: list[dict], total_anomalias: int, tasa: float, s) -> Table:
    cabecera = [["Código", "Tipo", "Gravedad", "Casos detectados"]]
    filas = cabecera + [
        [
            a.get("codigo", "—"),
            a.get("tipo", "—").replace("_", " "),
            a.get("gravedad", "—"),
            str(a.get("total", 0)),
        ]
        for a in resumen
    ]
    if not resumen:
        filas.append(["—", "Sin anomalías detectadas", "—", "0"])

    anchos = [3 * cm, 5 * cm, 3 * cm, 4 * cm]
    t = Table(filas, colWidths=anchos)

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), ROJO),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROJO_CLARO]),
        ("GRID",  (0, 0), (-1, -1), 0.3, GRIS),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]
    for i, a in enumerate(resumen, start=1):
        if a.get("gravedad") == "ALTA":
            style.append(("TEXTCOLOR", (2, i), (2, i), ROJO))
            style.append(("FONTNAME",  (2, i), (2, i), "Helvetica-Bold"))
    t.setStyle(TableStyle(style))
    return t


def generar_pdf(
    stats: dict[str, Any],
    anomalias_data: dict[str, Any] | None = None,
    fecha_ejecucion: str | None = None,
) -> bytes:
    """Genera el PDF ejecutivo y retorna los bytes del archivo."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    s = _estilos()
    fecha = fecha_ejecucion or datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    story = []

    # ── Encabezado ────────────────────────────────────────────────────────────
    story.append(Paragraph("DataHealth Cloud Solutions", s["titulo"]))
    story.append(Paragraph("Reporte Ejecutivo — Sistema de Salud Chernovia", s["subtitulo"]))
    story.append(Paragraph(f"Generado: {fecha}  ·  Versión del pipeline: 2.0", s["pie"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=AZUL, spaceAfter=12))

    # ── KPIs principales ──────────────────────────────────────────────────────
    story.append(Paragraph("Resumen de procesamiento", s["subtitulo"]))
    story.append(_tabla_kpis(stats, s))
    story.append(Spacer(1, 0.4 * cm))

    # ── Distribución por día ──────────────────────────────────────────────────
    por_dia = stats.get("por_dia", [])
    if por_dia:
        story.append(Paragraph("Distribución diaria de solicitudes", s["subtitulo"]))
        cab = [["Fecha", "Total", "Cubiertos", "No cubiertos", "Tasa cobertura"]]
        rows = cab + [
            [
                d.get("fecha", "—"),
                f"{d.get('total', 0):,}",
                f"{d.get('cubiertos', 0):,}",
                f"{d.get('total', 0) - d.get('cubiertos', 0):,}",
                f"{d['cubiertos']/d['total']*100:.1f}%" if d.get("total") else "—",
            ]
            for d in por_dia
        ]
        t = Table(rows, colWidths=[3.5 * cm, 3 * cm, 3 * cm, 3 * cm, 3.5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLARO]),
            ("GRID",  (0, 0), (-1, -1), 0.3, GRIS),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4 * cm))

    # ── Cobertura por perfil ──────────────────────────────────────────────────
    por_perfil = stats.get("por_perfil", [])
    if por_perfil:
        story.append(Paragraph("Cobertura por perfil de usuario", s["subtitulo"]))
        story.append(_tabla_perfiles(por_perfil, s))
        story.append(Spacer(1, 0.4 * cm))

    # ── Top 10 servicios ──────────────────────────────────────────────────────
    por_servicio = stats.get("por_servicio", [])
    if por_servicio:
        story.append(Paragraph("Top 10 servicios más solicitados", s["subtitulo"]))
        story.append(_tabla_top_servicios(por_servicio, s))
        story.append(Spacer(1, 0.4 * cm))

    # ── Anomalías ─────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS, spaceAfter=8))
    story.append(Paragraph("Alertas y anomalías detectadas", s["subtitulo"]))
    if anomalias_data:
        total_an = anomalias_data.get("total_anomalias", 0)
        tasa_an = anomalias_data.get("tasa_anomalia_pct", 0)
        story.append(Paragraph(
            f"Anomalías detectadas: <b>{total_an:,}</b> ({tasa_an:.2f}% del total). "
            f"Requieren revisión manual.",
            s["normal_ch"],
        ))
        story.append(Spacer(1, 0.2 * cm))
        story.append(_tabla_anomalias(anomalias_data.get("resumen_por_tipo", []), total_an, tasa_an, s))
    else:
        story.append(Paragraph("No se ejecutó el módulo de detección de anomalías.", s["normal_ch"]))
    story.append(Spacer(1, 0.5 * cm))

    # ── Pie de página ─────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS, spaceAfter=4))
    story.append(Paragraph(
        "DataHealth Cloud Solutions · Universidad Panamericana MX × UPB Colombia · "
        "Proyecto COIL Big Data 2026 · Documento generado automáticamente — no requiere firma.",
        s["pie"],
    ))

    doc.build(story)
    return buf.getvalue()
