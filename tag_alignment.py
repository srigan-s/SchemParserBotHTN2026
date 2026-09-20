"""Image-space alignment for one selected AprilTag 36h11; no range estimate."""

import time

import cv2

TARGET_X_FRACTION = 0.5  # Adjust if the claw's grasp axis is offset in the image.
CENTER_TOLERANCE = 0.025
CORRECTION_STEP_M = 0.03
MANUAL_SHIFT_M = 0.05
MAX_CORRECTIONS = 10
FORWARD_STEP_M = 0.10
FINAL_APPROACH_M = 0.15


class TagAligner:
    def __init__(self, ep, drive):
        self.ep = ep
        self.drive = drive
        self.dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
        self.params = (cv2.aruco.DetectorParameters_create()
                       if hasattr(cv2.aruco, "DetectorParameters_create")
                       else cv2.aruco.DetectorParameters())
        self.params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        self.detector = (cv2.aruco.ArucoDetector(self.dictionary, self.params)
                         if hasattr(cv2.aruco, "ArucoDetector") else None)

    def observe(self, expected_id):
        # Discard one frame to avoid using an image buffered during chassis motion.
        self.ep.camera.read_cv2_image(strategy="newest", timeout=None)
        frame = self.ep.camera.read_cv2_image(strategy="newest", timeout=None)
        if frame is None:
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.detector is not None:
            corners, ids, _ = self.detector.detectMarkers(gray)
        else:
            corners, ids, _ = cv2.aruco.detectMarkers(gray, self.dictionary, parameters=self.params)
        if ids is None:
            return None
        matches = [points.reshape(4, 2) for points, tag_id in zip(corners, ids.flatten())
                   if int(tag_id) == expected_id]
        if len(matches) != 1:
            return None
        return float(matches[0][:, 0].mean()) / frame.shape[1] - TARGET_X_FRACTION

    def manual_adjustment(self):
        while True:
            choice = input("Enter to retry camera, r = shift RIGHT 5 cm, "
                           "l = shift LEFT 5 cm, q = abort: ").strip().lower()
            if choice == "q":
                raise KeyboardInterrupt
            if choice == "":
                return 0.0
            if choice in ("r", "l"):
                shift = MANUAL_SHIFT_M if choice == "r" else -MANUAL_SHIFT_M
                self.drive(self.ep, sideways=shift, speed=0.5)
                return shift
            print("Choose r, l, Enter, or q.", flush=True)

    def approach(self, expected_id, distance):
        if distance <= FINAL_APPROACH_M:
            raise ValueError("Approach must include a tracked segment before the final 15 cm")
        tracked_distance = distance - FINAL_APPROACH_M
        lateral = 0.0
        corrections = 0
        previous_error = None
        stalled = 0
        travelled = 0.0
        while travelled < tracked_distance - 1e-8:
            stable = 0
            while stable < 3:
                error = self.observe(expected_id)
                if error is None:
                    stable = 0
                    print(f"Tag 36h11 [{expected_id}] not uniquely visible; robot remains stopped.", flush=True)
                    lateral += self.manual_adjustment()
                    previous_error = None
                    stalled = 0
                    corrections = 0
                    continue
                print(f"Tag {expected_id}: horizontal error {error:+.3f}", flush=True)
                if abs(error) <= CENTER_TOLERANCE:
                    previous_error = None
                    stalled = 0
                    stable += 1
                    time.sleep(0.1)
                    continue
                stable = 0
                if previous_error is not None:
                    stalled = stalled + 1 if abs(error) >= abs(previous_error) - 0.005 else 0
                if corrections >= MAX_CORRECTIONS or stalled >= 3:
                    print("Alignment isn't improving; choose a manual sideways shift or retry.", flush=True)
                    lateral += self.manual_adjustment()
                    previous_error = None
                    stalled = 0
                    corrections = 0
                    continue
                # SDK body +y is right; slide toward the tag without changing heading.
                step = CORRECTION_STEP_M if error > 0 else -CORRECTION_STEP_M
                print(f"Shifting {'RIGHT' if step > 0 else 'LEFT'} 3 cm toward tag {expected_id}...", flush=True)
                self.drive(self.ep, sideways=step, speed=0.5)
                lateral += step
                corrections += 1
                previous_error = error
            step = min(FORWARD_STEP_M, tracked_distance - travelled)
            self.drive(self.ep, distance=step)
            travelled += step
        # Finish from the 45 cm point without requiring the tag near the claw.
        print(f"Tag {expected_id} approach aligned; driving final 15 cm without vision...", flush=True)
        self.drive(self.ep, distance=FINAL_APPROACH_M)
        return lateral
