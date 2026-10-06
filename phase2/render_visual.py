"""Make a viewable PDF study from the editorial text in book-preview.tex.

This is a visual companion, not the output of a LaTeX compiler.
"""
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer


HERE = Path(__file__).parent
source = (HERE / "book-preview.tex").read_text(encoding="utf-8")
output = HERE / "book-preview-visual.pdf"
font_dir = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Georgia", str(font_dir / "georgia.ttf")))
pdfmetrics.registerFont(TTFont("Georgia-Bold", str(font_dir / "georgiab.ttf")))

body = ParagraphStyle("body", fontName="Georgia", fontSize=10.6, leading=15.0,
                      spaceAfter=8, alignment=TA_LEFT, allowWidows=0, allowOrphans=0)
head = ParagraphStyle("head", parent=body, fontName="Georgia-Bold", fontSize=12.3,
                      leading=16, spaceBefore=15, spaceAfter=5)
kicker = ParagraphStyle("kicker", parent=body, fontSize=8.5, leading=11, textColor=colors.HexColor("#666666"))
title = ParagraphStyle("title", parent=body, fontName="Georgia-Bold", fontSize=24, leading=28, spaceAfter=13)

def clean(text):
    text = re.sub(r"(?m)^%.*\n?", "", text).strip()
    text = text.replace("---", "—").replace("``", "“").replace("''", "”")
    text = text.replace("`baraka'", "‘baraka’")
    return html.escape(text)

story = [Spacer(1, 28), Paragraph("A SELECTION OF SHORT PIECES", kicker),
         Spacer(1, 15), Paragraph("A Handful of Days", title),
         Paragraph("________________", kicker), Spacer(1, 13)]
pieces = re.split(r"(?m)^\\piecehead\{([^}]+)\}\s*\n", source)[1:]
for name, raw in zip(pieces[::2], pieces[1::2]):
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", re.sub(r"(?m)^%.*$", "", raw)) if p.strip()]
    paragraphs = [p for p in paragraphs if not p.startswith("\\end{document}")]
    first = Paragraph(clean(paragraphs[0]), body)
    story.append(KeepTogether([Paragraph(html.escape(name), head), first]))
    story.extend(Paragraph(clean(p), body) for p in paragraphs[1:])

def furniture(canvas, doc):
    canvas.saveState()
    page = doc.page
    canvas.setFont("Georgia", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    if page % 2:
        canvas.drawRightString(5.5 * 72 - 0.68 * 72, 8.5 * 72 - 44, "A HANDFUL OF DAYS")
        canvas.drawRightString(5.5 * 72 - 0.68 * 72, 38, str(page))
    else:
        canvas.drawString(0.82 * 72, 8.5 * 72 - 44, "MUHIB")
        canvas.drawString(0.82 * 72, 38, str(page))
    canvas.restoreState()

doc = SimpleDocTemplate(str(output), pagesize=(5.5 * 72, 8.5 * 72),
                        leftMargin=0.82 * 72, rightMargin=0.68 * 72,
                        topMargin=0.92 * 72, bottomMargin=0.78 * 72)
doc.build(story, onFirstPage=furniture, onLaterPages=furniture)
print(output)
