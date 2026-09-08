import sys
import csv
import json
from pathlib import Path
from datetime import datetime

VEHICLE_TYPE_LABELS = {
    "car": "Carro",
    "motorcycle": "Moto",
    "truck": "Caminhão",
    "bus": "Ônibus",
}
VEHICLE_COLUMNS = ["Carro", "Moto", "Caminhão", "Ônibus"]


def load_json(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def hour_bucket(iso_datetime: str):
    dt = datetime.fromisoformat(iso_datetime)
    return dt.replace(minute=0, second=0, microsecond=0)


def build_matrix(input_dir: Path):
    matrix = {}
    trips_ignored = 0

    for file in sorted(input_dir.glob("*.json")):
        content = load_json(file)
        for track_id, trip in content.items():
            if trip.get("status") != "completed" or not trip.get("entry_time"):
                trips_ignored += 1
                continue

            vehicle_label = VEHICLE_TYPE_LABELS.get(trip.get("type"))
            if vehicle_label is None:
                trips_ignored += 1
                continue

            hour = hour_bucket(trip["entry_time"])
            key = (hour, trip["entry"], trip["exit"])

            if key not in matrix:
                matrix[key] = {col: 0 for col in VEHICLE_COLUMNS}
            matrix[key][vehicle_label] += 1

    return matrix, trips_ignored


def generate_report(input_path: str, output_path: str):
    input_dir = Path(input_path)
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Erro: pasta de entrada não encontrada: {input_dir}")
        sys.exit(1)

    json_files = sorted(input_dir.glob("*.json"))
    if not json_files:
        print(f"Nenhum arquivo .json encontrado em: {input_dir}")
        sys.exit(1)

    print(f"Encontrados {len(json_files)} arquivo(s) JSON. Processando...")

    matrix, trips_ignored = build_matrix(input_dir)

    if trips_ignored:
        print(f"Aviso: {trips_ignored} veículo(s) ignorado(s) (trajeto incompleto, sem horário ou tipo não reconhecido).")

    if not matrix:
        print("Nenhum trajeto completo com horário foi encontrado nos arquivos JSON.")
        sys.exit(1)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header = ["Hora", "Entrada", "Saída"] + VEHICLE_COLUMNS + ["Total"]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(header)

        for hour, entry, exit_ in sorted(matrix.keys()):
            counts = matrix[(hour, entry, exit_)]
            total = sum(counts.values())
            row = [hour.strftime("%d/%m/%Y %H:00"), entry, exit_] + [counts[col] for col in VEHICLE_COLUMNS] + [total]
            writer.writerow(row)

    print(f"\nRelatório gerado com sucesso: {output_path}")
    print(f"Total de combinações hora/movimento: {len(matrix)}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python generate_movement_report.py <input_path> <output_path.csv>")
        sys.exit(1)

    generate_report(sys.argv[1], sys.argv[2])