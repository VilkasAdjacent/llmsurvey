#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""fly.io deployment helpers — replaces Makefile."""

import subprocess
import sys

APP = "llmsurvey"


def setup():
    subprocess.run(
        ["fly", "volumes", "create", "llmsurvey_data", "--size", "1", "--app", APP],
        check=True,
    )
    print(f"Next: fly secrets set REPLICATE_API_TOKEN=<your-token> --app {APP}")


def deploy():
    subprocess.run(["fly", "deploy", "--app", APP], check=True)


def publish():
    """Tar local surveys/ and stream it into the fly.io volume."""
    tar = subprocess.Popen(["tar", "czf", "-", "surveys"], stdout=subprocess.PIPE)
    ssh = subprocess.Popen(
        ["fly", "ssh", "console", "--app", APP, "-C", "tar xzf - -C /data"],
        stdin=tar.stdout,
    )
    tar.stdout.close()
    ssh.communicate()
    if tar.wait() != 0 or ssh.returncode != 0:
        sys.exit(1)


def pull():
    """Stream surveys/ from the fly.io volume back to local."""
    ssh = subprocess.Popen(
        ["fly", "ssh", "console", "--app", APP, "-C", "tar czf - -C /data surveys/"],
        stdout=subprocess.PIPE,
    )
    tar = subprocess.Popen(["tar", "xzf", "-"], stdin=ssh.stdout)
    ssh.stdout.close()
    tar.communicate()
    if ssh.wait() != 0 or tar.returncode != 0:
        sys.exit(1)


COMMANDS = {"setup": setup, "deploy": deploy, "publish": publish, "pull": pull}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: uv run deploy.py [{' | '.join(COMMANDS)}]")
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
