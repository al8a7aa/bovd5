"""يبني كل الوثائق: الإنجليزية في deliverables/English، والعربية في deliverables وجذر المشروع.
Run: python scripts/build_all.py"""
import shutil
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
D = R / "deliverables"
run = lambda s: subprocess.run([sys.executable, str(R / "scripts" / s)], check=True)  # noqa: E731
run("build_deliverables.py")
(D / "English").mkdir(exist_ok=True)
for f in ("README.md", "SOURCES.md", "RISK_REGISTER.md", "TRACEABILITY.md", "PROJECT_STATUS.md", "PRIVACY.md"):
    shutil.move(str(R / f), str(D / "English" / f))
for f in ("CODE_EXPLAINED.docx", "CODE_EXPLAINED.md", "ISO_STANDARDS_ALIGNMENT.docx", "BOVD_Presentation.pptx"):
    shutil.move(str(D / f), str(D / "English" / f))
run("build_docs_ar.py")
run("build_presentation_ar.py")
run("build_demo_deck.py")
# The English README is the main one (submission material must be in English); the Arabic one is README_AR.md.
shutil.copy(str(D / "English" / "README.md"), str(R / "README.md"))
print("all deliverables built")
