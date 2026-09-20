"""Offline command/state checks; no physical robot or terminal required."""
import sys, types, tempfile, subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sdk=types.ModuleType('robomaster');sdk.robot=MagicMock();sys.modules['robomaster']=sdk
from terminal_controller import Controller
from robot_lock import acquire_robot_lock

ep=MagicMock();c=Controller(ep)
for key,expected in [('w',(.25,0,0)),('s',(-.25,0,0)),('a',(0,-.25,0)),('d',(0,.25,0)),('j',(0,0,30)),('l',(0,0,-30))]:
 c.key(key,0)
 assert ep.chassis.drive_speed.call_args.kwargs==dict(zip(('x','y','z'),expected))
 c.tick(.21)
 assert c.motion_until is None
 ep.chassis.drive_wheels.assert_called_with(0,0,0,0)
# Grab closes before lifting, and lifting only begins after the close interval.
c.key('g',1);ep.gripper.close.assert_called_with(power=40)
c.tick(2);ep.robotic_arm.move.assert_not_called()
c.tick(2.51);ep.robotic_arm.move.assert_called_once_with(x=0,y=50)
# Busy arm prevents overlapping commands but stop remains accessible.
assert c.arm_action is not None
calls=ep.robotic_arm.move.call_count;c.key('i',2.6)
assert ep.robotic_arm.move.call_count==calls
c.key(' ',2.7);ep.gripper.pause.assert_called()
# Stop cancels a grab's scheduled lift.
ep=MagicMock();c=Controller(ep);c.key('g',0);c.key('x',.5);c.tick(2)
ep.robotic_arm.move.assert_not_called()
assert c.key('q',3) is False
# Fixed adjustment sizes and opening settings.
ep=MagicMock();c=Controller(ep);c.key('i',0);ep.robotic_arm.move.assert_called_with(x=0,y=10)
c.arm_action=None;c.key('o',1);ep.robotic_arm.move.assert_called_with(x=-10,y=0)
c.arm_action=None;c.key('v',2);ep.gripper.open.assert_called_once_with(power=30)
# Same process can only acquire the file lock once through separate handles.
with tempfile.TemporaryDirectory() as tmp, patch('robot_lock.Path.home',return_value=Path(tmp)):
 with acquire_robot_lock():
  try:acquire_robot_lock()
  except RuntimeError:pass
  else:raise AssertionError('Second controller must be rejected')
 with acquire_robot_lock():pass
print('PASS: movement directions, nudge stop, grab/lift ordering, cancel pending lift, busy handling, arm adjustments and controller lock.')
