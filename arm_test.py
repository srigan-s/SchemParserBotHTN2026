import argparse
from robomaster import robot

parser = argparse.ArgumentParser()
parser.add_argument('--clear', action='store_true', help='Confirm arm has clearance and nobody is touching it.')
if not parser.parse_args().clear:
    parser.error('Clear the arm area, then pass --clear.')
ep = robot.Robot()
def finish(action):
    if not action.wait_for_completed(timeout=15) or not action.has_succeeded:
        raise RuntimeError('Arm action did not complete successfully')
try:
    if not ep.initialize(conn_type='rndis'):
        raise RuntimeError('SDK initialization failed')
    print('Centering arm...', flush=True)
    finish(ep.robotic_arm.recenter())
    print('Moving arm...', flush=True)
    finish(ep.robotic_arm.move(x=20, y=0))
    print('Returning...', flush=True)
    finish(ep.robotic_arm.move(x=-20, y=0))
finally:
    ep.close()
