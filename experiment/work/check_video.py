import cv2

cap = cv2.VideoCapture("experiment/work/navfail-demo.mp4")
frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"frames={frames} fps={fps} size={w}x{h} duration_s={frames / fps:.1f}")
for name, idx in (("mid_failure", 300), ("chart", 1250), ("closing", 1500)):
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, frame = cap.read()
    print(name, ok)
    if ok:
        cv2.imwrite(f"experiment/work/video_frames/check_{name}.png", frame)
cap.release()
