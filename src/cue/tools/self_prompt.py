import asyncio
import time
import logging
from typing import Optional, Callable
from ..schemas.agent_config import AgentConfig

logger = logging.getLogger(__name__)

class SelfPromptTimer:
    def __init__(self, config: AgentConfig, prompt_callback: Callable):
        """Initialize the self-prompt timer.
        
        Args:
            config: AgentConfig instance with self-prompt settings
            prompt_callback: Async callback function to execute when timer triggers
        """
        self.config = config
        self.prompt_callback = prompt_callback
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def _timer_loop(self):
        """Main timer loop that checks for and triggers self-prompts."""
        while self._running:
            current_time = time.time()
            
            # Check if it's time for a self-prompt
            if self.config.last_self_prompt_time is None or \
               (current_time - self.config.last_self_prompt_time) >= self.config.self_prompt_interval:
                try:
                    logger.info("Triggering self-prompt...")
                    await self.prompt_callback()
                    self.config.last_self_prompt_time = current_time
                except Exception as e:
                    logger.error(f"Error during self-prompt: {e}")
            
            # Sleep until next check (check every minute)
            await asyncio.sleep(60)

    def start(self):
        """Start the self-prompt timer."""
        if not self.config.enable_self_prompt:
            logger.info("Self-prompting is disabled in config")
            return

        if self._running:
            logger.warning("Timer is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._timer_loop())
        logger.info("Started self-prompt timer")

    def stop(self):
        """Stop the self-prompt timer."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Stopped self-prompt timer")