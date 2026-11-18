#!/usr/bin/env python3
"""RQ2 case (acl / sudo) rendered at the SAME large-font size as RQ1_case_big.
Reuses make_case_cards_v3's render, overriding only the layout/font globals, so the shared
card set keeps its normal size. Output: figures/RQ2_case_big.{png,pdf}."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import make_case_cards_v3 as M

# --- large-font overrides (match RQ1_case_big) ---
M.FS_TITLE, M.FS_TH, M.FS_CMD, M.FS_OUT, M.FS_LBL, M.FS_SKIP, M.FS_BADGE = 14.0, 13.2, 13.0, 12.7, 12.7, 12.7, 11.6
M.LH = 1.0
M.WTHINK, M.WMONO, M.WSKIP = 72, 56, 58
M.XBADGE, M.XTHINK, M.XBOX_L, M.XBOX_R = 0.034, 0.060, 0.050, 0.982
M.WIDTH, M.VSCALE = 7.7, 0.235
M.LBL_CW = 0.0145

spec = M.CASES['sudo']
H = M.card_height(spec)
fig = plt.figure(figsize=(M.WIDTH, M.VSCALE * H))
ax = fig.add_axes([0.012, 0.012, 0.976, 0.976])
M.render_card(ax, spec)
fig.savefig('figures/RQ2_case_big.png', dpi=220, bbox_inches='tight')
fig.savefig('figures/RQ2_case_big.pdf', bbox_inches='tight')
print('wrote figures/RQ2_case_big.{png,pdf}  H=%.1f  %sx%.2f in' % (H, M.WIDTH, M.VSCALE * H))
