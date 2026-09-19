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

Translations are 20 cm at 0.10 m/s. The turn is 45 degrees at 20 degrees/s. The arm recentres, moves 20 mm, and returns. The gripper opens and closes at power 30. The `--clear` option confirms the operator has checked the physical space. Keep the power switch accessible; software cleanup is not an emergency stop.

## Validation

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
