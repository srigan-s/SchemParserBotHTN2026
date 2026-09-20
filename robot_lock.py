"""Prevent this project's SDK clients from controlling the robot together."""
import fcntl
from pathlib import Path


def acquire_robot_lock():
    folder = Path.home() / ".cache" / "robopi-live"
    folder.mkdir(parents=True, exist_ok=True)
    handle = (folder / "controller.lock").open("a+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise RuntimeError("Another robot controller is running. Stop it with Ctrl+C first.")
    return handle  # Keep open until the controller exits.
