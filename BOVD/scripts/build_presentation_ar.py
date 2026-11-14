"""
عرض BÖVD التقديمي بالعربية (16:9، من اليمين لليسار، ملاحظات المتحدث).
الخط: Sakkal Majalla — خط نسخ عربي أصيل مثبّت مع Windows (7 فما فوق).
Run: python scripts/build_presentation_ar.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from astra import config  # noqa: E402

OUT = ROOT / "deliverables" / "BOVD_Presentation_AR.pptx"
IMG = ROOT / "deliverables" / "img"
FONT = "Sakkal Majalla"
NAVY, NAVY2, CARD = RGBColor(0x0D, 0x17, 0x35), RGBColor(0x07, 0x0B, 0x16), RGBColor(0x14, 0x22, 0x45)  # BÖVD logo palette (v2)
CYAN, GOLD, WHITE, MUTED = RGBColor(0x1B, 0xA6, 0xCF), RGBColor(0xC8, 0xA9, 0x6A), RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0x9D, 0xB3, 0xCC)
GREEN, AMBER, RED, PURPLE = RGBColor(0x2E, 0xCC, 0x71), RGBColor(0xF5, 0xA6, 0x23), RGBColor(0xFF, 0x4D, 0x4F), RGBColor(0xB3, 0x8C, 0xFF)
W, H = 13.333, 7.5
REFS = config.references()

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(W), Inches(H)
BLANK = prs.slide_layouts[6]
COUNT = [0]


# ------------------------------------------------------------------ RTL text helpers
def _rtl_run(run, size: float, color: RGBColor, bold: bool) -> None:
    run.font.size, run.font.bold, run.font.color.rgb, run.font.name = Pt(size), bold, color, FONT
    rpr = run._r.get_or_add_rPr()
    rpr.set("lang", "ar-OM")
    rpr.set("altLang", "en-US")
    for tag in ("a:ea", "a:cs"):
        el = rpr.find(qn(tag))
        if el is None:
            el = rpr.makeelement(qn(tag), {})
            rpr.append(el)
        el.set("typeface", FONT)


def text(s, x, y, w, h, lines, size=24, color=WHITE, bold=False, align="r", anchor=MSO_ANCHOR.TOP, spacing=4):
    box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, Inches(0.04))
    lines = lines if isinstance(lines, list) else [lines]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {"r": PP_ALIGN.RIGHT, "c": PP_ALIGN.CENTER, "l": PP_ALIGN.LEFT}[align]
        p._p.get_or_add_pPr().set("rtl", "0" if align == "l" else "1")
        p.space_after = Pt(spacing)
        segs = ln if isinstance(ln, list) else [(ln, color, bold)]
        for seg in segs:
            r = p.add_run()
            r.text = seg[0]
            _rtl_run(r, size, seg[1], seg[2])
    return box


def shape(s, kind, x, y, w, h, fill=None, line=None, lw=1.0, round_=None):
    sh = s.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(lw)
    if round_ is not None:
        sh.adjustments[0] = round_
    sh.shadow.inherit = False
    return sh


def stars(s, seed: int, n: int = 26) -> None:
    import random
    rnd = random.Random(seed)
    for _ in range(n):
        d = rnd.choice((0.03, 0.04, 0.05, 0.07))
        st = shape(s, MSO_SHAPE.OVAL, rnd.uniform(0.1, W - 0.2), rnd.uniform(0.1, H - 0.2), d, d, fill=rnd.choice((WHITE, CYAN, GOLD)))
        st.fill.transparency = 0.3


def background(s, seed: int) -> None:
    f = s.background.fill
    f.gradient()
    f.gradient_angle = 120
    f.gradient_stops[0].color.rgb = NAVY
    f.gradient_stops[1].color.rgb = NAVY2
    stars(s, seed)
    # orbit arcs (decorative, left side because the text reads from the right)
    for i, (d, col) in enumerate(((6.5, CYAN), (8.6, GOLD))):
        arc = shape(s, MSO_SHAPE.ARC, -d / 2.2, H - d / 2.4 + i * 0.4, d, d, line=col, lw=1.25)
        arc.line.color.rgb = col


def frame(title: str, kicker: str, notes: str, crit: str = ""):
    COUNT[0] += 1
    s = prs.slides.add_slide(BLANK)
    background(s, COUNT[0])
    text(s, 0.6, 0.28, W - 1.2, 0.5, kicker, 16, GOLD, True)
    text(s, 0.6, 0.62, W - 1.2, 0.9, title, 40, WHITE, True)
    shape(s, MSO_SHAPE.RECTANGLE, W - 0.6 - 1.6, 1.52, 1.6, 0.06, fill=CYAN)
    shape(s, MSO_SHAPE.RECTANGLE, W - 0.6 - 2.0, 1.52, 0.3, 0.06, fill=GOLD)
    if crit:
        text(s, 0.5, 0.35, 4.2, 0.45, "معيار التحكيم: " + crit, 14, MUTED, align="l")
    # footer with page badge
    text(s, 1.3, H - 0.52, W - 2.0, 0.4, "BÖVD · تحدي ناسا Space Apps 2026 · نموذج أولي لدعم القرار – ليس جهازًا طبيًا معتمدًا", 13, MUTED)
    b = shape(s, MSO_SHAPE.OVAL, 0.5, H - 0.62, 0.55, 0.55, fill=CYAN)
    text(s, 0.5, H - 0.62, 0.55, 0.55, str(COUNT[0]), 18, NAVY, True, "c", MSO_ANCHOR.MIDDLE)
    b.line.fill.background()
    s.notes_slide.notes_text_frame.text = notes
    return s


def card(s, x, y, w, h, icon, title, body, accent=CYAN, bsize=19, tsize=22):
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=CARD, line=accent, lw=1.25, round_=0.07)
    shape(s, MSO_SHAPE.RECTANGLE, x + w - 0.09, y + 0.25, 0.09, h - 0.5, fill=accent)
    text(s, x + 0.08, y + 0.08, 0.6, 0.5, icon, 20, WHITE, align="l")
    text(s, x + 0.55, y + 0.1, w - 0.8, 0.9, title, tsize, accent, True, anchor=MSO_ANCHOR.TOP, spacing=0)
    text(s, x + 0.15, y + 1.12, w - 0.35, h - 1.2, body, bsize, WHITE, spacing=3)


def row_cards(s, items, y, h, accent_list=None, bsize=19, gap=0.18, tsize=22):
    n = len(items)
    if n >= 5:
        tsize = min(tsize, 19)
    w = (W - 1.2 - gap * (n - 1)) / n
    for i, it in enumerate(items):  # first item on the RIGHT (RTL reading order)
        x = W - 0.6 - w - i * (w + gap)
        card(s, x, y, w, h, *it, accent=(accent_list[i] if accent_list else CYAN), bsize=bsize, tsize=tsize)


def picture(s, name, x, y, w=None, h=None, border=CYAN):
    f = IMG / name
    if not f.exists():
        return
    p = s.shapes.add_picture(str(f), Inches(x), Inches(y), Inches(w) if w else None, Inches(h) if h else None)
    p.line.color.rgb = border
    p.line.width = Pt(1.5)


# ====================================================================== slides
# 1 — Title
COUNT[0] += 1
s = prs.slides.add_slide(BLANK)
background(s, 1)
for d, col, t in ((5.2, CYAN, 0.0), (6.6, GOLD, 0.35), (8.0, CYAN, 0.6)):
    o = shape(s, MSO_SHAPE.OVAL, 1.9 - d / 2, 3.75 - d / 2, d, d, line=col, lw=1)
    o.line.transparency = t
planet = shape(s, MSO_SHAPE.OVAL, 0.75, 2.6, 2.3, 2.3, fill=CYAN)
planet.fill.transparency = 0.15
shape(s, MSO_SHAPE.OVAL, 3.85, 1.3, 0.35, 0.35, fill=GOLD)
text(s, 4.6, 1.15, 8.2, 1.6, "BÖVD", 96, WHITE, True, anchor=MSO_ANCHOR.MIDDLE)
text(s, 4.6, 0.55, 8.2, 0.6, "الإصدار 2 · نوفمبر 2026", 20, GOLD, True)
shape(s, MSO_SHAPE.RECTANGLE, 9.9, 2.85, 2.8, 0.07, fill=GOLD)
text(s, 4.6, 2.95, 8.2, 1.3, "رعاية صحية ذكية تشرح نفسها… لرواد الفضاء في كل جاذبية", 34, CYAN, True)
text(s, 4.6, 4.45, 8.2, 1.9, ["تحدي ناسا Space Apps 2026 · برمجيات مراقبة صحة رواد الفضاء",
                             "برمجيات فقط · واجهة HTML ومحرك بايثون · يعمل على الجهاز من ملف واحد start.bat",
                             "نموذج أولي لدعم القرار والتدريب – ليس جهازًا طبيًا معتمدًا"], 21, WHITE)
s.notes_slide.notes_text_frame.text = "عرّف بالفريق وبالفكرة في جملة واحدة: BÖVD يخبر رائد الفضاء بحالته، ولماذا، وما الخطوة التالية، وبمن يتصل – دون الحاجة لاتصال بالأرض."

# 2 — Five hazards
s = frame("المخاطر الخمسة للرحلات الفضائية", "لماذا نحتاج BÖVD؟",
          "يقسّم برنامج أبحاث الإنسان في ناسا المخاطر إلى خمسة (NASA Human Research Program, n.d.). كل تنبيه في BÖVD يذكر الخطر الذي ينتمي إليه.", "الملاءمة")
row_cards(s, [("☢️", "الإشعاع", "أشعة كونية وعواصف شمسية خارج الغلاف المغناطيسي"),
              ("🧠", "العزلة والحبس", "النوم والمزاج وتماسك الفريق"),
              ("📡", "البعد عن الأرض", "تأخر 4–24 دقيقة إلى المريخ ← رعاية مستقلة"),
              ("🪐", "مجالات الجاذبية", "الانتقال بين 0 و 1/6 و 3/8 و 1 g"),
              ("🏭", "بيئة مغلقة ومعادية", "ثاني أكسيد الكربون وموارد محدودة")],
          2.0, 3.4, [RED, PURPLE, CYAN, GOLD, AMBER], bsize=20)
text(s, 0.6, 5.7, W - 1.2, 0.5, "المصدر: NASA Human Research Program (n.d.). Five hazards of human spaceflight.", 15, MUTED)

# 3 — Body in microgravity
s = frame("انعدام الجاذبية يغيّر الجسم", "العلم أولًا",
          "اشرح لماذا لا تكفي الحدود الأرضية وحدها: انتقال السوائل يخفّض النبض والضغط أثناء الرحلة (HRP, 2015a)، فقد العظم يرفع كالسيوم البول (Smith et al., 2012)، متلازمة SANS (Lee et al., 2020)، نقص النوم (Barger et al., 2014).", "الصدق العلمي")
row_cards(s, [("💧", "انتقال السوائل", "نحو 2 لتر نحو الرأس؛ عدم تحمّل الانتصاب عند العودة للجاذبية"),
              ("🦴", "العظام والكلى", "يخرج الكالسيوم من العظم ← يرتفع في البول ويزيد خطر الحصى"),
              ("👁️", "العين – SANS", "وذمة القرص البصري وتسطّح مقلة العين"),
              ("😴", "النوم", "نحو 6 ساعات في الرحلة و16 شروقًا في اليوم")],
          1.95, 3.3, [CYAN, GOLD, PURPLE, GREEN], bsize=21)
shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.6, 5.5, W - 1.2, 0.85, fill=RGBColor(0x0F, 0x3B, 0x52), line=CYAN, round_=0.3)
text(s, 0.8, 5.55, W - 1.6, 0.75, "⟵ القاعدة الأولى: نقارن القراءة بخط أساس الرائد نفسه أولًا، ثم بالحدود الأرضية", 26, WHITE, True, anchor=MSO_ANCHOR.MIDDLE)

# 4 — Personas
s = frame("الشخصيات المستخدمة", "لمن صُمّم BÖVD؟",
          "خمسة أدوار بصلاحيات دنيا. إشارة العزلة لا يراها إلا صاحبها وأخصائي الصحة السلوكية.", "الأثر")
row_cards(s, [("👩‍🚀", "نور – رائدة فضاء", "تطفو وترتدي قفازات؛ تريد فحصًا في دقيقة وخطوة تالية واضحة"),
              ("🩺", "سامي – الضابط الطبي", "طبيب الطاقم على المركبة؛ يحتاج التنبيهات والبروتوكولات"),
              ("🧠", "أخصائي الصحة السلوكية", "يرى إشارات المزاج والعزلة فقط"),
              ("🌍", "الجراح الجوي", "على الأرض؛ يرى فقط ما وصل عبر الوصلة المتأخرة"),
              ("🔬", "الباحث", "بيانات بأسماء مستعارة وبموافقة فقط")],
          2.0, 3.9, [CYAN, GREEN, PURPLE, GOLD, MUTED], bsize=20, tsize=22)

# 5 — Solution
s = frame("الحل: الحالة · السبب · الخطوة · الاتصال", "كيف يعمل؟",
          "اعرض سلسلة العمل كاملة. أكّد أن التطبيق لا يشخّص أبدًا.", "الإبداع · الصدق العلمي")
steps = ["الإدخال", "التحقق", "التقييم", "الشرح", "الإجراء", "التصعيد", "المتابعة"]
cw = (W - 1.2) / len(steps)
for i, st in enumerate(steps):
    x = W - 0.6 - (i + 1) * cw
    ch = shape(s, MSO_SHAPE.CHEVRON, x + 0.03, 1.95, cw - 0.06, 0.8, fill=CYAN if i % 2 == 0 else RGBColor(0x00, 0x7A, 0x99))
    ch.rotation = 180  # arrows point left: Arabic reading direction
    text(s, x + 0.1, 1.95, cw - 0.2, 0.8, st, 21, NAVY if i % 2 == 0 else WHITE, True, "c", MSO_ANCHOR.MIDDLE)
picture(s, "measure.png", 0.6, 3.05, h=3.75)
text(s, 5.3, 3.05, 7.45, 3.8, ["• خط أساس شخصي ±2 انحراف معياري يراعي الجاذبية",
                               "• حدود أرضية قابلة للتعديل وموثّقة بالمصادر",
                               "• قواعد الاتجاه: 3 ليالٍ قصيرة ← أحمر",
                               "• درجة مركّبة من 0 إلى 20",
                               "• «لماذا»: الخطر والتفسير والخطوات وجهة الاتصال والمراجع"], 24, WHITE, spacing=8)

# 6 — Demo
s = frame("العرض الحي في دقيقتين", "جرّبه بنفسك",
          "اتبع خطوات العرض. اجعل start.bat يعمل مسبقًا.", "جودة العرض")
demo = ["انقر start.bat ← الانترو المتحرك ثم صفحة الدخول",
        "ادخل باسم astro1 ← الجولة التعريفية، ثم اللوحة والجسم ثلاثي الأبعاد",
        "القياس: نبض 128، نوم 4.5، مزاج 2 ← أحمر مع السبب والخطوة التالية",
        "شريط التنبيه الأحمر يومض ← الجراح الجوي يرى فقط ما وصل",
        "حدث «هبوط على المريخ» ← بروتوكول انتقال الجاذبية واختبار الوقوف",
        "النموذج ثلاثي الأبعاد ← رسوم «ضغط الدم» ← تحقق بالكاميرا أو يدويًا",
        "المصادر العلمية ← كل قيمة برابطها · محاكاة البيئة ← المقصورة والارتفاع"]
for i, d in enumerate(demo):
    y = 1.9 + i * 0.66
    shape(s, MSO_SHAPE.OVAL, W - 1.2, y + 0.06, 0.55, 0.55, fill=GOLD)
    text(s, W - 1.2, y + 0.06, 0.55, 0.55, str(i + 1), 20, NAVY, True, "c", MSO_ANCHOR.MIDDLE)
    text(s, 6.4, y, W - 7.75, 0.75, d, 21, WHITE, anchor=MSO_ANCHOR.MIDDLE)
picture(s, "v2/dash_169.png", 0.6, 1.95, w=5.5)

# ---------------------------------------------------------------- v2 slides
s = frame("هوية بصرية جديدة بلمسة عُمانية", "الإصدار 2 · التصميم",
          "الألوان والأشكال مأخوذة من الشعار. اللمسة العُمانية: نقشة النجمة الثمانية من الأبواب والمشربيات، فاصل على شكل شُرفات قلعتي نزوى وبهلاء، ونافذة مقوّسة لعارض الجسم. لم نستخدم أحمر وأخضر العلم لأنهما لونا حالة طبية.", "جودة العرض")
picture(s, "v2/dash_169.png", 0.6, 1.95, w=6.9)
text(s, 7.8, 1.95, 4.95, 4.8, ["• تصميم مسطح هندسي هادئ بألوان الشعار", "• وضع ليلي كامل", "• نقشة الخاتم العُماني وشُرفات القلاع",
                               "• نافذة مقوّسة لعارض الجسم", "• الحالة = لون + أيقونة + نص", "• تباين النص ≥ 4.5:1"], 22, spacing=8)

s = frame("الانترو والانتقالات والحركة", "الإصدار 2 · الحركة",
          "الانترو الجديد يعمل عند الفتح ويمكن تخطيه. ثلاثة أساليب انتقال من Motion Kit تُختار من الإعدادات. كل الحركة تتوقف مع «تقليل الحركة».", "جودة العرض")
for i, (img, cap) in enumerate((("v2/splash.png", "الانترو"), ("v2/trans_pulse.png", "انتقال «نبضة قلب»"), ("v2/settings_169.png", "اختيار الأسلوب"))):
    x = W - 0.6 - 3.95 - i * 4.1
    picture(s, img, x, 1.95, w=3.95)
    text(s, x, 4.47, 3.95, 0.45, cap, 17, GOLD, True, "c")
row_cards(s, [("🪐", "كوكب يتمدّد", "يغطي الشاشة ثم ينكمش"), ("💓", "نبضة قلب", "خط نبض يُرسم ثم ينفتح"),
              ("🛰️", "قمر عابر", "ستارة قطرية خلف القمر"), ("⏳", "تحميل وتفاعل", "قمر يدور · نبض · نقاط · رادار")],
          5.0, 1.75, [CYAN, RED, GOLD, GREEN], bsize=17, tsize=20)

s = frame("نموذج بشري ثلاثي الأبعاد تفاعلي", "الإصدار 2 · الجسم",
          "محرك WebGL مكتوب للمشروع يعمل دون إنترنت. الطريقة الصحيحة لكل فحص برسوم متحركة. إن لم يدعم الجهاز WebGL يظهر المخطط ثنائي الأبعاد تلقائيًا.", "الإبداع")
picture(s, "v2/b3d_169.png", 0.6, 1.95, w=6.9)
text(s, 7.8, 1.95, 4.95, 4.8, ["• تدوير 360° وتكبير بالفأرة أو بإصبعين", "• اضغط عضوًا ← تطير الكاميرا وتظهر حالته ومصادره",
                               "• 6 رسوم تعليمية: الضغط، الأكسجين، الحرارة، البصر، الوقوف، التثبيت", "• تشغيل · إيقاف · إعادة · خطوة خطوة",
                               "• متوسط الإطار 0.6 ملّي ثانية"], 21, spacing=8)

s = frame("التحقق من الوضعية بالكاميرا", "الإصدار 2 · OpenCV + MediaPipe",
          "الكاميرا تتحقق من الوضعية وخطوات الإجراء فقط، ولا تقيس أي مؤشر حيوي. الإطارات تُعالج على الجهاز ولا تُحفظ. دقة MediaPipe على صور حقيقية لم تُقَس بعد.", "الصدق العلمي")
picture(s, "v2/pose_169.png", 0.6, 1.95, w=6.9)
text(s, 7.8, 1.95, 4.95, 3.3, ["• OpenCV: الإضاءة والوضوح والحركة", "• MediaPipe: ‏33 معلمًا للجسم", "• قواعد لكل خطوة وتنبيه عربي فوري",
                               "• وضع يدوي عند رفض الإذن أو انقطاع الكاميرا"], 21, spacing=8)
shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 7.8, 5.35, 4.95, 1.35, fill=RGBColor(0x3A, 0x2A, 0x0A), line=GOLD, round_=0.15)
text(s, 7.95, 5.4, 4.65, 1.25, "الكاميرا لا تقيس الضغط ولا الأكسجين ولا الحرارة. القيم تأتي من جهازك المعتمد.", 19, WHITE, True, anchor=MSO_ANCHOR.MIDDLE)

s = frame("كل قيمة علمية لها مصدر", "الإصدار 2 · الأدلة",
          "29 مدخلًا: المؤشر والقيمة والوحدة والظروف والعينة والجهة والتاريخ والرابط والموضع والقيود. لا نخترع قيمًا، ولا ننسب إلى ناسا ما ليس منها.", "الصدق العلمي")
picture(s, "v2/sci_169.png", 0.6, 1.95, w=6.9)
row = [("✅", "مقيسة منشورة", GREEN), ("📏", "معيار / حد", CYAN), ("📐", "نموذج / معادلة", PURPLE), ("⚠️", "افتراضي (ليس من ناسا)", AMBER), ("⛔", "دليل غير كافٍ", RED)]
for i, (ic, t, col) in enumerate(row):
    y = 1.95 + i * 0.95
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 7.8, y, 4.95, 0.8, fill=CARD, line=col, round_=0.25)
    text(s, 7.95, y, 4.3, 0.8, t, 21, col, True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 12.15, y, 0.5, 0.8, ic, 20, WHITE, align="c", anchor=MSO_ANCHOR.MIDDLE)

s = frame("محاكاة البيئة: الجاذبية والضغط", "الإصدار 2 · المحاكاة",
          "نموذجان منفصلان. الجاذبية: قيم منشورة على خط الأساس، و«دليل غير كافٍ» حيث لا بيانات. الضغط: معادلات منشورة (الغلاف الجوي القياسي، الغاز السنخي، سفيرينغهاوس). كل نتيجة موسومة «محاكاة».", "الصدق العلمي")
picture(s, "v2/sim_top.png", 0.6, 1.95, h=4.75)
text(s, 6.4, 1.95, 6.35, 4.8, ["• المراحل: قبل الرحلة · أثناءها · بعد العودة", "• فقد العظم: عمود فقري 0.9%/شهر، ورك 1.4–1.5%/شهر",
                               "• بعد 6 أشهر: خط متقطع «استقراء»", "• مقصورة الاستكشاف 8.2 psia ‏34% ← PIO₂ = ‏128.2",
                               "• عند 5000 م: الضغط 54.02 kPa", "• CO₂ يُقيَّم بالضغط الجزئي حسب المقصورة"], 21, spacing=8)

s = frame("جولة تعريفية وتصميم لكل الشاشات", "الإصدار 2 · التجربة",
          "جولة من 11 مرحلة تنتهي بفحص ضغط دم تجريبي. يعمل على الحاسوب والجهاز اللوحي والهاتف دون تمرير أفقي.", "الأثر")
picture(s, "v2/r_phone_375.png", W - 0.6 - 2.15, 1.9, h=4.75)
picture(s, "v2/r_phone_375_menu.png", W - 0.6 - 4.5, 1.9, h=4.75)
picture(s, "v2/r_tablet_768.png", W - 0.6 - 8.15, 1.9, h=4.75)
text(s, 0.6, 1.95, 3.7, 4.8, ["الجولة:", "ترحيب · الواجهة · الأقسام · ثلاثي الأبعاد · الفحوصات · الأجهزة · إذن الكاميرا · الطريقة الصحيحة · فحص تجريبي · قراءة النتائج · المصادر",
                              "", "تُعاد من «المساعدة» أو «الإعدادات»"], 18, spacing=6)

s = frame("نتائج الاختبارات", "الإصدار 2 · الجودة",
          "كل الأرقام من تشغيل فعلي. الدقة 99.75% تخص منطق القواعد على بيانات اصطناعية، وليست دقة الكاميرا الحقيقية.", "الصدق العلمي")
row_cards(s, [("🐍", "pytest", "139 / 139 ناجح"), ("🌐", "اختبارات المتصفح", "35 / 35 ناجح"),
              ("📱", "77 صفحة × 3 مقاسات", "0 أخطاء · 0 تمرير أفقي"), ("♿", "إمكانية الوصول", "تباين ≥ 4.59:1 · 0 أزرار بلا وصف")],
          1.95, 2.0, [GREEN, CYAN, GOLD, PURPLE], bsize=20)
row_cards(s, [("🧍", "قواعد الوضعية", "400 حالة · إيجابي كاذب 1 · سلبي كاذب 0"), ("⚡", "الأداء", "الدخول 0.2 ث · اللوحة 0.3 ث · ذاكرة 5 ميغابايت"),
              ("📷", "الكاميرا", "إطار 5 ملّي ث · رفض الإذن وانقطاعها ← يدوي"), ("🧊", "ثلاثي الأبعاد", "تدوير · تكبير · لمس · فشل WebGL ← ثنائي الأبعاد")],
          4.2, 2.3, [AMBER, CYAN, RED, GREEN], bsize=18)

# 7–8 — Features
FEATS = [("🎙️", "F1 قراءة الصوت (تجريبي)", "7 خصائص صوتية تُحسب على الجهاز؛ لا يُحفظ الصوت أبدًا؛ تُدمج مع النوم والمزاج", PURPLE),
         ("👁️", "F2 عين الحقيقة", "حدة بصر معايرة، شبكة أمسلر، مقارنة صور OCT وقاع العين – دون تشخيص", CYAN),
         ("🤝", "F3 مؤشر انسجام الطاقم", "بيانات وصفية فقط؛ إشارة العزلة لك وللأخصائي فقط", GREEN),
         ("🤖", "F4 الطبيب الذكي دون اتصال", "7 بروتوكولات: سؤال ← إجراء ← «توقف واتصل بالضابط الطبي»", GOLD),
         ("☢️", "F5 خريطة الإشعاع الشخصية", "جرعة تراكمية، خريطة حرارية للموئل، وضع العاصفة الشمسية والملجأ", RED),
         ("🚽", "F6 تحليلات المرحاض الذكي", "مخطط JSON واحد لشرائط البول والمختبر والأجهزة المستقبلية", AMBER),
         ("🏋️", "F7 وصفة الحركة والغذاء", "يعدّل التمارين داخل حدود الجراح الجوي ويقترح وجبات", GREEN),
         ("🌍", "F8 الحنين الذكي", "وسائط عائلية عند استمرار انخفاض المزاج؛ يُحفظ «ساعد/لم يساعد» فقط", PURPLE),
         ("📦", "F9 الصندوق الأسود الصحي", "سلسلة تجزئة SHA-256 مشفّرة؛ كشف العبث؛ تصدير بحثي بأسماء مستعارة", CYAN)]
for part, chunk in ((1, FEATS[:5]), (2, FEATS[5:])):
    s = frame(f"الميزات التسع المتقدمة ({part}/2)", "ما يميّز BÖVD",
              "لكل ميزة وحدة برمجية مستقلة، ومفتاح تشغيل، وشاشة موافقة، وملاحظة خصوصية، وشرح، ومراجع، واختبارات.", "الإبداع · الأثر")
    cols = 3
    w = (W - 1.2 - 0.2 * (cols - 1)) / cols
    for i, (ic, t, b, col) in enumerate(chunk):
        x = W - 0.6 - w - (i % cols) * (w + 0.2)
        y = 1.95 + (i // cols) * 2.55
        card(s, x, y, w, 2.35, ic, t, b, col, bsize=19, tsize=22)

# 9 — Architecture
s = frame("البنية: برمجيات فقط، دون اتصال", "تحت الغطاء",
          "مكتبة بايثون القياسية فقط مع تشفير اختياري. يعمل على 127.0.0.1. قاعدة بيانات مشفّرة. تشغيل بأمر واحد.", "الصدق العلمي")
layers = [("🖥️", "الواجهة HTML", "عربي/إنجليزي · ثلاثي الأبعاد WebGL · الكاميرا · الجولة · الحركة"),
          ("🔌", "الخادم server.py", "REST · OpenAPI · صلاحيات JWT"),
          ("⚙️", "المحرك والتنبيهات", "خط الأساس ← الحدود ← الاتجاه ← السبب · 3 أولويات · طابور التأخير"),
          ("🔒", "التخزين", "SQLite · تشفير AES-256-GCM · FHIR R4 · صندوق أسود"),
          ("📥", "العلم والوضعية", "سجل 29 دليلًا · محاكاة · OpenCV + MediaPipe · محمّل OSDR")]
for i, (ic, t, b) in enumerate(layers):
    y = 1.9 + i * 0.98
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 5.2, y, W - 5.8, 0.86, fill=CARD, line=CYAN, round_=0.2)
    text(s, 5.35, y + 0.04, W - 7.0, 0.8, [[(t + "   ", CYAN, True), (b, WHITE, False)], ], 19, anchor=MSO_ANCHOR.MIDDLE)
    text(s, W - 1.15, y, 0.5, 0.86, ic, 22, WHITE, align="c", anchor=MSO_ANCHOR.MIDDLE)
shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.6, 1.9, 4.3, 4.78, fill=RGBColor(0x0F, 0x3B, 0x52), line=GOLD, round_=0.06)
text(s, 0.8, 2.0, 3.9, 4.6, [[("▶ start.bat", GOLD, True)], "← يبحث عن بايثون", "← يثبّت التشفير السريع إن أمكن",
                              "← python -m astra.server", "← يفتح 127.0.0.1:8765", "", [("لا سحابة · لا حساسات · لا أردوينو", CYAN, True)],
                              "الميكروفون والكاميرا: أرقام فقط، والوسائط الخام تُحذف"], 21)

# 10 — Data & provenance
s = frame("بيانات ناسا ومصدر كل قيمة", "لا نخترع البيانات",
          "البيانات الحقيقية فقط بعد تحميل مجموعة من OSDR بالمحمّل؛ والمُصطنعة دائمًا موسومة.", "الصدق العلمي · الملاءمة")
row_cards(s, [("✅", "حقيقية REAL", "من NASA OSDR وNLSP عبر المحمّل ← REAL(OSD-n)"),
              ("🧪", "مُصطنعة SYNTHETIC", "10 سيناريوهات معايرة على قيم منشورة"),
              ("✍️", "مُدخلة USER-ENTERED", "يكتبها الطاقم مع ظروف القياس")],
          1.95, 1.95, [GREEN, PURPLE, CYAN], bsize=20)
picture(s, "chart.png", 0.6, 4.1, h=2.65)
text(s, 5.1, 4.15, 7.65, 2.6, ["• كل نقطة ملوّنة حسب مصدرها", "• شريط خط الأساس وعلامات انتقال الجاذبية", "• الاختبارات تتأكد أن كل قيمة مُصطنعة موسومة"], 23, spacing=8)

# 11 — Explainable
s = frame("تقييم يشرح نفسه", "الثقة تبدأ بالشفافية",
          "اعرض لوحة «لماذا»: أي قاعدة انطبقت، مقارنةً بأي خط أساس، أي خطر، ماذا تفعل، بمن تتصل، والمراجع.", "الصدق العلمي")
picture(s, "dashboard.png", 0.6, 1.9, h=4.85)
items = [("1", "خط الأساس الشخصي أولًا"), ("2", "الأحمر لا يُخفَّف أبدًا"), ("3", "تنخفض الثقة إذا نقصت ظروف القياس"),
         ("4", "كل حدّ: مرجع + «يحتاج مراجعة»"), ("5", "الجسم: لون + رمز + نص (ليس اللون وحده)")]
for i, (n_, t) in enumerate(items):
    y = 2.0 + i * 0.92
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 6.5, y, W - 7.1, 0.78, fill=CARD, line=CYAN, round_=0.3)
    text(s, 6.7, y, W - 8.1, 0.78, t, 23, WHITE, anchor=MSO_ANCHOR.MIDDLE)
    shape(s, MSO_SHAPE.OVAL, W - 1.25, y + 0.12, 0.54, 0.54, fill=GOLD)
    text(s, W - 1.25, y + 0.12, 0.54, 0.54, n_, 18, NAVY, True, "c", MSO_ANCHOR.MIDDLE)

# 12 — Alerts & delay
s = frame("التنبيهات وتأخر الاتصال بين الأرض والمريخ", "حين تكون الأرض بعيدة",
          "أولويات بأسلوب IEC 60601-1-8. تأخر المريخ 4–24 دقيقة في الاتجاه الواحد؛ إقرارات الأرض تعود بالتأخير نفسه.", "الملاءمة · الأثر")
row_cards(s, [("⛔", "أولوية عالية", "أحمر يومض + صوت · يتكرر كل 30 ث · تصعيد كل دقيقتين"),
              ("⚠️", "أولوية متوسطة", "كهرماني ثابت · يتكرر كل 10 د · تصعيد كل 30 د"),
              ("ℹ️", "أولوية منخفضة", "معلومة فقط · بلا تكرار ولا تصعيد")],
          1.95, 1.95, [RED, AMBER, CYAN], bsize=20)
picture(s, "surgeon.png", 0.6, 4.1, h=2.65)
text(s, 4.6, 4.15, 8.15, 2.6, ["• القمر ≈ 1.3 ثانية · المريخ 4–24 دقيقة", "• طابور «خزّن ثم أرسل» في الاتجاهين",
                               "• الطاقم ← الضابط الطبي ← الجراح الجوي", "• البروتوكولات تعمل على المركبة دون اتصال"], 23, spacing=6)

# 13 — Privacy & ethics
s = frame("خصوصية الصوت والكاميرا وأخلاقياتها", "الثقة قبل التقنية",
          "لا يُحفظ الصوت أو الفيديو الخام ولا يُرسل؛ موافقة لكل فئة؛ اختبارات تثبت عدم جمع أي شيء عند سحب الموافقة؛ صياغة محايدة.", "الأثر · الصدق العلمي")
priv = [("🎙️", "الصوت (تجريبي)", "7 أرقام فقط؛ الصوت الخام يُحذف داخل المتصفح؛ لا ينبّه وحده", PURPLE),
        ("📷", "الكاميرا", "الوضعية فقط + أرقام الرمش؛ موافقة منفصلة؛ الإطارات لا تُحفظ أبدًا", AMBER),
        ("🤝", "الطاقم", "مع من وكم دقيقة فقط – لا محتوى أبدًا", GREEN),
        ("📦", "البحث العلمي", "بموافقة، بأسماء مستعارة، تواريخ عامة، حزمة OAIS", CYAN)]
w = (W - 1.4) / 2
for i, (ic, t, b, col) in enumerate(priv):
    card(s, W - 0.6 - w - (i % 2) * (w + 0.2), 1.95 + (i // 2) * 2.4, w, 2.2, ic, t, b, col, bsize=21)

# 14 — Standards (Arabic descriptions)
s = frame("المعايير الدولية: توافق دون اعتماد", "الجودة والسلامة",
          "32 معيارًا مربوطة بالكود والاختبارات والفجوات. صُمّم البرنامج بما يتماشى معها، ولم يُدقَّق أو يُعتمد رسميًا – التفاصيل في ملف ISO_STANDARDS_ALIGNMENT.docx.", "الصدق العلمي")
STD_AR = [
    ("🩺", "برمجيات الصحة والسلامة", "دورة حياة البرمجيات الطبية، إدارة المخاطر، ضبط الوثائق، جودة التطبيقات الصحية",
     "IEC 62304 · IEC 82304-1 · ISO 14971 · ISO 13485 · ISO/TS 82304-2", CYAN),
    ("🚀", "طب الفضاء", "معيار ناسا لصحة الطاقم وبيئة المركبة: المراقبة الصحية، حدود الإشعاع، ثاني أكسيد الكربون",
     "NASA-STD-3001 المجلد 1 و 2", GOLD),
    ("🗂️", "البيانات الصحية", "تبادل البيانات بصيغة موحّدة، رموز ووحدات القياس، صور العين، الأسماء المستعارة، الأرشفة طويلة المدى",
     "HL7 FHIR R4 · LOINC · UCUM · DICOM · ISO 13606 · ISO 25237 · ISO 14721 · ISO 8601", GREEN),
    ("🔒", "الأمن والخصوصية", "ضوابط أمن المعلومات، حماية البيانات الصحية، الموافقة وتقليل البيانات",
     "ISO/IEC 27001 · 27002 · ISO 27799 · ISO/IEC 27701 · 29100", PURPLE),
    ("🤖", "الذكاء الاصطناعي", "إدارة أنظمة الذكاء الاصطناعي ومخاطرها وشفافيتها وجودتها والحد من التحيّز",
     "ISO/IEC 42001 · 23894 · 22989 · 25059 · TR 24027", AMBER),
    ("🛠️", "هندسة البرمجيات", "دورة حياة البرمجيات، وصف البنية، نموذج الجودة، جودة البيانات، الاختبار، قائمة المكوّنات",
     "ISO/IEC 12207 · 42010 · 25010 · 25012 · 29119 · 5055 · 5962", CYAN),
    ("🧤", "تجربة المستخدم", "قابلية الاستخدام الطبية، تصميم الإنذارات، مبادئ التفاعل، إتاحة الويب",
     "IEC 62366-1 · IEC 60601-1-8 · ISO 9241 · ISO/IEC 40500", GOLD),
]
w = (W - 1.2 - 0.2 * 3) / 4
for i, (ic, area, desc, ids, col) in enumerate(STD_AR):
    x = W - 0.6 - w - (i % 4) * (w + 0.2)
    y = 1.9 + (i // 4) * 2.5
    card(s, x, y, w, 2.4, ic, area, [desc, [(ids, col, False)]], col, bsize=13, tsize=18)
shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.6, 4.4, w, 2.35, fill=RGBColor(0x0F, 0x3B, 0x52), line=GOLD, round_=0.07)
text(s, 0.75, 4.5, w - 0.3, 2.15, [[("للتوضيح", GOLD, True)], "«صُمّم بما يتماشى مع» يعني أننا طبّقنا مبادئ هذه المعايير في الكود والاختبارات.",
                                   "لا يعني أن البرنامج حاصل على شهادة أو اعتماد."], 15)

# 15 — Impact
s = frame("أثر يتجاوز محطة الفضاء", "من المريخ إلى القرى البعيدة",
          "النموذج نفسه يصلح لأي مكان بعيد تتأخر فيه الرعاية.", "الأثر")
row_cards(s, [("🌕", "قاعدة القمر – أرتميس", "تأخر 1.3 ثانية، جاذبية جزئية، ملجأ العواصف"),
              ("🔴", "المريخ", "رعاية مستقلة عن الأرض، تأخر 4–24 دقيقة"),
              ("🧊", "القارة القطبية", "عزلة الشتاء، النوم والمزاج"),
              ("🏥", "العيادات النائية", "دون اتصال، عربي/إنجليزي، حاسوب بسيط")],
          2.0, 3.6, [GOLD, RED, CYAN, GREEN], bsize=22)

# 16 — Status
s = frame("ما أُنجز · ما هو جزئي · ما التالي", "بصدق",
          "كن صريحًا في الحدود – هذا نموذج أولي لهاكاثون.", "جودة العرض")
status = [("✅", "أُنجز", ["تطبيق محلي كامل يعمل من start.bat", "تشفير وFHIR ومصدر لكل قيمة", "محرك خط الأساس والتنبيهات والتأخير",
                          "ثلاثي الأبعاد والكاميرا والأدلة والمحاكاة والجولة", "139 اختبارًا + 35 اختبار متصفح"], GREEN),
          ("🟡", "جزئي", ["دقة MediaPipe على صور حقيقية لم تُقَس", "الصوت تجريبي وغير مُتحقق منه", "أوزان مؤشر الطاقم أمثلة تحتاج خبيرًا",
                         "لا توجد بيانات حقيقية مضمّنة (تُحمَّل يدويًا)"], AMBER),
          ("➡️", "التالي", ["مراجعة جراح جوي لكل الحدود", "اختبار استخدام بالقفازات في بيئة محاكاة", "قياس دقة الكاميرا بصور مصنّفة", "اختبار على أجهزة لمس حقيقية",
                           "التحقق من إشارات الصوت على بيانات حقيقية"], CYAN)]
w = (W - 1.2 - 0.4) / 3
for i, (ic, t, lines, col) in enumerate(status):
    card(s, W - 0.6 - w - i * (w + 0.2), 1.95, w, 4.75, ic, t, ["• " + x for x in lines], col, bsize=20)

# 17 — References (Arabic descriptions)
s = frame("المراجع العلمية – مختارات", "المصادر",
          "وصف عربي لأهم المصادر؛ الصيغة الكاملة بأسلوب APA 7 في ملف SOURCES.md وصفحة «المصادر العلمية والأبحاث المرجعية» في التطبيق.", "الصدق العلمي")
REF_AR = [
    ("المخاطر الخمسة للرحلات الفضائية البشرية", "برنامج أبحاث الإنسان – ناسا (د.ت.)"),
    ("معيار ناسا للنظم البشرية في الرحلات الفضائية – المجلد 1: صحة الطاقم", "ناسا (2023)"),
    ("تقرير الأدلة: خطر عدم تحمّل الانتصاب عند العودة إلى الجاذبية", "برنامج أبحاث الإنسان – ناسا (2015)"),
    ("متلازمة العين والأعصاب المرتبطة بالرحلات الفضائية (SANS): مراجعة وتحديث", "لي وآخرون (2020) – npj Microgravity"),
    ("انتشار نقص النوم واستخدام المنوّمات لدى رواد الفضاء قبل الرحلة وأثناءها وبعدها", "بارجر وآخرون (2014) – The Lancet Neurology"),
    ("الكالسيوم في الرحلات الفضائية: آثاره على صحة الرواد وعمليات المركبة", "سميث وآخرون (2012) – Nutrients"),
    ("قياسات الإشعاع الفضائي خلال مهمة أرتميس 1 القمرية", "جورج وآخرون (2024) – Nature"),
    ("قيمة نظام دعم القرار السريري للعمليات الطبية المستقلة عن الأرض", "قدرات الطب الاستكشافي – ناسا (2022)"),
    ("التعلّم الآلي للتنبؤ بأداء الفريق في مهمات HERA (من خصائص الكلام)", "ميشرا وآخرون (2026)"),
    ("إعادة استخدام البيانات والوصول المفتوح والخصوصية في أرشيف بيانات علوم الحياة", "أرشيف بيانات علوم الحياة – ناسا (2024)"),
]
for i, (t_, who) in enumerate(REF_AR):
    col = i % 2
    x = W - 0.6 - 5.95 - col * 6.15
    y = 1.9 + (i // 2) * 0.98
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, 5.95, 0.88, fill=CARD, line=CYAN if col == 0 else GOLD, round_=0.2)
    text(s, x + 0.15, y + 0.02, 5.2, 0.84, [[(t_, WHITE, True)], [(who, MUTED, False)]], 15, spacing=0, anchor=MSO_ANCHOR.MIDDLE)
    shape(s, MSO_SHAPE.OVAL, x + 5.4, y + 0.22, 0.44, 0.44, fill=CYAN if col == 0 else GOLD)
    text(s, x + 5.4, y + 0.22, 0.44, 0.44, str(i + 1), 15, NAVY, True, "c", MSO_ANCHOR.MIDDLE)

# 18 — Thank you
COUNT[0] += 1
s = prs.slides.add_slide(BLANK)
background(s, 99)
for d, col in ((3.2, CYAN), (4.4, GOLD)):
    shape(s, MSO_SHAPE.OVAL, W / 2 - d / 2, 1.9 - d / 2 + 0.6, d, d, line=col, lw=1)
text(s, 0.8, 1.0, W - 1.6, 1.4, "شكرًا لكم", 80, WHITE, True, "c", MSO_ANCHOR.MIDDLE)
shape(s, MSO_SHAPE.RECTANGLE, W / 2 - 1.5, 3.35, 3.0, 0.07, fill=GOLD)
text(s, 0.8, 3.6, W - 1.6, 0.9, "BÖVD — الحالة · السبب · الخطوة التالية · بمن تتصل", 32, CYAN, True, "c")
text(s, 0.8, 4.6, W - 1.6, 0.8, "انقر start.bat · ‎127.0.0.1:8765‎ · كلمة المرور التجريبية astra2026", 22, WHITE, align="c")
s.notes_slide.notes_text_frame.text = "ادعُ لطرح الأسئلة واعرض التشغيل الحي."

prs.save(str(OUT))
print("saved", OUT)
