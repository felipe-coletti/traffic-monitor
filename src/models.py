from collections import defaultdict
from dataclasses import dataclass
from typing import Optional


@dataclass
class VehicleTrip:
    track_id: int
    vehicle_type: str
    entry_line: Optional[str] = None
    entry_time: Optional[str] = None
    exit_line: Optional[str] = None
    exit_time: Optional[str] = None
    status: str = "tracking"  # tracking | inside_intersection | completed
    trajectory: list = None

    def __post_init__(self):
        if self.trajectory is None:
            self.trajectory = []


@dataclass
class LineCounter:
    name: str
    p1: tuple
    p2: tuple
    in_count: int = 0
    out_count: int = 0
    by_type: dict = None

    def __post_init__(self):
        self.by_type = defaultdict(lambda: {"in": 0, "out": 0})


@dataclass
class SessionStats:
    total_tracked: int
    completed_trips: int
    in_progress: int
    total_entries: int
    total_exits: int
    per_line: dict = None
    per_vehicle_type: dict = None

    def __post_init__(self):
        if self.per_line is None:
            self.per_line = {}
        if self.per_vehicle_type is None:
            self.per_vehicle_type = {}