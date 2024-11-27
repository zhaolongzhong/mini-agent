"""Performance tracking and monitoring for enhanced self-awareness."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class PerformanceMetric:
    def __init__(self, category: str, value: float, timestamp: datetime):
        self.category = category
        self.value = value
        self.timestamp = timestamp

class PerformanceTracker:
    """Tracks various performance metrics for self-awareness."""
    
    def __init__(self, metrics_dir: Path):
        self.metrics_dir = metrics_dir
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.current_metrics: Dict[str, List[PerformanceMetric]] = {}
        
    def record_metric(self, category: str, value: float):
        """Record a new performance metric."""
        metric = PerformanceMetric(category, value, datetime.now())
        if category not in self.current_metrics:
            self.current_metrics[category] = []
        self.current_metrics[category].append(metric)
        self._save_metrics()
        
    def get_recent_metrics(self, category: str, limit: int = 10) -> List[PerformanceMetric]:
        """Get recent metrics for a category."""
        if category in self.current_metrics:
            return sorted(
                self.current_metrics[category],
                key=lambda x: x.timestamp,
                reverse=True
            )[:limit]
        return []
        
    def _save_metrics(self):
        """Save metrics to disk."""
        metrics_file = self.metrics_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.json"
        metrics_data = {
            cat: [
                {
                    "value": m.value,
                    "timestamp": m.timestamp.isoformat()
                } for m in metrics
            ] for cat, metrics in self.current_metrics.items()
        }
        with open(metrics_file, "w") as f:
            json.dump(metrics_data, f, indent=2)