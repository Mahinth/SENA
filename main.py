"""
Network Cascade Lab — Main Pipeline
=====================================

This is the entry point that runs EVERYTHING:
  1. Loads the dataset and builds the network
  2. Runs cascade simulations
  3. Runs all experiments (threshold sweep, homophily, weak ties)
  4. Generates all visualization plots
  5. Prints key insights and analysis

Usage:
    python main.py

All plots are saved to the outputs/ directory.
"""

import os
import sys
import random
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from data_loader import load_and_build, build_temporal_snapshots
from simulation import run_cascade, run_temporal_cascade, select_seeds
from experiments import (threshold_sweep, variance_analysis,
                         homophily_experiment, weak_tie_experiment)
from visualization import (plot_adoption_vs_threshold, plot_cascade_over_time,
                            plot_network, plot_homophily_comparison,
                            plot_weak_tie_comparison, OUTPUT_DIR)


def print_header(text):
    print("\n" + "=" * 65)
    print(f"  {text}")
    print("=" * 65)


def print_section(text):
    print(f"\n{'─' * 50}")
    print(f"  {text}")
    print(f"{'─' * 50}")


def print_insights(sweep_df, homophily_df, weak_tie_df, G, agg_res=None, temp_res=None):
    """
    Print key insights from all experiments.
    This is the "so what?" section — what did we learn?
    """
    print_header("KEY INSIGHTS & ANALYSIS")

    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    # ── Insight 0: Aggregated vs Temporal ──
    print_section("0. AGGREGATED vs TEMPORAL DIFFUSION")
    if agg_res and temp_res:
        a_pct = agg_res['adoption_fraction'] * 100
        t_pct = temp_res['adoption_fraction'] * 100
        print(f"   Using the SAME seeds and threshold (θ=0.10):")
        print(f"   • Aggregated Graph: {a_pct:.1f}% adoption")
        print(f"   • Temporal Snapshots: {t_pct:.1f}% adoption")
        print(f"   • Difference: {a_pct - t_pct:+.1f}%")
        print(f"\n   📝 Insight: Temporal constraints often SLOW DOWN or BLOCK")
        print(f"      diffusion because the 'bridge' contacts might happen")
        print(f"      at the wrong time for the cascade to cross.")


    sweep_stats = sweep_df.groupby("threshold")["adoption_fraction"].mean()

    # Find the critical threshold
    success_thresholds = [t for t, a in sweep_stats.items() if a > 0.5]
    fail_thresholds = [t for t, a in sweep_stats.items() if a <= 0.15]

    if success_thresholds:
        print(f"   ✅ Cascades SUCCEED (>50% adoption) at thresholds: "
              f"{[f'{t:.2f}' for t in success_thresholds]}")
    else:
        print(f"   ⚠  No thresholds achieved >50% adoption")
        print(f"      This means the network is resistant to cascade diffusion")
        print(f"      (likely due to high density — avg degree = "
              f"{2*n_edges/n_nodes:.1f})")

    if fail_thresholds:
        print(f"   ❌ Cascades FAIL (<15% adoption) at thresholds: "
              f"{[f'{t:.2f}' for t in fail_thresholds]}")

    # Find critical transition point
    thresholds_sorted = sorted(sweep_stats.items())
    for i in range(1, len(thresholds_sorted)):
        t_prev, a_prev = thresholds_sorted[i-1]
        t_curr, a_curr = thresholds_sorted[i]
        if a_prev > 0.3 and a_curr < 0.15:
            print(f"\n   📍 PHASE TRANSITION detected between "
                  f"θ={t_prev:.2f} ({a_prev:.1%}) "
                  f"and θ={t_curr:.2f} ({a_curr:.1%})")
            print(f"      → This is the 'tipping point' where cascades "
                  f"stop spreading")
            break

    # ── Insight 2: Network Structure ──
    print_section("2. NETWORK STRUCTURE")
    density = 2 * n_edges / (n_nodes * (n_nodes - 1))
    print(f"   Network has {n_nodes} nodes, {n_edges} edges")
    print(f"   Density: {density:.4f}")

    if density > 0.5:
        print(f"   📝 This is a DENSE network (density > 0.5)")
        print(f"      Dense networks require MANY neighbors to adopt")
        print(f"      before threshold is met, making cascades harder")
        print(f"      at moderate-to-high thresholds.")
    elif density > 0.1:
        print(f"   📝 This is a MODERATELY connected network")
    else:
        print(f"   📝 This is a SPARSE network — cascades depend on bridges")

    # ── Insight 3: Homophily Effect ──
    print_section("3. EFFECT OF HOMOPHILY")

    if homophily_df is not None and len(homophily_df) > 0:
        homo_stats = homophily_df.groupby("homophily_weight")[
            "adoption_fraction"].mean()

        no_homo = homo_stats.get(0.0, None)
        high_homo = homo_stats.iloc[-1] if len(homo_stats) > 1 else None

        if no_homo is not None and high_homo is not None:
            diff = high_homo - no_homo
            if abs(diff) < 0.02:
                print(f"   📝 Homophily has MINIMAL effect on cascade size")
                print(f"      Without: {no_homo:.1%} → With max: "
                      f"{high_homo:.1%} (Δ = {diff:+.1%})")
                print(f"      This suggests the network already has strong")
                print(f"      cross-department connections.")
            elif diff > 0:
                print(f"   📈 Homophily INCREASES cascade size!")
                print(f"      Without: {no_homo:.1%} → With max: "
                      f"{high_homo:.1%} (Δ = {diff:+.1%})")
                print(f"      Same-department influence helps ideas spread")
                print(f"      within departments, creating local clusters")
                print(f"      that then spill over.")
            else:
                print(f"   📉 Homophily DECREASES cascade size!")
                print(f"      Without: {no_homo:.1%} → With max: "
                      f"{high_homo:.1%} (Δ = {diff:+.1%})")
                print(f"      Over-weighting same-department ties makes it")
                print(f"      harder for ideas to cross department boundaries.")
    else:
        print(f"   ⚠ Homophily experiment data not available")

    # ── Insight 4: Weak Ties ──
    print_section("4. EFFECT OF WEAK TIES (GRANOVETTER)")

    if weak_tie_df is not None and len(weak_tie_df) > 0:
        wt_orig = weak_tie_df[weak_tie_df["fraction_removed"] == 0.0][
            "adoption_fraction"].mean()

        wt_high = weak_tie_df[
            (weak_tie_df["mode"] == "high") &
            (weak_tie_df["fraction_removed"] > 0)
        ]
        wt_low = weak_tie_df[
            (weak_tie_df["mode"] == "low") &
            (weak_tie_df["fraction_removed"] > 0)
        ]

        if len(wt_high) > 0:
            wt_high_avg = wt_high.groupby("fraction_removed")[
                "adoption_fraction"].mean()
            wt_high_20 = wt_high_avg.get(0.2, wt_high_avg.iloc[-1])
            diff_h = wt_high_20 - wt_orig

            print(f"   Baseline adoption: {wt_orig:.1%}")
            print(f"   After removing 20% bridges: {wt_high_20:.1%} "
                  f"(Δ = {diff_h:+.1%})")

            if diff_h < -0.05:
                print(f"   📝 Removing bridges HURTS diffusion significantly!")
                print(f"      → Weak ties are CRITICAL for cascade spread")
                print(f"      → Granovetter's hypothesis is SUPPORTED")
            elif abs(diff_h) < 0.02:
                print(f"   📝 Removing bridges has LITTLE effect")
                print(f"      → Network has too many redundant paths")
            else:
                print(f"   📝 Removing bridges paradoxically helps (dense network)")

        if len(wt_low) > 0:
            wt_low_avg = wt_low.groupby("fraction_removed")[
                "adoption_fraction"].mean()
            wt_low_20 = wt_low_avg.get(0.2, wt_low_avg.iloc[-1])
            diff_l = wt_low_20 - wt_orig
            print(f"   After removing 20% redundant edges: {wt_low_20:.1%} "
                  f"(Δ = {diff_l:+.1%})")
    else:
        print(f"   ⚠ Weak tie experiment data not available")

    # ── Insight 5: Multiple Equilibria ──
    print_section("5. MULTIPLE EQUILIBRIA (VARIANCE)")

    var_stats = sweep_df.groupby("threshold")["adoption_fraction"].agg(
        ["mean", "std"])
    var_stats["cv"] = var_stats["std"] / var_stats["mean"].replace(0, 1)

    high_var = var_stats[var_stats["cv"] > 0.3]
    if len(high_var) > 0:
        print(f"   ⚡ Multiple equilibria detected at {len(high_var)} "
              f"threshold(s)!")
        for t, row in high_var.iterrows():
            print(f"      θ={t:.2f}: mean={row['mean']:.1%}, "
                  f"std={row['std']:.1%}, CV={row['cv']:.2f}")
        print(f"   📝 This means cascade outcomes are UNPREDICTABLE")
        print(f"      at these thresholds — small changes in seed selection")
        print(f"      lead to very different outcomes.")
    else:
        print(f"   ✓ No strong multiple equilibria detected")
        print(f"      Cascade outcomes are relatively predictable")
        print(f"      for any given threshold.")

    print("\n" + "=" * 65)
    print("  ANALYSIS COMPLETE")
    print("=" * 65)


# ─── MAIN PIPELINE ─────────────────────────────────────────

def main():
    random.seed(42)
    np.random.seed(42)

    print_header("NETWORK CASCADE LAB")
    print("  Simulation of Idea Diffusion using Coordination Games")
    print("  on Real-World Social Networks")
    print("=" * 65)

    # ────────────────────────────────────────────────────────
    # STEP 1: Load Data
    # ────────────────────────────────────────────────────────
    print_header("STEP 1: Loading Dataset")
    G, contacts, departments = load_and_build()
    snapshots = build_temporal_snapshots(contacts, departments)

    # ────────────────────────────────────────────────────────
    # STEP 2: Network Visualization (Departments)
    # ────────────────────────────────────────────────────────
    print_header("STEP 2: Network Visualization")
    plot_network(G, title="Workplace Social Network — Departments")

    # ────────────────────────────────────────────────────────
    # STEP 3: Example Cascade Simulations (Aggregated)
    # ────────────────────────────────────────────────────────
    print_header("STEP 3: Example Cascade Simulations (Aggregated)")

    # Low threshold — should spread
    print_section("Test A: Low threshold (0.10)")
    result_low = run_cascade(G, threshold=0.10, n_seeds=15,
                              seed_strategy="high_degree",
                              verbose=True)
    plot_cascade_over_time(
        result_low,
        save_path=os.path.join(OUTPUT_DIR, "cascade_low_threshold_agg.png"),
        title=f"Aggregated Cascade (θ=0.10, adopted={result_low['adoption_fraction']:.1%})")
    
    plot_network(
        G, adopters=result_low["final_adopters"],
        seeds=result_low["seeds"],
        save_path=os.path.join(OUTPUT_DIR, "network_cascade_low.png"),
        title=f"Network after Cascade (θ=0.10)")

    # ────────────────────────────────────────────────────────
    # STEP 4: Temporal Cascade Simulation
    # ────────────────────────────────────────────────────────
    print_header("STEP 4: Temporal Cascade Simulation")
    print_section("Test D: Temporal Cascade (θ=0.10)")
    
    # We use the same seeds for a fair comparison
    temporal_result = run_temporal_cascade(
        snapshots, threshold=0.10, seeds=result_low["seeds"],
        verbose=True
    )
    
    plot_cascade_over_time(
        temporal_result,
        save_path=os.path.join(OUTPUT_DIR, "cascade_temporal.png"),
        title=f"Temporal Cascade (θ=0.10, adopted={temporal_result['adoption_fraction']:.1%})")

    # ────────────────────────────────────────────────────────
    # STEP 4: Threshold Sweep Experiment
    # ────────────────────────────────────────────────────────
    print_header("STEP 4: Threshold Sweep Experiment")
    sweep_df = threshold_sweep(G, n_seeds=15, n_runs=10)
    plot_adoption_vs_threshold(sweep_df)

    # Variance analysis
    var_df = variance_analysis(sweep_df)

    # ────────────────────────────────────────────────────────
    # STEP 5: Homophily Experiment
    # ────────────────────────────────────────────────────────
    print_header("STEP 5: Homophily Experiment")
    homophily_df = homophily_experiment(
        G,
        thresholds=[0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5],
        homophily_values=[0.0, 0.5, 1.0, 2.0],
        n_seeds=15, n_runs=5
    )
    plot_homophily_comparison(homophily_df)

    # ────────────────────────────────────────────────────────
    # STEP 6: Weak Tie Experiment
    # ────────────────────────────────────────────────────────
    print_header("STEP 6: Weak Tie Experiment")
    weak_tie_df = weak_tie_experiment(
        G, threshold=0.15, n_seeds=15, n_runs=5
    )
    plot_weak_tie_comparison(weak_tie_df)

    # ────────────────────────────────────────────────────────
    # STEP 7: Print Insights
    # ────────────────────────────────────────────────────────
    print_insights(sweep_df, homophily_df, weak_tie_df, G, 
                   agg_res=result_low, temp_res=temporal_result)

    # ────────────────────────────────────────────────────────
    # SUMMARY
    # ────────────────────────────────────────────────────────
    print(f"\n📁 All plots saved to: {OUTPUT_DIR}/")
    print(f"\n📊 Generated visualizations:")
    for fname in sorted(os.listdir(OUTPUT_DIR)):
        if fname.endswith('.png'):
            fpath = os.path.join(OUTPUT_DIR, fname)
            size_kb = os.path.getsize(fpath) / 1024
            print(f"   • {fname} ({size_kb:.0f} KB)")

    print(f"\n🌐 To start the web interface:")
    print(f"   python src/api.py")
    print(f"   Then open frontend/index.html in your browser")

    print(f"\n✅ Pipeline complete!")


if __name__ == "__main__":
    main()
