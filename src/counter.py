from datetime import datetime
from typing import Optional

from models import LineCounter


class LineCounterEngine:
    """Detecta direção de cruzamento através de linhas."""

    def __init__(self):
        self.counters: dict[str, LineCounter] = {}
        self.crossed: dict[int, dict[str, float]] = {}  # track_id -> {line_name: timestamp}
        self.cooldown_seconds = 5.0  # Tempo mínimo entre recontagens

    def add_line(self, name: str, p1: tuple, p2: tuple):
        self.counters[name] = LineCounter(name=name, p1=p1, p2=p2)

    @staticmethod
    def _get_crossing_direction(line_p1, line_p2, prev_pt, curr_pt) -> Optional[str]:
        """
        Calcula se o ponto cruzou a linha para 'in' ou 'out'.
        Usa o produto vetorial para determinar o lado da linha.
        """
        line_vec = (line_p2[0] - line_p1[0], line_p2[1] - line_p1[1])

        def get_side(p):
            return (line_vec[0] * (p[1] - line_p1[1])) - (line_vec[1] * (p[0] - line_p1[0]))

        side_prev = get_side(prev_pt)
        side_curr = get_side(curr_pt)

        if side_prev * side_curr < 0:
            if side_prev < 0 and side_curr > 0:
                return 'out'
            elif side_prev > 0 and side_curr < 0:
                return 'in'
        return None

    def check_crossing(self, track_id: int, prev_pt: tuple, curr_pt: tuple,
                       current_time: datetime) -> list:
        """
        Verifica cruzamentos em todas as linhas.
        Retorna lista de eventos: (line_name, direction, current_time)
        """
        events = []

        for name, counter in self.counters.items():
            # Verificar cooldown para recontagem
            if track_id in self.crossed:
                last_crossed = self.crossed[track_id].get(name)
                if last_crossed:
                    elapsed = (current_time - last_crossed).total_seconds()
                    if elapsed < self.cooldown_seconds:
                        continue

            for other_track_id, crossed_lines in list(self.crossed.items()):
                if track_id in crossed_lines:
                    last_time = crossed_lines[track_id]
                    if isinstance(last_time, datetime):
                        elapsed = (current_time - last_time).total_seconds()
                        if elapsed < self.cooldown_seconds:
                            continue

            direction = self._get_crossing_direction(counter.p1, counter.p2, prev_pt, curr_pt)

            if direction:
                counter.in_count += (direction == 'in')
                counter.out_count += (direction == 'out')
                counter.by_type  # lazy init

                if track_id not in self.crossed:
                    self.crossed[track_id] = {}
                self.crossed[track_id][name] = current_time

                events.append((name, direction, current_time))

        return events
