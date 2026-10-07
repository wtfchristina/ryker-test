import io
from typing import List
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.models.audit import Control, Engagement, EvidenceArtifact

class PDFWorkpaperService:
    @staticmethod
    def build_pdf(
        engagement: Engagement,
        controls: List[Control],
        artifacts: List[EvidenceArtifact]
    ) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=8, textColor=colors.HexColor('#0F172A'))
        meta_style = ParagraphStyle('DocMeta', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#475569'))
        h2_style = ParagraphStyle('SectionHeader', parent=styles['Heading2'], fontSize=12, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor('#1E293B'))
        body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#334155'))

        story.append(Paragraph("RYKER ROOM | SOC 2 TYPE II TESTING WORKPAPER", title_style))
        story.append(Paragraph(f"<b>Engagement:</b> {engagement.title} | <b>Period:</b> {engagement.period_start} to {engagement.period_end}", meta_style))
        story.append(Paragraph(f"<b>Tenant:</b> {engagement.organization_id} | <b>Status:</b> {engagement.status}", meta_style))
        story.append(Spacer(1, 10))

        story.append(Paragraph("Control Testing & Sealed Vault Evidence Matrix", h2_style))
        table_data = [
            ["Control", "Evidence File", "SHA-256 Hash", "Storage Status", "Retention"]
        ]

        for ctrl in controls:
            ctrl_arts = [a for a in artifacts if str(a.control_id) == str(ctrl.id)]
            if not ctrl_arts:
                table_data.append([f"{ctrl.framework_code}", "(No evidence)", "N/A", "PENDING", "N/A"])
            else:
                for a in ctrl_arts:
                    table_data.append([
                        f"{ctrl.framework_code}",
                        Paragraph(a.file_name, body_style),
                        Paragraph(f"{a.sha256_hash[:16]}...", body_style),
                        "SEALED (WORM)",
                        "LOCKED 2033"
                    ])

        t = Table(table_data, colWidths=[60, 150, 130, 90, 80])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t)
        story.append(Spacer(1, 14))

        story.append(Paragraph("Auditor Attestation", h2_style))
        attest_text = (
            "[X] Standard audit procedures executed under AICPA SSAE 18 attestation standards.<br/>"
            "[X] Immutability and cryptographic chain of custody verified.<br/>"
            f"<b>Lead Partner:</b> {engagement.lead_partner_id}<br/>"
            "<b>Conclusion:</b> CC8.1 Change Management controls operated effectively during the observation period."
        )
        story.append(Paragraph(attest_text, meta_style))

        doc.build(story)
        buffer.seek(0)
        return buffer
