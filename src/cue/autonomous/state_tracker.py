"""
State Tracking System for Autonomous Operations

This module implements the state tracking capabilities needed for autonomous
operations, including:
- Current system state tracking
- Action history management
- Performance metrics collection
- Safety state monitoring
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ActionResult:
    """Represents the result of an autonomous action"""
    action_id: str
    action_type: str
    status: str
    result: Dict[str, Any]
    timestamp: float
    metrics: Dict[str, float]

class StateTracker:
    """Tracks and manages system state for autonomous operations"""
    
    def __init__(self):
        self.current_state: Dict[str, Any] = {
            'system_health': 1.0,
            'memory_usage': 0.0,
            'action_success_rate': 1.0,
            'last_human_interaction': time.time(),
            'active_tasks': [],
            'resource_usage': {},
            'safety_status': 'normal'
        }
        
        self.action_history: List[ActionResult] = []
        self.metrics: Dict[str, float] = {
            'avg_response_time': 0.0,
            'success_rate': 1.0,
            'error_rate': 0.0,
            'safety_violations': 0
        }
        
        # Safety thresholds
        self.thresholds = {
            'max_actions_per_minute': 10,
            'min_success_rate': 0.8,
            'max_memory_usage': 0.9,
            'max_autonomous_time': 3600  # 1 hour
        }
    
    def update(self, action_result: ActionResult) -> None:
        """Update system state based on action results"""
        # Update action history
        self.action_history.append(action_result)
        if len(self.action_history) > 1000:  # Keep last 1000 actions
            self.action_history = self.action_history[-1000:]
        
        # Update metrics
        self._update_metrics(action_result)
        
        # Update system health
        self._update_system_health()
    
    def can_continue(self) -> bool:
        """Determine if autonomous actions should continue"""
        # Check all safety thresholds
        checks = [
            self._check_action_rate(),
            self._check_success_rate(),
            self._check_resource_usage(),
            self._check_autonomous_time()
        ]
        
        return all(checks)
    
    def get_metrics(self) -> Dict[str, float]:
        """Get current performance metrics"""
        return self.metrics.copy()
    
    def get_state(self) -> Dict[str, Any]:
        """Get current system state"""
        return self.current_state.copy()
    
    def _update_metrics(self, action_result: ActionResult) -> None:
        """Update system metrics based on action result"""
        # Update success rate
        total_actions = len(self.action_history)
        successful_actions = sum(
            1 for a in self.action_history 
            if a.status == 'success'
        )
        self.metrics['success_rate'] = successful_actions / total_actions
        
        # Update error rate
        self.metrics['error_rate'] = 1 - self.metrics['success_rate']
        
        # Update average response time
        self.metrics['avg_response_time'] = sum(
            a.metrics.get('response_time', 0) 
            for a in self.action_history
        ) / total_actions
    
    def _update_system_health(self) -> None:
        """Update overall system health score"""
        # Weighted average of key metrics
        weights = {
            'success_rate': 0.4,
            'error_rate': 0.3,
            'resource_usage': 0.3
        }
        
        health_score = (
            weights['success_rate'] * self.metrics['success_rate'] +
            weights['error_rate'] * (1 - self.metrics['error_rate']) +
            weights['resource_usage'] * 
            (1 - max(self.current_state['resource_usage'].values(), default=0))
        )
        
        self.current_state['system_health'] = health_score
    
    def _check_action_rate(self) -> bool:
        """Check if action rate is within safe limits"""
        recent_actions = [
            a for a in self.action_history
            if time.time() - a.timestamp < 60  # Last minute
        ]
        return len(recent_actions) < self.thresholds['max_actions_per_minute']
    
    def _check_success_rate(self) -> bool:
        """Check if success rate is acceptable"""
        return self.metrics['success_rate'] >= self.thresholds['min_success_rate']
    
    def _check_resource_usage(self) -> bool:
        """Check if resource usage is within limits"""
        return all(
            usage < self.thresholds['max_memory_usage']
            for usage in self.current_state['resource_usage'].values()
        )
    
    def _check_autonomous_time(self) -> bool:
        """Check if we've been autonomous for too long"""
        autonomous_time = time.time() - self.current_state['last_human_interaction']
        return autonomous_time < self.thresholds['max_autonomous_time']