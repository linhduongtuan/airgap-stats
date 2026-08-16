# DR Stage D2b: Visual exploration (correlation heatmap + boxplot series)
# Requires: pandas, numpy, matplotlib. Run from the project folder.
#
# PRIVACY NOTE ---------------------------------------------------------------
# These figures are drawn from row-level data: every point is one participant.
# On a real run figures are written NEXT TO YOUR REAL DATASET, outside this
# repo, so nothing derived from real data can ever be committed to git.
# Never paste a figure made from real data into an AI chat. Aggregate numbers
# (Table 1, model estimates) are fine to paste; pictures of raw rows are not.
# ---------------------------------------------------------------------------
#
# SYNTHESIS-MODE CHECK (Phase 4): last verified clean against both Stage B
# (independent synthesis, the default below) and Stage B2 (correlated
# synthesis -- see synthesize_data_correlated.py) as of 2026-08-15. The
# Stage B2 check used a stand-in file (this project's own Stage B output fed
# in as if it were real data, only to exercise the code path) -- re-verify
# against a genuine Stage B2 file once you generate one from real data.

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# === USER SETTINGS ==========================================================
input_csv  = "data_synthetic/synthetic_dataset.csv"
output_dir = "outputs_synthetic/figures"
# To run on REAL data, comment the two lines above and uncomment these:
# input_csv  = input("Path to real dataset CSV: ").strip()
# output_dir = os.path.join(os.path.dirname(os.path.abspath(input_csv)), "dr_figures")
# ============================================================================

# Show individual data points and boxplot outliers.
# True is correct for your own analysis: outliers carry real clinical meaning.
# Set to False only if you intend to show this figure outside your own machine.
show_individual_points = True

dat = pd.read_csv(input_csv, encoding="utf-8")
os.makedirs(output_dir, exist_ok=True)

# --- Variables from plans/analysis_plan.yaml ---
group_var    = "mortality_30day"
group_labels = ["Sống", "Tử vong"]   # for values 0 and 1
numeric_vars = ["age", "bmi", "sbp", "dbp", "egfr", "hba1c", "crp", "length_of_stay"]

missing_cols = [v for v in numeric_vars + [group_var] if v not in dat.columns]
if missing_cols:
    raise ValueError(f"Missing columns in dataset: {missing_cols}")

# Keep only variables that actually vary; a constant column breaks corr()
usable  = [v for v in numeric_vars if dat[v].dropna().nunique() > 1]
dropped = [v for v in numeric_vars if v not in usable]
if dropped:
    print(f"Skipped (no variation or all missing): {', '.join(dropped)}")
assert len(usable) >= 2

# === FIGURE 1: CORRELATION HEATMAP ==========================================
M = dat[usable].corr(method="pearson")
p = len(usable)
cmap = mcolors.LinearSegmentedColormap.from_list(
    "bwr2", ["#2166AC", "#4393C3", "#F7F7F7", "#D6604D", "#B2182B"]
)
fig, (ax_heat, ax_bar) = plt.subplots(
    1, 2, figsize=(max(8, p * 1.1), max(6, p * 0.9)),
    gridspec_kw={"width_ratios": [8, 0.55]},
)
im = ax_heat.imshow(M.values, vmin=-1, vmax=1, cmap=cmap, aspect="auto")
ax_heat.set_xticks(range(p))
ax_heat.set_yticks(range(p))
ax_heat.set_xticklabels(M.columns, rotation=45, ha="right", fontsize=9)
ax_heat.set_yticklabels(M.columns, fontsize=9)
for i in range(p + 1):
    ax_heat.axhline(i - 0.5, color="white", lw=1.5)
    ax_heat.axvline(i - 0.5, color="white", lw=1.5)
for i in range(p):
    for j in range(p):
        r = float(M.values[i, j])
        ax_heat.text(j, i, f"{r:.2f}", ha="center", va="center", fontsize=7.5,
                     color="white" if abs(r) > 0.55 else "#222222")
ax_heat.set_title(
    "Tương quan giữa các biến liên tục (Pearson)\npairwise complete observations",
    fontsize=10, loc="left",
)
plt.colorbar(im, cax=ax_bar)
plt.tight_layout()
fig1_path = os.path.join(output_dir, "fig1_correlation_heatmap.png")
fig.savefig(fig1_path, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"Figure 1 written: {fig1_path}")

# === FIGURE 2: BOXPLOT SERIES BY OUTCOME ====================================
g      = dat[group_var]
keep   = g.notna()
g_vals = sorted(g[keep].unique())

if len(g_vals) < 2:
    print("Skipping Figure 2: grouping variable has fewer than 2 observed levels.")
else:
    # Small-cell guard: a group of 2-3 people yields a meaningless box and
    # exposes those individuals. Standard disclosure control threshold is 5.
    g_n = {v: int((g == v).sum()) for v in g_vals}
    too_small = [v for v, cnt in g_n.items() if cnt < 5]
    if too_small:
        print(f"WARNING: group(s) {too_small} have fewer than 5 observations. Figure 2 skipped.")
    else:
        labs   = group_labels if len(g_vals) == len(group_labels) else [str(v) for v in g_vals]
        colors = ["#92C5DE", "#F4A582", "#B8E186", "#C7B0D9"][: len(g_vals)]

        n_col = min(4, len(usable))
        n_row = -(-len(usable) // n_col)
        fig2, axes = plt.subplots(n_row, n_col, figsize=(4 * n_col, 4 * n_row + 0.6), squeeze=False)
        _rng = np.random.default_rng(42)

        for idx, var in enumerate(usable):
            ax     = axes[idx // n_col][idx % n_col]
            groups = [dat[var][keep & (g == v)].dropna().to_numpy() for v in g_vals]
            bp = ax.boxplot(groups, tick_labels=labs, patch_artist=True,
                            showfliers=show_individual_points,
                            flierprops={"marker": "o", "markersize": 4, "markerfacecolor": "#999999"})
            for patch, color in zip(bp["boxes"], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.85)
            if show_individual_points:
                for k, grp in enumerate(groups):
                    jitter = _rng.uniform(-0.13, 0.13, size=len(grp))
                    ax.scatter(k + 1 + jitter, grp, s=8, color="#333333", alpha=0.35, zorder=3)
            ns = " / ".join(str(len(grp)) for grp in groups)
            ax.set_title(var, fontsize=10.5)
            ax.text(0.5, 1.0, f"n = {ns}", transform=ax.transAxes,
                    ha="center", va="bottom", fontsize=7.5, color="#666666")

        for idx in range(len(usable), n_row * n_col):
            axes[idx // n_col][idx % n_col].set_visible(False)

        fig2.suptitle(f"Phân bố biến liên tục theo {group_var}", fontsize=11, fontweight="bold")
        plt.tight_layout()
        fig2_path = os.path.join(output_dir, "fig2_boxplot_series.png")
        fig2.savefig(fig2_path, dpi=150, bbox_inches="tight")
        plt.close(fig2)
        print(f"Figure 2 written: {fig2_path}")

print(f"\nVisual exploration complete. Figures in: {output_dir}")
print("These figures describe distributions and associations only.")
print("They are not statistical tests and prove nothing on their own.")
