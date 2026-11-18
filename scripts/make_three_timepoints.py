#!/usr/bin/env python3
"""RQ1 three-timepoint CDFs (corrected).
- all three CDFs over the FULL 1184 failed trajectories (same denominator)
- t_err, t_lock reach 100%; t_obs CAPS at 72% because 28% never surface (silent)
- t_err/t_lock: standard median (full-sample 50%). t_obs: median/mean conditional on the
  72% that surface (its mean can only be computed there), stated explicitly.
- means on FULL data, untruncated.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import numpy as np
import palette as P

plt.rcParams.update({'font.size': 9, 'font.family': 'DejaVu Sans',
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.linewidth': 0.9, 'savefig.bbox': 'tight'})

fail = [r for r in json.load(open('data/traj_data_v2_all89tasks.json')) if 't_commit' in r]
N = len(fail)
te = np.array([r['t_err'] for r in fail])
tl = np.array([r['t_commit'] for r in fail])
ts = np.array([r['t_surface'] for r in fail if r.get('t_surface') is not None])
ceil_obs = len(ts) / N                                   # 0.72

XMAX = 55
xs = np.arange(0, XMAX + 1)
cdf = lambda v: np.array([(v <= x).sum() / N * 100 for x in xs])
c_err, c_lock, c_obs = cdf(te), cdf(tl), cdf(ts)

m_err, m_lock = 7, 12                                     # full-sample medians (no nulls)
m_obs = int(np.median(ts))                               # 16, conditional on surfacing
mean_err, mean_lock, mean_obs = te.mean(), tl.mean(), ts.mean()

C = {'err': P.T_ERR, 'lock': P.T_LOCK, 'obs': P.T_OBS}       # shared palette (matches overview)
fig, ax = plt.subplots(figsize=(8.2, 5.0))

ax.step(xs, c_err,  where='post', color=C['err'],  lw=2.7,
        label=fr'$t_{{\mathrm{{err}}}}$   median {m_err},  mean {mean_err:.1f}')
ax.step(xs, c_lock, where='post', color=C['lock'], lw=2.7,
        label=fr'$t_{{\mathrm{{lock}}}}$  median {m_lock},  mean {mean_lock:.1f}')
ax.step(xs, c_obs,  where='post', color=C['obs'],  lw=2.7,
        label=fr'$t_{{\mathrm{{obs}}}}$   median {m_obs},  mean {mean_obs:.1f}  (of the 72% that surface)')

# --- 50% reference line + 72% ceiling (the headline: 28% never surface) ---
ax.axhline(50, ls='--', color='#999', lw=0.9, zorder=1)
ax.axhline(ceil_obs * 100, ls=':', color=C['obs'], lw=1.3, alpha=0.9)
ax.text(XMAX - 0.5, ceil_obs * 100 + 1.6,
        f'{ceil_obs*100:.0f}% ceiling — {(1-ceil_obs)*100:.0f}% of failures NEVER surface (silent)',
        ha='right', va='bottom', fontsize=8.4, color=P.BLUE_DARK, fontweight='bold')

# --- unified median bubbles: marker + one short leader to a white box (no vertical lines) ---
def median_bubble(m, my, col, bx, by, marker='o'):
    ax.plot(m, my, marker, mfc='white', mec=col, ms=7.6, mew=2.3, zorder=6)
    ax.annotate(f'median {m}', xy=(m, my), xytext=(bx, by),
                ha='center', va='center', fontsize=8.6, color=P.INK, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.34', fc=col, ec='none'),
                arrowprops=dict(arrowstyle='-', color=col, lw=1.5), zorder=7)

median_bubble(m_err,  50,           C['err'],   4, 40, marker='o')   # circle on the 50% line
median_bubble(m_lock, 50,           C['lock'], 16, 42, marker='o')   # circle on the 50% line
median_bubble(m_obs,  c_obs[m_obs], C['obs'],  25, 30, marker='o')   # circle on the curve (conditional)

ax.set_xlim(0, XMAX)
ax.set_ylim(0, 100)
ax.set_xticks(range(0, XMAX + 1, 5))
ax.set_yticks([0, 25, 50, 72, 75, 100])
ax.set_yticklabels(['0%', '25%', '50%', '72%', '', '100%'])
ax.set_xlabel('Step (absolute)', fontweight='bold')
ax.set_ylabel('Proportion of failed trajectories', fontweight='bold')
ax.legend(loc='lower right', bbox_to_anchor=(0.995, 0.03), frameon=True, fontsize=8.6,
          framealpha=0.96, title='first step reaching 50% (CDF)', title_fontsize=8.3)
ax.grid(axis='y', color='#eee', lw=0.8, zorder=0)
ax.text(0.5, -0.155, f'n = {N} failed trajectories · x truncated at {XMAX} (means on full data)',
        transform=ax.transAxes, ha='center', fontsize=7.6, color='#888')

fig.savefig('figures/fig_three_timepoints.png', dpi=200)
fig.savefig('figures/fig_three_timepoints.pdf')
print('wrote figures/fig_three_timepoints.{png,pdf}')
