"""Shared look for every chart and table in analysis.ipynb.

One palette, one font, recessive axes, a left-aligned title that states the
takeaway, and small HTML helpers (stat tiles, takeaway boxes) whose numbers
are computed in the notebook, so they stay correct on every re-run.
"""
from pathlib import Path

import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from IPython.display import HTML, display

try:  # Arabic needs shaping + right-to-left reordering to render in matplotlib
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:  # pip install arabic-reshaper python-bidi
    arabic_reshaper = None

# ---- Palette (validated: scripts/validate_palette.js, light mode) -------------
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
          "#e87ba4", "#008300", "#6250d6", "#e34948"]   # fixed order, never cycled
BLUE = SERIES[0]          # the one accent: the thing the chart is about
CONTEXT = "#c3c2b7"       # everything else, in gray
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING = ("#2a78d6", "#f0efec", "#e34948")   # blue <- gray -> red

SURFACE = "#fcfcfb"
INK = "#0b0b0b"           # titles, values
INK_2 = "#52514e"         # subtitles, labels
MUTED = "#898781"         # axis ticks, notes
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

SECTION_COLORS = {"projects": SERIES[0], "mosques": SERIES[1], "housing": SERIES[2]}

FIG = Path("outputs/figures")
RTL = False   # set by setup(lang="ar"): mirror layouts for the Arabic notebook


def setup(lang="en"):
    """Apply the notebook-wide matplotlib style. lang="ar" mirrors chart layout
    right-to-left (titles, notes and category labels on the right; bars grow
    leftwards). Time axes keep years running left to right, as is usual in
    Arabic publications."""
    global RTL
    RTL = lang == "ar"
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
        "font.size": 10.5,
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE, "figure.dpi": 110, "savefig.dpi": 200,
        "axes.edgecolor": AXIS, "axes.linewidth": 1, "axes.labelcolor": INK_2,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 1, "grid.linestyle": "-",
        "axes.axisbelow": True, "axes.prop_cycle": mpl.cycler(color=SERIES),
        "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.labelcolor": INK_2, "ytick.labelcolor": INK_2,
        "xtick.major.size": 0, "ytick.major.size": 0,
        "lines.linewidth": 2, "lines.solid_capstyle": "round",
        "legend.frameon": False, "legend.fontsize": 9.5,
    })


def ar(text):
    """Make Arabic text render correctly in a chart (no-op for other text)."""
    if not isinstance(text, str) or arabic_reshaper is None:
        return text
    if not any("؀" <= ch <= "ۿ" for ch in text):
        return text
    return get_display(arabic_reshaper.reshape(text))


def compact(x, _=None):
    """1,284 -> 1.3K, 4,200,000 -> 4.2M, 1.8e9 -> 1.8B."""
    for div, unit in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(x) >= div:
            v = x / div
            return f"{v:.0f}{unit}" if v >= 10 else f"{v:.1f}{unit}".replace(".0", "")
    return f"{x:,.0f}"


def title(ax, headline, sub=None):
    """Left-aligned headline (the takeaway) and an optional subtitle (what is plotted)."""
    side = "right" if RTL else "left"
    leg = ax.get_legend()
    if leg is not None:   # legend gets its own row between subtitle and plot
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, loc="lower right" if RTL else "lower left",
                  bbox_to_anchor=(1 if RTL else 0, 1.0), ncol=len(labels),
                  handlelength=1, handleheight=1, borderaxespad=0.2, frameon=False)
    # Offsets in points (not axes fractions) so short and tall charts look the same.
    legend_row = 22 if leg is not None else 0
    ax.set_title(ar(headline), loc=side, fontsize=13.5, fontweight="semibold",
                 color=INK, pad=(24 if sub else 10) + legend_row)
    if sub:
        ax.annotate(ar(sub), xy=(1 if RTL else 0, 1), xycoords="axes fraction",
                    xytext=(0, 5 + legend_row), textcoords="offset points",
                    fontsize=10, color=INK_2, va="bottom", ha=side)


def only_grid(ax, axis="x"):
    """Keep gridlines on the value axis only; hide the category-axis spine."""
    ax.grid(axis="y" if axis == "x" else "x", visible=False)
    if axis == "x":
        ax.spines["left"].set_visible(False)
    else:
        ax.spines["bottom"].set_color(AXIS)


def hbar(ax, labels, values, highlight=None, fmt=compact, color=BLUE, extra=None):
    """Horizontal bars, largest on top, value at each bar tip.
    `highlight`: labels drawn in the accent; the rest go gray.
    `extra`: optional second fact per bar, shown after the value in muted ink."""
    labels, values = list(labels)[::-1], list(values)[::-1]
    extra = list(extra)[::-1] if extra is not None else [None] * len(labels)
    colors = [color if highlight is None or l in highlight else CONTEXT for l in labels]
    ax.barh([ar(l) for l in labels], values, height=0.62, color=colors)
    vmax = max(values) if values else 1
    for i, (v, e) in enumerate(zip(values, extra)):
        t = ax.text(v + vmax * 0.01, i, fmt(v), va="center", fontsize=9.5, color=INK_2,
                    ha="right" if RTL else "left")
        if e:
            ax.annotate(f"  ·  {ar(e)}", xycoords=t, xy=(0 if RTL else 1, 0.5), va="center",
                        ha="right" if RTL else "left", fontsize=9, color=MUTED)
    ax.xaxis.set_major_formatter(FuncFormatter(compact))
    ax.set_xlim(0, vmax * (1.32 if any(extra) else 1.12))
    only_grid(ax, "x")
    if RTL:  # bars grow right-to-left from a baseline on the right, labels on the right
        ax.invert_xaxis()
        ax.yaxis.tick_right()
    return ax



def vbar(ax, labels, values, highlight=None, fmt=compact, color=BLUE):
    """Columns in the given order (e.g. ordered bins), value on each cap."""
    labels, values = list(labels), list(values)
    colors = [color if highlight is None or l in highlight else CONTEXT for l in labels]
    ax.bar([ar(l) for l in labels], values, width=0.62, color=colors)
    vmax = max(values) if values else 1
    for i, v in enumerate(values):
        ax.text(i, v + vmax * 0.015, fmt(v), ha="center", va="bottom", fontsize=9.5, color=INK_2)
    ax.yaxis.set_major_formatter(FuncFormatter(compact))
    ax.set_ylim(0, vmax * 1.12)
    ax.grid(axis="x", visible=False)
    ax.spines["left"].set_visible(False)
    if RTL:
        ax.invert_xaxis()
    return ax


def hbar_stack(ax, labels, parts, colors=None, total_fmt=compact):
    """Horizontal stacked bars. `parts`: {series name: values}, drawn in order
    with a 2px surface gap between segments; the total sits at the bar tip."""
    labels = list(labels)[::-1]
    colors = colors or SERIES
    left = [0.0] * len(labels)
    for (name, vals), col in zip(parts.items(), colors):
        vals = list(vals)[::-1]
        ax.barh([ar(l) for l in labels], vals, left=left, height=0.62, color=col,
                edgecolor=SURFACE, linewidth=2, label=ar(name))
        left = [a + b for a, b in zip(left, vals)]
    vmax = max(left) if left else 1
    for i, v in enumerate(left):
        ax.text(v + vmax * 0.01, i, total_fmt(v), va="center", fontsize=9.5, color=INK_2,
                ha="right" if RTL else "left")
    ax.xaxis.set_major_formatter(FuncFormatter(compact))
    ax.set_xlim(0, vmax * 1.12)
    only_grid(ax, "x")
    ax.legend(loc="lower right", ncol=len(parts), bbox_to_anchor=(1, 1.0), handlelength=1, handleheight=1)
    if RTL:
        ax.invert_xaxis()
        ax.yaxis.tick_right()
    return ax


def hbar_pair(ax, labels, before, after, names=("Raw", "Clean"), fmt=lambda v: f"{v:.0%}"):
    """Before/after per category: gray bar (before) above the accent bar (after),
    each labelled at its tip."""
    labels, before, after = list(labels)[::-1], list(before)[::-1], list(after)[::-1]
    y = range(len(labels))
    h = 0.34
    ax.barh([i + h / 2 for i in y], before, height=h, color=CONTEXT, label=ar(names[0]))
    ax.barh([i - h / 2 for i in y], after, height=h, color=BLUE, label=ar(names[1]))
    for i, (b, a) in enumerate(zip(before, after)):
        ax.text(b + 0.01, i + h / 2, fmt(b), va="center", fontsize=9, color=MUTED)
        ax.text(a + 0.01, i - h / 2, fmt(a), va="center", fontsize=9.5, color=INK)
    ax.set_yticks(list(y), [ar(l) for l in labels])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlim(0, 1.12)
    only_grid(ax, "x")
    ax.legend(loc="lower right", ncol=2, bbox_to_anchor=(1, 1.0), handlelength=1, handleheight=1)
    if RTL:
        ax.invert_xaxis()
        ax.yaxis.tick_right()
    return ax


def _luminance(rgb):
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb[:3]]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def heat(ax, table, center=1.0, log=True, low_is_bad=True, fmt=lambda v: f"{v:.1f}", mask=None,
         limits=None):
    """Diverging heatmap (red <- gray -> blue) around `center`. Values below
    the center are red when `low_is_bad`. `mask`: cells to leave blank (e.g.
    too few observations). Labels sit in each cell, ink chosen by luminance."""
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
    lo_col, mid, hi_col = (DIVERGING[2], DIVERGING[1], DIVERGING[0]) if low_is_bad else DIVERGING
    cmap = LinearSegmentedColormap.from_list("div", [lo_col, mid, hi_col])
    vals = table.to_numpy(dtype=float)
    z = np.log2(vals / center) if log else vals - center
    lim = limits or np.nanmax(np.abs(z[np.isfinite(z)]))
    z = np.clip(z, -lim, lim)
    if mask is not None:
        z = np.where(mask.to_numpy(), np.nan, z)
    norm = TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim)
    cmap.set_bad(SURFACE)
    ax.imshow(z, cmap=cmap, norm=norm, aspect="auto")
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            if np.isnan(vals[i, j]):
                continue
            if np.isnan(z[i, j]):
                ax.text(j, i, "–", ha="center", va="center", fontsize=9, color=MUTED)
                continue
            ink = "#ffffff" if _luminance(cmap(norm(z[i, j]))) < 0.4 else INK
            ax.text(j, i, fmt(vals[i, j]), ha="center", va="center", fontsize=9, color=ink)
    ax.set_xticks(range(vals.shape[1]), [ar(c) for c in table.columns])
    ax.set_yticks(range(vals.shape[0]), [ar(r) for r in table.index])
    ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xticks(np.arange(-.5, vals.shape[1]), minor=True)
    ax.set_yticks(np.arange(-.5, vals.shape[0]), minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=2)   # 2px surface gap between cells
    ax.tick_params(which="minor", length=0)
    return ax

def note(fig, text):
    """Source / caveat line under the chart."""
    fig.text(0.99 if RTL else 0.01, -0.02, ar(text), fontsize=8.5, color=MUTED,
             ha="right" if RTL else "left", va="top")


def save(fig, name):
    """Save to outputs/figures/<name>.png (used in the report and the X post)."""
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight")


# ---- HTML pieces for the notebook ---------------------------------------------
# HTML pieces inherit the notebook theme's text color, so they read in light and
# dark mode; only translucent tints and the dark-safe accent step are fixed.
_BOX = "font-family:Segoe UI,system-ui,sans-serif;box-sizing:border-box;max-width:100%;"  # unquoted: it sits inside style='...'
ACCENT = "#3987e5"
TINT = "rgba(57,135,229,.12)"


def _dir():
    return "direction:rtl;text-align:right;" if RTL else ""


def tiles(items):
    """Row of headline numbers: tiles([("Opportunities", "10,728", "2021–2026"), ...])."""
    cells = "".join(
        f"<div style='box-sizing:border-box;min-width:0;padding:14px 16px;background:{TINT};"
        f"border-radius:10px;white-space:normal;overflow-wrap:anywhere'>"
        f"<div style='font-size:13px;opacity:.75'>{label}</div>"
        f"<div style='font-size:28px;font-weight:600;margin:2px 0'>{value}</div>"
        f"<div style='font-size:12px;opacity:.6'>{sub}</div></div>"
        for label, value, sub in items)
    # a grid (not flex) so every tile in a row gets the same width and long text wraps inside its tile
    display(HTML(f"<div style='{_BOX}{_dir()}display:grid;gap:12px;margin:8px 0;"
                 f"grid-template-columns:repeat(auto-fit,minmax(160px,1fr))'>{cells}</div>"))


def takeaway(text):
    """The one sentence a reader should remember from the cell above."""
    edge, radius = ("right", "8px 0 0 8px") if RTL else ("left", "0 8px 8px 0")
    label = "الخلاصة." if RTL else "Takeaway."
    display(HTML(
        f"<div style='{_BOX}{_dir()}border-{edge}:4px solid {ACCENT};background:{TINT};"
        f"padding:10px 14px;margin:10px 0;border-radius:{radius};font-size:14px'>"
        f"<b>{label}</b> {text}</div>"))


def table(df, money=(), pct=(), ints=(), decimals=None, caption=None):
    """Styled pandas table: no index, thousands separators, recessive header.
    decimals maps a column to its number of decimal places."""
    fmt = {**{c: "{:,.0f}" for c in ints}, **{c: "SAR {:,.0f}" for c in money},
           **{c: "{:.0%}" for c in pct}, **{c: f"{{:.{n}f}}" for c, n in (decimals or {}).items()}}
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    sty = (df.style.hide(axis="index").format(fmt, na_rep="–")
           .set_properties(**{"text-align": "left"})
           .set_properties(subset=numeric, **{"text-align": "right"})
           .set_table_styles([
               {"selector": "th", "props": "opacity:.8;font-weight:600;text-align:left;"
                                           "border-bottom:1px solid rgba(127,127,127,.5);padding:6px 10px"},
               {"selector": "td", "props": "padding:5px 10px;border-bottom:1px solid rgba(127,127,127,.2)"},
               {"selector": "", "props": "border-collapse:collapse;font-size:13px"}]))
    if caption:
        sty = sty.set_caption(caption).set_table_styles(
            [{"selector": "caption", "props": "caption-side:top;text-align:left;"
                                              "font-weight:600;padding-bottom:6px"}],
            overwrite=False)
    return sty
