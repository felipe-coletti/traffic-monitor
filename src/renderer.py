import cv2
import numpy as np
from PIL import Image, ImageDraw

from utils.font import load_font

class VideoRenderer:
    """Desenha overlays no frame (texto, trajetórias, linhas)."""

    def __init__(self, font_size: int = 20):
        self.font = load_font(font_size)
        self.trajectory_colors = {}
        self._color_counter = 0

    def _get_color(self, track_id: int) -> tuple:
        if track_id not in self.trajectory_colors:
            self._color_counter += 1
            # Gerar cores distintas por HSV
            color = cv2.cvtColor(
                np.uint8([[[[np.random.randint(50, 200), np.random.randint(50, 200), 255]]]]),
                cv2.COLOR_HSV2BGR,
            )[0][0]
            self.trajectory_colors[track_id] = tuple(int(c) for c in color)
        return self.trajectory_colors[track_id]

    @staticmethod
    def bgr_to_rgb(color_bgr: tuple) -> tuple:
        return (color_bgr[2], color_bgr[1], color_bgr[0])

    def draw_texts(self, frame_bgr: np.ndarray, texts: list) -> np.ndarray:
        """
        texts: list of (text: str, position: tuple, color_bgr: tuple)
        """
        image_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(image_rgb)
        draw = ImageDraw.Draw(pil_img)

        for text, pos, color_bgr in texts:
            color_rgb = self.bgr_to_rgb(color_bgr)
            draw.text(pos, text, font=self.font, fill=color_rgb)

        result_rgb = np.array(pil_img)
        return cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)

    def draw_trajectory(self, frame_bgr: np.ndarray, track_id: int,
                        history: list, max_points: int = 30) -> np.ndarray:
        """Desenha a trajetória do veículo no frame."""
        if len(history) < 2:
            return frame_bgr

        color = self._get_color(track_id)
        points = history[-max_points:]

        for i in range(1, len(points)):
            prev = points[i - 1]
            curr = points[i]
            alpha = i / len(points)  # fade-in
            thickness = max(1, int(2 * alpha))
            cv2.line(frame_bgr, prev, curr, color, thickness)

        # Ponto atual
        cv2.circle(frame_bgr, points[-1], 5, color, -1)
        return frame_bgr
