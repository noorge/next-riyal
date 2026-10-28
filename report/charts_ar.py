"""Arabic, right-to-left versions of the three charts in the executive summary.

Runs the code cells of analysis.ipynb (so every number is the notebook's own),
then redraws 4_2, 5_2 and 6_1 with Arabic labels into outputs/figures/ar/.

    python report/charts_ar.py        (from the project root, after the notebook runs clean)
"""
import os
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import nbformat
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
import viz

# ---- run the notebook's code, without re-saving its English figures ---------------
from IPython.display import display
ns = {"display": display}
real_save, viz.save = viz.save, lambda fig, name: None
plt.show = lambda *a, **k: plt.close("all")
for cell in nbformat.read(ROOT / "analysis.ipynb", 4).cells:
    if cell.cell_type == "code":
        exec("\n".join(l for l in cell.source.splitlines() if not l.lstrip().startswith(("%", "!"))), ns)
plt.close("all")
viz.save = real_save

# ---- Arabic style: Tajawal, mirrored layouts ----------------------------------------
def chart_font(path):
    """Tajawal for matplotlib. matplotlib does not join Arabic letters, so viz.ar() uses the
    presentation-form characters; Tajawal maps the joined forms but not the isolated ones,
    which look exactly like the base letter. Map those (and the Arabic decimal/thousands
    separators) to existing glyphs in a temporary copy."""
    import tempfile
    import unicodedata
    from fontTools.ttLib import TTFont
    font = TTFont(path)
    for table in font["cmap"].tables:
        if not table.isUnicode():
            continue
        cmap = table.cmap
        for code in range(0xFE70, 0xFEFD):
            d = unicodedata.decomposition(chr(code)).split()
            if code not in cmap and len(d) == 2 and d[0] == "<isolated>" and int(d[1], 16) in cmap:
                cmap[code] = cmap[int(d[1], 16)]
        cmap.setdefault(0x066B, cmap[ord(",")])   # Arabic decimal separator
        cmap.setdefault(0x066C, cmap[ord(",")])   # Arabic thousands separator
    out = Path(tempfile.gettempdir()) / f"chart-{path.name}"
    font.save(out)
    return out


for f in (ROOT / "report/fonts").glob("*.ttf"):
    font_manager.fontManager.addfont(str(chart_font(f)))
viz.setup(lang="ar")
matplotlib.rcParams["font.sans-serif"] = ["Tajawal", "Segoe UI", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
viz.FIG = ROOT / "outputs/figures/ar"
ar = viz.ar

DIGITS = str.maketrans("0123456789-%", "٠١٢٣٤٥٦٧٨٩−٪")
def n(text):
    """Western digits -> Arabic-Indic digits, as in the report (a full stop stays one)."""
    return re.sub(r"(?<=\d)\.(?=\d)", "٫", str(text)).translate(DIGITS)


def signed(v):
    """+8 / −14 / 0 in Arabic-Indic digits, kept left to right like any number."""
    return n(f"{v:+d}") if v else n("0")


def label_edge(fig, ax):
    """Right edge of the chart's outermost text (category labels, value-axis label), in axes and figure
    fractions. In a right-to-left chart that is where the eye expects the title to start."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    parts = [ax.get_window_extent(r)] + [t.get_window_extent(r) for t in ax.get_yticklabels() if t.get_text()]
    if ax.yaxis.label.get_text():
        parts.append(ax.yaxis.label.get_window_extent(r))
    right = max(b.x1 for b in parts)
    return ax.transAxes.inverted().transform((right, 0))[0], fig.transFigure.inverted().transform((right, 0))[0]


def title(fig, ax, headline, sub):
    """viz.title, aligned with the labels' right edge instead of the plot's, so the chart reads as centred."""
    x_ax, _ = label_edge(fig, ax)
    legend_row = 0
    if ax.get_legend() is not None:
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, loc="lower right", bbox_to_anchor=(x_ax, 1.0), ncol=len(labels),
                  handlelength=1, handleheight=1, borderaxespad=0.2, frameon=False)
        legend_row = 22
    ax.annotate(ar(headline), xy=(x_ax, 1), xycoords="axes fraction", xytext=(0, 24 + legend_row),
                textcoords="offset points", fontsize=13.5, fontweight="semibold", color=viz.INK, va="bottom", ha="right")
    ax.annotate(ar(sub), xy=(x_ax, 1), xycoords="axes fraction", xytext=(0, 5 + legend_row),
                textcoords="offset points", fontsize=10, color=viz.INK_2, va="bottom", ha="right")


def note(fig, ax, text):
    """viz.note, aligned with the same right edge."""
    _, x_fig = label_edge(fig, ax)
    fig.text(x_fig, -0.02, ar(text), fontsize=8.5, color=viz.MUTED, ha="right", va="top")


REGION = {"Riyadh": "الرياض", "Makkah": "مكة المكرمة", "Madinah": "المدينة المنورة", "Qassim": "القصيم",
          "Eastern": "الشرقية", "Asir": "عسير", "Tabuk": "تبوك", "Hail": "حائل", "Northern Borders": "الحدود الشمالية",
          "Jazan": "جازان", "Najran": "نجران", "Al-Bahah": "الباحة", "Al-Jouf": "الجوف"}
CAUSE = {"Feeding": "الإطعام", "Housing": "الإسكان", "Religious": "البرامج الدينية", "Mosques": "المساجد",
         "Health": "الصحة", "Social": "الرعاية الاجتماعية", "Education": "التعليم"}
MONTH = ["محرم", "صفر", "ربيع الأول", "ربيع الآخر", "جمادى الأولى", "جمادى الآخرة",
         "رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة"]
FEATURE = {"Amount": "المبلغ", "Competition": "ازدحام النشر", "Cause": "المجال", "Beneficiaries": "عدد المستفيدين",
           "Association's track record": "سجل الجمعية", "Hijri month": "الشهر الهجري",
           "Days until salary day": "الأيام المتبقية حتى يوم الراتب", "Amount per beneficiary": "المبلغ لكل مستفيد",
           "Weekday": "يوم النشر", "Association's earlier postings": "عدد فرص الجمعية السابقة",
           "Target group": "الفئة المستفيدة", "Region": "المنطقة", "Ehsan section": "قسم إحسان"}

# ---- 4.2 speed by Hijri month: Muharram on the right ------------------------------
months, TOL = ns["months"], ns["TOL"]
names = [MONTH[ns["HIJRI_MONTHS"].index(m)] for m in months.index]
fig, ax = plt.subplots(figsize=(10, 4.6))
x = np.arange(12)[::-1]                       # first month at the right
colors = [viz.DIVERGING[2] if round(v) < -TOL else viz.DIVERGING[0] if round(v) > TOL else viz.CONTEXT
          for v in months.vs_year]
ax.bar(x, months.vs_year, width=0.62, color=colors)
ax.axhspan(-TOL, TOL, color=viz.CONTEXT, alpha=0.18, lw=0)
ax.axhline(0, color=viz.MUTED, lw=0.8)
for xi, v in zip(x, months.vs_year):
    ax.text(xi, v + (0.6 if v >= 0 else -0.6), signed(round(v)), ha="center",
            va="bottom" if v >= 0 else "top", fontsize=10, color=viz.INK_2)
ax.set_xticks(x, ["\n".join(ar(w) for w in m.split(" ", 1)) for m in names], fontsize=10)   # two-word months on two lines
ax.set_ylim(months.vs_year.min() - 4, months.vs_year.max() + 4)
ax.yaxis.tick_right()
ax.yaxis.set_label_position("right")
ax.spines["left"].set_visible(False)
ax.spines["right"].set_visible(True)
ax.yaxis.set_major_formatter(lambda v, _: signed(round(v)))
ax.grid(axis="x", visible=False)
ax.set_ylabel(ar("الفرق عن متوسط السنة (نقاط)"))
slow = MONTH[ns["HIJRI_MONTHS"].index(months.vs_year.idxmin())]
fast = MONTH[ns["HIJRI_MONTHS"].index(months.vs_year.idxmax())]
title(fig, ax, f"{slow} أبطأ الأشهر في التمويل، و{fast} أسرعها",
          "نسبة الفرص المموّلة خلال أسبوع، مطروحًا منها متوسط السنة الهجرية نفسها (نقاط مئوية)")
note(fig, ax, n(f"المنطقة المظللة: ±{TOL} نقاط، وهي الوتيرة الطبيعية. الفرص المكتملة منذ أغسطس 2021 (بعد فترة الإطلاق)، "
                "بحسب الشهر الهجري للنشر."))
viz.save(fig, "4_2_speed_by_month")
plt.close(fig)

# ---- 5.2 drivers -------------------------------------------------------------------
imp = ns["importance"]
fig, ax = plt.subplots(figsize=(8.5, 5.2))
labels = [FEATURE[k] for k in imp.index]
viz.hbar(ax, labels, imp.values, highlight=labels[:2], fmt=lambda v: n(f"{v:.3f}"))
ax.xaxis.set_major_formatter(lambda v, _: n(f"{v:.2f}"))
title(fig, ax, f"{labels[0]} و{labels[1]} أهم العوامل، والمنطقة لا تضيف شيئًا",
          "انخفاض دقة النموذج عند خلط قيم العامل عشوائيًا (آخر ١٥ شهرًا)")
note(fig, ax, "كلما طال العمود زاد اعتماد النموذج على العامل. القيم السالبة (بلا أثر) تظهر صفرًا.")
viz.save(fig, "5_2_drivers")
plt.close(fig)

# ---- 6.1 priority pairs: bars grow leftwards, speed column on the left -------------
NEG = "فجوة في النشر والتمويل: منح أو تمويل مطابق"
SUP = "فجوة في النشر: دعم الجمعيات لتنشر أكثر"
neg, sup = ns["neglected"], ns["supply"]
pairs = __import__("pandas").concat([neg.assign(kind=NEG), sup.assign(kind=SUP)]).iloc[::-1]
pairs["label"] = [f"{REGION[r]} · {CAUSE[c]}" for r, c in zip(pairs.Region, pairs.Cause)]
fig, ax = plt.subplots(figsize=(9.5, 6.4))
for kind, color in {NEG: viz.DIVERGING[2], SUP: viz.BLUE}.items():
    rows = (pairs.kind == kind).to_numpy()
    ax.barh(np.flatnonzero(rows), pairs.Coverage[rows], height=0.62, color=color, label=ar(kind))
for i, (v, week, vs) in enumerate(zip(pairs.Coverage, pairs["Funded within a week"], pairs["vs national"])):
    ax.text(v + 0.012, i, n(f"{v:.2f}"), va="center", ha="right", fontsize=10, color=viz.INK)
    pts = int(vs.replace(" pts", ""))
    ax.text(1.08, i, ar(n(f"{week:.0%}")) + "     " + signed(pts), va="center", ha="right",
            fontsize=9.5, color=viz.INK_2)
ax.text(1.08, len(pairs) - 0.4, "\n".join(ar(t) for t in ("اكتمل تمويلها خلال أسبوع", "والفرق عن الوطني (نقاط)")),
        va="bottom", ha="right", fontsize=9.5, color=viz.MUTED)
ax.set_yticks(range(len(pairs)), [ar(l) for l in pairs.label], fontsize=10.5)
ax.axvline(1, color=viz.MUTED, lw=1, ls=(0, (3, 3)))
ax.text(0.985, len(pairs) - 0.4, ar("الحصة المتوقعة"), ha="left", va="bottom", fontsize=9.5, color=viz.MUTED)
ax.set_xlim(0, 1.42)
ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
ax.xaxis.set_major_formatter(lambda v, _: n(f"{v:.1f}"))
ax.invert_xaxis()
ax.yaxis.tick_right()
viz.only_grid(ax, "x")
ax.legend()
title(fig, ax, n(f"{len(neg)} تركيبات تحتاج إلى تمويل، و{len(sup)} تحتاج إلى نشر أكثر"),
          "التغطية: قيمة الفرص المنشورة لكل ساكن مقارنةً بالمعدل الوطني للمجال (١ = الحصة المتوقعة)")
note(fig, ax, n("التركيبات التي تغطيتها أقل من 0.75 ولديها 20 فرصة على الأقل. السرعة مقارنةً بالنسبة الوطنية للمجال نفسه "
                "منذ أغسطس 2021. السكان: تعداد الهيئة العامة للإحصاء 2022."))
viz.save(fig, "6_1_priorities")
plt.close(fig)
print("saved:", sorted(p.name for p in viz.FIG.glob("*.png")))
