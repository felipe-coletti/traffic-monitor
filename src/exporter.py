from datetime import datetime
from pathlib import Path


class DataExporter:
    """Exporta dados para JSON e CSV."""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _filename(self, suffix: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"traffic_data_{timestamp}_{suffix}.json"

    def export_json(self, trips: dict[int, VehicleTrip],
                    stats: SessionStats, filepath: Optional[Path] = None):
        """Exporta relatório completo em JSON."""
        filepath = filepath or self._filename("report")

        data = {
            "session_info": {
                "exported_at": datetime.now().isoformat(),
                "total_tracked": stats.total_tracked,
                "completed_trips": stats.completed_trips,
                "in_progress": stats.in_progress,
                "total_entries": stats.total_entries,
                "total_exits": stats.total_exits,
            },
            "per_line": {
                name: {
                    "entries": counter.in_count,
                    "exits": counter.out_count,
                    "by_type": dict(counter.by_type),
                }
                for name, counter in globals().get('_counters', {}).items()
            },
            "per_vehicle_type": stats.per_vehicle_type,
            "vehicle_trips": {
                str(tid): asdict(trip) for tid, trip in trips.items()
            },
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        logger.info(f"Relatório JSON salvo: {filepath}")
        return filepath

    def export_csv(self, trips: dict[int, VehicleTrip], filepath: Optional[Path] = None):
        """Exporta trajetórias detalhadas em CSV."""
        filepath = filepath or self._filename("trips")

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "track_id", "vehicle_type", "entry_line", "entry_time",
                "exit_line", "exit_time", "status", "trajectory_points"
            ])

            for tid, trip in trips.items():
                writer.writerow([
                    tid,
                    trip.vehicle_type,
                    trip.entry_line or "",
                    trip.entry_time or "",
                    trip.exit_line or "",
                    trip.exit_time or "",
                    trip.status,
                    len(trip.trajectory) if trip.trajectory else 0,
                ])

        logger.info(f"CSV de trajetórias salvo: {filepath}")
        return filepath