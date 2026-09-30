import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="Traffic Monitor — Detecção e contagem de veículos com YOLO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Contagem básica
  python traffic_monitor.py --video intersection.mp4 --start-datetime "2024-01-15 14:30:00"

  # Com vídeo de saída e modelo customizado
  python traffic_monitor.py \\
      --video intersection.mp4 \\
      --start-datetime "2024-01-15 14:30:00" \\
      --output-dir results \\
      --output-video \\
      --model best.pt \\
      --conf 0.4

  # Linhas customizadas
  python traffic_monitor.py \\
      --video intersection.mp4 \\
      --start-datetime "2024-01-15 14:30:00" \\
      --lines "1:125,435:1100,445" "3:845,315:340,305"
        """,
    )

    parser.add_argument("--video", required=True, help="Caminho do vídeo de entrada")
    parser.add_argument(
        "--start-datetime", required=True,
        help="Data/hora real do início da filmagem (YYYY-MM-DD HH:MM:SS)"
    )
    parser.add_argument("--output-dir", default="output", help="Diretório de saída")
    parser.add_argument("--output-video", action="store_true", help="Salvar vídeo anotado")
    parser.add_argument("--model", default="yolo11n.pt", help="Caminho do modelo YOLO (.pt)")
    parser.add_argument("--conf", type=float, default=0.35, help="Confiança mínima (0.0–1.0)")
    parser.add_argument(
        "--lines", nargs="+", default=[
            "1:125,435:1100,445",
            "3:845,315:340,305",
            "2:1100,415:950,335",
            "4:275,300:100,425",
        ],
        help="Linhas de detecção (formato: NAME:x1,y1:x2,y2)"
    )

    return parser.parse_args()


def parse_lines(lines_str: list) -> list:
    """Parseia strings de linhas no formato 'NAME:x1,y1:x2,y2'."""
    parsed = []
    for line_str in lines_str:
        parts = line_str.split(":")
        if len(parts) != 3:
            raise ValueError(f"Formato inválido para linha '{line_str}'. Use: NAME:x1,y1:x2,y2")

        name = parts[0].strip()
        p1_parts = parts[1].strip().split(",")
        p2_parts = parts[2].strip().split(",")

        if len(p1_parts) != 2 or len(p2_parts) != 2:
            raise ValueError(f"Coordenadas inválidas na linha '{name}'")

        p1 = (int(p1_parts[0]), int(p1_parts[1]))
        p2 = (int(p2_parts[0]), int(p2_parts[1]))
        parsed.append((name, p1, p2))

    return parsed