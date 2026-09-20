"""Single-key manual controller. Run in an interactive SSH terminal."""
import curses
import time

from robomaster import robot
from pickup import stop
from robot_lock import acquire_robot_lock


class Controller:
    def __init__(self, ep):
        self.ep = ep
        self.speed = 0.25
        self.motion_until = None
        self.claw_until = None
        self.lift_after_close = False
        self.arm_action = None
        self.message = "Ready. Each movement key gives a short nudge."

    def halt(self):
        self.motion_until = None
        self.claw_until = None
        self.lift_after_close = False
        try:
            stop(self.ep)
        finally:
            self.ep.gripper.pause()
        self.message = "Wheels stopped; claw paused. An active arm move may still finish."

    def tick(self, now):
        if self.motion_until is not None and now >= self.motion_until:
            self.motion_until = None
            stop(self.ep)
        if self.arm_action is not None and self.arm_action.is_completed:
            succeeded = self.arm_action.has_succeeded
            self.arm_action = None
            self.message = "Arm movement complete." if succeeded else "Arm reported failure."
        if self.claw_until is not None and now >= self.claw_until:
            self.claw_until = None
            self.ep.gripper.pause()
            lift = self.lift_after_close
            self.lift_after_close = False
            if lift:
                self.arm_action = self.ep.robotic_arm.move(x=0, y=50)
                self.message = "Claw closed; lifting 5 cm."

    def key(self, key, now):
        if key in (" ", "x", "q"):
            self.halt()
            return key != "q"
        if key in ("+", "=", "-"):
            self.speed = round(max(.1, min(.6, self.speed + (-.05 if key == "-" else .05))), 2)
            return True
        if self.arm_action is not None or self.claw_until is not None:
            self.message = "Arm/claw busy. Space pauses claw and cancels a pending lift."
            return True
        directions = {"w": (1,0,0), "s": (-1,0,0), "a": (0,-1,0),
                      "d": (0,1,0), "j": (0,0,1), "l": (0,0,-1)}
        if key in directions:
            x,y,z = directions[key]
            self.motion_until = now + .20
            if not self.ep.chassis.drive_speed(x=x*self.speed, y=y*self.speed, z=z*30):
                self.halt()
                raise RuntimeError("Chassis command failed")
            self.message = "Moving for 0.2 s; release key to stop after the nudge."
        elif key in ("i", "k", "u", "o"):
            stop(self.ep)
            self.motion_until = None
            x,y = {"i": (0,10), "k": (0,-10), "u": (10,0), "o": (-10,0)}[key]
            self.arm_action = self.ep.robotic_arm.move(x=x, y=y)
            self.message = "Arm nudge: 1 cm."
        elif key in ("v", "c", "g"):
            stop(self.ep)
            self.motion_until = None
            opening = key == "v"
            command = self.ep.gripper.open if opening else self.ep.gripper.close
            if not command(power=30 if opening else 40):
                raise RuntimeError("Claw command failed")
            self.claw_until = now + (1.0 if opening else 1.5)
            self.lift_after_close = key == "g"
            self.message = "Opening claw." if opening else "Closing claw" + (", then lifting 5 cm." if key == "g" else ".")
        return True


def ui(screen, controller):
    screen.nodelay(True)
    screen.keypad(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    while True:
        controller.tick(time.monotonic())
        key = screen.getch()
        if key != -1:
            # Drop buffered keyboard repeats so they cannot run later operations.
            curses.flushinp()
            mapped = {curses.KEY_UP:"w", curses.KEY_DOWN:"s",
                      curses.KEY_LEFT:"a", curses.KEY_RIGHT:"d"}.get(key)
            if key == 3:
                raise KeyboardInterrupt
            if mapped is None and 0 <= key < 256:
                mapped = chr(key).lower()
            if mapped and not controller.key(mapped, time.monotonic()):
                return
        screen.erase()
        lines = ["ROBOPI MANUAL CONTROLLER — no Enter needed",
                 "W/S or up/down: forward/back    A/D or left/right: strafe",
                 "J/L: turn left/right           +/-: adjust drive speed",
                 "I/K: arm up/down 1 cm          U/O: arm forward/back 1 cm",
                 "V: open claw   C: close claw   G: GRAB + LIFT 5 cm",
                 "SPACE or X: stop wheels / pause claw    Q or Ctrl+C: exit",
                 "An already-running arm action may finish after Stop.",
                 f"Drive speed: {controller.speed:.2f} m/s; turn speed: 30 deg/s",
                 "", controller.message]
        height,width = screen.getmaxyx()
        for row,line in enumerate(lines[:max(0,height-1)]):
            screen.addnstr(row,0,line,max(0,width-1))
        screen.refresh()
        time.sleep(.02)


def main():
    with acquire_robot_lock():
        ep = robot.Robot()
        controller = None
        try:
            if not ep.initialize(conn_type="rndis"):
                raise RuntimeError("Robot connection failed")
            controller = Controller(ep)
            controller.halt()
            curses.wrapper(ui, controller)
        finally:
            try:
                if controller is not None:
                    controller.halt()
            finally:
                ep.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Controller exited; stop commands sent.")
