#!/usr/bin/env python3
"""RQ1 case study (v3) — git-workflow-hack · terminus2 · gpt-5, with the three timestamps
t_err / t_lock / t_obs marked on the real transcript. v3 styling (deep text colors, larger
fonts, distinct backgrounds, full-text-width) + a left real-step-number badge coloured by
timestamp (purple t_err / green t_lock / blue t_obs — same palette as the RQ1 CDF figure).
True step indices: t_err=2 (silent cd), t_lock=6 (git branch), t_obs=23 (git add)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import textwrap
import palette as P

plt.rcParams['text.parse_math'] = False
MONO, SANS = 'DejaVu Sans Mono', 'DejaVu Sans'

# v3 text + box colors
C_THINK, C_CMD, C_OUT, C_TITLE = '#000000', '#0d6526', '#171717', '#101010'
TERM_BG, TERM_EC = '#e8ebef', '#cdd3da'
C_GAP = '#1f1f1f'
# error visual language shared with the RQ2 cards: red badge + red box + red label
BADGE_N = '#566e83'                       # neutral step badge (non-error turns)
RED     = '#c83232'                        # error red (badge, chip, box border)
RED_HL  = '#f6cdc6'                        # deeper pale-red background (t_err turn only)
ERR_BG, ERR_EC = '#f6d4cd', '#c83232'      # red-bordered error box (t_err only)
# per timestamp: (badge colour, chip colour, is_error)
TS = {
  't_err':  (RED,     RED,          True),
  't_lock': (BADGE_N, P.GREEN_DARK, False),
  't_obs':  (BADGE_N, P.BLUE_DARK,  False),
}
FS_TITLE, FS_TH, FS_CMD, FS_OUT, FS_NAME, FS_EXPL, FS_SKIP, FS_BADGE = 14.0, 13.2, 13.0, 12.7, 12.9, 12.6, 12.7, 11.6
LH, WTHINK, WMONO, WEXPL, WSKIP = 1.0, 72, 56, 60, 58
XBADGE, XTHINK, XBOX_L, XBOX_R, XEXPL = 0.034, 0.060, 0.050, 0.982, 0.230
WIDTH, VSCALE = 7.7, 0.235

def wrap(t, w):
    out = []
    for para in t.split('\n'):
        out += textwrap.wrap(para, w) or ['']
    return out

# turn = think / cmd / out / ts(name, step, key) ; or skip
TURNS = [
  {'think': "We're in /app. Locate the repo's .git directory and cd into it before building the site.",
   'cmd': 'REPO_DIR=$(dirname "$(find . -name .git | head -1)"); cd "$REPO_DIR"',
   'out': ['(no output)'],
   'ts': ('t_err', 2, 'decisive error — the cd silently fails; the agent assumes it is inside the repo')},
  {'think': "Set up the git branch, then start scaffolding the site.",
   'cmd': 'git branch --show-current; git checkout -b main',
   'out': ['(no output — still outside the repo)'],
   'ts': ('t_lock', 6, 'lock-in — from here it builds the whole site in /app (wrong dir), irreversibly')},
  {'skip': 'steps 7–22:  writes every page in /app — 16 steps, no error at all'},
  {'think': "Everything's built. Stage and commit the site.",
   'cmd': 'git add -A',
   'out': ['fatal: not a git repository (or any parent): .git'],
   'ts': ('t_obs', 23, 'first observable error — surfaces 17 steps after lock-in')},
]

def turn_h(t):
    if 'skip' in t:
        return len(wrap(t['skip'], WSKIP)) * LH + 0.55
    th = len(wrap(t['think'], WTHINK))
    nb = (len(wrap(t['cmd'], WMONO)) if t.get('cmd') else 0) + len(t.get('out', []))
    ex = len(wrap(t['ts'][2], WEXPL))
    return th * LH + 0.30 + nb * LH + 0.50 + 0.20 + (ex * LH + 0.30) + 0.55

H = 1.55 + sum(turn_h(t) for t in TURNS)
fig = plt.figure(figsize=(WIDTH, VSCALE * H))
ax = fig.add_axes([0.012, 0.012, 0.976, 0.976]); ax.set_xlim(0, 1); ax.set_ylim(0, H); ax.axis('off')
ax.add_patch(FancyBboxPatch((0.004, 0.03), 0.992, H - 0.06, boxstyle='round,pad=0.002,rounding_size=0.10',
             fc='white', ec='#d2d2d2', lw=1.0, zorder=0, mutation_aspect=1 / H))
y = H - 0.55
ax.text(0.030, y, 'git-workflow-hack · terminus2 · gpt-5', fontsize=FS_TITLE, fontweight='bold',
        color=C_TITLE, va='center', family=SANS)
y -= 0.46; ax.plot([0.020, 0.980], [y, y], color='#e3e3e3', lw=0.9); y -= 0.58

for t in TURNS:
    if 'skip' in t:
        lines = wrap(t['skip'], WSKIP)
        for i, ln in enumerate(lines):
            pre = '⋯  ' if i == 0 else '    '; suf = '  ⋯' if i == len(lines) - 1 else ''
            ax.text(0.52, y - LH / 2, pre + ln + suf, fontsize=FS_SKIP, va='center', ha='center',
                    color=C_GAP, style='italic', family=SANS)
            y -= LH
        y -= 0.55; continue

    name, step, expl = t['ts']
    badge_col, chip_col, is_err = TS[name]
    th = len(wrap(t['think'], WTHINK))
    nb = (len(wrap(t['cmd'], WMONO)) if t.get('cmd') else 0) + len(t.get('out', []))
    ex = len(wrap(expl, WEXPL)); t_h = turn_h(t); turn_top = y
    # deeper pale-red background ONLY on the t_err (decisive-error) turn
    if is_err:
        ax.add_patch(FancyBboxPatch((0.012, y - t_h + 0.22), 0.976, t_h - 0.02,
                     boxstyle='round,pad=0.002,rounding_size=0.06', fc=RED_HL, ec='none',
                     zorder=0.5, mutation_aspect=1 / t_h))
    # left step badge (red for the error turn, neutral otherwise)
    ax.plot(XBADGE, turn_top - 0.42, 'o', ms=16, mfc=badge_col, mec='none', zorder=4)
    ax.text(XBADGE, turn_top - 0.42, str(step), fontsize=FS_BADGE - (0.9 if step >= 10 else 0),
            fontweight='bold', color='white', ha='center', va='center', zorder=5, family=SANS)
    # thinking
    for i, ln in enumerate(wrap(t['think'], WTHINK)):
        ax.text(XTHINK, y - LH / 2, ('▸ ' if i == 0 else '  ') + ln, fontsize=FS_TH, va='center',
                style='italic', color=C_THINK, family=SANS, zorder=2)
        y -= LH
    y -= 0.30
    # terminal box: red-bordered on the error turn, neutral grey otherwise
    box_h = nb * LH + 0.50
    bg, ec, lw = (ERR_BG, ERR_EC, 1.5) if is_err else (TERM_BG, TERM_EC, 0.9)
    ax.add_patch(FancyBboxPatch((XBOX_L, y - box_h + 0.18), XBOX_R - XBOX_L, box_h,
                 boxstyle='round,pad=0.003,rounding_size=0.05', fc=bg, ec=ec, lw=lw,
                 zorder=1, mutation_aspect=1 / box_h))
    yy = y - 0.10
    for i, ln in enumerate(wrap(t['cmd'], WMONO)):
        ax.text(XBOX_L + 0.016, yy - LH / 2, ('$ ' if i == 0 else '  ') + ln, fontsize=FS_CMD,
                va='center', color=C_CMD, family=MONO, fontweight='bold', zorder=2); yy -= LH
    for o in t.get('out', []):
        ax.text(XBOX_L + 0.028, yy - LH / 2, o, fontsize=FS_OUT, va='center', color=C_OUT,
                family=MONO, zorder=2); yy -= LH
    y -= box_h + 0.20
    # colour-coded chip (name) + explanation — no strip behind it
    bar_h = ex * LH + 0.30
    cy = y - 0.10 - LH / 2                                  # annotation row centre
    chip_w, chip_h = 0.0162 * len(name) + 0.054, 0.95       # wide enough to wrap the '_'
    ax.add_patch(FancyBboxPatch((XBOX_L + 0.012, cy - chip_h / 2), chip_w, chip_h,
                 boxstyle='round,pad=0.001,rounding_size=0.05', fc=chip_col, ec='none', zorder=3,
                 mutation_aspect=1 / chip_h))
    ax.text(XBOX_L + 0.012 + chip_w / 2, cy, name, fontsize=FS_NAME, va='center', ha='center',
            color='white', family=MONO, fontweight='bold', zorder=4)
    for i, ln in enumerate(wrap(expl, WEXPL)):
        ax.text(XEXPL, cy - i * LH, ln, fontsize=FS_EXPL, va='center',
                color='#222222', family=SANS, zorder=4)
    y -= bar_h + 0.10
    y -= 0.55

fig.savefig('figures/RQ1_case_big.png', dpi=220, bbox_inches='tight')
fig.savefig('figures/RQ1_case_big.pdf', bbox_inches='tight')
print('wrote figures/RQ1_case_big.{png,pdf}  H=%.1f  %sx%.2f in' % (H, WIDTH, VSCALE * H))
