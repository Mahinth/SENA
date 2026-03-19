"""
Visualization Module
=====================

This module creates all the plots and network diagrams for
analyzing cascade diffusion results.

PLOTS WE GENERATE:
  1. Adoption vs Threshold  — The "phase transition" plot
  2. Cascade Over Time      — How adoption grows step by step
  3. Network Visualization  — Color-coded graph diagram
  4. Homophily Comparison   — How department bias affects diffusion
  5. Weak Tie Comparison    — Effect of removing bridge edges
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend (works without display)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
from collections import defaultdict

# ─── Style Configuration ───────────────────────────────────

# Color palette for departments
DEPT_COLORS = {
    "DISQ": "#e74c3c",   # Red
    "DMCT": "#3498db",   # Blue
    "DSE": "#2ecc71",    # Green
    "SFLE": "#f39c12",   # Orange
    "SRH": "#9b59b6",    # Purple
    "SSI": "#1abc9c",    # Teal
    "SCOM": "#e67e22",   # Dark orange
    "SDOC": "#34495e",   # Dark gray-blue
    "DCAR": "#e91e63",   # Pink
    "DISQ2": "#ff5722",  # Deep orange
    "UNKNOWN": "#95a5a6", # Gray
}

# Style constants
ADOPTED_COLOR = "#2ecc71"     # Green
NOT_ADOPTED_COLOR = "#e74c3c"  # Red
SEED_COLOR = "#f1c40f"         # Yellow/Gold

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "outputs")


def _ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─── PLOT 1: Adoption vs Threshold ────────────────────────

def plot_adoption_vs_threshold(results_df, save_path=None, title=None):
    """
    Plot how final adoption changes as threshold increases.

    This is the most important plot — it shows the "phase transition":
      - At low thresholds, cascades succeed (high adoption)
      - At some critical threshold, cascades start failing
      - At high thresholds, almost no adoption beyond seeds

    The error bars show VARIANCE — if they're large, it means
    the outcome depends heavily on which seeds are chosen
    (multiple equilibria!).

    Args:
        results_df: DataFrame from threshold_sweep experiment
        save_path: Where to save the plot (or None for default)
        title: Custom title
    """
    _ensure_output_dir()
    if save_path is None:
        save_path = os.path.join(OUTPUT_DIR, "adoption_vs_threshold.png")

    # Calculate mean and std per threshold
    stats = results_df.groupby("threshold")["adoption_fraction"].agg(
        ["mean", "std"]).reset_index()

    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot with error bars
    ax.errorbar(stats["threshold"], stats["mean"] * 100,
                yerr=stats["std"] * 100,
                fmt='o-', color='#3498db', linewidth=2.5,
                markersize=8, capsize=5, capthick=2,
                markerfacecolor='white', markeredgewidth=2,
                label='Mean adoption ± std')

    # Fill between for visual clarity
    ax.fill_between(stats["threshold"],
                    (stats["mean"] - stats["std"]) * 100,
                    (stats["mean"] + stats["std"]) * 100,
                    alpha=0.15, color='#3498db')

    # Individual run points (jittered for visibility)
    for _, row in results_df.iterrows():
        jitter = np.random.normal(0, 0.005)
        ax.scatter(row["threshold"] + jitter,
                   row["adoption_fraction"] * 100,
                   alpha=0.2, s=15, color='#3498db', zorder=1)

    ax.set_xlabel("Adoption Threshold (θ)", fontsize=13, fontweight='bold')
    ax.set_ylabel("Final Adoption (%)", fontsize=13, fontweight='bold')
    ax.set_title(title or "Cascade Diffusion: Adoption vs Threshold",
                 fontsize=15, fontweight='bold', pad=15)  
    ax.set_xlim(-0.02, max(stats["threshold"]) + 0.05)
    ax.set_ylim(-2, 105)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=11, loc='upper right')

    # Add annotation for phase transition
    if len(stats) > 2:
        # Find steepest drop
        diffs = np.diff(stats["mean"].values)
        if len(diffs) > 0:
            steepest_idx = np.argmin(diffs)
            critical_threshold = stats["threshold"].values[steepest_idx + 1]
            ax.axvline(x=critical_threshold, color='#e74c3c',
                      linestyle='--', alpha=0.5, linewidth=1.5)
            ax.annotate(f'Critical θ ≈ {critical_threshold:.2f}',
                       xy=(critical_threshold, 50),
                       fontsize=10, color='#e74c3c',
                       ha='left', va='center',
                       bbox=dict(boxstyle='round,pad=0.3',
                                facecolor='white', edgecolor='#e74c3c',
                                alpha=0.8))

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Saved: {save_path}")
    return save_path


# ─── PLOT 2: Cascade Over Time ────────────────────────────

def plot_cascade_over_time(cascade_result, save_path=None, title=None):
    """
    Plot how adoption grows over simulation steps.

    Shows the S-curve (or lack thereof) of cascade spread:
      - Seed phase: initial adopters
      - Growth phase: cascade spreading rapidly
      - Saturation: cascade slowing down and converging

    Args:
        cascade_result: dict from run_cascade()
        save_path: Where to save
        title: Custom title
    """
    _ensure_output_dir()
    if save_path is None:
        save_path = os.path.join(OUTPUT_DIR, "cascade_over_time.png")

    steps = cascade_result["steps"]
    n_total = cascade_result["n_total"]

    x = list(range(len(steps)))
    y = [len(s) / n_total * 100 for s in steps]

    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot cumulative adoption
    ax.fill_between(x, y, alpha=0.2, color='#2ecc71')
    ax.plot(x, y, 'o-', color='#2ecc71', linewidth=2.5,
            markersize=8, markerfacecolor='white',
            markeredgewidth=2, label='Cumulative adoption')

    # Mark phases
    if len(x) > 1:
        # New adoptions per step
        new_per_step = [y[0]] + [y[i] - y[i-1] for i in range(1, len(y))]

        ax2 = ax.twinx()
        ax2.bar(x, new_per_step, alpha=0.3, color='#f39c12',
                label='New adoptions per step', width=0.4)
        ax2.set_ylabel("New Adoptions per Step (%)",
                       fontsize=11, color='#f39c12')
        ax2.tick_params(axis='y', labelcolor='#f39c12')

    ax.set_xlabel("Simulation Step", fontsize=13, fontweight='bold')
    ax.set_ylabel("Cumulative Adoption (%)", fontsize=13, fontweight='bold')

    threshold = cascade_result.get("threshold", "?")
    ax.set_title(
        title or f"Cascade Over Time (θ = {threshold})",
        fontsize=15, fontweight='bold', pad=15)

    ax.set_ylim(-2, 105)
    ax.grid(True, alpha=0.3, linestyle='--')

    # Combined legend
    lines1, labels1 = ax.get_legend_handles_labels()
    if len(x) > 1:
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2,
                  fontsize=10, loc='center right')
    else:
        ax.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Saved: {save_path}")
    return save_path


# ─── PLOT 3: Network Visualization ────────────────────────

def plot_network(G, adopters=None, seeds=None, save_path=None, title=None):
    """
    Draw the network with nodes colored by department and adoption status.

    Colors:
      - Gold border on seed nodes
      - Green = adopted, Red = not adopted
      - Node fill colored by department
      - Edge thickness by interaction weight

    Args:
        G: NetworkX graph
        adopters: Set of adopted node IDs (or None for department-only view)
        seeds: Set of seed node IDs (to highlight)
        save_path: Where to save
        title: Custom title
    """
    _ensure_output_dir()
    if save_path is None:
        save_path = os.path.join(OUTPUT_DIR, "network_visualization.png")

    fig, ax = plt.subplots(figsize=(14, 10))

    # Layout: spring layout with department-based grouping
    pos = nx.spring_layout(G, k=1.5/np.sqrt(G.number_of_nodes()),
                           iterations=50, seed=42)

    # Edge drawing
    edge_weights = [G[u][v].get('weight', 1) for u, v in G.edges()]
    max_weight = max(edge_weights) if edge_weights else 1
    normalized_weights = [0.1 + 1.5 * (w / max_weight) for w in edge_weights]

    nx.draw_networkx_edges(G, pos, alpha=0.08, width=normalized_weights,
                           edge_color='#7f8c8d', ax=ax)

    # Node colors
    if adopters is not None:
        # Color by adoption status
        node_colors = []
        node_edges = []
        node_sizes = []
        for node in G.nodes():
            dept = G.nodes[node].get('department', 'UNKNOWN')
            if node in (seeds or set()):
                node_colors.append(SEED_COLOR)
                node_edges.append('#000000')
                node_sizes.append(250)
            elif node in adopters:
                node_colors.append(ADOPTED_COLOR)
                node_edges.append('#27ae60')
                node_sizes.append(180)
            else:
                node_colors.append(NOT_ADOPTED_COLOR)
                node_edges.append('#c0392b')
                node_sizes.append(120)
    else:
        # Color by department
        node_colors = [DEPT_COLORS.get(G.nodes[n].get('department', 'UNKNOWN'),
                                        '#95a5a6')
                       for n in G.nodes()]
        node_edges = ['#2c3e50'] * G.number_of_nodes()
        node_sizes = [150] * G.number_of_nodes()

    nx.draw_networkx_nodes(G, pos, node_color=node_colors,
                           edgecolors=node_edges,
                           node_size=node_sizes, linewidths=1.5, ax=ax)

    # Labels (only for small graphs)
    if G.number_of_nodes() <= 100:
        nx.draw_networkx_labels(G, pos, font_size=6, font_color='white',
                                font_weight='bold', ax=ax)

    # Legend
    if adopters is not None:
        legend_elements = [
            mpatches.Patch(color=SEED_COLOR, label=f'Seeds ({len(seeds or set())})'),
            mpatches.Patch(color=ADOPTED_COLOR,
                          label=f'Adopted ({len(adopters)})'),
            mpatches.Patch(color=NOT_ADOPTED_COLOR,
                          label=f'Not adopted ({G.number_of_nodes() - len(adopters)})'),
        ]
    else:
        legend_elements = [
            mpatches.Patch(color=color, label=f'{dept}')
            for dept, color in DEPT_COLORS.items()
            if dept in set(G.nodes[n].get('department', '') for n in G.nodes())
        ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=9,
              framealpha=0.9)

    ax.set_title(title or "Workplace Social Network",
                 fontsize=15, fontweight='bold', pad=15)
    ax.axis('off')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight',
                facecolor='white')
    plt.close()
    print(f"📈 Saved: {save_path}")
    return save_path


# ─── PLOT 4: Homophily Comparison ─────────────────────────

def plot_homophily_comparison(results_df, save_path=None):
    """
    Compare cascade outcomes across different homophily strengths.

    Shows multiple lines (one per homophily value) on an
    adoption vs threshold plot.
    """
    _ensure_output_dir()
    if save_path is None:
        save_path = os.path.join(OUTPUT_DIR, "homophily_comparison.png")

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6',
              '#1abc9c', '#e67e22']

    hw_values = sorted(results_df["homophily_weight"].unique())

    for idx, hw in enumerate(hw_values):
        subset = results_df[results_df["homophily_weight"] == hw]
        stats = subset.groupby("threshold")["adoption_fraction"].agg(
            ["mean", "std"]).reset_index()

        color = colors[idx % len(colors)]
        ax.errorbar(stats["threshold"], stats["mean"] * 100,
                    yerr=stats["std"] * 100,
                    fmt='o-', color=color, linewidth=2,
                    markersize=6, capsize=3,
                    label=f'Homophily = {hw:.2f}')

    ax.set_xlabel("Adoption Threshold (θ)", fontsize=13, fontweight='bold')
    ax.set_ylabel("Final Adoption (%)", fontsize=13, fontweight='bold')
    ax.set_title("Effect of Homophily on Cascade Diffusion",
                 fontsize=15, fontweight='bold', pad=15)
    ax.set_ylim(-2, 105)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=10, title="Homophily Weight", title_fontsize=11)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Saved: {save_path}")
    return save_path


# ─── PLOT 5: Weak Tie Comparison ──────────────────────────

def plot_weak_tie_comparison(results_df, save_path=None):
    """
    Compare cascades when bridge edges vs redundant edges are removed.

    Two series:
      - "High betweenness removed" (bridges cut)
      - "Low betweenness removed" (redundant cut)

    X axis = fraction of edges removed
    Y axis = adoption rate
    """
    _ensure_output_dir()
    if save_path is None:
        save_path = os.path.join(OUTPUT_DIR, "weak_tie_comparison.png")

    fig, ax = plt.subplots(figsize=(10, 6))

    for mode, color, label in [("high", "#e74c3c", "Bridges removed (high betweenness)"),
                                ("low", "#3498db", "Redundant removed (low betweenness)")]:
        subset = results_df[results_df["mode"].isin([mode, "original"])]
        stats = subset.groupby("fraction_removed")["adoption_fraction"].agg(
            ["mean", "std"]).reset_index()

        ax.errorbar(stats["fraction_removed"] * 100, stats["mean"] * 100,
                    yerr=stats["std"] * 100,
                    fmt='o-', color=color, linewidth=2.5,
                    markersize=8, capsize=4,
                    markerfacecolor='white', markeredgewidth=2,
                    label=label)

    ax.set_xlabel("Edges Removed (%)", fontsize=13, fontweight='bold')
    ax.set_ylabel("Final Adoption (%)", fontsize=13, fontweight='bold')
    ax.set_title("Effect of Weak Ties on Cascade Diffusion",
                 fontsize=15, fontweight='bold', pad=15)
    ax.set_ylim(-2, 105)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=11)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Saved: {save_path}")
    return save_path


# ─── TEST ──────────────────────────────────────────────────

if __name__ == "__main__":
    from data_loader import load_and_build
    from simulation import run_cascade
    from experiments import threshold_sweep

    print("=" * 60)
    print("  Step 8-10: Visualization")
    print("=" * 60)

    G, contacts, departments = load_and_build()

    # 1. Network visualization (department view)
    plot_network(G, title="Workplace Network by Department")

    # 2. Run a cascade and visualize
    result = run_cascade(G, threshold=0.15, n_seeds=15,
                         seed_strategy="high_degree", verbose=True)
    plot_cascade_over_time(result)
    plot_network(G, adopters=result["final_adopters"],
                 seeds=result["seeds"],
                 save_path=os.path.join(OUTPUT_DIR, "network_cascade.png"),
                 title=f"Cascade Result (θ={result['threshold']}, "
                       f"adopted={result['adoption_fraction']:.1%})")

    # 3. Threshold sweep plot
    sweep_df = threshold_sweep(G, n_seeds=15, n_runs=5)
    plot_adoption_vs_threshold(sweep_df)

    print(f"\n✅ All plots saved to {OUTPUT_DIR}/")
