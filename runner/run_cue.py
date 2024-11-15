import os
import json
import time
import signal
import logging
import subprocess
from datetime import datetime

import psutil
from cue_runner.config import RunnerConfig


class CueRunner:
    def __init__(self, runner_id: str = RunnerConfig.DEFAULT_RUNNER_ID):
        self.runner_id = runner_id
        self.process = None
        self.should_run = True

        # Get dedicated space for this runner
        self.space = RunnerConfig.get_runner_space(runner_id)
        self.setup_logging()

        self.last_control_check = time.time()
        self.control_check_interval = 5  # Check control file every x second

    def setup_logging(self):
        """Setup dedicated logging for this runner"""
        self.logger = logging.getLogger(f"cue_runner.{self.runner_id}")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - [%(name)s] %(message)s")

        # File handler for runner-specific log file
        file_handler = logging.FileHandler(self.space["log_file"])
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        self.logger.setLevel(logging.INFO)

    def ensure_single_instance(self):
        """Ensure only one instance of this specific runner ID runs"""
        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                cmdline = " ".join(proc.cmdline())
                if (
                    proc.pid != os.getpid()
                    and "cue -r --runner" in cmdline
                    and f"--runner-id {self.runner_id}" in cmdline
                ):
                    self.logger.info(f"Killing existing runner process: {proc.pid}")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Clean up stale files
        for file in RunnerConfig.get_files(self.runner_id):
            if file.exists():
                try:
                    data = json.loads(file.read_text()) if "control" in str(file) else int(file.read_text())
                    pid = data.get("pid") if "control" in str(file) else data
                    if not psutil.pid_exists(pid):
                        file.unlink()
                except (json.JSONDecodeError, ValueError):
                    file.unlink()

    def setup_control_file(self):
        """Initialize control file for this runner with clean state"""
        control_data = {
            "runner_id": self.runner_id,
            "pid": os.getpid(),
            "last_start": datetime.now().isoformat(),
            "restart_requested": False,  # Always start clean
            "status": "running",
            "last_check": datetime.now().isoformat(),
        }
        self.space["control_file"].write_text(json.dumps(control_data, indent=2))
        self.space["pid_file"].write_text(str(os.getpid()))
        self.logger.info(f"Control files created in {self.space['space_dir']}")

    def handle_restart(self):
        """Handle the restart sequence"""
        self.logger.info("Initiating restart sequence")

        # Clear the restart flag before stopping the process
        try:
            current_data = json.loads(self.space["control_file"].read_text())
            current_data.update(
                {
                    "restart_requested": False,
                    "status": "running",
                    "last_check": datetime.now().isoformat(),
                    "restart_completed_at": datetime.now().isoformat(),
                }
            )
            self.space["control_file"].write_text(json.dumps(current_data, indent=2))
        except Exception as e:
            self.logger.error(f"Error updating control file during restart: {e}")

        # Stop the process
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.logger.warning("Process didn't terminate gracefully, forcing kill")
            self.process.kill()
            self.process.wait()

        self.logger.info("Process stopped for restart")
        return True

    def update_control_file(self):
        """Update control file with latest status"""
        try:
            if not self.space["control_file"].exists():
                return

            current_data = json.loads(self.space["control_file"].read_text())

            # Only update if not in a restart sequence
            if current_data.get("status") not in ["restart_pending", "restarting"]:
                current_data.update(
                    {
                        "last_check": datetime.now().isoformat(),
                        "pid": os.getpid(),
                        "status": "running",
                        "restart_requested": False,  # Clear restart flag after restart
                    }
                )
                self.space["control_file"].write_text(json.dumps(current_data, indent=2))

        except Exception as e:
            self.logger.error(f"Error updating control file: {e}")

    def start(self):
        """Start the runner with its specific ID"""
        signal.signal(signal.SIGTERM, lambda signum, frame: self.stop())
        signal.signal(signal.SIGINT, lambda signum, frame: self.stop())

        self.logger.info(f"Starting Cue runner: {self.runner_id}")
        self.ensure_single_instance()
        self.setup_control_file()  # Start with clean state

        cmd = ["cue", "-r", "--runner"]
        if self.runner_id:
            cmd.extend(["--runner-id", self.runner_id])

        while self.should_run:
            try:
                # Redirect logs to our log file
                log_file = open(self.space["log_file"], "a")

                self.logger.info("Starting new process instance")
                self.process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    env={
                        **os.environ,
                        "PYTHONUNBUFFERED": "1",
                        "CUE_RUNNER_ID": self.runner_id,
                        "CUE_CONTROL_FILE": str(self.space["control_file"]),
                        "CUE_SERVICE_FILE": str(self.space["service_file"]),
                    },
                )

                self.logger.info(f"Started process with PID: {self.process.pid}")

                # Monitor process and check for restart
                while self.process.poll() is None and self.should_run:
                    # Check for restart request
                    if self.check_restart_request():
                        if self.handle_restart():
                            log_file.close()
                            time.sleep(1)  # Brief pause before restart
                            # Break to outer loop to start new process
                            break

                    # Update control file periodically
                    self.update_control_file()
                    time.sleep(1)  # Sleep to prevent busy waiting

                if not self.should_run:
                    self.logger.info("Runner stop requested")
                    break

                exit_code = self.process.poll()
                if exit_code is not None:
                    if exit_code == -15:  # SIGTERM
                        self.logger.info("Process terminated for restart")
                    else:
                        self.logger.error(f"Process exited with code {exit_code}")
                        time.sleep(5)

                log_file.close()

            except Exception as e:
                self.logger.error(f"Error in runner: {e}")
                time.sleep(5)

    def check_restart_request(self) -> bool:
        """Check if restart has been requested via control file"""
        try:
            now = time.time()
            if now - self.last_control_check < self.control_check_interval:
                return False

            self.last_control_check = now

            if not self.space["control_file"].exists():
                return False

            current_data = json.loads(self.space["control_file"].read_text())

            # Only handle restart if explicitly requested
            if current_data.get("restart_requested"):
                reason = current_data.get("restart_reason", "Unknown")
                self.logger.info(f"Restart requested: {reason}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error checking restart request: {e}")
            return False

    def stop(self):
        """Stop this specific runner instance"""
        self.should_run = False
        if self.process:
            self.logger.info("Stopping runner process...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.logger.warning("Process didn't terminate gracefully, forcing kill")
                self.process.kill()

        # Clean up files
        for file in RunnerConfig.get_files(self.runner_id):
            try:
                if file.exists():
                    file.unlink()
                    self.logger.debug(f"Cleaned up file: {file}")
            except Exception as e:
                self.logger.error(f"Error cleaning up {file}: {e}")

        self.logger.info("Runner cleanup completed")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runner-id", default=RunnerConfig.DEFAULT_RUNNER_ID, help="Unique identifier for this runner instance"
    )
    args = parser.parse_args()

    runner = CueRunner(runner_id=args.runner_id)
    try:
        runner.start()
    except KeyboardInterrupt:
        runner.logger.info("Received keyboard interrupt")
    finally:
        runner.stop()
        runner.logger.info("Runner stopped")
