#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""fly.io deployment helpers — replaces Makefile."""

import json
import subprocess
import sys
import time

APP = "llmsurvey"


def _ensure_machine_running():
    """Start any stopped machines and wait until one is in 'started' state."""
    result = subprocess.run(
        ["fly", "machine", "list", "--app", APP, "--json"],
        capture_output=True, text=True, check=True,
    )
    machines = json.loads(result.stdout)
    for m in machines:
        if m["state"] != "started":
            subprocess.run(["fly", "machine", "start", m["id"], "--app", APP], check=True)

    for _ in range(30):
        result = subprocess.run(
            ["fly", "machine", "list", "--app", APP, "--json"],
            capture_output=True, text=True, check=True,
        )
        if any(m["state"] == "started" for m in json.loads(result.stdout)):
            break
        time.sleep(2)
    else:
        sys.exit("Timed out waiting for a machine to start")

    # Machine is "started" in API but SSH may not be ready yet — poll until it is.
    # [Dirko 2026-04-07] Doesn't work, throws weird SSH errors. Will investigate later.
    # for i in range(30):
    #     print(f"Polling {APP} for SSH/console access ({i+1} / 30)")
    #     probe = subprocess.run(
    #         ["fly", "ssh", "console", "--app", APP, "-C", "true"],
    #         capture_output=True,
    #     )
    #     if probe.returncode == 0:
    #         return
    #     
    #     print(probe.stderr)
    #     time.sleep(2)
    # sys.exit("Timed out waiting for SSH to become available")


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
    _ensure_machine_running()
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
    _ensure_machine_running()
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
