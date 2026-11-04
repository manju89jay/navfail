import importlib.util
import shutil

for name in ("matplotlib", "PIL", "imageio", "imageio_ffmpeg", "numpy", "cv2"):
    print(name, bool(importlib.util.find_spec(name)))
for exe in ("ffmpeg", "avconv"):
    print(exe, shutil.which(exe))
try:
    import imageio_ffmpeg
    print("imageio_ffmpeg exe:", imageio_ffmpeg.get_ffmpeg_exe())
except Exception as e:
    print("imageio_ffmpeg exe: none", e)
