import subprocess


def execute_shell_command(command, wait=True):
    try:
        if wait:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip() if result.stdout else result.stderr.strip()
        else:
            subprocess.Popen(command, shell=True)
            return "Command executed in non-blocking mode."
    except subprocess.CalledProcessError as e:
        return f"Error executing command '{command}': {e.stderr.strip()}"
