import os

from PIL import ImageFont

from src.config import FONT_PATHS, logger


def load_font(size: int) -> ImageFont:
    for path in FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    logger.warning("Nenhuma fonte TrueType encontrada. Acentos podem não aparecer.")
    return ImageFont.load_default()