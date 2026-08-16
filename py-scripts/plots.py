# DR Stage D2b: Visual exploration (correlation heatmap + boxplot series)
# Requires: pandas, numpy, matplotlib. Run from the project folder.
#
# PRIVACY NOTE ---------------------------------------------------------------
# These figures are drawn from row-level data: every point is one participant.
# On a real run figures are written NEXT TO YOUR REAL DATASET, outside this
# repo, so nothing derived from real data can ever be committed to git.
# Never paste a figure made from real data into an AI chat.
# ---------------------------------------------------------------------------

from __future__ import annotations
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# === USER SETTINGS ==========================================================
# Runs on the synthetic dataset as delivered:
input_csv  = "data_synthetic/synthetic_dataset.csv"
output_dir = "outputs_synthetic/figures"
# To run on REAL data, comment the two lines above and uncomment these:
# input_csv  = input("Path to real dataset CSV: ").strip()
# output_dir = os.path.join(os.path.dirname(os.path.abspath(input_csv)), "dr_figures")

# Columns to include in the heatmap. None = auto-detect all numeric columns.
numeric_vars = None          # e.g. ["age", "bmi", "crp"]

# Grouping variable for the boxplot series. None = skip Figure 2.
group_var    = None          # e.g. "mortality_30day"
group_labels = []            # e.g. ["Sống", "Tử vong"]  (leave [] to use raw values)

# Show individual data points over each box.
# Set to False only if you intend to show this figure outside your own machine.
show_individual_points = True
# ============================================================================


def _heatmap(dat: pd.DataFrame, usable: list[str], output_dir: str) -> None:
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
    path = os.path.join(output_dir, "fig1_correlation_heatmap.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Figure 1 written: {path}")


def _boxplots(
    dat: pd.DataFrame,
    usable: list[str],
    group_var: str,
    group_labels: list[str],
    show_individual_points: bool,
    output_dir: str,
) -> None:
    g      = dat[group_var]
    keep   = g.notna()
    g_vals = sorted(g[keep].unique())
    if len(g_vals) < 2:
        print("Skipping Figure 2: grouping variable has fewer than 2 observed levels.")
        return
    g_n = {v: int((g == v).sum()) for v in g_vals}
    too_small = [v for v, cnt in g_n.items() if cnt < 5]
    if too_small:
        print(f"WARNING: group(s) {too_small} have < 5 observations. Figure 2 skipped.")
        return
    labs   = group_labels if len(g_vals) == len(group_labels) else [str(v) for v in g_vals]
    colors = ["#92C5DE", "#F4A582", "#B8E186", "#C7B0D9"][: len(g_vals)]
    n_col  = min(4, len(usable))
    n_row  = -(-(len(usable)) // n_col)
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
    path = os.path.join(output_dir, "fig2_boxplot_series.png")
    fig2.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"Figure 2 written: {path}")


def run(
    input_csv: str,
    output_dir: str,
    numeric_vars: list[str] | None,
    group_var: str | None,
    group_labels: list[str],
    show_individual_points: bool,
) -> None:
    dat = pd.read_csv(input_csv, encoding="utf-8")
    os.makedirs(output_dir, exist_ok=True)

    if numeric_vars is None:
        numeric_vars = [
            c for c in dat.select_dtypes(include="number").columns
            if dat[c].dropna().nunique() > 1
        ]
        print(f"Auto-detected numeric columns: {numeric_vars}")

    if group_var is not None and group_var not in dat.columns:
        raise ValueError(f"group_var '{group_var}' not found in dataset.")

    missing_cols = [v for v in numeric_vars if v not in dat.columns]
    if missing_cols:
        raise ValueError(f"numeric_vars not found in dataset: {missing_cols}")

    usable  = [v for v in numeric_vars if dat[v].dropna().nunique() > 1]
    dropped = set(numeric_vars) - set(usable)
    if dropped:
        print(f"Skipped (no variation or all missing): {', '.join(sorted(dropped))}")
    assert len(usable) >= 2, "Need at least 2 usable numeric variables."

    _heatmap(dat, usable, output_dir)

    if group_var is None:
        print("group_var is None — skipping Figure 2.")
    else:
        _boxplots(dat, usable, group_var, group_labels, show_individual_points, output_dir)


run(
    input_csv=input_csv,
    output_dir=output_dir,
    numeric_vars=numeric_vars,
    group_var=group_var,
    group_labels=group_labels,
    show_individual_points=show_individual_points,
)

print(f"\nVisual exploration complete. Figures in: {output_dir}")
print("These figures describe distributions and associations only.")
print("They are not statistical tests and prove nothing on their own.")
