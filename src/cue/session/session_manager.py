"""
Session Management System

Handles conversation sessions and time awareness for the agent system.
Key features:
- Session tracking and management
- Time-based session boundaries
- Context continuity tracking
- Session metadata management
"""

import time
import json
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import uuid

@dataclass
class SessionMetadata:
    """Metadata for a conversation session"""
    session_id: str
    start_time: float
    last_active: float
    interaction_count: int
    context_continuity: float  # 0-1 score of context relevance
    primary_topic: Optional[str]
    topics: List[str]
    metrics: Dict[str, float]
    state: str  # 'active', 'idle', 'ended'

class SessionManager:
    """Manages conversation sessions and time awareness"""
    
    def __init__(self, 
                 session_timeout: int = 1800,  # 30 minutes
                 max_session_length: int = 14400,  # 4 hours
                 min_interaction_gap: int = 60):  # 1 minute
        self.session_timeout = session_timeout
        self.max_session_length = max_session_length
        self.min_interaction_gap = min_interaction_gap
        
        # Current session state
        self.current_session: Optional[SessionMetadata] = None
        self.previous_sessions: List[SessionMetadata] = []
        
        # Time tracking
        self.last_interaction_time: float = 0
        self.system_start_time: float = time.time()
        
        # Metrics
        self.metrics: Dict[str, float] = {
            'avg_session_length': 0.0,
            'avg_interactions_per_session': 0.0,
            'context_continuity_score': 1.0
        }
    
    def start_interaction(self, 
                         context: Dict[str, Any]) -> SessionMetadata:
        """Start or continue a session based on current context"""
        current_time = time.time()
        
        # Check if we need a new session
        if self._needs_new_session(current_time):
            # End current session if exists
            if self.current_session:
                self._end_session()
            
            # Create new session
            self.current_session = SessionMetadata(
                session_id=str(uuid.uuid4()),
                start_time=current_time,
                last_active=current_time,
                interaction_count=0,
                context_continuity=1.0,
                primary_topic=None,
                topics=[],
                metrics={
                    'response_time_avg': 0.0,
                    'context_switches': 0,
                    'topic_depth': 0.0
                },
                state='active'
            )
        
        # Update current session
        if self.current_session:
            self._update_session(current_time, context)
        
        self.last_interaction_time = current_time
        return self.current_session
    
    def end_interaction(self, 
                       context: Dict[str, Any],
                       metrics: Dict[str, float]) -> None:
        """End current interaction and update metrics"""
        if not self.current_session:
            return
        
        # Update session metrics
        self.current_session.metrics.update(metrics)
        self.current_session.last_active = time.time()
        self.current_session.interaction_count += 1
        
        # Update context continuity
        if 'context_relevance' in metrics:
            self._update_context_continuity(metrics['context_relevance'])
        
        # Check if session should end
        if self._should_end_session():
            self._end_session()
    
    def get_session_context(self) -> Dict[str, Any]:
        """Get current session context for agent use"""
        if not self.current_session:
            return {}
        
        return {
            'session_id': self.current_session.session_id,
            'session_age': time.time() - self.current_session.start_time,
            'interaction_count': self.current_session.interaction_count,
            'context_continuity': self.current_session.context_continuity,
            'current_topics': self.current_session.topics,
            'primary_topic': self.current_session.primary_topic,
            'session_metrics': self.current_session.metrics
        }
    
    def get_system_metrics(self) -> Dict[str, float]:
        """Get overall system metrics"""
        return {
            'uptime': time.time() - self.system_start_time,
            'total_sessions': len(self.previous_sessions) + 
                            (1 if self.current_session else 0),
            **self.metrics
        }
    
    def _needs_new_session(self, current_time: float) -> bool:
        """Determine if a new session should be started"""
        if not self.current_session:
            return True
        
        # Check timeout
        if (current_time - self.current_session.last_active 
            > self.session_timeout):
            return True
        
        # Check max session length
        if (current_time - self.current_session.start_time 
            > self.max_session_length):
            return True
        
        # Check minimum interaction gap
        if (current_time - self.last_interaction_time 
            < self.min_interaction_gap):
            return False
        
        return False
    
    def _update_session(self, 
                       current_time: float,
                       context: Dict[str, Any]) -> None:
        """Update current session with new interaction data"""
        if not self.current_session:
            return
        
        # Update basic metrics
        self.current_session.last_active = current_time
        
        # Update topics if provided
        if 'topic' in context:
            if context['topic'] not in self.current_session.topics:
                self.current_session.topics.append(context['topic'])
            
            # Update primary topic if confidence is high
            if context.get('topic_confidence', 0) > 0.8:
                self.current_session.primary_topic = context['topic']
    
    def _update_context_continuity(self, relevance_score: float) -> None:
        """Update context continuity score"""
        if not self.current_session:
            return
        
        # Weighted average with more weight to recent scores
        weight = 0.7  # 70% weight to new score
        old_score = self.current_session.context_continuity
        new_score = (weight * relevance_score + 
                    (1 - weight) * old_score)
        
        self.current_session.context_continuity = new_score
    
    def _should_end_session(self) -> bool:
        """Determine if current session should end"""
        if not self.current_session:
            return False
        
        current_time = time.time()
        
        # Check absolute timeouts
        if (current_time - self.current_session.start_time 
            > self.max_session_length):
            return True
        
        if (current_time - self.current_session.last_active 
            > self.session_timeout):
            return True
        
        # Check context continuity
        if (self.current_session.context_continuity < 0.3 and
            self.current_session.interaction_count > 5):
            return True
        
        return False
    
    def _end_session(self) -> None:
        """End current session and update metrics"""
        if not self.current_session:
            return
        
        # Update session state
        self.current_session.state = 'ended'
        
        # Store session history
        self.previous_sessions.append(self.current_session)
        
        # Update system metrics
        total_sessions = len(self.previous_sessions)
        self.metrics['avg_session_length'] = sum(
            s.last_active - s.start_time 
            for s in self.previous_sessions
        ) / total_sessions
        
        self.metrics['avg_interactions_per_session'] = sum(
            s.interaction_count 
            for s in self.previous_sessions
        ) / total_sessions
        
        self.metrics['context_continuity_score'] = sum(
            s.context_continuity 
            for s in self.previous_sessions
        ) / total_sessions
        
        # Clear current session
        self.current_session = None
    
    def save_state(self, path: str) -> None:
        """Save session manager state to file"""
        state = {
            'current_session': asdict(self.current_session) 
                             if self.current_session else None,
            'previous_sessions': [asdict(s) for s in self.previous_sessions],
            'last_interaction_time': self.last_interaction_time,
            'system_start_time': self.system_start_time,
            'metrics': self.metrics
        }
        
        with open(path, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self, path: str) -> None:
        """Load session manager state from file"""
        with open(path, 'r') as f:
            state = json.load(f)
        
        self.current_session = (
            SessionMetadata(**state['current_session'])
            if state['current_session'] else None
        )
        
        self.previous_sessions = [
            SessionMetadata(**s) for s in state['previous_sessions']
        ]
        
        self.last_interaction_time = state['last_interaction_time']
        self.system_start_time = state['system_start_time']
        self.metrics = state['metrics']