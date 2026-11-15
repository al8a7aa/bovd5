"""
Build the 30-second project demo video (NASA Space Apps: video demos must be 30 seconds or less).

A fast tour of every slide of the full presentation and every page of the app, with short English captions
(no voice, so no subtitles are needed). Frames are composed with Pillow/OpenCV and encoded with ffmpeg.

Inputs : deliverables/img/video/Slide*.PNG (full deck exported at 1920x1080) and app_*.png (app screenshots)
Run    : python scripts/build_demo_video.py
Output : deliverables/English/BOVD_Demo_30s.mp4
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "deliverables" / "img" / "video"
OUT = ROOT / "deliverables" / "English" / "BOVD_Demo_30s.mp4"
W, H, FPS, MAX_SECONDS = 1920, 1080, 30, 30.0
FONT = "C:/Windows/Fonts/segoeuib.ttf"

# (image, seconds, caption) – S<n> = slide n of the full presentation, app_<page> = app screenshot
TIMELINE = [
    ("S2", 2.0, ""), ("S1", 1.3, ""), ("S3", 1.5, ""), ("S4", 1.3, ""), ("S5", 1.0, ""),
    ("app_login", 0.45, "Sign in – 5 roles, English and Arabic"),
    ("app_dashboard", 0.8, "Dashboard: status, 0–20 score, 3D body"),
    ("app_body3d", 0.6, "Clickable 3D body"),
    ("app_measure", 0.5, "Guided measurement in 0 g"),
    ("app_alerts", 0.6, "Why · next step · who to contact"),
    ("app_charts", 0.45, "Trends vs personal baseline"),
    ("app_history", 0.4, "Measurement history with sources"),
    ("S6", 0.9, ""),
    ("app_cdss", 0.7, "Smart Doctor + NASA-grounded AI assistant"),
    ("S7", 0.9, ""),
    ("app_radiation", 0.45, "Personal radiation dose map"),
    ("app_spe", 0.6, "Solar storm mode: go to shelter"),
    ("app_vision", 0.4, "Eye check (SANS)"),
    ("app_urine", 0.4, "Urine and hydration"),
    ("app_coach", 0.4, "Exercise and nutrition coach"),
    ("app_crew", 0.4, "Crew harmony"),
    ("app_voice", 0.4, "Voice check (experimental)"),
    ("app_connection", 0.4, "Connection with home"),
    ("app_schedule", 0.45, "Mission, routine and landing"),
    ("app_simulate", 0.4, "Environment simulation"),
    ("app_posecheck", 0.4, "Camera posture check"),
    ("S8", 0.9, ""),
    ("app_surgeon", 0.6, "Flight surgeon on Earth – delayed link"),
    ("S9", 0.9, ""),
    ("app_nasa_glucose", 0.7, "Real NASA data – OSDR OSD-575"),
    ("S10", 0.9, ""),
    ("app_blackbox", 0.45, "Tamper-proof black box"),
    ("app_settings", 0.4, "Consent, privacy and accessibility"),
    ("app_help", 0.4, "Guided tour and help"),
    ("S11", 0.9, ""), ("S12", 1.0, ""), ("S13", 0.9, ""), ("S14", 0.8, ""), ("S15", 0.7, ""), ("S16", 1.4, ""),
]


def load(name: str) -> Image.Image:
    f = SRC / (f"Slide{name[1:]}.PNG" if name.startswith("S") and name[1:].isdigit() else f"{name}.png")
    return Image.open(f).convert("RGB").resize((W, H), Image.LANCZOS)


def with_caption(img: Image.Image, text: str) -> Image.Image:
    if not text:
        return img
    img = img.copy()
    d = ImageDraw.Draw(img, "RGBA")
    font = ImageFont.truetype(FONT, 46)
    tw = d.textlength(text, font=font)
    x, y, pad = 60, H - 150, 26
    d.rounded_rectangle((x, y, x + tw + 2 * pad, y + 92), radius=22, fill=(11, 31, 58, 235), outline=(0, 180, 216, 255), width=3)
    d.text((x + pad, y + 18), text, font=font, fill=(255, 255, 255, 255))
    d.rounded_rectangle((W - 250, 40, W - 50, 110), radius=18, fill=(11, 31, 58, 220))
    d.text((W - 225, 48), "BÖVD", font=ImageFont.truetype(FONT, 44), fill=(0, 180, 216, 255))
    return img


def main() -> None:
    total = sum(t for _, t, _ in TIMELINE)
    scale = min(1.0, (MAX_SECONDS - 0.2) / total)  # keep the video under 30 s
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg not found on PATH")
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
           "-metadata", "title=BÖVD – NASA Space Apps 2026 demo",
           "-metadata", "comment=AI disclosure: AI assistants helped write code, documents and this video script; screenshots are of the real app.",
           "-movflags", "+faststart", str(OUT)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frames = 0
    for name, secs, cap in TIMELINE:
        base = cv2.cvtColor(np.asarray(with_caption(load(name), cap)), cv2.COLOR_RGB2BGR)
        n = max(1, round(secs * scale * FPS))
        for k in range(n):
            z = 1.0 + 0.035 * k / max(1, n - 1)  # gentle push-in
            cw, ch = int(W / z), int(H / z)
            x0, y0 = (W - cw) // 2, (H - ch) // 2
            frame = cv2.resize(base[y0:y0 + ch, x0:x0 + cw], (W, H), interpolation=cv2.INTER_LINEAR)
            proc.stdin.write(frame.tobytes())
            frames += 1
    proc.stdin.close()
    proc.wait()
    print(f"saved {OUT}  {frames} frames = {frames / FPS:.2f} s")


if __name__ == "__main__":
    main()
