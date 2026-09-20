import argparse
from robomaster import robot

parser = argparse.ArgumentParser(description='Run one low-speed chassis test.')
parser.add_argument('direction', choices=['forward', 'sideways', 'turn'], nargs='?', default='forward')
parser.add_argument('--clear', action='store_true', help='Confirm robot is on floor with at least 1 metre clear around it.')
args = parser.parse_args()
if not args.clear:
    parser.error('Place robot on floor with clear space, then pass --clear.')
moves = {'forward': dict(x=0.20), 'sideways': dict(y=0.20), 'turn': dict(z=45)}
raise SystemExit('Chassis tests disabled: unexpected drift is under investigation. Do not run motion until diagnosed.')
ep = robot.Robot()
try:
    if not ep.initialize(conn_type='rndis'):
        raise RuntimeError('SDK initialization failed')
    action = ep.chassis.move(**moves[args.direction], xy_speed=0.10, z_speed=20)
    if not action.wait_for_completed(timeout=15) or not action.has_succeeded:
        raise RuntimeError('Motion did not complete successfully')
    print('Done!')
finally:
    try:
        if ep.chassis is not None:
            ep.chassis.drive_speed(x=0, y=0, z=0)
    finally:
        ep.close()
