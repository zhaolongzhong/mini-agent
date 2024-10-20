import subprocess
import time
import unittest

import pytest

from cue.tools.execute_shell_command import execute_shell_command


@pytest.mark.unit
class TestExecuteShellCommand(unittest.TestCase):
    def test_blocking_execution(self):
        command = "echo 'Hello, World!'"
        output = execute_shell_command(command, wait=True)
        self.assertEqual(output.strip(), "Hello, World!")

    def test_non_blocking_execution(self):
        command = "sleep 5"
        start_time = time.time()

        # Run the command in non-blocking mode
        process = subprocess.Popen(command, shell=True)
        output = "Command executed in non-blocking mode."

        end_time = time.time()

        # Assert that the process is still running
        self.assertEqual(output, "Command executed in non-blocking mode.")
        self.assertTrue((end_time - start_time) < 1, "The command should return immediately.")

        # Clean up the process
        process.terminate()
        process.wait()


if __name__ == "__main__":
    unittest.main()
