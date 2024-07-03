import unittest
from tools.execute_shell_command import execute_shell_command
import time

class TestExecuteShellCommand(unittest.TestCase):
    def test_blocking_execution(self):
        command = "echo 'Hello, World!'"
        output = execute_shell_command(command, wait=True)
        self.assertEqual(output, 'Hello, World!')

    def test_non_blocking_execution(self):
        command = "sleep 5"
        start_time = time.time()
        output = execute_shell_command(command, wait=False)
        end_time = time.time()
        self.assertEqual(output, 'Command executed in non-blocking mode.')
        self.assertTrue((end_time - start_time) < 1, "The command should return immediately.")

if __name__ == '__main__':
    unittest.main()
