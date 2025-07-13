# generate_charts.py – create 13 dashboard‑ready visuals
# --------------------------------------------------------------
# Prerequisites:
#   pip install pandas matplotlib numpy
#   (Optional) pip install wordcloud networkx if you extend the script.
#
# All CSVs are expected to live in the same directory as this script.
# Figures are saved to ./figures/ (created automatically).

from datetime import UTC, datetime
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ------------------------------------------------------------------
# Global Matplotlib styling – bigger fonts & spacious canvases
mpl.rcParams.update(
    {
        "figure.dpi": 120,
        "figure.autolayout": False,  # we call tight_layout per‑plot
        "font.size": 13,
        "axes.titlesize": 16,
        "axes.labelsize": 14,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 11,
    }
)


# Helper: consistent colour palette (matplotlib "cool")
def cool_colors(n: int):
    """Return n evenly spaced colours from the cool colormap."""
    return mpl.cm.cool(np.linspace(0.15, 0.85, n))


# Helper: safe CSV loader ------------------------------------------------------


def load_csv(filename: str) -> pd.DataFrame:
    """Read a CSV that sits next to this script."""
    path = Path(__file__).with_name(filename)
    return pd.read_csv(path)


# Ensure an output folder for images ------------------------------------------

FIG_DIR = Path(__file__).with_name("figures")
FIG_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------------
# 1. Convergence Progress Line Chart
# ------------------------------------------------------------------


def plot_convergence_progress():
    conv = load_csv("convergence_metrics_detailed.csv")
    # Parse timestamps of form YYYYMMDD_HHMMSS
    conv["dt"] = pd.to_datetime(
        conv["timestamp"].astype(str),
        errors="coerce",
        format="%Y%m%d_%H%M%S",
        utc=True,
    )
    conv = conv.dropna(subset=["dt", "agreement_score"])
    ts_agg = conv.groupby("dt", as_index=False)["agreement_score"].mean().sort_values("dt")

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(
        ts_agg["dt"], ts_agg["agreement_score"], marker="o", linewidth=3, color=mpl.cm.cool(0.3)
    )
    ax.axhline(y=0.85, linestyle="--", linewidth=2, color=mpl.cm.cool(0.8))
    ax.set_title("Convergence Progress")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Agreement Score")
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    plt.tight_layout()
    fig.savefig(FIG_DIR / "01_convergence_progress.png")


# ------------------------------------------------------------------
# 2. Agent Cost Donut Chart
# ------------------------------------------------------------------


def plot_agent_cost_donut():
    aps = load_csv("agent_performance_summary.csv")
    fig, ax = plt.subplots(figsize=(8, 8))
    colors = cool_colors(len(aps))
    wedges, _texts, _autotexts = ax.pie(
        aps["total_cost_usd"],
        labels=aps["agent_name"],
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.8,
        colors=colors,
        wedgeprops=dict(width=0.4, edgecolor="white"),
        textprops=dict(color="black"),
    )
    ax.set(aspect="equal", title="Agent Cost Distribution")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "02_agent_cost_donut.png")


# ------------------------------------------------------------------
# 3. Cost‑per‑Token Bar Chart
# ------------------------------------------------------------------


def plot_cost_per_token_bar():
    tcd = load_csv("token_cost_data.csv")
    tcd["cost_per_token"] = tcd["cost_usd"] / tcd["total_tokens"].replace(0, np.nan)
    eff = (
        tcd.groupby("agent_type", as_index=False)["cost_per_token"]
        .mean()
        .sort_values("cost_per_token")
    )

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(eff["agent_type"], eff["cost_per_token"], color=cool_colors(len(eff)))
    ax.set_title("Average Cost per Token by Agent Type")
    ax.set_ylabel("USD per Token")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "03_cost_per_token_bar.png")


# ------------------------------------------------------------------
# 4. Execution Timeline (Gantt‑like)
# ------------------------------------------------------------------


def _parse_ts_millis_or_iso(x):
    """Helper to parse mixed epoch‑ms or ISO timestamps."""
    try:
        return datetime.utcfromtimestamp(int(x) / 1000).replace(tzinfo=UTC)
    except Exception:
        try:
            return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
        except Exception:
            return pd.NaT


def plot_execution_timeline():
    ets = load_csv("execution_timeline_summary.csv")
    ets["dt"] = ets["timestamp"].apply(_parse_ts_millis_or_iso)
    ets = ets.dropna(subset=["dt"]).sort_values("dt")
    ets["end_dt"] = ets["dt"].shift(-1).fillna(ets["dt"])
    ets["duration_s"] = (ets["end_dt"] - ets["dt"]).dt.total_seconds().fillna(0)

    fig, ax = plt.subplots(figsize=(14, 6))
    for i, (_, row) in enumerate(ets.iterrows()):
        ax.barh(
            i,
            row["duration_s"],
            left=row["dt"],
            height=0.5,
            color=mpl.cm.cool(0.2 + 0.6 * i / len(ets)),
        )
    ax.set_yticks(range(len(ets)))
    ax.set_yticklabels([f"Step {row['step']} – {row['agent_id']}" for _, row in ets.iterrows()])
    ax.set_xlabel("Time")
    ax.set_title("Execution Timeline Flow")
    ax.grid(axis="x", alpha=0.3)
    fig.autofmt_xdate()
    plt.tight_layout()
    fig.savefig(FIG_DIR / "04_execution_timeline.png")


# ------------------------------------------------------------------
# 5. Influence Bubble Chart
# ------------------------------------------------------------------


def plot_influence_bubble():
    inf = load_csv("influencer_agents.csv")
    inf_agg = inf.groupby("agent_type", as_index=False).agg(
        tokens=("tokens", "sum"), cost_usd=("cost_usd", "sum")
    )

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.scatter(
        x=range(len(inf_agg)),
        y=inf_agg["cost_usd"],
        s=inf_agg["tokens"] / 5,  # scale bubbles
        c=cool_colors(len(inf_agg)),
        edgecolors="k",
        alpha=0.7,
    )
    ax.set_xticks(range(len(inf_agg)))
    ax.set_xticklabels(inf_agg["agent_type"], rotation=45, ha="right")
    ax.set_ylabel("Total Cost (USD)")
    ax.set_title("Influencer Agents – Tokens vs Cost")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "05_influence_bubble.png")


# ------------------------------------------------------------------
# 6–8. Attack‑Defence Heatmap, Multi‑Bar, Radar
# ------------------------------------------------------------------


def _build_attack_defence_aggregates():
    metrics = [
        "attack_deflection",
        "counteroffensive",
        "position_reinforcement",
        "moral_high_ground",
        "wisdom_superiority",
    ]
    attack = load_csv("agent_attack_defense.csv")
    # word‑count proxy → numeric
    for m in metrics:
        attack[f"{m}_len"] = attack[m].fillna("").apply(lambda s: len(str(s).split()))
    agg = attack.groupby("agent_type")[[f"{m}_len" for m in metrics]].mean()
    return agg, metrics


def plot_attack_defence_heatmap():
    agg, metrics = _build_attack_defence_aggregates()
    fig, ax = plt.subplots(figsize=(12, 8))
    im = ax.imshow(agg.values, cmap="cool", aspect="auto")
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(metrics, rotation=45, ha="right")
    ax.set_yticks(range(len(agg.index)))
    ax.set_yticklabels(agg.index)
    ax.set_title("Attack vs Defence (Avg Word‑Count)")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.ax.set_ylabel("Avg Word Count")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "06_attack_defence_heatmap.png")


def plot_attack_defence_multibar():
    agg, metrics = _build_attack_defence_aggregates()
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(agg.index))
    width = 0.12
    for i, m in enumerate(metrics):
        ax.bar(
            x + i * width,
            agg[f"{m}_len"],
            width=width,
            label=m,
            color=mpl.cm.cool(0.15 + 0.12 * i),
        )
    ax.set_xticks(x + width * (len(metrics) - 1) / 2)
    ax.set_xticklabels(agg.index, rotation=45, ha="right")
    ax.set_ylabel("Average Word Count")
    ax.set_title("Attack/Defense Metric Comparison")
    ax.legend(ncol=3)
    plt.tight_layout()
    fig.savefig(FIG_DIR / "07_attack_defence_multibar.png")


def plot_attack_defence_radar():
    agg, metrics = _build_attack_defence_aggregates()
    angles = np.linspace(0, 2 * np.pi, len(metrics) + 1)
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, polar=True)
    for idx, row in agg.iterrows():
        values = row.tolist() + [row.tolist()[0]]
        ax.plot(angles, values, label=idx, linewidth=2)
        ax.fill(angles, values, alpha=0.1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics)
    ax.set_title("Attack/Defense Radar (Word‑Count Proxy)")
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.1))
    plt.tight_layout()
    fig.savefig(FIG_DIR / "08_attack_defence_radar.png")


# ------------------------------------------------------------------
# 9–11. Agent Performance Summary Charts
# ------------------------------------------------------------------


def plot_tokens_vs_cost_barline():
    aps = load_csv("agent_performance_summary.csv")
    fig, ax1 = plt.subplots(figsize=(12, 6))
    x_pos = np.arange(len(aps))
    ax1.bar(x_pos, aps["total_tokens"], color=cool_colors(len(aps)), label="Total Tokens")
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(aps["agent_name"], rotation=45, ha="right")
    ax1.set_ylabel("Total Tokens")
    ax1.set_title("Tokens vs Cost by Agent")

    ax2 = ax1.twinx()
    ax2.plot(
        x_pos,
        aps["total_cost_usd"],
        color="black",
        marker="o",
        linestyle="--",
        label="Total Cost (USD)",
    )
    ax2.set_ylabel("Total Cost (USD)")

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper left")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "09_tokens_vs_cost.png")


def plot_call_distribution_donut():
    aps = load_csv("agent_performance_summary.csv")
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(
        aps["total_calls"],
        labels=aps["agent_name"],
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.8,
        colors=cool_colors(len(aps)),
    )
    ax.add_patch(plt.Circle((0, 0), 0.5, color="white"))
    ax.set_title("Call Distribution by Agent")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "10_call_distribution_donut.png")


def plot_cost_efficiency_scatter():
    aps = load_csv("agent_performance_summary.csv")
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.scatter(
        aps["tokens_per_call"],
        aps["cost_per_call"],
        s=aps["total_calls"] * 40,
        c=cool_colors(len(aps)),
        edgecolors="k",
        alpha=0.8,
    )
    for i, txt in enumerate(aps["agent_name"]):
        ax.annotate(
            txt,
            (aps["tokens_per_call"][i], aps["cost_per_call"][i]),
            textcoords="offset points",
            xytext=(5, 5),
            fontsize=9,
        )
    ax.set_xlabel("Tokens per Call")
    ax.set_ylabel("Cost per Call (USD)")
    ax.set_title("Cost Efficiency per Call")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "11_cost_efficiency_scatter.png")


# ------------------------------------------------------------------
# 12–13. Agent Performance Detailed Charts
# ------------------------------------------------------------------


def plot_total_tokens_bar():
    ap = load_csv("agent_performance.csv")
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(ap["agent_type"], ap["total_tokens"], color=cool_colors(len(ap)))
    ax.set_ylabel("Total Tokens")
    ax.set_title("Total Tokens by Agent Type")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "12_total_tokens_bar.png")


def plot_cost_vs_performance_scatter():
    ap = load_csv("agent_performance.csv")
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.scatter(
        ap["avg_tokens_per_appearance"],
        ap["avg_cost_per_appearance"],
        s=ap["total_appearances"] * 30,
        c=cool_colors(len(ap)),
        edgecolors="k",
        alpha=0.8,
    )
    for i, txt in enumerate(ap["agent_type"]):
        ax.annotate(
            txt,
            (ap["avg_tokens_per_appearance"][i], ap["avg_cost_per_appearance"][i]),
            textcoords="offset points",
            xytext=(5, 5),
            fontsize=9,
        )
    ax.set_xlabel("Avg Tokens per Appearance")
    ax.set_ylabel("Avg Cost per Appearance (USD)")
    ax.set_title("Cost vs Performance Relationship")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "13_cost_vs_performance_scatter.png")


# ------------------------------------------------------------------
# Driver ----------------------------------------------------------------------

ALL_PLOTS = [
    plot_convergence_progress,
    plot_agent_cost_donut,
    plot_cost_per_token_bar,
    plot_execution_timeline,
    plot_influence_bubble,
    plot_attack_defence_heatmap,
    plot_attack_defence_multibar,
    plot_attack_defence_radar,
    plot_tokens_vs_cost_barline,
    plot_call_distribution_donut,
    plot_cost_efficiency_scatter,
    plot_total_tokens_bar,
    plot_cost_vs_performance_scatter,
]


def main():
    print(f"Saving figures to {FIG_DIR.resolve()}")
    for fn in ALL_PLOTS:
        fn()
    print("✔️  All figures generated.")


if __name__ == "__main__":
    main()
