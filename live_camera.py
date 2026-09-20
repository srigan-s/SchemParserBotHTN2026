"""Read-only local camera feed and AprilTag recognition. No motion commands."""
import json, os, threading, time, signal
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import cv2
from robomaster import robot, camera
from robot_lock import acquire_robot_lock

_controller_lock = acquire_robot_lock()

RUNTIME = Path.home() / '.cache' / 'robopi-live'
RUNTIME.mkdir(parents=True, exist_ok=True)
os.chmod(RUNTIME, 0o700)
lock = threading.Lock()
jpeg = b''
state = {'mode': 'read-only; movement disabled', 'tags': [], 'frame_time': 0, 'arm': None}
command_lock = threading.Lock()
ep = robot.Robot()
PAGE = b'''<!doctype html><meta name="viewport" content="width=device-width"><title>RoboPi Live Camera</title><style>body{background:#10151c;color:#e5edf5;font:18px system-ui;margin:24px}img{width:100%;max-width:1100px;border-radius:12px}pre{white-space:pre-wrap}</style><h1>RoboPi Live Camera</h1><p>READ ONLY - movement disabled &bull; AprilTag outlines and IDs</p><img id="feed"><pre id="status">Connecting...</pre><script>const img=document.querySelector('#feed');async function tick(){try{const s=await fetch('/status').then(r=>r.json());document.querySelector('#status').textContent=JSON.stringify(s,null,2);img.src='/frame.jpg?t='+Date.now()}catch(e){document.querySelector('#status').textContent='Disconnected'}setTimeout(tick,250)}tick()</script>'''
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path=self.path.split('?')[0]
        with lock:
            body=jpeg if path=='/frame.jpg' else json.dumps(state).encode() if path=='/status' else PAGE
        self.send_response(200 if body else 503)
        self.send_header('Content-Type','image/jpeg' if path=='/frame.jpg' else 'application/json' if path=='/status' else 'text/html')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass
    def log_message(self,*args):pass

def wheel_status(value):
    with lock:
        state['wheel_rpm']=list(value[0])
        state['wheel_state']=list(value[3])
        state['wheel_time']=time.time()

def arm_position(value):
    with lock:state['arm']=list(value)

families=['36h11','36h10','25h9','16h5']
dictionaries=[(f,cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco,'DICT_APRILTAG_'+f))) for f in families]
params=cv2.aruco.DetectorParameters_create()
params.cornerRefinementMethod=cv2.aruco.CORNER_REFINE_SUBPIX
def terminate(signum, frame):
    raise KeyboardInterrupt
signal.signal(signal.SIGTERM, terminate)
server=ThreadingHTTPServer(('127.0.0.1',8765),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    if not ep.initialize(conn_type='rndis'):raise RuntimeError('Robot connection failed')
    ep.chassis.sub_attitude(freq=5,callback=lambda v: state.update(attitude=list(v)))
    ep.chassis.sub_esc(freq=5,callback=wheel_status)
    ep.robotic_arm.sub_position(freq=5,callback=arm_position)
    if not ep.camera.start_video_stream(display=False,resolution=camera.STREAM_720P):raise RuntimeError('Camera failed')
    while True:
        frame=ep.camera.read_cv2_image(timeout=5,strategy='newest')
        if frame is None:continue
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        tags=[]
        for family,dictionary in dictionaries:
            corners,ids,_=cv2.aruco.detectMarkers(gray,dictionary,parameters=params)
            if ids is None:continue
            cv2.aruco.drawDetectedMarkers(frame,corners,ids)
            for pts,idx in zip(corners,ids.flatten()):
                p=pts.reshape(4,2)
                tags.append({'family':family,'id':int(idx),'center':p.mean(axis=0).tolist(),'corners':p.tolist()})
        ok,encoded=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,80])
        if ok:
            with lock:
                jpeg=encoded.tobytes();state.update(tags=tags,frame_time=time.time(),width=frame.shape[1],height=frame.shape[0])

except Exception as e:
    with lock:state['error']=str(e)
    raise
finally:
    try:ep.camera.stop_video_stream();ep.robotic_arm.unsub_position();ep.chassis.unsub_esc();ep.chassis.unsub_attitude()
    finally:ep.close();server.shutdown()
