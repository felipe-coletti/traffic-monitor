from datetime import datetime
from typing import Optional

from .models import LineCounter


class LineCounterEngine:
    """Detecta direção de cruzamento através de linhas."""

    def __init__(self):
        self.counters: dict[str, LineCounter] = {}
        self.crossed: dict[int, dict[str, datetime]] = {}
        self.cooldown_seconds = 5.0

    def add_line(self, name: str, p1: tuple, p2: tuple):
        self.counters[name] = LineCounter(
            name=name,
            p1=p1,
            p2=p2,
        )

    @staticmethod
    def _get_crossing_direction(
        line_p1,
        line_p2,
        prev_pt,
        curr_pt,
    ) -> Optional[str]:
        line_vec = (
            line_p2[0] - line_p1[0],
            line_p2[1] - line_p1[1],
        )

        def get_side(point):
            return (
                line_vec[0] * (point[1] - line_p1[1])
                - line_vec[1] * (point[0] - line_p1[0])
            )

        side_prev = get_side(prev_pt)
        side_curr = get_side(curr_pt)

        if side_prev * side_curr < 0:
            if side_prev < 0 and side_curr > 0:
                return "out"

            if side_prev > 0 and side_curr < 0:
                return "in"

        return None

    def check_crossing(
        self,
        track_id: int,
        vehicle_type: str,
        prev_pt: tuple,
        curr_pt: tuple,
        current_time: datetime,
    ) -> list:

        events = []

        for name, counter in self.counters.items():
            last_crossed = self.crossed.get(track_id, {}).get(name)

            if last_crossed:
                elapsed = (
                    current_time - last_crossed
                ).total_seconds()

                if elapsed < self.cooldown_seconds:
                    continue

            direction = self._get_crossing_direction(
                counter.p1,
                counter.p2,
                prev_pt,
                curr_pt,
            )

            if not direction:
                continue

            if direction == "in":
                counter.in_count += 1
                counter.by_type[vehicle_type]["in"] += 1
            else:
                counter.out_count += 1
                counter.by_type[vehicle_type]["out"] += 1

            if track_id not in self.crossed:
                self.crossed[track_id] = {}

            self.crossed[track_id][name] = current_time

            events.append(
                (name, direction, current_time)
            )

        return events