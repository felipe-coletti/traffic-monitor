#!/usr/bin/env python3

import os
import sys

from src.args import parse_args, parse_lines
from src.config import logger
from src.traffic_monitor import TrafficMonitor


def main():
    args = parse_args()

    # Validar vídeo
    if not os.path.isfile(args.video):
        logger.error(f"Arquivo de vídeo não encontrado: {args.video}")
        sys.exit(1)

    # Parsear linhas
    try:
        args.lines = parse_lines(args.lines)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    # Executar
    monitor = TrafficMonitor(args)
    monitor.run()


if __name__ == "__main__":
    main()