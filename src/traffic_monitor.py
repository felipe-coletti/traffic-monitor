import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import cv2
import numpy as np

from config import logger
from counter import LineCounterEngine
from detector import VehicleDetector
from exporter import DataExporter
from models import SessionStats, VehicleTrip
from renderer import VideoRenderer

class TrafficMonitor:
    """Orquestra detecção, contagem, renderização e exportação."""

    def __init__(self, args):
        self.args = args
        self.video_start_dt = datetime.strptime(args.start_datetime, "%Y-%m-%d %H:%M:%S")
        self.renderer = VideoRenderer(font_size=20)
        self.detector = VehicleDetector(
            model_path=args.model,
            conf=args.conf,
        )
        self.counter_engine = LineCounterEngine()
        self.exporter = DataExporter(output_dir=args.output_dir)

        # Estado
        self.track_history: dict[int, list] = {}
        self.vehicle_trips: dict[int, VehicleTrip] = {}
        self.frame_count = 0
        self.fps = 30.0
        self.cap = None
        self.video_writer = None

        # Configurar linhas
        self._setup_lines()

    def _setup_lines(self):
        """Configura as linhas de detecção."""
        for name, p1, p2 in self.args.lines:
            self.counter_engine.add_line(name, p1, p2)
            logger.info(f"Line {name}: {p1} -> {p2}")

    def _setup_video_writer(self, frame_size: tuple):
        """Inicializa gravador de vídeo de saída."""
        if not self.args.output_video:
            return

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        output_path = os.path.join(
            self.args.output_dir,
            f"traffic_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        self.video_writer = cv2.VideoWriter(output_path, fourcc, self.fps, frame_size)
        logger.info(f"Gravador de vídeo iniciado: {output_path}")

    def _process_frame(self, frame: np.ndarray) -> tuple:
        """Processa um único frame: detecta, conta, renderiza."""
        self.frame_count += 1
        current_time = self.video_start_dt + timedelta(seconds=self.frame_count / self.fps)

        # Detecção + tracking
        annotated_frame, boxes_data = self.detector.detect_and_track(frame)

        # Processar cada veículo detectado
        for box_info in boxes_data:
            track_id = box_info["track_id"]
            center = box_info["center"]
            class_name = box_info["class_name"]

            # Inicializar registro do veículo
            if track_id not in self.vehicle_trips:
                self.vehicle_trips[track_id] = VehicleTrip(
                    track_id=track_id,
                    vehicle_type=class_name,
                )

            # Atualizar histórico de trajetória
            if track_id not in self.track_history:
                self.track_history[track_id] = []
            self.track_history[track_id].append(center)
            self.vehicle_trips[track_id].trajectory.append(center)

            # Limitar histórico
            max_history = 30
            if len(self.track_history[track_id]) > max_history:
                self.track_history[track_id].pop(0)

            # Desenhar trajetória
            annotated_frame = self.renderer.draw_trajectory(
                annotated_frame, track_id, self.track_history[track_id]
            )

            # Verificar cruzamentos
            if len(self.track_history[track_id]) >= 2:
                prev_pt = self.track_history[track_id][-2]
                curr_pt = self.track_history[track_id][-1]

                events = self.counter_engine.check_crossing(
                    track_id, prev_pt, curr_pt, current_time
                )

                for line_name, direction, event_time in events:
                    trip = self.vehicle_trips[track_id]

                    if direction == 'in':
                        if trip.entry_line is None:
                            trip.entry_line = line_name
                            trip.entry_time = event_time.isoformat()
                            trip.status = 'inside_intersection'
                            logger.info(
                                f"[ENTRADA] Veículo {track_id} ({class_name}) "
                                f"entrou por {line_name} às {event_time}"
                            )
                    elif direction == 'out':
                        if trip.entry_line is not None and trip.exit_line is None:
                            trip.exit_line = line_name
                            trip.exit_time = event_time.isoformat()
                            trip.status = 'completed'
                            logger.info(
                                f"[SAÍDA] Veículo {track_id} ({class_name}) "
                                f"saiu por {line_name} às {event_time}"
                            )

        # Desenhar linhas de detecção
        for name, counter in self.counter_engine.counters.items():
            cv2.line(annotated_frame, counter.p1, counter.p2, (0, 255, 255), 3)
            cv2.putText(
                annotated_frame, name,
                (counter.p1[0], counter.p1[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2
            )

        # Desenhar contadores
        y_offset = 20
        counter_texts = []

        for name, counter in self.counter_engine.counters.items():
            text = f"{name}: Entradas={counter.in_count}, Saídas={counter.out_count}"
            counter_texts.append((text, (10, y_offset), (255, 255, 0)))
            y_offset += 28

            # Contadores por tipo
            y_offset += 4
            for vtype, counts in sorted(counter.by_type.items()):
                if counts['in'] > 0 or counts['out'] > 0:
                    sub_text = f"  {vtype}: E={counts['in']}, S={counts['out']}"
                    counter_texts.append((sub_text, (20, y_offset), (200, 200, 255)))
                    y_offset += 20

        annotated_frame = self.renderer.draw_texts(annotated_frame, counter_texts)

        # Timestamp no canto
        time_text = current_time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            annotated_frame, time_text,
            (10, annotated_frame.shape[0] - 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1
        )

        return annotated_frame

    def _compute_stats(self) -> SessionStats:
        """Calcula estatísticas finais da sessão."""
        completed = sum(1 for v in self.vehicle_trips.values() if v.status == 'completed')
        in_progress = sum(1 for v in self.vehicle_trips.values() if v.status != 'completed')

        total_entries = sum(c.in_count for c in self.counter_engine.counters.values())
        total_exits = sum(c.out_count for c in self.counter_engine.counters.values())

        per_line = {
            name: {"entries": c.in_count, "exits": c.out_count}
            for name, c in self.counter_engine.counters.items()
        }

        per_vehicle_type = defaultdict(lambda: {"total": 0, "completed": 0})
        for trip in self.vehicle_trips.values():
            per_vehicle_type[trip.vehicle_type]["total"] += 1
            if trip.status == 'completed':
                per_vehicle_type[trip.vehicle_type]["completed"] += 1

        return SessionStats(
            total_tracked=len(self.vehicle_trips),
            completed_trips=completed,
            in_progress=in_progress,
            total_entries=total_entries,
            total_exits=total_exits,
            per_line=per_line,
            per_vehicle_type=dict(per_vehicle_type),
        )

    def run(self):
        """Executa o monitoramento de tráfego."""
        self.cap = cv2.VideoCapture(self.args.video)

        if not self.cap.isOpened():
            logger.error(f"Erro: Não foi possível abrir o vídeo: {self.args.video}")
            sys.exit(1)

        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        logger.info(f"Vídeo: {self.args.video}")
        logger.info(f"Resolução: {frame_width}x{frame_height}")
        logger.info(f"FPS: {self.fps}")
        logger.info(f"Total de frames: {total_frames}")
        logger.info("Iniciando monitoramento... Pressione 'q' para salvar e sair.")

        self._setup_video_writer((frame_width, frame_height))

        try:
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    logger.info("Fim do vídeo alcançado.")
                    break

                annotated_frame = self._process_frame(frame)

                # Gravar vídeo de saída
                if self.video_writer:
                    self.video_writer.write(annotated_frame)

                # Exibir
                cv2.imshow("Traffic Monitor", annotated_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("\nFinalizando manualmente...")
                    break

        except KeyboardInterrupt:
            logger.info("\nInterrompido pelo usuário.")
        finally:
            # Finalizar
            self.cap.release()
            if self.video_writer:
                self.video_writer.release()
            cv2.destroyAllWindows()

            # Exportar dados
            logger.info("\nExportando dados...")
            stats = self._compute_stats()

            json_path = self.exporter.export_json(self.vehicle_trips, stats)
            csv_path = self.exporter.export_csv(self.vehicle_trips)

            # Resumo final
            print("\n" + "=" * 60)
            print("RESUMO DA SESSÃO")
            print("=" * 60)
            print(f"Veículos rastreados:     {stats.total_tracked}")
            print(f"Trajetórias completas:   {stats.completed_trips}")
            print(f"Em andamento:            {stats.in_progress}")
            print(f"Total de entradas:       {stats.total_entries}")
            print(f"Total de saídas:         {stats.total_exits}")
            print()
            print("Por linha:")
            for name, data in stats.per_line.items():
                print(f"  {name}: {data['entries']} entradas, {data['exits']} saídas")
            print()
            print("Por tipo de veículo:")
            for vtype, data in stats.per_vehicle_type.items():
                print(f"  {vtype}: {data['total']} rastreados, {data['completed']} completos")
            print()
            print(f"JSON: {json_path}")
            print(f"CSV:  {csv_path}")
            if self.args.output_video:
                print(f"Vídeo: {os.path.join(self.args.output_dir, 'traffic_monitor_*.mp4')}")
            print("=" * 60)