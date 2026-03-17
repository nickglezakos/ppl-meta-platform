"""Analyze video frames - find optimal padding for Dlib validation."""
import cv2
import numpy as np
import dlib
import sys

video_path = sys.argv[1] if len(sys.argv) > 1 else "ppl-meta-media/media/4cf362b1-3e05-4e85-81c7-c08a98c7e41b/video/2026/03/c25db3e914666ee9f9059b3605bc7ab6.mp4"

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Video: fps={fps}, total_frames={total}, size={w}x{h}, duration={total/fps if fps>0 else 0:.1f}s")
print()

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
dlib_detector = dlib.get_frontal_face_detector()

# Test multiple padding levels
pad_levels = [0.0, 0.5, 0.75, 1.0, 1.5, 2.0]
headers = ["Tight(0%)"] + [f"Pad{int(p*100)}%" for p in pad_levels[1:]]
print(f"{'Frame':>5}  {'BBox':>20}  {'Size':>7}  " + "  ".join(f"{h:>8}" for h in headers))
print("-" * (45 + 10 * len(pad_levels)))

cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
fn = 0
stats = {p: 0 for p in pad_levels}
haar_total = 0

while fn < total:
    ret, frame = cap.read()
    if not ret:
        break
    if fn % 2 == 0:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        haar_faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        for (x, y, fw, fh) in haar_faces:
            haar_total += 1
            results = []
            for pad_pct in pad_levels:
                pad = int(max(fw, fh) * pad_pct)
                px1 = max(0, x - pad)
                py1 = max(0, y - pad)
                px2 = min(w, x + fw + pad)
                py2 = min(h, y + fh + pad)
                region = gray[py1:py2, px1:px2]
                ok = len(dlib_detector(region, 1)) > 0
                if ok:
                    stats[pad_pct] += 1
                results.append("PASS" if ok else "FAIL")
            
            print(f"{fn:5d}  ({x:3d},{y:3d},{fw:3d},{fh:3d})  {fw:3d}x{fh:3d}  " + "  ".join(f"{r:>8}" for r in results))
    fn += 1

print("-" * (45 + 10 * len(pad_levels)))
print(f"\nSUMMARY: {haar_total} Haar detections total")
for p, label in zip(pad_levels, headers):
    print(f"  {label:>12}: {stats[p]:2d} / {haar_total} pass ({100*stats[p]/max(1,haar_total):.0f}%)")

cap.release()
