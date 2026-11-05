"""
PDF Report Export service using ReportLab.
Generates evidence-grounded medical document summaries with
plain-language findings, results table, and safety disclaimers.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.export import GeneratedExport
from app.services.document_service import get_document_for_user


async def generate_document_pdf_summary(
    db: AsyncSession,
    document_id: UUID,
    user_id: UUID,
) -> GeneratedExport:
    """
    Generates a clean, branded PDF summary for a medical document.
    """
    doc = await get_document_for_user(db, document_id, user_id)

    export_id = uuid.uuid4()
    pdf_filename = f"JohnnySummUP_Summary_{export_id}.pdf"
    pdf_path = os.path.join(settings.EXPORTS_DIR, pdf_filename)

    # Build PDF using ReportLab
    pdf = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Branded styles
    brand_color = colors.HexColor("#6257F5")
    deep_ink = colors.HexColor("#292443")
    teal_color = colors.HexColor("#22B8B0")
    canvas_bg = colors.HexColor("#F7F7FB")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=brand_color,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "DocSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#77758A"),
        spaceAfter=14,
    )
    heading_style = ParagraphStyle(
        "SecHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=deep_ink,
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=deep_ink,
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Italic"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        textColor=colors.HexColor("#77758A"),
        spaceBefore=14,
    )

    story = []

    # Title & Header
    story.append(Paragraph("JohnnySummUP — Medical Intelligence Summary", title_style))
    date_str = doc.document_date.strftime("%B %d, %Y") if doc.document_date else "Not stated"
    sub_text = (
        f"<b>Document:</b> {doc.document_title or doc.original_filename} | "
        f"<b>Type:</b> {doc.document_type.replace('_', ' ').title()} | "
        f"<b>Test Date:</b> {date_str}"
    )
    story.append(Paragraph(sub_text, subtitle_style))
    story.append(Spacer(1, 8))

    # Summary Section
    summary_record = doc.summaries[0] if doc.summaries else None
    if summary_record:
        story.append(Paragraph("Plain-Language Overview", heading_style))
        story.append(Paragraph(summary_record.summary_text, body_style))
        story.append(Spacer(1, 8))

    # Findings
    if doc.findings:
        story.append(Paragraph("Key Observations & Source Flags", heading_style))
        for f in doc.findings[:8]:
            snippet_text = ""
            if f.evidence_reference and len(f.evidence_reference) > 0:
                snip = f.evidence_reference[0].get("snippet")
                if snip:
                    snippet_text = f" <i>(Evidence: '{snip}')</i>"
            f_text = f"• <b>{f.title}</b>: {f.explanation}{snippet_text}"
            story.append(Paragraph(f_text, body_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))

    # Measurements Table
    if doc.extracted_measurements:
        story.append(Paragraph("Extracted Test Measurements", heading_style))
        table_data = [
            ["Test Parameter", "Result Value", "Report Reference Range", "Status"]
        ]
        for m in doc.extracted_measurements:
            name = m.parameter_name_display or m.parameter_name_raw
            val = f"{m.raw_value_text} {m.source_unit or ''}".strip()
            range_text = m.reference_text_raw or (
                f"{m.reference_low} - {m.reference_high} {m.source_unit or ''}".strip()
                if m.reference_low and m.reference_high
                else "Not stated"
            )
            status_text = m.calculated_range_status.replace("_", " ").title()
            table_data.append([name[:30], val, range_text, status_text])

        t = Table(table_data, colWidths=[160, 110, 160, 100])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), brand_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E8E7F0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, canvas_bg]),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))

    # Clinician Questions
    if summary_record and summary_record.structured_summary:
        questions = summary_record.structured_summary.get("questionsForClinician", [])
        if questions:
            story.append(Paragraph("Questions to Discuss with Your Doctor", heading_style))
            for q in questions:
                story.append(Paragraph(f"? {q}", body_style))
                story.append(Spacer(1, 3))
            story.append(Spacer(1, 8))

    # Mandatory Safety Disclaimer
    story.append(Paragraph(
        "<b>Important Medical Notice:</b> This document is an informational explanation generated by JohnnySummUP "
        "and is grounded in the source text of the uploaded medical report. It does NOT diagnose medical conditions, "
        "predict disease risk, prescribe medication, or replace the expertise of qualified healthcare professionals. "
        "Always review the original laboratory report with your physician.",
        disclaimer_style,
    ))

    pdf.build(story)

    export = GeneratedExport(
        id=export_id,
        user_id=user_id,
        document_id=doc.id,
        export_type="single_report_summary",
        storage_path=pdf_path,
        status="completed",
    )
    db.add(export)
    await db.commit()
    await db.refresh(export)

    return export

