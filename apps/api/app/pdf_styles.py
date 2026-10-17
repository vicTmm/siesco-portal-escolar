"""Embedded Unicode fonts shared by exported school documents."""

from pathlib import Path
from fastapi import HTTPException
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet

FONT = "SiescoSans"
BOLD = "SiescoSans-Bold"
DIRECTORY = Path(__file__).parent / "assets" / "fonts"
regular = TTFont(FONT, str(DIRECTORY / "DejaVuSans.ttf"))
bold = TTFont(BOLD, str(DIRECTORY / "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(regular)
pdfmetrics.registerFont(bold)
pdfmetrics.registerFontFamily(
    FONT, normal=FONT, bold=BOLD, italic=FONT, boldItalic=BOLD
)
SUPPORTED = set(regular.face.charToGlyph) & set(bold.face.charToGlyph) | {9, 10, 13}


def validate_text(*values):
    missing = {c for value in values for c in str(value) if ord(c) not in SUPPORTED}
    if missing:
        raise HTTPException(
            422,
            "O PDF não suporta estes caracteres: "
            + "".join(sorted(missing))[:30]
            + ". Revise o texto ou use uma figura para a notação da questão.",
        )


def styles():
    result = getSampleStyleSheet()
    for style in result.byName.values():
        style.fontName = (
            BOLD if style.name.startswith("Heading") or style.name == "Title" else FONT
        )
    return result
