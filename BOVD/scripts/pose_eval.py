"""
Evaluate real posture-detection accuracy on a LABELLED image folder (camera frames you recorded with consent).

Folder layout:  <root>/<exam>/<step_id>/correct/*.jpg   and   <root>/<exam>/<step_id>/wrong/*.jpg
Usage:          python scripts/pose_eval.py <root> [--side left]
Writes:         pose_eval_report.json  (TP, TN, FP, FN per exam/step + lists of misclassified files)
Requires OpenCV + MediaPipe + the model (scripts/fetch_models.py).
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from astra.pose import landmarks, quality, rules  # noqa: E402


def main(argv: list[str]) -> int:
    root = Path(argv[0])
    side = argv[argv.index("--side") + 1] if "--side" in argv else "left"
    if not landmarks.status()["ready"]:
        print("MediaPipe model not ready – run scripts/fetch_models.py")
        return 1
    report: dict[str, dict] = {}
    for exam_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        steps = {s["id"]: i for i, s in enumerate(rules.EXAMS[exam_dir.name]["steps"])}
        for step_dir in sorted(p for p in exam_dir.iterdir() if p.is_dir()):
            r = {"tp": 0, "tn": 0, "fp": [], "fn": []}
            for label in ("correct", "wrong"):
                for f in sorted((step_dir / label).glob("*.jpg")):
                    img = quality.decode(base64.b64encode(f.read_bytes()).decode())
                    q = quality.analyse(img)
                    lm = landmarks.detect(q["_img"])
                    h, w = img.shape[:2]
                    ctx = {"L": {p["name"]: p for p in lm} if lm else None, "q": q, "motion": 0.0, "side": side,
                           "aspect": w / h, "state": {}}
                    passed = rules.evaluate(exam_dir.name, steps[step_dir.name], ctx)["passed"]
                    if label == "correct":
                        r["tp" if passed else "fn"] += 1 if passed else 0
                        if not passed:
                            r["fn"].append(f.name)
                    else:
                        if passed:
                            r["fp"].append(f.name)
                        else:
                            r["tn"] += 1
            report[f"{exam_dir.name}/{step_dir.name}"] = r
    Path("pose_eval_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    for k, r in report.items():
        print(f"{k}: TP={r['tp']} TN={r['tn']} FP={len(r['fp'])} FN={len(r['fn'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
