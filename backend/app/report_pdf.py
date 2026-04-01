"""
Generador de reportes PDF para Malaquías CV Screener.
Genera un PDF profesional con los resultados del screening de una oferta.
"""
import io
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# Colores del brand
BG_DARK = HexColor('#0a0a0a')
PRIMARY = HexColor('#ededed')
ACCENT = HexColor('#0bdacb')
GREEN = HexColor('#22c55e')
YELLOW = HexColor('#eab308')
RED = HexColor('#ef4444')
GRAY = HexColor('#71717a')
WHITE = HexColor('#ffffff')
LIGHT_BG = HexColor('#1a1a1a')
BORDER = HexColor('#27272a')


def get_rec_color(rec):
    r = (rec or '').lower()
    if 'entrevistar' in r:
        return GREEN
    if 'considerar' in r:
        return YELLOW
    return RED


def build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'BrandTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=HexColor('#1a1a1a'),
        spaceAfter=4 * mm,
    ))
    styles.add(ParagraphStyle(
        'BrandSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=GRAY,
        spaceAfter=8 * mm,
    ))
    styles.add(ParagraphStyle(
        'SectionHead',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=HexColor('#1a1a1a'),
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
    ))
    styles.add(ParagraphStyle(
        'CandidateName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=HexColor('#0a0a0a'),
        spaceAfter=1 * mm,
    ))
    styles.add(ParagraphStyle(
        'BodyText2',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=HexColor('#3f3f46'),
        leading=13,
    ))
    styles.add(ParagraphStyle(
        'SmallLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=GRAY,
        spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        textColor=GRAY,
        alignment=TA_CENTER,
    ))

    return styles


def generate_oferta_pdf(oferta, candidatos):
    """
    Genera un PDF con los resultados de screening de una oferta.
    Retorna un buffer de bytes con el PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = build_styles()
    elements = []

    # Header
    elements.append(Paragraph('Malaquías Recruiting Suite', styles['BrandTitle']))

    desc_preview = (oferta.descripcion or '')[:200]
    if len(oferta.descripcion or '') > 200:
        desc_preview += '...'
    subtitle_parts = []
    if oferta.categoria:
        subtitle_parts.append(f'Categoría: {oferta.categoria.capitalize()}')
    if oferta.stack:
        subtitle_parts.append(f'Stack: {oferta.stack}')
    subtitle_parts.append(f'{len(candidatos)} candidatos analizados')
    elements.append(Paragraph(' · '.join(subtitle_parts), styles['BrandSub']))

    # Línea separadora
    elements.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))

    # Resumen rápido
    elements.append(Paragraph('Resumen de la Posición', styles['SectionHead']))
    elements.append(Paragraph(desc_preview, styles['BodyText2']))
    elements.append(Spacer(1, 4 * mm))

    # Tabla resumen
    total = len(candidatos)
    ent = sum(1 for c in candidatos if 'entrevistar' in (c.recomendacion or '').lower())
    con = sum(1 for c in candidatos if 'considerar' in (c.recomendacion or '').lower())
    des = sum(1 for c in candidatos if 'descartar' in (c.recomendacion or '').lower())
    scores = [c.match_score for c in candidatos if c.match_score and c.match_score > 0]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    summary_data = [
        ['Total CVs', 'Entrevistar', 'Considerar', 'Descartar', 'Score Prom.'],
        [str(total), str(ent), str(con), str(des), f'{avg_score}%']
    ]
    summary_table = Table(summary_data, colWidths=[80, 80, 80, 80, 80])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f4f4f5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), GRAY),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 1), (-1, 1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
        # Colores de texto por recomendación
        ('TEXTCOLOR', (1, 1), (1, 1), GREEN),
        ('TEXTCOLOR', (2, 1), (2, 1), YELLOW),
        ('TEXTCOLOR', (3, 1), (3, 1), RED),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 8 * mm))

    # Ranking de candidatos
    elements.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))
    elements.append(Paragraph('Ranking de Candidatos', styles['SectionHead']))

    # Ordenar por score desc
    sorted_cands = sorted(candidatos, key=lambda x: x.match_score or 0, reverse=True)

    for idx, c in enumerate(sorted_cands):
        rec = (c.recomendacion or '').strip()
        rec_color = get_rec_color(rec)
        name = (c.filename or 'CV').replace('.pdf', '')
        score = c.match_score or 0

        # Nombre + score + recomendación en una línea
        elements.append(Paragraph(
            f'<b>#{idx + 1}</b>&nbsp;&nbsp;'
            f'<font size="12"><b>{name}</b></font>&nbsp;&nbsp;&nbsp;'
            f'<font size="10" color="{rec_color.hexval()}">[{rec}]</font>&nbsp;&nbsp;'
            f'<font size="10" color="#71717a">Score: {score:.1f}%</font>',
            styles['BodyText2']
        ))
        elements.append(Spacer(1, 2 * mm))

        # Fortalezas
        fortalezas = json.loads(c.fortalezas) if c.fortalezas else []
        if fortalezas:
            elements.append(Paragraph('<font color="#22c55e"><b>Fortalezas:</b></font> ' + ' · '.join(fortalezas), styles['BodyText2']))

        # Carencias
        carencias = json.loads(c.carencias) if c.carencias else []
        if carencias:
            elements.append(Paragraph('<font color="#ef4444"><b>Carencias:</b></font> ' + ' · '.join(carencias), styles['BodyText2']))

        # Valoración
        if c.valoracion:
            elements.append(Paragraph(f'<i>"{c.valoracion}"</i>', styles['BodyText2']))

        # Contacto
        contact_parts = []
        if c.email_candidato and c.email_candidato != 'null':
            contact_parts.append(f'Email: {c.email_candidato}')
        if c.telefono_candidato and c.telefono_candidato != 'null':
            contact_parts.append(f'Tel: {c.telefono_candidato}')
        if contact_parts:
            elements.append(Paragraph(' · '.join(contact_parts), styles['SmallLabel']))

        elements.append(Spacer(1, 3 * mm))
        if idx < len(sorted_cands) - 1:
            elements.append(HRFlowable(width='100%', thickness=0.3, color=HexColor('#e4e4e7'), spaceAfter=3 * mm))

    # Footer
    elements.append(Spacer(1, 10 * mm))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=3 * mm))
    elements.append(Paragraph('Generado por Malaquías Recruiting Suite · Reporte confidencial', styles['FooterStyle']))

    doc.build(elements)
    buffer.seek(0)
    return buffer
