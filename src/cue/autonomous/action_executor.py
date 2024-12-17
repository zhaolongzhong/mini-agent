"""
Safe Action Executor for Autonomous Operations

This module implements safe execution of autonomous actions with:
- Pre-execution safety checks
- Post-execution validation
- Action history tracking
- Error handling and recovery
"""

import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from .state_tracker import StateTracker, ActionResult

@dataclass
class SafetyCheck:
    """Represents a safety check to be performed"""
    name: str
    check_fn: Callable[[Dict[str, Any]], bool]
    severity: str  # 'critical' or 'warning'
    description: str

@dataclass
class ActionContext:
    """Context for action execution"""
    action_type: str
    parameters: Dict[str, Any]
    safety_level: str
    timeout: float
    retries: int

class SafeActionExecutor:
    """Safely executes autonomous actions with comprehensive safety checks"""
    
    def __init__(self, state_tracker: StateTracker):
        self.state_tracker = state_tracker
        self.action_history: List[ActionResult] = []
        
        # Initialize safety checks
        self.safety_checks: List[SafetyCheck] = [
            SafetyCheck(
                name='system_health',
                check_fn=self._check_system_health,
                severity='critical',
                description='Ensures system health is above minimum threshold'
            ),
            SafetyCheck(
                name='resource_usage',
                check_fn=self._check_resource_usage,
                severity='critical',
                description='Verifies resource usage is within safe limits'
            ),
            SafetyCheck(
                name='action_rate',
                check_fn=self._check_action_rate,
                severity='warning',
                description='Checks if action rate is within acceptable range'
            )
        ]
    
    async def execute(self, 
                     action_context: ActionContext) -> ActionResult:
        """Safely execute an autonomous action"""
        start_time = time.time()
        
        try:
            # Run pre-execution checks
            if not self._run_safety_checks(action_context):
                return ActionResult(
                    action_id=self._generate_action_id(),
                    action_type=action_context.action_type,
                    status='failed',
                    result={'error': 'safety_check_failed'},
                    timestamp=start_time,
                    metrics={'response_time': time.time() - start_time}
                )
            
            # Execute action with timeout and retries
            result = await self._execute_with_retries(action_context)
            
            # Validate result
            if not self._validate_result(result, action_context):
                return ActionResult(
                    action_id=self._generate_action_id(),
                    action_type=action_context.action_type,
                    status='failed',
                    result={'error': 'validation_failed'},
                    timestamp=start_time,
                    metrics={'response_time': time.time() - start_time}
                )
            
            # Create success result
            action_result = ActionResult(
                action_id=self._generate_action_id(),
                action_type=action_context.action_type,
                status='success',
                result=result,
                timestamp=start_time,
                metrics={
                    'response_time': time.time() - start_time,
                    'retries': 0
                }
            )
            
            # Update history and state
            self.action_history.append(action_result)
            self.state_tracker.update(action_result)
            
            return action_result
            
        except Exception as e:
            # Handle execution error
            error_result = ActionResult(
                action_id=self._generate_action_id(),
                action_type=action_context.action_type,
                status='error',
                result={'error': str(e)},
                timestamp=start_time,
                metrics={'response_time': time.time() - start_time}
            )
            
            self.state_tracker.update(error_result)
            return error_result
    
    def _run_safety_checks(self, 
                          action_context: ActionContext) -> bool:
        """Run all safety checks before execution"""
        context_dict = {
            'action_type': action_context.action_type,
            'parameters': action_context.parameters,
            'safety_level': action_context.safety_level,
            'system_state': self.state_tracker.get_state(),
            'metrics': self.state_tracker.get_metrics()
        }
        
        # Run all critical checks first
        critical_checks = [
            check for check in self.safety_checks 
            if check.severity == 'critical'
        ]
        
        if not all(
            check.check_fn(context_dict) 
            for check in critical_checks
        ):
            return False
        
        # Run warning checks
        warning_checks = [
            check for check in self.safety_checks 
            if check.severity == 'warning'
        ]
        
        # Warning checks don't fail execution but are logged
        for check in warning_checks:
            if not check.check_fn(context_dict):
                print(f"Warning: {check.name} - {check.description}")
        
        return True
    
    async def _execute_with_retries(self,
                                  action_context: ActionContext) -> Dict[str, Any]:
        """Execute action with timeout and retry logic"""
        retries = action_context.retries
        last_error = None
        
        while retries >= 0:
            try:
                # Execute with timeout
                return await asyncio.wait_for(
                    self._execute_action(action_context),
                    timeout=action_context.timeout
                )
            except asyncio.TimeoutError:
                last_error = "Action timeout"
            except Exception as e:
                last_error = str(e)
            
            retries -= 1
            if retries >= 0:
                # Wait before retry using exponential backoff
                await asyncio.sleep(2 ** (action_context.retries - retries))
        
        raise Exception(f"Action failed after retries: {last_error}")
    
    async def _execute_action(self,
                            action_context: ActionContext) -> Dict[str, Any]:
        """Execute the actual action - to be implemented by specific executors"""
        raise NotImplementedError(
            "Specific action executors must implement this method"
        )
    
    def _validate_result(self,
                        result: Dict[str, Any],
                        action_context: ActionContext) -> bool:
        """Validate action results"""
        # Basic validation - override for specific validation rules
        return isinstance(result, dict) and 'error' not in result
    
    def _generate_action_id(self) -> str:
        """Generate unique action ID"""
        return f"action_{int(time.time() * 1000)}"
    
    # Safety check implementations
    def _check_system_health(self, context: Dict[str, Any]) -> bool:
        """Check if system health is acceptable"""
        return context['system_state']['system_health'] >= 0.8
    
    def _check_resource_usage(self, context: Dict[str, Any]) -> bool:
        """Check if resource usage is within limits"""
        resource_usage = context['system_state'].get('resource_usage', {})
        return all(usage < 0.9 for usage in resource_usage.values())
    
    def _check_action_rate(self, context: Dict[str, Any]) -> bool:
        """Check if action rate is acceptable"""
        recent_actions = [
            a for a in self.action_history
            if time.time() - a.timestamp < 60
        ]
        return len(recent_actions) < 10  # Max 10 actions per minute