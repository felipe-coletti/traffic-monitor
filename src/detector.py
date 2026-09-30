import numpy as np
from ultralytics import YOLO

from config import logger


class VehicleDetector:
    """Carrega modelo YOLO e executa detecção + tracking."""

    VEHICLE_CLASSES = {2: "bicycle", 3: "motorcycle", 5: "bus", 7: "truck"}

    def __init__(self, model_path: str = "yolo11n.pt", conf: float = 0.35):
        self.model_path = model_path
        self.conf = conf
        logger.info(f"Carregando modelo YOLO: {model_path}")
        self.model = YOLO(model_path)
        logger.info("Modelo carregado com sucesso.")

    def detect_and_track(self, frame: np.ndarray) -> tuple:
        """
        Executa detecção e tracking.
        Retorna (annotated_frame, boxes_data)
        """
        results = self.model.track(
            frame,
            persist=True,
            tracker='bytetrack.yaml',
            classes=list(self.VEHICLE_CLASSES.keys()),
            conf=self.conf,
            verbose=False,
        )

        annotated_frame = results[0].plot() if len(results) > 0 else frame

        boxes_data = []
        if len(results) > 0 and results[0].boxes.id is not None:
            for box in results[0].boxes:
                if box.id is None:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                track_id = int(box.id.item())
                class_id = int(box.cls.item())
                class_name = self.model.names.get(class_id, f"class_{class_id}")
                confidence = float(box.conf.item())
                boxes_data.append({
                    "track_id": track_id,
                    "center": (cx, cy),
                    "bbox": (x1, y1, x2, y2),
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": confidence,
                })

        return annotated_frame, boxes_data
