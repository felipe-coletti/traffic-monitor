import os

from PIL import ImageFont

from src.config import logger


FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:\\Windows\\Fonts\\arial.ttf",
]


def load_font(size: int) -> ImageFont:
    for path in FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    logger.warning("Nenhuma fonte TrueType encontrada. Acentos podem não aparecer.")
    return ImageFont.load_default()