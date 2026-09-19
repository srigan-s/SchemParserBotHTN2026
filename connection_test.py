from robomaster import robot

ep = robot.Robot()
try:
    print('Connecting...', flush=True)
    if not ep.initialize(conn_type='rndis'):
        raise RuntimeError('SDK initialization failed')
    print('ROBOT CONNECTED!', flush=True)
finally:
    ep.close()
print('Connection closed.')
