# DR Stage D2b (SEM): Visual exploration of scale items
# Requires: pandas, numpy, matplotlib. Run from the project folder.
#
# PRIVACY NOTE ---------------------------------------------------------------
# These figures are drawn from row-level data: every point is one respondent.
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
import matplotlib.patches as mpatches

# === USER SETTINGS ==========================================================
# Runs on the synthetic dataset as delivered:
input_csv  = "data_synthetic/synthetic_dataset.csv"
output_dir = "outputs_synthetic/figures"
# To run on REAL data, comment the two lines above and uncomment these:
# input_csv  = input("Path to real dataset CSV: ").strip()
# output_dir = os.path.join(os.path.dirname(os.path.abspath(input_csv)), "dr_figures")

# Constructs from plans/sem_measurement_plan.yaml.
# Item order matters: items of the same construct must be adjacent so the
# diagonal block structure appears on the heatmap.
constructs: dict[str, list[str]] = {
    "Job Satisfaction": ["js_q1", "js_q2", "js_q3", "js_q4", "js_q5"],
    "Burnout":          ["bo_q1", "bo_q2", "bo_q3", "bo_q4", "bo_q5"],
    "Turnover":         ["turnover_intent"],
}

# Show individual jittered data points over each box.
# Set to False only if you intend to show this figure outside your own machine.
show_individual_points: bool = True

# Construct colours (one per construct; extras for additional constructs)
construct_palette = ["#4393C3", "#D6604D", "#7FBC7F", "#C7B0D9",
                     "#F4A582", "#92C5DE", "#B8E186"]
# ============================================================================


def _item_heatmap(
    dat: pd.DataFrame,
    usable: list[str],
    item_construct: dict[str, str],
    output_dir: str,
) -> None:
    M = dat[usable].corr(method="pearson")
    p = len(usable)

    cmap = mcolors.LinearSegmentedColormap.from_list(
        "bwr2", ["#2166AC", "#4393C3", "#F7F7F7", "#D6604D", "#B2182B"]
    )
    fig, (ax_heat, ax_bar) = plt.subplots(
        1, 2, figsize=(max(8, p * 0.9), max(7, p * 0.85)),
        gridspec_kw={"width_ratios": [8, 0.55]},
    )

    im = ax_heat.imshow(M.values, vmin=-1, vmax=1, cmap=cmap, aspect="auto")
    ax_heat.set_xticks(range(p))
    ax_heat.set_yticks(range(p))
    ax_heat.set_xticklabels(M.columns, rotation=45, ha="right", fontsize=8.5)
    ax_heat.set_yticklabels(M.columns, fontsize=8.5)

    for i in range(p + 1):
        ax_heat.axhline(i - 0.5, color="white", lw=1.2)
        ax_heat.axvline(i - 0.5, color="white", lw=1.2)

    for i in range(p):
        for j in range(p):
            r = float(M.values[i, j])
            ax_heat.text(j, i, f"{r:.2f}", ha="center", va="center", fontsize=7,
                         color="white" if abs(r) > 0.55 else "#222222")

    # Draw construct block outlines along the diagonal
    constructs_seq = [item_construct[v] for v in usable]
    block_starts: list[int] = []
    block_ends:   list[int] = []
    prev = constructs_seq[0]
    start = 0
    for idx, c in enumerate(constructs_seq):
        if c != prev:
            block_starts.append(start)
            block_ends.append(idx - 1)
            start = idx
            prev = c
    block_starts.append(start)
    block_ends.append(len(constructs_seq) - 1)

    for bs, be in zip(block_starts, block_ends):
        rect = mpatches.Rectangle(
            (bs - 0.5, bs - 0.5), be - bs + 1, be - bs + 1,
            linewidth=2.5, edgecolor="#111111", facecolor="none",
        )
        ax_heat.add_patch(rect)

    ax_heat.set_title(
        "Tương quan giữa các item, nhóm theo construct\n"
        "Khối đậm trên đường chéo = các item cùng một nhân tố tiềm ẩn",
        fontsize=9.5, loc="left",
    )
    plt.colorbar(im, cax=ax_bar)
    plt.tight_layout()

    path = os.path.join(output_dir, "fig1_item_correlation_heatmap.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Figure 1 written: {path}")


def _item_boxplots(
    dat: pd.DataFrame,
    usable: list[str],
    item_construct: dict[str, str],
    construct_cols: dict[str, str],
    show_individual_points: bool,
    output_dir: str,
) -> None:
    n_items = len(usable)
    fig, ax = plt.subplots(figsize=(max(10, n_items * 0.85), 6))

    groups  = [dat[v].dropna().to_numpy() for v in usable]
    fills   = [construct_cols.get(item_construct[v], "#CCCCCC") for v in usable]

    bp = ax.boxplot(
        groups,
        patch_artist=True,
        showfliers=show_individual_points,
        flierprops={"marker": "o", "markersize": 4, "markerfacecolor": "#999999"},
        boxprops={"linewidth": 1.2},
        medianprops={"linewidth": 1.5, "color": "#333333"},
    )
    ax.set_xticks(range(1, len(usable) + 1))
    ax.set_xticklabels(usable, rotation=45, ha="right", fontsize=9)
    for patch, color in zip(bp["boxes"], fills):
        patch.set_facecolor(color)
        patch.set_alpha(0.65)

    if show_individual_points:
        _rng = np.random.default_rng(42)
        for k, grp in enumerate(groups):
            jx = k + 1 + _rng.uniform(-0.16, 0.16, size=len(grp))
            jy = grp + _rng.uniform(-0.12, 0.12, size=len(grp))
            ax.scatter(jx, jy, s=6, color="#333333", alpha=0.30, zorder=3)

    # Vertical dashed separators between constructs
    constructs_seq = [item_construct[v] for v in usable]
    for idx in range(1, len(constructs_seq)):
        if constructs_seq[idx] != constructs_seq[idx - 1]:
            ax.axvline(idx + 0.5, color="#777777", linestyle="--", lw=1)

    ax.set_xticklabels(usable, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Điểm trả lời", fontsize=10)
    ax.set_title(
        "Phân bố từng item theo construct\n"
        "Kiểm tra hiệu ứng trần/sàn và item lệch trước khi chạy CFA",
        fontsize=10, loc="left",
    )

    # Legend
    legend_handles = [
        mpatches.Patch(facecolor=construct_cols[c], alpha=0.65, edgecolor="#555555", label=c)
        for c in construct_cols
    ]
    ax.legend(handles=legend_handles, loc="upper right", frameon=False, fontsize=9)

    plt.tight_layout()
    path = os.path.join(output_dir, "fig2_item_boxplot_series.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Figure 2 written: {path}")


def run(
    input_csv: str,
    output_dir: str,
    constructs: dict[str, list[str]],
    show_individual_points: bool,
    construct_palette: list[str],
) -> None:
    dat = pd.read_csv(input_csv, encoding="utf-8")
    os.makedirs(output_dir, exist_ok=True)

    items = [item for items in constructs.values() for item in items]
    missing = [v for v in items if v not in dat.columns]
    if missing:
        raise ValueError(f"Missing columns in dataset: {missing}")

    usable  = [v for v in items if dat[v].dropna().nunique() > 1]
    dropped = set(items) - set(usable)
    if dropped:
        print(f"Skipped (no variation or all missing): {', '.join(sorted(dropped))}")
    assert len(usable) >= 2, "Need at least 2 usable items."

    # Map each item to its construct name (preserves order)
    item_construct = {
        item: cname
        for cname, citems in constructs.items()
        for item in citems
        if item in usable
    }
    construct_names = list(constructs.keys())
    construct_cols  = dict(zip(construct_names, construct_palette[: len(construct_names)]))

    _item_heatmap(dat, usable, item_construct, output_dir)
    _item_boxplots(dat, usable, item_construct, construct_cols, show_individual_points, output_dir)

    print(f"\nVisual exploration complete. Figures in: {output_dir}")
    print("NOTE: on the synthetic dataset items are simulated independently,")
    print("so no block structure will appear on the heatmap. That is expected")
    print("and only proves the code runs. The blocks appear on your real data.")


run(
    input_csv=input_csv,
    output_dir=output_dir,
    constructs=constructs,
    show_individual_points=show_individual_points,
    construct_palette=construct_palette,
)
