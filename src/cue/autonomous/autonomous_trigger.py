"""
Autonomous Trigger System for Atlas

This module implements the autonomous trigger system that enables Atlas to initiate
actions independently based on various trigger types:
- Time-based triggers
- Event-based triggers
- State-based triggers
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class TriggerEvent:
    """Represents a trigger event that can initiate autonomous actions"""
    def __init__(self, trigger_type: str, context: Dict[str, Any], priority: int = 1):
        self.trigger_type = trigger_type
        self.context = context
        self.priority = priority
        self.created_at = datetime.now()

    def __repr__(self):
        return f"TriggerEvent(type={self.trigger_type}, priority={self.priority})"

class TimeTrigger:
    """Manages time-based triggers"""
    def __init__(self, trigger_time: datetime, context: Dict[str, Any], repeat_interval: Optional[timedelta] = None):
        self.trigger_time = trigger_time
        self.context = context
        self.repeat_interval = repeat_interval
        self.last_triggered = None

    def is_due(self) -> bool:
        """Check if trigger is due to fire"""
        now = datetime.now()
        if self.last_triggered and self.repeat_interval:
            next_trigger = self.last_triggered + self.repeat_interval
            return now >= next_trigger
        return now >= self.trigger_time

    def mark_triggered(self):
        """Mark this trigger as having fired"""
        self.last_triggered = datetime.now()
        if self.repeat_interval:
            self.trigger_time = self.last_triggered + self.repeat_interval

class AutonomousTrigger:
    """Main trigger system that coordinates different trigger types"""
    def __init__(self):
        self.time_triggers: List[TimeTrigger] = []
        self.event_triggers: List[Dict[str, Any]] = []
        self.state_triggers: List[Dict[str, Any]] = []
        self._initialize_default_triggers()

    def _initialize_default_triggers(self):
        """Set up default system triggers"""
        # Daily system health check
        daily_health_check = TimeTrigger(
            trigger_time=datetime.now() + timedelta(minutes=5),  # First check in 5 minutes
            context={"action": "health_check", "scope": "system"},
            repeat_interval=timedelta(days=1)
        )
        self.add_time_trigger(daily_health_check)

        # Hourly memory optimization
        memory_optimization = TimeTrigger(
            trigger_time=datetime.now() + timedelta(minutes=30),  # First optimization in 30 minutes
            context={"action": "optimize", "target": "memory"},
            repeat_interval=timedelta(hours=1)
        )
        self.add_time_trigger(memory_optimization)

    def add_time_trigger(self, trigger: TimeTrigger):
        """Add a new time-based trigger"""
        self.time_triggers.append(trigger)

    def check_triggers(self) -> List[TriggerEvent]:
        """Check all trigger types and return applicable ones"""
        triggers = []
        triggers.extend(self._check_time_triggers())
        triggers.extend(self._check_event_triggers())
        triggers.extend(self._check_state_triggers())
        return triggers

    def _check_time_triggers(self) -> List[TriggerEvent]:
        """Check time-based triggers"""
        triggered = []
        for trigger in self.time_triggers:
            if trigger.is_due():
                event = TriggerEvent(
                    trigger_type="time",
                    context=trigger.context
                )
                triggered.append(event)
                trigger.mark_triggered()
        return triggered

    def _check_event_triggers(self) -> List[TriggerEvent]:
        """Check event-based triggers"""
        # To be implemented
        return []

    def _check_state_triggers(self) -> List[TriggerEvent]:
        """Check state-based triggers"""
        # To be implemented
        return []

    def get_trigger_status(self) -> Dict[str, Any]:
        """Get current status of all triggers"""
        return {
            "time_triggers": len(self.time_triggers),
            "event_triggers": len(self.event_triggers),
            "state_triggers": len(self.state_triggers),
            "next_time_trigger": min(
                (t.trigger_time for t in self.time_triggers),
                default=None
            )
        }