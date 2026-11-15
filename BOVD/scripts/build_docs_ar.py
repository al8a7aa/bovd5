"""
بناء الوثائق العربية (من اليمين لليسار) بـ python-docx + ملفات Markdown العربية.
Run: python scripts/build_docs_ar.py
الخط العربي: Sakkal Majalla (مثبّت مع Windows)؛ الأكواد بخط Consolas من اليسار لليمين.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import content as CE  # noqa: E402
import content_ar as A  # noqa: E402
from build_deliverables import FOLDER_TREE, INTEXT, MODULES as MOD_EN, _field, _shade  # noqa: E402

from astra import config  # noqa: E402
from astra.server import ROUTES, VERSION  # noqa: E402

OUT = ROOT / "deliverables"
IMG = OUT / "img"
AR_FONT, LAT_FONT = "Sakkal Majalla", "Calibri"
NAVY, CYAN, WHITE, TEAL = RGBColor(0x0B, 0x1F, 0x3A), RGBColor(0x00, 0xB4, 0xD8), RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0x00, 0x7A, 0x99)
REFS = config.references()
STD = config.load("standards")["register"]
TODAY = date.today().isoformat()


def cite(*keys: str) -> str:
    return "(" + "; ".join(INTEXT[k] for k in keys) + ")"


def _set(el, tag: str, **attrs: str):
    child = el.find(qn(tag))
    if child is None:
        child = OxmlElement(tag)
        el.append(child)
    for k, v in attrs.items():
        child.set(qn(k), v)
    return child


def rtl_par(par, rtl: bool = True) -> None:
    ppr = par._p.get_or_add_pPr()
    if rtl:
        _set(ppr, "w:bidi")


def rtl_run(run, size: float = 15, bold: bool = False, color: RGBColor | None = None, rtl: bool = True) -> None:
    rpr = run._r.get_or_add_rPr()
    _set(rpr, "w:rFonts", **{"w:ascii": LAT_FONT, "w:hAnsi": LAT_FONT, "w:cs": AR_FONT})
    if bold:
        run.bold = True
        _set(rpr, "w:bCs")
    if color is not None:
        run.font.color.rgb = color
    run.font.size = Pt(size * 0.8)  # Sakkal Majalla Arabic looks smaller than Calibri at equal size
    _set(rpr, "w:szCs", **{"w:val": str(int(size * 2))})
    if rtl:
        _set(rpr, "w:rtl")


class DocAR:
    def __init__(self, title: str, subtitle: str, header: str) -> None:
        self.d = Document()
        self.fig = self.tab = 0
        self.heads: list[tuple[int, str]] = []
        st = self.d.styles
        n = st["Normal"]
        n.font.name = LAT_FONT
        n.font.size = Pt(11)
        _set(n.element.get_or_add_rPr(), "w:rFonts", **{"w:cs": AR_FONT})
        _set(n.element.get_or_add_rPr(), "w:szCs", **{"w:val": "30"})
        for lvl, size in ((1, 24), (2, 19), (3, 16)):
            h = st[f"Heading {lvl}"]
            h.font.name = LAT_FONT
            h.font.bold = True
            h.font.size = Pt(size * 0.75)
            h.font.color.rgb = NAVY if lvl != 2 else TEAL
            rpr = h.element.get_or_add_rPr()
            _set(rpr, "w:rFonts", **{"w:ascii": LAT_FONT, "w:hAnsi": LAT_FONT, "w:cs": AR_FONT})
            _set(rpr, "w:szCs", **{"w:val": str(size * 2)})
            _set(rpr, "w:bCs")
            h.paragraph_format.space_before = Pt(14 if lvl == 1 else 10)
            h.paragraph_format.space_after = Pt(6)
            h.paragraph_format.keep_with_next = True
        sec = self.d.sections[0]
        sec.page_width, sec.page_height = Cm(21), Cm(29.7)
        sec.left_margin = sec.right_margin = Cm(2.2)
        sec.different_first_page_header_footer = True
        _set(sec._sectPr, "w:bidi")
        hp = sec.header.paragraphs[0]
        rtl_par(hp)
        rtl_run(hp.add_run(header), 11, color=RGBColor(0x55, 0x66, 0x77))
        fp = sec.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rtl_par(fp)
        rtl_run(fp.add_run("تحدي ناسا Space Apps 2026 · صفحة "), 11)
        _field(fp, "PAGE", "1")
        rtl_run(fp.add_run(" من "), 11)
        _field(fp, "NUMPAGES", "1")
        uf = OxmlElement("w:updateFields")
        uf.set(qn("w:val"), "true")
        self.d.settings.element.append(uf)
        self._cover(title, subtitle)

    # ------------------------------------------------------------ building blocks
    def _cover(self, title: str, subtitle: str) -> None:
        t = self.d.add_table(rows=1, cols=1)
        _set(t._tbl.tblPr, "w:bidiVisual")
        c = t.rows[0].cells[0]
        _shade(c, "0B1F3A")
        lines = [("BÖVD 🛰", 44, WHITE, True, 60), (title, 30, CYAN, True, 0), (subtitle, 17, WHITE, False, 0),
                 (f"تحدي ناسا Space Apps 2026 · برمجيات مراقبة صحة رواد الفضاء في المهمات الفضائية", 13, WHITE, False, 0),
                 (f"الإصدار {VERSION} · {TODAY}", 13, WHITE, False, 0)]
        for i, (txt, size, col, bold, before) in enumerate(lines):
            p = c.paragraphs[0] if i == 0 else c.add_paragraph()
            rtl_par(p)
            p.paragraph_format.space_before = Pt(before)
            rtl_run(p.add_run(txt), size, bold, col)
        c.paragraphs[-1].paragraph_format.space_after = Pt(60)
        self.d.add_paragraph()
        box = self.d.add_table(rows=1, cols=1)
        _set(box._tbl.tblPr, "w:bidiVisual")
        bc = box.rows[0].cells[0]
        _shade(bc, "FFF4E0")
        bp = bc.paragraphs[0]
        rtl_par(bp)
        rtl_run(bp.add_run("بيان الأمانة: "), 15, True)
        rtl_run(bp.add_run(A.HONESTY), 15)
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        self.h("المحتويات", 1, toc=False)
        self.toc_par = self.d.add_paragraph()
        rtl_par(self.toc_par)
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def h(self, text: str, lvl: int = 1, toc: bool = True) -> None:
        p = self.d.add_heading("", lvl)
        rtl_par(p)
        rtl_run(p.add_run(text), {1: 24, 2: 19, 3: 16}[lvl], True, NAVY if lvl != 2 else TEAL)
        if toc and lvl <= 2:
            self.heads.append((lvl, text))

    def p(self, text: str, lead: str | None = None, size: float = 15) -> None:
        par = self.d.add_paragraph()
        rtl_par(par)
        if lead:
            rtl_run(par.add_run(lead), size, True)
        rtl_run(par.add_run(text), size)

    def bullets(self, items: list[str]) -> None:
        for it in items:
            par = self.d.add_paragraph(style="List Bullet")
            rtl_par(par)
            rtl_run(par.add_run(it), 15)

    def code(self, text: str) -> None:
        for line in text.strip("\n").split("\n"):
            par = self.d.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            par.paragraph_format.space_after = Pt(0)
            r = par.add_run(line)
            r.font.name, r.font.size, r.font.color.rgb = "Consolas", Pt(8.5), NAVY

    def caption(self, kind: str, text: str) -> None:
        par = self.d.add_paragraph()
        rtl_par(par)
        if kind == "fig":
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            self.fig += 1
            rtl_run(par.add_run("الشكل "), 13, True)
            _field(par, "SEQ Figure \\* ARABIC", str(self.fig))
        else:
            self.tab += 1
            rtl_run(par.add_run("الجدول "), 13, True)
            _field(par, "SEQ Table \\* ARABIC", str(self.tab))
        rtl_run(par.add_run(": " + text), 13)

    def table(self, header: list[str], rows, caption: str, widths: list[float] | None = None, size: float = 12, ltr_cols: tuple[int, ...] = ()) -> None:
        self.caption("tab", caption)
        t = self.d.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set(t._tbl.tblPr, "w:bidiVisual")
        for i, htxt in enumerate(header):
            c = t.rows[0].cells[i]
            _shade(c, "0B1F3A")
            rtl_par(c.paragraphs[0])
            rtl_run(c.paragraphs[0].add_run(htxt), size, True, WHITE)
        for k, row in enumerate(rows):
            cells = t.add_row().cells
            for i, v in enumerate(row):
                sv = str(v)
                par = cells[i].paragraphs[0]
                ltr = i in ltr_cols
                rtl_par(par, not ltr)
                if ltr:
                    par.alignment = WD_ALIGN_PARAGRAPH.LEFT
                rtl_run(par.add_run(sv), size, rtl=not ltr)
                if sv in ("منخفض", "green"):
                    _shade(cells[i], "DFF7E8")
                elif sv in ("متوسط", "yellow"):
                    _shade(cells[i], "FFF1D6")
                elif sv in ("مرتفع", "red"):
                    _shade(cells[i], "FFE0E0")
                elif k % 2:
                    _shade(cells[i], "F2F7FB")
        if widths:
            t.autofit = False
            for i, w in enumerate(widths):
                t.columns[i].width = Cm(w)
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)
        self.d.add_paragraph()

    def image(self, name: str, caption: str, width_cm: float = 14) -> None:
        f = IMG / name
        if f.exists():
            self.d.add_picture(str(f), width=Cm(width_cm))
            self.d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            self.caption("fig", caption)

    def references(self) -> None:
        self.h("المراجع", 1)
        self.p("المراجع مكتوبة بصيغة APA 7 بلغتها الأصلية (الإنجليزية) كما تقتضي قواعد التوثيق، ويسبق كل مرجع وصف عربي لمحتواه.", size=14)
        items = sorted(((k, v) for k, v in REFS.items() if k != "clinical_default"), key=lambda kv: kv[1]["apa"].replace("National Aeronautics and Space Administration", "NASA").lower())
        for key, v in items:
            pa = self.d.add_paragraph()
            rtl_par(pa)
            pa.paragraph_format.space_after = Pt(0)
            rtl_run(pa.add_run("◂ " + A.REF_AR.get(key, "")), 14, True, TEAL)
            pe = self.d.add_paragraph()
            pe.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pe.paragraph_format.left_indent = Cm(1.27)
            pe.paragraph_format.first_line_indent = Cm(-1.27)
            r = pe.add_run(f"{v['apa']} {v['url']}".strip())
            r.font.size = Pt(9.5)

    def _finish_toc(self) -> None:
        tp = self.toc_par

        def fc(par, kind: str) -> None:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
            par.add_run()._r.append(el)

        fc(tp, "begin")
        it = OxmlElement("w:instrText")
        it.set(qn("xml:space"), "preserve")
        it.text = 'TOC \\o "1-2" \\h \\z \\u'
        tp.add_run()._r.append(it)
        fc(tp, "separate")
        anchor, last = tp._p, None
        for lvl, text in self.heads:
            np_ = self.d.add_paragraph()
            rtl_par(np_)
            np_.paragraph_format.right_indent = Cm(0.8 * (lvl - 1))
            np_.paragraph_format.space_after = Pt(1)
            rtl_run(np_.add_run(text), 15 if lvl == 1 else 13.5, lvl == 1)
            anchor.addnext(np_._p)
            anchor, last = np_._p, np_
        fc(last or tp, "end")

    def save(self, path: Path) -> None:
        self._finish_toc()
        self.d.save(str(path))


SNIP = {m[0]: m[3] for m in MOD_EN}


# ====================================================================== أ. شرح الكود
def build_code_ar() -> None:
    D = DocAR("شرح الكود", "البنية، الوحدات البرمجية، قواعد انعدام الجاذبية، الميزات التسع، أمثلة محلولة، الواجهة البرمجية، الاختبارات",
              "BÖVD · شرح الكود · نموذج أولي لهاكاثون – ليس جهازًا طبيًا")
    D.h("1. نظرة عامة ودليل التشغيل", 1)
    D.p("BÖVD نموذج أولي لدعم القرار الصحي لرواد الفضاء، يعمل دون اتصال بالإنترنت وعلى جهاز واحد: خادم بايثون من المكتبة القياسية "
        "(‎127.0.0.1:8765‎) يقدّم واجهة HTML وجافاسكربت. لا سحابة ولا أجهزة ولا حساسات. المدخلات: لوحة المفاتيح والفأرة، والميكروفون والكاميرا اختياريًا "
        "(تُعالَج على الجهاز)، واستيراد الملفات، وبيانات ناسا المفتوحة عبر محمّل خاص، ومولّد بيانات مُصطنعة موسومة بوضوح " + cite("osdr", "nasa_std_3001_v1") + ".")
    D.p("اقترح الملف الأصلي React و FastAPI؛ وبناءً على طلب الفريق نُفّذت الواجهة بـ HTML وكل المنطق ببايثون، ويُشغَّل من ملف ‎.bat‎. طبقات البنية لم تتغير.",
        "اختيار التنفيذ: ")
    D.h("1.1 التشغيل", 2)
    D.bullets(["Windows: ثبّت Python 3.10 أو أحدث (فعّل «Add to PATH»)، فك الضغط، ثم انقر نقرًا مزدوجًا على start.bat. يفتح المتصفح تلقائيًا.",
               "macOS/Linux: ‎./start.sh‎ · Docker: ‎docker compose up‎ (على 127.0.0.1 فقط).",
               "الحسابات التجريبية: astro1 و astro3 و cmo1 و bhs1 و surgeon1 و research1 – كلمة المرور astra2026 (للنموذج فقط).",
               "إذا توفّر الإنترنت يثبّت start.bat مكتبة cryptography الاختيارية؛ وإلا يُستخدم تشفير AES-256-GCM المكتوب ببايثون والمُتحقق منه.",
               "الاختبارات: run_tests.bat (pytest + تقرير التغطية). إعادة البيانات التجريبية: reset_data.bat."])
    D.h("1.2 عرض المحكّمين في دقيقتين", 2)
    D.bullets(A.DEMO)
    D.image("dashboard.png", "اللوحة الرئيسية: حلقة الحالة (الدرجة المركّبة 0–20)، خريطة الجسم التفاعلية، أحدث القراءات مع شارة المصدر.")

    D.h("2. البنية المعمارية", 1)
    D.p("وحدة برمجية لكل طبقة كما في الملف الأصلي: الإدخال ← التحقق ← التخزين ← المحرك ← التنبيهات ← الواجهة البرمجية ← واجهة المستخدم. "
        "المنطق السريري (المحرك) ومنطق الإنذار (التنبيهات) والتنسيق (الخدمة) منفصلة، ليُتحقق من كل منها مستقلًا (IEC 62304 §5.3).")
    D.code("""inputs: keyboard · mic* · webcam* · files · OSDR loader · synthetic
        (* features only – raw media never stored)
   ▼  ingest/ → validation.py
   ▼  fhir.py + storage.py   SQLite WAL · AES-256-GCM · black box
   ▼  engine.py              baseline → Earth range → trends → score → WHY
   ▼  alerts.py              3 priorities · escalation · delay queue
   ▼  server.py              REST + polling · OpenAPI · RBAC
   ▼  web/                   HTML UI · AR/EN · PWA""")
    D.caption("fig", "البنية الطبقية (برمجيات فقط، دون اتصال، شبكة محلية).")
    D.h("2.1 شجرة المجلدات", 2)
    D.code(FOLDER_TREE.replace("ASTRA-Health", "BOVD"))

    D.h("3. شرح الوحدات البرمجية واحدة واحدة", 1)
    for name, desc, std in A.MODULES:
        D.h(name, 2)
        D.p(desc)
        D.p(std, "البنود المعيارية (توافق): ")
        D.code(SNIP.get(name, ""))

    D.h("4. قواعد انعدام الجاذبية وموضعها في الكود", 1)
    D.p("انتقال نحو 2 لتر من السوائل نحو الرأس وغياب وضعية الوقوف يغيّران معنى «الطبيعي» أثناء الرحلة "
        + cite("hrp_oi_2015", "nasa_cv_risk") + "؛ كما ينام الرواد أقل أثناء الرحلة " + cite("barger_2014") + ".")
    D.table(["القاعدة", "الموضع في الكود", "السلوك"], A.MICRO, "قواعد انعدام الجاذبية ← الكود.", [4.5, 6, 6.5], ltr_cols=(1,))

    D.h("5. مصدر البيانات", 1)
    D.p("كل قيمة تحمل شارة مصدر: حقيقية REAL (رقم مجموعة البيانات) | مُصطنعة SYNTHETIC (السيناريو) | مُدخلة USER-ENTERED (المستخدم). لا تُعرض البيانات المُصطنعة أبدًا كقراءات حقيقية.")
    D.table(["المصدر", "الحالة في النموذج", "الحقول", "التحويل"], [
        ("مستودع ناسا OSDR " + cite("osdr"), "المحمّل وملف الربط جاهزان؛ لا توجد بيانات مضمّنة – يجب التحميل", "الأعمدة المحددة في mapping.json", "CSV ← تحقق ← قراءة FHIR، المصدر REAL(OSD-n)"),
        ("بوابة ناسا لعلوم الحياة " + cite("nlsp"), "تحميل يدوي بعد طلب البيانات", "كما سبق", "نفس طريقة الربط"),
        ("تقارير أدلة برنامج أبحاث الإنسان", "تُستخدم دليلًا للعتبات", "—", "مراجع في config/thresholds.json"),
        ("مولّد البيانات المُصطنعة", "10 سيناريوهات", "كل المؤشرات والميزات", "وسم SYNTHETIC(<السيناريو>)")], "مصادر البيانات.", [4, 4.5, 3.5, 5])

    D.h("6. الميزات التسع (F1–F9)", 1)
    for fid, title, mod, text, cites in A.FEATURES:
        D.h(f"{fid} · {title}", 2)
        D.p(mod, "الوحدة: ")
        D.p(text + f" ({cites}).")
    D.image("vision.png", "F2 عين الحقيقة: معايرة الشاشة، لوحة logMAR، شبكة أمسلر، الأعراض.")
    D.image("radiation.png", "F5 خريطة الإشعاع الشخصية: الجرعة التراكمية مقابل الحد وخريطة الموئل الحرارية.")

    D.h("7. أمثلة محلولة لمحرك القواعد", 1)
    D.h("7.1 عدم تحمّل الانتصاب بعد الهبوط على المريخ", 2)
    D.p("يهبط أحد أفراد الطاقم على المريخ (حدث «هبوط» ← mars_surface). يبدأ بروتوكول انتقال الجاذبية (تحميل السوائل، الملابس الضاغطة، اختبار الوقوف جالسًا عند +2 ساعة و+24 ساعة). "
        "اختبار الوقوف: نبض الجلوس 62 والانقباضي 112؛ نبض الوقوف 98 والانقباضي 98 ← ارتفاع النبض 36 أكبر من 30 ← أصفر؛ وإذا كان الانقباضي واقفًا أقل من 90 ← أحمر. "
        "«لماذا»: الخطر «مجالات الجاذبية»، الإجراء «لا وقوف أو مهام خارجية دون مساعدة، أبلغ الضابط الطبي»، البروتوكول «الدوار بعد الهبوط» " + cite("hrp_oi_2015") + ".")
    D.h("7.2 دين النوم لخمس ليالٍ", 2)
    D.p("خط الأساس في بداية الرحلة 6.1 ± 0.5 ساعة (0 g). الليالي: 5.4، 5.2، 5.0، 4.8. القيمة 4.8 حمراء أرضيًا (أقل من 5 ساعات) وتحت النطاق الشخصي؛ "
        "وثلاث ليالٍ قصيرة متتالية تطلق قاعدة الاتجاه ← أحمر، وترتفع الدرجة المركّبة، ويُقترح بروتوكول الأرق مع معيار توقف قبل المهام الحرجة " + cite("barger_2014", "ochmo_sleep_2023") + ".")
    D.h("7.3 الاحتماء من العاصفة الشمسية", 2)
    D.p("معدل الخلفية في العبور إلى المريخ 1.8 ملي سيفرت/يوم (مُصطنع). معامل العاصفة ×50 ← 90 ملي سيفرت/يوم في المختبر (تدريع 1.0) مقابل 27 في ملجأ جدار الماء (0.3). "
        "لعاصفة مدتها 12 ساعة تكون الجرعة الموفرة المقدّرة (90 − 27) × 0.5 = 31.5 ملي سيفرت. يُرفع تنبيه عالي الأولوية لكل فرد مع عدّ تنازلي وقائمة تحقق " + cite("george_2024", "nasa_artemis_rad") + ".")
    D.image("measure.png", "نتيجة سلسلة القياس: الحالة، «لماذا»، الخطوة التالية، جهة الاتصال، التصعيد والمتابعة.", 12)

    D.h("8. الواجهة البرمجية (API)", 1)
    rows = [(m, pat.pattern.strip("^$").replace("(?P<", "{").replace(">[^/]+)", "}"), perm or "عام", doc[:70]) for m, pat, _, perm, doc in ROUTES]
    D.table(["الطريقة", "المسار", "الصلاحية", "الغرض"], rows, "واجهة REST (مولّدة من جدول المسارات؛ وصف OpenAPI على ‎/api/openapi.json‎).", [1.6, 5.5, 2.8, 7], 10.5, ltr_cols=(0, 1, 3))

    D.h("9. الاختبارات", 1)
    D.p("140 اختبارًا آليًا (pytest): اختبارات وحدات لكل طبقة، و33 حالة لحدود العتبات، و10 اختبارات سيناريو (واحد لكل سيناريو مُصطنع)، واختبار العبث بسلسلة التجزئة، "
        "و8 اختبارات لسحب الموافقة واختبار لإطفاء الميزة تثبت عدم حفظ أي شيء، واختبارات الصلاحيات، واختبار تطابق التشفير مع OpenSSL. "
        "التغطية (مقيسة بسكربت من المكتبة القياسية scripts/coverage_lite.py): المحرك والتحقق والميزات نحو 97٪، والحزمة كاملة نحو 88٪. "
        "الفحوص الثابتة: ruff (مع قواعد الأمان) نظيف، و mypy الصارم نظيف، وتشغيل الواجهة في متصفح آلي دون أخطاء.")
    D.h("10. كيف تضيف وتطوّر", 1)
    D.bullets(["مؤشر جديد: أضفه في config/thresholds.json (LOINC، UCUM، المنطقة، القواعد، المرجع) – يلتقطه المحرك والواجهة تلقائيًا.",
               "بروتوكول جديد: أضف شجرة في config/cdss_protocols.json؛ والاختبار الآلي يفرض معايير التوقف والمواد المعتمدة.",
               "جهاز جديد (مثل محلل بول آلي): أرسل البيانات بمخطط JSON الموثّق إلى ‎/api/urine‎.",
               "سياق جاذبية جديد: أضفه في config/gravity_contexts.json مع قيمة g ومدى التأخير.",
               "لغة جديدة: أضف قاموسًا في web/i18n.js وحقول _xx في الإعدادات."])
    D.h("11. مسرد المصطلحات عربي–إنجليزي", 1)
    D.table(["العربية", "English"], [(ar, en) for en, ar in CE.GLOSSARY], "مسرد المصطلحات.", [9, 7], ltr_cols=(1,))
    D.references()
    D.save(OUT / "CODE_EXPLAINED_AR.docx")


# ====================================================================== ب. مواءمة المعايير
def build_iso_ar() -> None:
    D = DocAR("مواءمة المعايير الدولية (ISO)", "صُمّم بما يتماشى مع المعايير – دون تدقيق أو اعتماد رسمي",
              "BÖVD · مواءمة المعايير الدولية · نموذج أولي لهاكاثون – ليس جهازًا طبيًا")
    D.h("1. إخلاء المسؤولية", 1)
    D.p(A.HONESTY)
    D.h("2. الملخص التنفيذي", 1)
    D.p(f"يربط BÖVD عدد {len(STD)} معيارًا بمواضع محددة في الكود وبالاختبارات والأدلة، ويذكر لكل معيار الفجوة التي يتطلبها الاعتماد الرسمي. "
        "تتبع إدارة المخاطر معيار ISO 14971 بـ 25 خطرًا محددًا؛ وتتبع الإنذارات مبادئ IEC 60601-1-8؛ وتتبع البيانات HL7 FHIR R4 و LOINC و UCUM؛ "
        "وتتبع ضوابط الأمن والخصوصية ISO/IEC 27002 و ISO 27799 و ISO/IEC 29100. المحتوى الطبي الفضائي موثّق بمعيار NASA-STD-3001 وأدلة برنامج أبحاث الإنسان "
        + cite("nasa_std_3001_v1", "nasa_std_3001_v2", "hrp_hazards") + ".")
    D.h("3. النطاق والاستخدام المقصود وغير المقصود", 1)
    D.bullets(["الاستخدام المقصود: دعم القرار والتدريب على المراقبة الذاتية للطاقم في بيئات الهاكاثون والمحاكاة؛ يشرح الحالة والخطوة التالية وجهة الاتصال.",
               "المستخدمون: رائد الفضاء، الضابط الطبي للطاقم، أخصائي الصحة السلوكية، الجراح الجوي، الباحث.",
               "البيئات: محطة الفضاء الدولية (0 g)، قاعدة القمر (1/6 g)، العبور إلى المريخ (0 g)، سطح المريخ (3/8 g)، المركبة المتنقلة المضغوطة.",
               "غير مقصود: التشخيص، قرارات العلاج، وصف الأدوية، الاستخدام التشغيلي في الرحلات، استبدال حكم الجراح الجوي، قياس الضغط داخل الجمجمة."])
    D.h("4. سجل المعايير", 1)
    D.table(["المعيار", "العنوان", "المجال", "الموضع في الكود", "الدليل"],
            [(s["id"], s["title_ar"], s["area_ar"], s["where"], s["evidence_ar"]) for s in STD], "سجل المعايير (البنود التفصيلية في القسم 5).", [3, 4.4, 2.6, 3.4, 3.4], 11, ltr_cols=(0, 3))
    D.h("5. المعايير معيارًا معيارًا", 1)
    for s in STD:
        D.h(s["id"], 2)
        D.p(s["title_ar"] + ".", "العنوان: ")
        D.p(s["clauses_ar"], "محور المتطلبات: ")
        D.p(f"{s['evidence_ar']} – {s['where']}.", "كيف طُبّق: ")
        D.p(s["gap_ar"], "الفجوات / ما يتطلبه الاعتماد: ")
    D.h("6. تصنيف سلامة البرمجيات وفق IEC 62304", 1)
    D.p("الفئة المقترحة B: قد يُسهم خلل في البرنامج في حالة خطرة تؤدي إلى إصابة غير خطيرة (مثل اتجاه أصفر لم يُكتشف)، "
        "بينما تُضبط مسارات الإصابة الخطيرة بضوابط خارجية: الضابط الطبي والجراح الجوي يبقيان في الحلقة، والنتائج الحمراء تُصعَّد دائمًا، والبرنامج لا يصف علاجًا أبدًا. "
        "تنطبق الفئة C لو استُخدم البرنامج لقرارات علاج مستقلة، وهذا خارج النطاق صراحةً.")
    D.h("7. سجل المخاطر وفق ISO 14971", 1)
    D.table(["الرقم", "الحالة الخطرة", "الضرر", "ش", "ح", "ضابط الخطر", "الموضع", "التحقق", "المتبقي"], A.RISKS,
            "سجل المخاطر (ش = الشدة 1–5، ح = الاحتمال 1–5، قبل الضوابط).", [1, 3.2, 2, 0.6, 0.6, 3.6, 2.2, 2.6, 1.4], 9.5, ltr_cols=(0, 6, 7))
    D.h("8. سيناريوهات الاستخدام وفق IEC 62366-1", 1)
    D.table(["الرقم", "سيناريو الاستخدام", "الاستجابة التصميمية"], A.USE_SCENARIOS, "سيناريوهات الاستخدام، ومنها الطفو والقفازات.", [1.2, 7, 8.5])
    D.h("9. تصميم الإنذارات (بأسلوب IEC 60601-1-8)", 1)
    D.table(["الأولوية", "المُطلِق", "الإشارة", "التكرار حتى الإقرار", "التصعيد", "إلى الأرض"], A.ALARMS, "جدول تصميم الإنذارات.", [2, 3, 3.6, 2.5, 3, 3])
    D.image("alerts.png", "شاشة التنبيهات: لون الأولوية، المستوى، عدد التكرارات، الإقرار، «لماذا».")
    D.h("10. الضوابط الأمنية", 1)
    D.table(["مجال الضابط", "التطبيق", "المرجع"], A.SECURITY, "ضوابط الأمن والخصوصية.", [3.5, 9, 4], ltr_cols=(2,))
    D.h("11. جدول مخاطر الذكاء الاصطناعي (ISO/IEC 23894)", 1)
    D.table(["مكوّن الذكاء الاصطناعي", "الخطر", "التخفيف في النموذج", "تحقق إضافي"], A.AI_RISKS, "مخاطر الذكاء الاصطناعي.", [3.2, 4, 5.5, 4])
    D.h("12. مصفوفة التتبع", 1)
    D.table(["المتطلب", "المصدر", "الوحدة", "الاختبار / الدليل"], A.TRACE, "المتطلب ← الكود ← الاختبار.", [5, 2, 4.5, 5.5], 10.5, ltr_cols=(2, 3))
    D.h("13. قائمة مكوّنات البرمجيات (SBOM / SOUP)", 1)
    D.table(["المكوّن", "الإصدار", "الترخيص", "الاستخدام"], A.SBOM, "قائمة المكوّنات (انظر sbom.spdx.json).", [5, 3, 5, 4])
    D.p("تقييم البرمجيات الجاهزة (IEC 62304 §5.3.3): المطلوب فقط مكتبة بايثون القياسية و SQLite؛ ومكتبة cryptography اختيارية ويُتحقق من مخرجاتها مقابل التطبيق الداخلي في الاختبارات.")
    D.h("14. خارطة الطريق", 1)
    D.table(["المدى الزمني", "الأنشطة"], A.ROADMAP, "خارطة الطريق نحو منتج قابل للاعتماد.", [3, 14])
    D.references()
    D.save(OUT / "ISO_STANDARDS_ALIGNMENT_AR.docx")


# ====================================================================== د. ملفات Markdown العربية
def md_table(h, rows) -> str:
    out = "| " + " | ".join(h) + " |\n|" + "---|" * len(h) + "\n"
    for r in rows:
        out += "| " + " | ".join(str(x).replace("|", "/") for x in r) + " |\n"
    return out


def build_md_ar() -> None:
    W = lambda name, body: (ROOT / name).write_text('<div dir="rtl">\n\n' + body + "\n\n</div>\n", encoding="utf-8")  # noqa: E731
    W("README_AR.md", f"""# 🛰️ BÖVD

**تحدي ناسا Space Apps 2026 – برمجيات مراقبة صحة رواد الفضاء في المهمات الفضائية**

> {A.HONESTY}

دعم قرار صحي يشرح نفسه ويعمل دون اتصال، لرواد الفضاء في انعدام الجاذبية وعلى القمر (1/6 g) وفي العبور إلى المريخ وعلى سطحه (3/8 g).
الواجهة: **HTML/JavaScript** · المنطق: **بايثون (المكتبة القياسية فقط)** · التشغيل: **`start.bat`** · البيانات تبقى على `127.0.0.1`.

## التشغيل السريع (Windows)
1. ثبّت Python 3.10 أو أحدث من python.org وفعّل خيار **Add python.exe to PATH**.
2. فك ضغط المجلد، ثم انقر نقرًا مزدوجًا على **`start.bat`**.
3. يفتح المتصفح تلقائيًا على `http://127.0.0.1:8765` – ادخل بأحد الحسابات التجريبية (كلمة المرور `astra2026`).
4. للإيقاف أغلق نافذة الأوامر. لإعادة البيانات التجريبية: `reset_data.bat`. للاختبارات: `run_tests.bat`.

macOS/Linux: `./start.sh` · Docker: `docker compose up`

| المستخدم | الدور |
|---|---|
| astro1 / astro3 | رائد فضاء |
| cmo1 | الضابط الطبي للطاقم |
| bhs1 | أخصائي الصحة السلوكية |
| surgeon1 | الجراح الجوي على الأرض |
| research1 | باحث (تصدير بأسماء مستعارة فقط) |

## عرض المحكّمين في دقيقتين
""" + "\n".join(f"{i + 1}. {x}" for i, x in enumerate(A.DEMO)) + """

## المحتوى
- الأساس: التحقق ← خط الأساس الشخصي (يراعي الجاذبية) ← العتبات ← الاتجاهات ← الدرجة المركّبة 0–20 ← «لماذا» ← التنبيهات (3 أولويات، تصعيد، تأخير القمر والمريخ).
- F1 الصوت (تجريبي) · F2 عين الحقيقة · F3 انسجام الطاقم · F4 الطبيب الذكي · F5 خريطة الإشعاع · F6 تحليلات البول · F7 المدرب · F8 الحنين الذكي · F9 الصندوق الأسود.
- تشفير أثناء التخزين (AES-256-GCM)، FHIR R4 + LOINC + UCUM، شارة مصدر لكل قيمة، عربي/إنجليزي، وضع القفازات والتباين العالي.

## الوثائق (بالعربية)
`deliverables/CODE_EXPLAINED_AR.docx` · `deliverables/ISO_STANDARDS_ALIGNMENT_AR.docx` · `deliverables/BOVD_Presentation_AR.pptx` ·
`SOURCES.md` · `RISK_REGISTER.md` · `TRACEABILITY.md` · `PROJECT_STATUS.md` · `PRIVACY.md` · `sbom.spdx.json`

النسخ الإنجليزية لكل الوثائق في `deliverables/English/` (مفيدة للمحكّمين الدوليين).

## الجودة
140 اختبارًا في pytest · التغطية للمحرك والتحقق والميزات نحو 97٪ · ruff نظيف · mypy الصارم نظيف.""")
    items = sorted(((k, v) for k, v in REFS.items() if k != "clinical_default"), key=lambda kv: kv[1]["apa"].replace("National Aeronautics and Space Administration", "NASA").lower())
    src = "# المصادر (APA 7)\n\nتحقّق من فتح كل رابط قبل التسليم. لم يُختلق أي مرجع؛ أي مرجع غير معروف يُوسم [CITATION NEEDED]. المراجع بلغتها الأصلية كما تقتضي قواعد APA، مع وصف عربي.\n\n"
    src += "\n".join(f"- **{A.REF_AR.get(k, '')}**  \n  <span dir=\"ltr\">{v['apa']} {v['url']}</span>" for k, v in items)
    src += "\n\n## مجموعات البيانات\n" + md_table(["المصدر", "الرقم", "الرابط", "الترخيص", "الحقول", "التحويل"], [
        ('مستودع ناسا OSDR – لوحة الأيض لطاقم SpaceX Inspiration4 (مضمّنة)', 'OSD-575', 'https://osdr.nasa.gov/bio/repo/data/studies/OSD-575', 'بيانات ناسا المفتوحة – “Data are courtesy of the NASA Open Science Data Repository”؛ الدراسة: Overbey, E. G., et al. (2024). The Space Omics and Medical Atlas (SOMA) and international astronaut biobank. Nature. https://doi.org/10.1038/s41586-024-07639-y', 'عمود الجلوكوز من LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv؛ 4 أفراد × 7 نقاط زمنية = 28 قيمة', 'scripts/build_osd575.py: تسميات الأيام L-n و R+n ← تواريخ من الإطلاق 2021-09-16 والعودة 2021-09-18 (12:00 UTC)؛ عينات L- ← earth_preflight وعينات R+ ← earth_postflight؛ CSV ← قراءة FHIR، REAL(OSD-575)'),
        ('مستودع ناسا OSDR (أي دراسة أخرى)', 'OSD-n يختاره الفريق', 'https://osdr.nasa.gov', 'بيانات ناسا المفتوحة + توثيق الدراسة', 'حسب mapping.json', 'CSV ← قراءة FHIR، REAL(OSD-n)'),
        ("بوابة ناسا لعلوم الحياة", "بعد طلب البيانات", "https://nlsp.nasa.gov", "حسب الاتفاقية", "حسب mapping.json", "نفس الطريقة"),
        ("مولّد البيانات المُصطنعة", "10 سيناريوهات", "astra/synthetic.py", "المشروع", "كل المؤشرات", "SYNTHETIC(السيناريو)")])
    W("SOURCES.md", src)
    W("RISK_REGISTER.md", "# سجل المخاطر (بأسلوب ISO 14971)\n\nش = الشدة 1–5، ح = الاحتمال 1–5 قبل الضوابط.\n\n"
      + md_table(["الرقم", "الحالة الخطرة", "الضرر", "ش", "ح", "الضابط", "الموضع", "التحقق", "المتبقي"], A.RISKS)
      + "\n## مخاطر الذكاء الاصطناعي (ISO/IEC 23894)\n" + md_table(["المكوّن", "الخطر", "التخفيف", "تحقق إضافي"], A.AI_RISKS))
    W("TRACEABILITY.md", "# مصفوفة التتبع\n\n" + md_table(["المتطلب", "المصدر", "الوحدة", "الاختبار / الدليل"], A.TRACE))
    stt = config.load("project_status")
    W("PROJECT_STATUS.md", "# حالة المشروع\n\n" + "".join(f"## {t}\n" + "\n".join(f"- {x}" for x in stt[k + '_ar']) + "\n\n"
                                                         for k, t in (("done", "أُنجز"), ("partial", "جزئي"), ("next", "التالي"))))
    W("PRIVACY.md", f"""# الخصوصية

{A.HONESTY}

- **محلي فقط.** الخادم يعمل على 127.0.0.1؛ لا تُرسل أي بيانات لخدمة سحابية. التحميل الاختياري من OSDR هو الاتصال الوحيد بالشبكة، وبأمر صريح فقط.
- **التشفير أثناء التخزين.** كل البيانات الصحية مشفّرة بـ AES-256-GCM في SQLite؛ المفتاح في `data/db/astra.key` (وفي النظام الحقيقي داخل وحدة أمان مادية).
- **موافقة لكل فئة** (خصائص الصوت، الرؤية، رمش الكاميرا، تفاعل الطاقم، الإشعاع، البول، الحنين، التصدير البحثي). سحب الموافقة أو إطفاء الميزة يوقف الجمع – وتثبت ذلك اختبارات آلية.
- **تقليل البيانات.** الصوت: لا يُحفظ الصوت الخام ولا يُرسل (7 أرقام فقط). الكاميرا: أرقام الرمش فقط، مطفأة افتراضيًا. الطاقم: مع من وكم دقيقة فقط، دون محتوى. الحنين: «ساعد/لم يساعد» فقط.
- **من يرى ماذا.** إشارة العزلة: الفرد وأخصائي الصحة السلوكية فقط. الباحثون: تصدير بأسماء مستعارة فقط.
- **السلامة من العبث.** كل عملية كتابة في سلسلة تجزئة SHA-256 غير قابلة للتعديل (الصندوق الأسود) مع أداة كشف العبث.
- **الحسابات التجريبية** تستخدم كلمة مرور مشتركة (`astra2026`) للهاكاثون فقط؛ غيّرها أو احذفها قبل أي استخدام آخر.
- **الحقوق.** احذف البيانات المحلية بـ `reset_data.bat`. التصدير البحثي يُنشأ فقط بطلب من الأدوار المخوّلة.""")


if __name__ == "__main__":
    build_md_ar()
    build_code_ar()
    build_iso_ar()
    print("arabic docs built")
