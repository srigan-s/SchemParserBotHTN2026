import argparse
import time
from robomaster import robot

parser = argparse.ArgumentParser()
parser.add_argument('--clear', action='store_true', help='Confirm fingers and objects are clear of the gripper.')
if not parser.parse_args().clear:
    parser.error('Clear the gripper, then pass --clear.')
ep = robot.Robot()
gripper = None
try:
    if not ep.initialize(conn_type='rndis'):
        raise RuntimeError('SDK initialization failed')
    gripper = ep.gripper
    print('Opening...', flush=True)
    gripper.open(power=30)
    time.sleep(2)
    gripper.pause()
    print('Closing...', flush=True)
    gripper.close(power=30)
    time.sleep(2)
finally:
    try:
        if gripper is not None:
            gripper.pause()
    finally:
        ep.close()
