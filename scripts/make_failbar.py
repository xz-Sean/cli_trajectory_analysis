#!/usr/bin/env python3
"""Number of failed trajectories, by scaffold (agent) and by model, with brand logos above
each bar and a right-hand legend. Harmonious soft palette. Counts are the true v2 fail counts
(1184 total). Model logos load from logos/<name>.png; scaffold logos are text placeholders
(mSWE / OH / T2) until real ones are supplied."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
import colorsys

plt.rcParams.update({'font.family': 'DejaVu Sans', 'axes.spines.top': False,
                     'axes.spines.right': False})

# ---------------- data (true v2 fail counts) ----------------
SCAFFOLDS = [
    ('miniswe',   428, 'miniswe',   'mini SWE-agent', '#8E86CF'),
    ('openhands', 407, 'openhands', 'OpenHands',      '#6F9FD0'),
    ('terminus2', 349, 'terminus2', 'Terminus2',      '#5FBEAC'),
]
MODELS = [
    ('qwen',     183, 'qwen',     'Qwen 3',          '#6FBF9A'),
    ('gemini',   181, 'gemini',   'Gemini 2.5 Pro',  '#8FC57E'),
    ('kimi',     177, 'kimi',     'Kimi K2',         '#C9BE72'),
    ('claude',   167, 'claude',   'Claude 4 Sonnet', '#DCA46E'),
    ('devstral', 165, 'devstral', 'Devstral 2',      '#D98C72'),
    ('deepseek', 162, 'deepseek', 'DeepSeek V3.2',   '#D082A6'),
    ('gpt5',     149, 'gpt5',     'GPT-5',           '#A98CD0'),
]
INK = '#222222'
SAT_FACTOR = 1.35          # bump colour saturation a touch (hue & lightness unchanged)

def SAT(hexc, f=SAT_FACTOR):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    r, g, b = colorsys.hsv_to_rgb(h, min(1.0, s * f), v)
    return '#%02x%02x%02x' % (round(r * 255), round(g * 255), round(b * 255))

# ---------------- logo loading (white->transparent, crop to content) ----------------
def load_logo(stem):
    img = mpimg.imread(f'logos/{stem}.png').astype(float)
    if img.max() > 1: img /= 255.0
    if img.ndim == 2: img = np.dstack([img] * 3)
    if img.shape[2] == 3: img = np.dstack([img, np.ones(img.shape[:2])])
    white = (img[:, :, 0] > 0.93) & (img[:, :, 1] > 0.93) & (img[:, :, 2] > 0.93)
    img[white, 3] = 0.0
    ys, xs = np.where(img[:, :, 3] > 0.05)
    if len(ys):
        m = 2
        img = img[max(0, ys.min() - m):ys.max() + 1 + m, max(0, xs.min() - m):xs.max() + 1 + m]
    return img

LOGOS = {stem: load_logo(stem) for _, _, stem, _, _ in SCAFFOLDS + MODELS}

def place_logo(ax, stem, x, y, disp_in):
    img = LOGOS[stem]
    zoom = disp_in * 72.0 / max(img.shape[0], img.shape[1])   # normalize by the LARGER side
    ax.add_artist(AnnotationBbox(OffsetImage(img, zoom=zoom), (x, y),
                  xycoords='data', frameon=False, box_alignment=(0.5, 0.5)))

# ---------------- figure ----------------
fig = plt.figure(figsize=(13, 7.2))
ax = fig.add_axes([0.058, 0.17, 0.64, 0.75])

sx = [0, 1, 2]
mx = [3.6, 4.6, 5.6, 6.6, 7.6, 8.6, 9.6]
BW = 0.66
trans = ax.get_xaxis_transform()

for x, (k, c, stem, name, col) in zip(sx, SCAFFOLDS):
    ax.bar(x, c, BW, color=SAT(col), zorder=3)
    ax.text(x, c + 8, str(c), ha='center', va='bottom', fontsize=14, fontweight='bold', color=INK)
    place_logo(ax, stem, x, c + 58, 0.40)
for x, (k, c, stem, name, col) in zip(mx, MODELS):
    ax.bar(x, c, BW, color=SAT(col), zorder=3)
    ax.text(x, c + 8, str(c), ha='center', va='bottom', fontsize=13.5, fontweight='bold', color=INK)
    place_logo(ax, stem, x, c + 58, 0.40)

ax.set_ylim(0, 560)
ax.set_xlim(-0.65, 10.25)
ax.set_yticks(range(0, 501, 50))
ax.set_ylabel('Number of Failed Trajectories', fontsize=13, fontweight='bold')
ax.set_title('Number of Failed Trajectories', fontsize=20, fontweight='bold', loc='left', pad=16)
ax.set_xticks(sx + mx)
ax.set_xticklabels([k for k, *_ in SCAFFOLDS] + [k for k, *_ in MODELS],
                   rotation=28, ha='right', fontsize=11)
ax.tick_params(length=0)
ax.yaxis.grid(True, color='#e8e8e8', lw=0.9, zorder=0)
ax.set_axisbelow(True)
ax.axvline(2.8, color='#d6d6d6', lw=1.0, ls=(0, (5, 5)), zorder=1)

def bracket(x0, x1, label):
    ax.plot([x0, x0, x1, x1], [-0.20, -0.225, -0.225, -0.20], transform=trans, color='#555',
            lw=1.3, clip_on=False)
    ax.text((x0 + x1) / 2, -0.275, label, transform=trans, ha='center', va='top',
            fontsize=13, fontweight='bold', color=INK)
bracket(-0.35, 2.35, 'by scaffold (agent)')
bracket(3.25, 9.95, 'by model')

# ---------------- right-hand legend (own axes, data coords 0..1) ----------------
lg = fig.add_axes([0.745, 0.05, 0.245, 0.90]); lg.set_xlim(0, 1); lg.set_ylim(0, 1); lg.axis('off')
def lg_logo(stem, x, y, disp_in=0.32):
    img = LOGOS[stem]
    zoom = disp_in * 72.0 / max(img.shape[0], img.shape[1])
    lg.add_artist(AnnotationBbox(OffsetImage(img, zoom=zoom), (x, y),
                  xycoords='data', frameon=False, box_alignment=(0.5, 0.5)))

lg.text(0.0, 0.965, 'Scaffolds (Agents)', fontsize=14, fontweight='bold', color=INK)
for i, (k, c, stem, name, col) in enumerate(SCAFFOLDS):
    y = 0.90 - i * 0.060
    lg_logo(stem, 0.10, y)
    lg.text(0.24, y, name, va='center', fontsize=12.5, color=INK)

lg.plot([0.0, 1.0], [0.685, 0.685], color='#dcdcdc', lw=1.0)
lg.text(0.0, 0.635, '7 Language Models', fontsize=14, fontweight='bold', color=INK)
for i, (k, c, stem, name, col) in enumerate(MODELS):
    y = 0.565 - i * 0.075
    lg_logo(stem, 0.10, y)
    lg.text(0.24, y, name, va='center', fontsize=12.5, color=INK)

fig.savefig('figures/fig_failbar.png', dpi=200, bbox_inches='tight')
fig.savefig('figures/fig_failbar.pdf', bbox_inches='tight')
print('wrote figures/fig_failbar.{png,pdf}')
