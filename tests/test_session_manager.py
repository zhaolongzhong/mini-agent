"""Tests for the SessionManager class"""

import time
import pytest
from datetime import datetime, timedelta
from cue.session.session_manager import SessionManager, SessionMetadata

@pytest.fixture
def session_manager():
    """Create a session manager with test configuration"""
    return SessionManager(
        session_timeout=300,  # 5 minutes
        max_session_length=600,  # 10 minutes
        min_interaction_gap=1  # 1 second
    )

def test_session_creation(session_manager):
    """Test basic session creation"""
    context = {'topic': 'test'}
    session = session_manager.start_interaction(context)
    
    assert session is not None
    assert session.session_id is not None
    assert session.state == 'active'
    assert session.interaction_count == 0
    assert session.context_continuity == 1.0
    assert abs(time.time() - session.start_time) < 1

def test_session_continuation(session_manager):
    """Test session continues within timeout"""
    context = {'topic': 'test'}
    
    # Start session
    session1 = session_manager.start_interaction(context)
    session_id = session1.session_id
    
    # Small delay
    time.sleep(1)
    
    # Continue session
    session2 = session_manager.start_interaction(context)
    
    assert session2.session_id == session_id
    assert session2.state == 'active'

def test_session_timeout(session_manager):
    """Test session times out after inactivity"""
    session_manager.session_timeout = 2  # Set timeout to 2 seconds
    context = {'topic': 'test'}
    
    # Start session
    session1 = session_manager.start_interaction(context)
    session1_id = session1.session_id
    
    # Wait for timeout
    time.sleep(3)
    
    # Start new interaction
    session2 = session_manager.start_interaction(context)
    
    assert session2.session_id != session1_id
    assert session2.state == 'active'

def test_context_continuity(session_manager):
    """Test context continuity score updates"""
    context = {'topic': 'test'}
    
    # Start session
    session = session_manager.start_interaction(context)
    
    # Update with high relevance
    session_manager.end_interaction(
        context,
        {'context_relevance': 0.9}
    )
    
    assert session_manager.current_session.context_continuity > 0.9
    
    # Update with low relevance
    session_manager.end_interaction(
        context,
        {'context_relevance': 0.3}
    )
    
    assert session_manager.current_session.context_continuity < 0.9

def test_session_metrics(session_manager):
    """Test session metrics tracking"""
    context = {'topic': 'test'}
    
    # Start session
    session = session_manager.start_interaction(context)
    
    # Add some interactions
    for _ in range(3):
        time.sleep(1)
        session_manager.end_interaction(
            context,
            {
                'response_time_avg': 0.5,
                'context_relevance': 0.9
            }
        )
        session_manager.start_interaction(context)
    
    metrics = session_manager.get_system_metrics()
    
    assert metrics['uptime'] > 0
    assert metrics['total_sessions'] >= 1
    assert metrics['context_continuity_score'] > 0

def test_topic_tracking(session_manager):
    """Test topic tracking in sessions"""
    # Start with one topic
    session = session_manager.start_interaction({
        'topic': 'topic1',
        'topic_confidence': 0.9
    })
    
    assert 'topic1' in session.topics
    assert session.primary_topic == 'topic1'
    
    # Add another topic
    session_manager.start_interaction({
        'topic': 'topic2',
        'topic_confidence': 0.7
    })
    
    assert 'topic2' in session.topics
    assert session.primary_topic == 'topic1'  # Still primary due to confidence

def test_state_persistence(session_manager, tmp_path):
    """Test saving and loading session state"""
    state_file = tmp_path / "session_state.json"
    
    # Create some session data
    context = {'topic': 'test'}
    session = session_manager.start_interaction(context)
    session_manager.end_interaction(
        context,
        {'context_relevance': 0.9}
    )
    
    # Save state
    session_manager.save_state(str(state_file))
    
    # Create new manager and load state
    new_manager = SessionManager()
    new_manager.load_state(str(state_file))
    
    # Verify state
    assert new_manager.metrics == session_manager.metrics
    assert new_manager.system_start_time == session_manager.system_start_time
    
    if session_manager.current_session:
        assert new_manager.current_session.session_id == \
               session_manager.current_session.session_id