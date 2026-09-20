import sys, io, contextlib, types
from pathlib import Path
from unittest.mock import MagicMock, patch
import cv2
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tag_alignment import TagAligner

def marker_image(dictionary, tag, size):
    if hasattr(cv2.aruco, "generateImageMarker"):
        return cv2.aruco.generateImageMarker(dictionary, tag, size)
    return cv2.aruco.drawMarker(dictionary, tag, size)

def frame(tag, center=320):
    out = np.full((480,640,3),255,dtype=np.uint8)
    dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    marker=marker_image(dictionary,tag,120)
    out[180:300,center-60:center+60]=cv2.cvtColor(marker,cv2.COLOR_GRAY2BGR)
    return out

ep=MagicMock(); drive=MagicMock(); tracker=TagAligner(ep,drive)
for tag in (6,0,2):
    ep.camera.read_cv2_image.return_value=frame(tag)
    assert abs(tracker.observe(tag))<.01
    assert tracker.observe(99) is None
    ep.camera.read_cv2_image.return_value=frame(tag,440)
    assert tracker.observe(tag)>.1
    ep.camera.read_cv2_image.return_value=frame(tag,200)
    assert tracker.observe(tag)<-.1

with patch.object(tracker,'observe',side_effect=[.15]+[0]*15), patch('tag_alignment.time.sleep'),contextlib.redirect_stdout(io.StringIO()):
    offset=tracker.approach(6,.6)
assert offset==.03
assert drive.call_args_list[0].kwargs==dict(sideways=.03,speed=.5)
assert abs(sum(c.kwargs.get('distance',0) for c in drive.call_args_list)-.6)<1e-8
# No motion when the target is missing.
drive.reset_mock()
with patch.object(tracker,'observe',return_value=None),patch('builtins.input',side_effect=KeyboardInterrupt),contextlib.redirect_stdout(io.StringIO()):
    try:tracker.approach(6,.6)
    except KeyboardInterrupt:pass
assert not drive.called
# A stalled error offers a manual right shift, then continues instead of aborting.
with patch.object(tracker,'observe',side_effect=[.106]*4+[0]*15),patch('builtins.input',return_value='r') as prompt,patch('tag_alignment.time.sleep'),contextlib.redirect_stdout(io.StringIO()):
    lateral=tracker.approach(0,.6)
assert abs(lateral-.14)<1e-8  # Three automatic 3 cm shifts plus manual 5 cm.
prompt.assert_called_once()
assert any(c.kwargs.get('sideways')==.05 for c in drive.call_args_list)
# Missing-tag prompt also supports manual right movement.
drive.reset_mock()
with patch.object(tracker,'observe',side_effect=[None]+[0]*15),patch('builtins.input',return_value='r'),patch('tag_alignment.time.sleep'),contextlib.redirect_stdout(io.StringIO()):
    assert tracker.approach(0,.6)==.05
assert drive.call_args_list[0].kwargs==dict(sideways=.05,speed=.5)

sdk=types.ModuleType('robomaster');sdk.robot=types.SimpleNamespace(Robot=lambda:ep);sdk.camera=types.SimpleNamespace(STREAM_720P='720p');sys.modules['robomaster']=sdk
import four_trips as m
ep.reset_mock()
with patch.object(m,'TagAligner') as cls,patch('builtins.input',return_value=''),patch.object(m.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
    cls.return_value.approach.side_effect=[.01,-.02,0]
    m.run()
    assert [c.args for c in cls.return_value.approach.call_args_list]==[(6,.6),(0,.6),(2,.6)]
assert ep.gripper.close.call_count==3
assert [Path(c.kwargs['filename']).name for c in ep.play_audio.call_args_list]==['capacitors.wav','integrated_circuits.wav','resistors.wav']
ep.camera.stop_video_stream.assert_called_once()
# Failure before alignment must never close the claw for pickup.
ep.reset_mock()
with patch.object(m,'TagAligner') as cls,patch('builtins.input',return_value=''),patch.object(m.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
    cls.return_value.approach.side_effect=RuntimeError('No alignment')
    try:m.run()
    except RuntimeError:pass
ep.gripper.close.assert_not_called()
ep.camera.stop_video_stream.assert_called_once()
print('PASS: real marker detection 6/0/2, wrong-ID rejection, correction direction, 60 cm total, missing-tag hold, convergence bound, announcement mapping and abort cleanup.')
# All three IDs can be visible together; each must select its own horizontal position.
scene=np.full((480,900,3),255,dtype=np.uint8)
for tag,center in [(6,150),(0,450),(2,750)]:
 marker=marker_image(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11),tag,120)
 scene[180:300,center-60:center+60]=cv2.cvtColor(marker,cv2.COLOR_GRAY2BGR)
ep.camera.read_cv2_image.return_value=scene
tracker=TagAligner(ep,MagicMock())
assert tracker.observe(6)<-.3
assert abs(tracker.observe(0))<.01
assert tracker.observe(2)>.3
assert tracker.observe(99) is None
# Once 46 cm has been travelled, the camera must not be consulted again.
progress=[0.0]
def drive_last(ep, distance=0, **kwargs):progress[0]+=distance
def see_selected(tag):
 assert tag==6
 assert progress[0]<.46-1e-8, 'Unexpected vision requirement inside last 14 cm'
 return 0
tracker=TagAligner(ep,drive_last)
with patch.object(tracker,'observe',side_effect=see_selected) as observed,patch('tag_alignment.time.sleep'),contextlib.redirect_stdout(io.StringIO()):
 tracker.approach(6,.6)
 assert observed.call_count==15
assert abs(progress[0]-.6)<1e-8
assert m.TRAVEL_DISTANCE_M == .6
from tag_alignment import FINAL_APPROACH_M
assert FINAL_APPROACH_M == .14
print('PASS: simultaneous 6/0/2 select independently; final 14 cm needs no images.')
