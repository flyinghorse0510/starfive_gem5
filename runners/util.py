import subprocess, os, sys

# Execute shell command
def exec_shell_cmd(cmd: str, writeStdout: bool = False, writeStderr: bool = False, directStdout: bool = False, directStderr: bool = False) -> tuple:
    # Run command
    process = subprocess.Popen(
        ["bash", "-c", cmd],
        stdout = sys.stdout if directStdout else subprocess.PIPE,
        stderr = sys.stderr if directStderr else subprocess.PIPE
    )
    # Get output and return code
    stdoutTxt, stderrTxt = process.communicate()
    exitCode = process.returncode
    # Write output
    if writeStdout and not directStdout:
        sys.stdout.write(stdoutTxt)
    if writeStderr and not directStderr:
        sys.stderr.write(stderrTxt)
    # return result
    return ("" if directStdout else str(stdoutTxt, encoding='utf-8').strip("\n"), "" if directStderr else str(stderrTxt, encoding='utf-8').strip("\n"), exitCode)
    
def get_repo_root() -> str:
    shellResults = exec_shell_cmd("git rev-parse --show-toplevel")
    return None if shellResults[2] != 0 else shellResults[0]

def get_system_info() -> None:
    return

def create_dir(path: str) -> bool:
    exec_shell_cmd("mkdir -p %s" %(path), directStdout = False, directStderr = False)