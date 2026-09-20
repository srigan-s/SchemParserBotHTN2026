"""Open claw, drive forward 10 cm, stop, grip, and lift 30 mm over USB."""

import time

from robomaster import robot
from robot_lock import acquire_robot_lock


def finish(action, label):
    started = time.monotonic()
    completed = action.wait_for_completed()
    if not completed or not action.has_succeeded:
        outcome = "ended without completion" if not completed else "reported unsuccessful completion"
        raise RuntimeError(
            f"{label} {outcome} after {time.monotonic() - started:.1f}s; "
            f"state={action.state}, reason={action.failure_reason}, action={action!r}. "
            "Sequence aborted; do not retry until the robot's actual position is checked."
        )


def stop(ep):
    try:
        ep.chassis.drive_speed(x=0, y=0, z=0)
    finally:
        ep.chassis.drive_wheels(0, 0, 0, 0)


def pickup():
    ep = robot.Robot()
    connected = False
    try:
        if not ep.initialize(conn_type="rndis"):
            raise RuntimeError("SDK initialization failed")
        connected = True
        stop(ep)
        print("Opening claw...", flush=True)
        try:
            ep.gripper.open(power=30)
            time.sleep(0.7)
        finally:
            ep.gripper.pause()

        print("Moving forward 10 cm...", flush=True)
        try:
            # Distance is in metres. This SDK's minimum position-move speed is 0.5 m/s.
            finish(ep.chassis.move(x=0.10, y=0, z=0, xy_speed=0.5), "Forward move")
        finally:
            stop(ep)
        time.sleep(0.3)

        print("Closing claw...", flush=True)
        try:
            ep.gripper.close(power=40)
            time.sleep(1.5)
        finally:
            ep.gripper.pause()

        print("Lifting 30 mm...", flush=True)
        finish(ep.robotic_arm.move(x=0, y=30), "Lift")
        print("Sequence complete; check that the box is held.", flush=True)
    finally:
        try:
            if connected:
                try:
                    stop(ep)
                finally:
                    ep.gripper.pause()
        finally:
            ep.close()


if __name__ == "__main__":
    with acquire_robot_lock():
        pickup()
