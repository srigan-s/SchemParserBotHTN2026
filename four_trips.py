"""Three 60 cm pickup/delivery lanes, spaced 25 cm to the starting right.

Start at the human's delivery line facing the boxes, with a holder 60 cm ahead
of the claw. Each cycle advances 60 cm and reverses the same 60 cm, then turns
for handoff. Between cycles shift to the next lane and face the boxes again.
Forward distances use odometry; AprilTags guide lateral alignment, not range.
There is no obstacle detection.
"""

import time
import wave
from pathlib import Path

from robomaster import robot, camera
from pickup import finish, stop
from tag_alignment import TagAligner

AUDIO_DIR = Path(__file__).resolve().parent / "audio"
DELIVERIES = (
    ("capacitors", "capacitors.wav", 6),
    ("integrated circuits", "integrated_circuits.wav", 0),
    ("resistors", "resistors.wav", 2),
)
TRIPS = len(DELIVERIES)
TRAVEL_DISTANCE_M = 0.60
LANE_SHIFT_M = 0.25
DRIVE_SPEED_MPS = 0.7
LIFT_MM = 30
PICKUP_X_MM = 180
HANDOFF_LIFT_MM = 50  # Raise 5 cm relative to the carrying position.
PICKUP_HEIGHT_MM = 0  # Lowest documented vertical coordinate.


def drive(ep, distance=0, sideways=0, speed=DRIVE_SPEED_MPS):
    try:
        # The installed SDK clamps position-move speeds to at least 0.5 m/s.
        finish(ep.chassis.move(x=distance, y=sideways, z=0, xy_speed=speed), "Drive")
    finally:
        stop(ep)
    time.sleep(0.3)


def claw(ep, opening):
    try:
        command = ep.gripper.open if opening else ep.gripper.close
        if not command(power=30 if opening else 40):
            raise RuntimeError("Claw command failed")
        time.sleep(1.0 if opening else 1.5)
    finally:
        ep.gripper.pause()


def turn(ep, degrees):
    try:
        finish(ep.chassis.move(x=0, y=0, z=degrees, z_speed=45), "Turn")
    finally:
        stop(ep)
    time.sleep(0.3)


def run():
    # Check every announcement before connecting or moving the robot.
    for _, filename, _ in DELIVERIES:
        with wave.open(str(AUDIO_DIR / filename), "rb") as audio:
            if (audio.getnchannels(), audio.getframerate(), audio.getsampwidth(), audio.getcomptype()) != (1, 48000, 2, "NONE"):
                raise RuntimeError(f"Unsupported speaker audio: {filename}")
    ep = robot.Robot()
    connected = False
    streaming = False
    try:
        if not ep.initialize(conn_type="rndis"):
            raise RuntimeError("SDK initialization failed")
        connected = True
        stop(ep)
        if not ep.camera.start_video_stream(display=False, resolution=camera.STREAM_720P):
            raise RuntimeError("Camera stream failed")
        streaming = True
        aligner = TagAligner(ep, drive)
        input("Empty the claw and clear the arm area. Enter to zero and position arm: ")
        claw(ep, opening=True)
        # SDK recenter moves to (0, 0); it does not recalibrate the hardware.
        finish(ep.robotic_arm.recenter(), "Arm zero")
        finish(ep.robotic_arm.moveto(x=PICKUP_X_MM, y=PICKUP_HEIGHT_MM), "Set pickup pose")
        for trip, (part, filename, tag_id) in enumerate(DELIVERIES, start=1):
            print(f"Trip {trip}/{TRIPS}: {part}, tag 36h11 [{tag_id}]", flush=True)
            claw(ep, opening=True)
            input("Align the next holder 60 cm ahead of the claw. "
                  "Clear the 60 cm route and space for a full turn, including feet. "
                  "Press Enter to pick up: ")
            pickup_x, pickup_y = PICKUP_X_MM, PICKUP_HEIGHT_MM
            print("Moving forward 60 cm to the box...", flush=True)
            lateral_offset = aligner.approach(tag_id, TRAVEL_DISTANCE_M)
            claw(ep, opening=False)
            finish(ep.robotic_arm.moveto(
                x=pickup_x, y=pickup_y + LIFT_MM), "Lift")
            input("Confirm the box is held and hands are clear. "
                  "Enter to deliver; Ctrl+C to stop: ")

            print("Reversing 60 cm to the chair delivery point...", flush=True)
            drive(ep, -TRAVEL_DISTANCE_M)
            if abs(lateral_offset) > 1e-8:
                drive(ep, sideways=-lateral_offset)
            print("Turning 180 degrees to face the person...", flush=True)
            turn(ep, 180)
            print("Raising claw 5 cm for handoff...", flush=True)
            finish(ep.robotic_arm.move(x=0, y=HANDOFF_LIFT_MM), "Handoff lift")
            print(f"Announcing {part} through the DJI speaker...", flush=True)
            playback = ep.play_audio(filename=str(AUDIO_DIR / filename))
            if playback is None:
                raise RuntimeError(f"Could not start announcement for {part}")
            finish(playback, f"Announce {part}")
            input("Robot stopped. Support the box, keeping fingers clear of "
                  "the jaws. Press Enter to release: ")
            claw(ep, opening=True)
            input("Remove the box and clear hands/feet from the route. "
                  "Press Enter to lower the arm and finish this cycle: ")

            finish(ep.robotic_arm.moveto(x=pickup_x, y=pickup_y), "Restore pickup height")

            if trip < TRIPS:
                print("Shifting 25 cm right to the next pickup lane...", flush=True)
                # Facing the human reverses body axes: body-left is starting-right.
                drive(ep, sideways=-LANE_SHIFT_M)
                print("Turning back toward the boxes...", flush=True)
                turn(ep, -180)
        print(f"All {TRIPS} delivery-and-return cycles complete.", flush=True)
    finally:
        try:
            if connected:
                try:
                    stop(ep)
                finally:
                    ep.gripper.pause()
        finally:
            try:
                if streaming:
                    ep.camera.stop_video_stream()
            finally:
                ep.close()


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("Interrupted; stop commands sent.")
