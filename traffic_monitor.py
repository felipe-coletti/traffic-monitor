import argparse
from datetime import datetime, timedelta

import cv2
from ultralytics import YOLO
import json
import os

screen_title = "Traffic Monitor"

parser = argparse.ArgumentParser()
parser.add_argument("--video", default="video.mp4")
parser.add_argument("--start-datetime", required=True, help="Formato: YYYY-MM-DD HH:MM:SS (horário real do início da filmagem)")
parser.add_argument("--output-dir", default="output")
args = parser.parse_args()

video_start_datetime = datetime.strptime(args.start_datetime, "%Y-%m-%d %H:%M:%S")

model = YOLO('yolo11n.pt')

cap = cv2.VideoCapture(args.video)

assert cap.isOpened(), "Error: Cannot open video file"

fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
frame_count = 0

lines = [
    ('1', (125, 435), (1100, 445)),
    ('3', (845, 315), (340, 305)),
    ('2', (1100, 415), (950, 335)),
    ('4', (275, 300), (100, 425)),
]

track_history = {}
vehicle_trips = {}

counters = {name: {'in': 0, 'out': 0, 'crossed': set()} for name, _, _ in lines}

def get_crossing_direction(line_p1, line_p2, prev_pt, curr_pt):
    line_vec = (line_p2[0] - line_p1[0], line_p2[1] - line_p1[1])

    def get_side(p):
        return (line_vec[0] * (p[1] - line_p1[1])) - (line_vec[1] * (p[0] - line_p1[0]))

    side_prev = get_side(prev_pt)
    side_curr = get_side(curr_pt)

    if side_prev * side_curr < 0:
        if side_prev < 0 and side_curr > 0:
            return 'out'
        else:
            return 'in'
    return None

print("Iniciando monitoramento... Pressione 'q' para salvar e sair.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    current_datetime = video_start_datetime + timedelta(seconds=frame_count / fps)

    results = model.track(
        frame,
        persist=True,
        tracker='bytetrack.yaml',
        classes=[2, 3, 5, 7],
        conf=0.35,
        verbose=False
    )

    annotated_frame = results[0].plot()

    for name, p1, p2 in lines:
        cv2.line(annotated_frame, p1, p2, (0, 255, 255), 3)
        cv2.putText(annotated_frame, name, (p1[0], p1[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    boxes = results[0].boxes if len(results) > 0 else []

    if boxes.id is not None:
        for box in boxes:
            if box.id is None:
                continue

            track_id = int(box.id.item())

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            class_name = model.names[int(box.cls.item())]

            if track_id not in vehicle_trips:
                vehicle_trips[track_id] = {
                    'type': class_name,
                    'entry': None,
                    'entry_time': None,
                    'exit': None,
                    'exit_time': None,
                    'status': 'tracking'
                }

            if track_id not in track_history:
                track_history[track_id] = []

            track_history[track_id].append((cx, cy))

            if len(track_history[track_id]) > 30:
                track_history[track_id].pop(0)

            cv2.circle(annotated_frame, (cx, cy), 5, (0, 0, 255), -1)

            if len(track_history[track_id]) >= 2:
                prev_pt = track_history[track_id][-2]
                curr_pt = track_history[track_id][-1]

                for name, p1, p2 in lines:
                    if track_id in counters[name]['crossed']:
                        continue

                    direction = get_crossing_direction(p1, p2, prev_pt, curr_pt)

                    if direction:
                        counters[name][direction] += 1
                        counters[name]['crossed'].add(track_id)

                        trip = vehicle_trips[track_id]

                        if direction == 'in':
                            if trip['entry'] is None:
                                trip['entry'] = name
                                trip['entry_time'] = current_datetime.isoformat()
                                trip['status'] = 'inside_intersection'

                                print(f"[ENTRADA] Veículo {track_id} ({class_name}) entrou por {name} às {current_datetime}")

                        elif direction == 'out':
                            if trip['entry'] is not None and trip['exit'] is None:
                                if name != trip['entry']:
                                    trip['exit'] = name
                                    trip['exit_time'] = current_datetime.isoformat()
                                    trip['status'] = 'completed'

                                    print(f"[SAÍDA] Veículo {track_id} ({class_name}) saiu por {name} às {current_datetime}")
                                else:
                                    print(f"[IGNORE] Veículo {track_id} retornou pela mesma linha {name}")

    y_offset = 30

    for name, counts in counters.items():
        text = f"{name}: Entradas={counts['in']}, Saídas={counts['out']}"
        cv2.putText(annotated_frame, text, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        y_offset += 25

    cv2.imshow(screen_title, annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("\nFinalizando e salvando dados...")
        break

cap.release()
cv2.destroyAllWindows()

os.makedirs(args.output_dir, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"traffic_data_{timestamp}.json"
output_file = os.path.join(args.output_dir, filename)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(vehicle_trips, f, indent=4, ensure_ascii=False)

print(f"Dados salvos em: {output_file}")
print(f"Veículos rastreados nesta sessão: {len(vehicle_trips)}")

completed = sum(1 for v in vehicle_trips.values() if v['status'] == 'completed')

print(f"Trajetórias completas (Entrada + Saída): {completed}")