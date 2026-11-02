"""Shared color palette — matches the Fig.1 overview (pastel blue / green / purple).

Use in any figure script:
    import palette as P
    ax.plot(..., color=P.T_ERR)        # semantic
    ax.bar(...,  color=P.PASS)
Roles:
    core pastels  -> thin lines & medium fills
    *_FILL        -> lighter, for large area fills (stacked bars, backgrounds)
    *_DARK / INK  -> text & emphasis on light/pastel backgrounds
Always use the semantic aliases (PASS, FAIL, T_ERR, …) in figures, not raw hex.
"""

# --- core pastels (legible for both thin lines and fills) ---
BLUE   = '#90caf9'
GREEN  = '#74c69d'
PURPLE = '#b18fd0'      # a touch deeper than the overview's #d2b7e5 so thin LINES stay legible

# --- lighter fill variants (large stacked-bar / background areas) ---
BLUE_FILL   = '#bbdefb'
GREEN_FILL  = '#95d5b2'
PURPLE_FILL = '#d2b7e5'

# --- dark variants (text / emphasis on light or pastel backgrounds) ---
BLUE_DARK   = '#1f6094'
GREEN_DARK  = '#2e7d5b'
PURPLE_DARK = '#6a4a8c'

INK  = '#243027'        # default dark label text (on pastel fills)
GREY = '#888888'        # secondary / caption text

# --- semantic aliases (use THESE in figures) ---
PASS = GREEN            # successful trajectories
FAIL = PURPLE_FILL      # failed trajectories
T_ERR  = PURPLE         # t_err  (decisive error)
T_LOCK = GREEN          # t_lock (failure lock-in)
T_OBS  = BLUE           # t_obs  (first observable)
ERROR  = PURPLE         # an error / mistake (RQ figures)
OK     = GREEN          # a recovery / success

TRIO = [BLUE, GREEN, PURPLE]            # ordered categorical use
