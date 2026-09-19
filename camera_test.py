from pathlib import Path
import cv2
from robomaster import robot, camera

ep = robot.Robot()
streaming = False
try:
    if not ep.initialize(conn_type='rndis'):
        raise RuntimeError('SDK initialization failed')
    if not ep.camera.start_video_stream(display=False, resolution=camera.STREAM_360P):
        raise RuntimeError('Camera stream failed to start')
    streaming = True
    frame = ep.camera.read_cv2_image(timeout=10, strategy='newest')
    if frame is None:
        raise RuntimeError('No camera frame received')
    path = Path(__file__).resolve().parent / 'robomaster_camera.jpg'
    if not cv2.imwrite(str(path), frame):
        raise RuntimeError('Could not save camera frame')
    print(f'Saved {path}')
finally:
    try:
        if streaming:
            ep.camera.stop_video_stream()
    finally:
        ep.close()
