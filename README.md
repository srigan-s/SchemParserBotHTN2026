# SchemParserBotHTN2026

Raspberry Pi 5 + DJI RoboMaster EP foundation for the schematic-parsing robot project.

## Hardware connection

Power the Pi and robot normally. Connect a USB-A port on the Pi to the Micro-USB port on the RoboMaster intelligent controller with a **data cable**. The scripts use USB RNDIS (`conn_type='rndis'`). The Pi can keep its Wi-Fi internet and SSH connection.

The robot's default USB address is `192.168.42.2`. Verify it from the Pi:

```bash
ping -c 3 192.168.42.2
```

## Install on Raspberry Pi OS Bookworm (64-bit)

```bash
sudo apt update
sudo apt install -y git python3-pip python3-venv python3-opencv libopus-dev build-essential python3-dev
python3 -m venv --system-site-packages ~/robomaster-env
source ~/robomaster-env/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install --index-url https://test.pypi.org/simple/ rm-libmedia-codec==0.0.1
python -c "from robomaster import robot; import cv2, libmedia_codec; print('SDK ready')"
```

NumPy stays below version 2 for compatibility with Bookworm's system OpenCV. The media codec is installed separately following the SDK maintainer's Python 3.11 instructions. ROS is not required.

## Run tests

```bash
source ~/robomaster-env/bin/activate
cd ~/schematic-robot
python connection_test.py
python camera_test.py
```

The camera test writes `robomaster_camera.jpg`, which Git ignores.

Place the robot on the floor with at least one metre of clear space and enough USB cable slack. Keep hands and objects away from the arm and gripper. Run each test separately:

```bash
python move_test.py forward --clear
python move_test.py sideways --clear
python move_test.py turn --clear
python arm_test.py --clear
python gripper_test.py --clear
```

Chassis tests are currently disabled following unexpected turning. The SDK clamps chassis.move() translation speed to a minimum of 0.5 m/s; lower requested values are not honored. The turn is 45 degrees at 20 degrees/s. The arm recentres, moves 20 mm, and returns. The gripper opens and closes at power 30. The `--clear` option confirms the operator has checked the physical space. Keep the power switch accessible; software cleanup is not an emergency stop.

## Simple pickup

`pickup.py` opens the claw, commands a straight 10 cm forward move, stops,
closes the claw, and lifts the arm 30 mm. Start with the claw at the holder's
height and the holder aligned 10 cm ahead of its grasp position. This fixed
sequence does not use AprilTags or verify that the box was grasped.

Run on the Pi with other robot SDK clients stopped:

```bash
systemctl --user stop robopi-live.service
cd ~/schematic-robot
~/robomaster-env/bin/python pickup.py
```

The position command uses the SDK minimum speed of 0.5 m/s. A failed approach
aborts the grasp and lift and attempts to stop the chassis. This new sequence
has been checked offline only, not run on the robot.

## Three 60 cm pickup/delivery cycles

Start at the human's delivery line facing the boxes, with the first holder
60 cm ahead of the claw. Arrange subsequent holders in parallel lanes 25 cm
apart to the robot's right when facing the boxes.

Each cycle tracks the first 45 cm in steps of up to 10 cm, then advances the
final 15 cm without vision at a requested 0.7 m/s, grips and lifts 30 mm,
reverses exactly 60 cm, turns 180 degrees, and raises the claw a further 50 mm (5 cm) from its carrying position for
handoff. Follow the prompts to support and remove the box. The arm then lowers
to y=0. After cycles 1–2 the robot shifts 25 cm toward the starting right and
turns back to face the boxes. There is no lateral shift after cycle 3; it finishes
facing the human. No 100 cm movement or extra return leg remains.

The lateral command is body-left while facing the human, which is right in the
original orientation. The delivery location moves sideways with each lane.
Startup recentres the empty arm and sets x=180 mm, y=0 mm. The fixed pickup
position check is disabled. The handoff height check and arm-position telemetry wait are removed.
Operation waits have no script deadlines. Ctrl+C requests a stop. There is no
person tracking or obstacle avoidance. Actual travel
can differ from commanded distances due to wheel slip.

```bash
systemctl --user stop robopi-live.service
cd ~/schematic-robot
~/robomaster-env/bin/python four_trips.py
```

The revised route has been verified with a mock SDK, not run on hardware.

## Previous hardware validation

Tested on a Raspberry Pi 5 running Python 3.11 and OpenCV 4.6 over USB: SDK connection, camera capture, chassis forward/sideways/turn action completion, arm sequence, and gripper sequence. Physical distances were not independently measured. No autonomous navigation or schematic parser is implemented yet.

## Sync changes on the Pi

```bash
cd ~/schematic-robot
git status
git pull --ff-only
```

Inspect and commit or stash local changes before pulling. GitHub authentication is needed to push; public pulls do not require credentials.

## References

- [DJI SDK connection guide](https://robomaster-dev-en.readthedocs.io/en/latest/python_sdk/connection.html)
- [Maintained SDK fork](https://github.com/jeguzzi/RoboMaster-SDK)
- [Python 3.11 installation instructions](https://github.com/jeguzzi/robomaster_ros#robomaster-sdk)

## Read-only camera

`live_camera.py` serves a local camera view and AprilTag detections on port 8765.
It has no movement command handler. Stop it before running the delivery script,
which owns the robot's camera and SDK connection.

Operation and camera waits have no script-imposed deadlines. Missing completion
or video messages can leave the sequence waiting until Ctrl+C. SDK errors still
abort. Pickup closing uses power 40 for 1.5 seconds, then pauses the gripper motor.

## DJI speaker announcements

The run now has three rounds: capacitors, integrated circuits, then resistors.
Arrange the boxes in that order across the pickup lanes. Tags select the expected box in a fixed order; this is not visual component classification. At each handoff, after turning toward the person and raising
the claw, the script plays that part's WAV through `ep.play_audio()` on the DJI
speaker, waits for completion, then prompts for release. The `audio/` files are
converted to mono 48 kHz 16-bit PCM WAV, and checked before any robot movement.
Keep `audio/` beside `four_trips.py` when copying to the Pi.

## AprilTag alignment

| Round | Part/audio | AprilTag family | ID |
|---|---|---|---|
| 1 | capacitors.wav | 36h11 | 6 |
| 2 | integrated_circuits.wav | 36h11 | 0 |
| 3 | resistors.wav | 36h11 | 2 |

`tag_alignment.py` uses the robot camera and OpenCV ArUco AprilTag support. Only
the expected ID is accepted. It ignores other IDs in the image and requires three centred frames before each
tracked 10 cm forward step. The first 45 cm are tracked; once 45 cm has been
commanded, it drives the final 15 cm and grips without another camera check.
The last visual check occurs before the step from 40 to 45 cm, since the tag
may already be hidden at the 45 cm boundary. It shifts sideways 3 cm at a time
using the SDK's minimum position speed of 0.5 m/s. If the tag is missing or
ambiguous it stays stopped and prompts for visibility; Ctrl+C exits. After three corrections without useful improvement, or ten corrections, it
pauses for manual adjustment instead of raising a convergence error. At this
prompt or a missing-tag prompt: `r` shifts right 5 cm, `l` shifts left 5 cm,
Enter retries the camera, and `q` aborts. Right is body-right while facing the
boxes. Both automatic and manual offsets are recorded for the return leg. Camera waits, like operation waits, have no script deadline.

Place each tag at the holder's centre and keep it visible until the last 15 cm.
`TARGET_X_FRACTION=0.5` assumes the claw's grasp axis aligns with image centre;
this must be verified on the physical robot. This controls horizontal image
alignment only, not tag range, holder height, obstacle avoidance, or grasp success.
The total commanded forward distance remains 60 cm. Lateral alignment offsets
are undone after reversing to the delivery line so the 25 cm lane spacing remains
relative to the starting layout. Camera/claw calibration and the latest tracking corrections have not been validated on hardware.

The audio now comes from `capacitors (2).wav`, `integrated_circuits (1).wav`, and
`resistors.wav`, converted to normalized filenames under `audio/`.

Upload all dependencies from the Mac:

```bash
scp -r pickup.py four_trips.py tag_alignment.py audio USER@PI_IP:~/schematic-robot/
```

Stop the separate `robopi-live.service` before running; this script owns the
robot's camera connection. Tests use generated real AprilTag images and a mock
robot to check IDs, correction direction, missing-tag holds, route and cleanup.

Run the offline checks from the repository (requires NumPy and OpenCV with ArUco):

```bash
python tests/check_tag_alignment.py
```

These checks use a mock robot and do not move hardware or play audio.
