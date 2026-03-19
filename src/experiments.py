"""
Experiments Module
==================

This module runs systematic experiments to study how cascades behave
under different conditions. Think of it as the "science" part —
we vary one thing at a time and measure the outcome.

EXPERIMENTS:
  1. THRESHOLD SWEEP: Try many threshold values → see which ones
     allow cascades and which ones block them.

  2. VARIANCE ANALYSIS: Run the same experiment many times with
     different random seeds → if results vary a lot, that means
     there are MULTIPLE EQUILIBRIA (the outcome depends on who
     starts adopting first).

  3. HOMOPHILY EXPERIMENT: Compare cascade sizes with different
     homophily strengths.

  4. WEAK TIE EXPERIMENT: Compare cascades with/without bridge edges.
"""

import random
import pandas as pd
import numpy as np
from collections import defaultdict


def threshold_sweep(G, thresholds=None, n_seeds=10, n_runs=10,
                    homophily_weight=0.0, seed_strategy="random"):
    """
    Run cascades across a range of threshold values.

    This is the most important experiment:
      At what threshold does the cascade succeed vs fail?

    For each threshold, we run n_runs simulations (with different
    random seeds each time) to get a distribution of outcomes.

    Args:
        G: NetworkX graph
        thresholds: List of thresholds to try (default: 0.05 to 0.8)
        n_seeds: Number of initial adopters per run
        n_runs: How many times to repeat each threshold
        homophily_weight: Homophily strength
        seed_strategy: How to pick seeds

    Returns:
        pd.DataFrame with columns:
          [threshold, run, adoption_fraction, n_adopted, converged_at]
    """
    from simulation import run_cascade

    if thresholds is None:
        thresholds = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35,
                      0.4, 0.45, 0.5, 0.6, 0.7, 0.8]

    print(f"\n📊 Threshold Sweep Experiment")
    print(f"   Thresholds: {len(thresholds)} values "
          f"({min(thresholds):.2f} to {max(thresholds):.2f})")
    print(f"   Runs per threshold: {n_runs}")
    print(f"   Seeds per run: {n_seeds}")
    print(f"   Homophily weight: {homophily_weight}")
    print(f"   Seed strategy: {seed_strategy}")

    records = []

    for threshold in thresholds:
        for run in range(n_runs):
            result = run_cascade(
                G, threshold=threshold, n_seeds=n_seeds,
                seed_strategy=seed_strategy,
                homophily_weight=homophily_weight
            )
            records.append({
                "threshold": threshold,
                "run": run,
                "adoption_fraction": result["adoption_fraction"],
                "n_adopted": result["n_adopted"],
                "converged_at": result["converged_at"],
            })

        # Progress indicator
        avg = np.mean([r["adoption_fraction"] for r in records
                       if r["threshold"] == threshold])
        print(f"   θ={threshold:.2f}: avg adoption = {avg:.1%}")

    df = pd.DataFrame(records)
    print(f"\n   ✓ Sweep complete: {len(records)} total simulations")
    return df


def variance_analysis(results_df):
    """
    Analyze variance in cascade outcomes to detect multiple equilibria.

    WHAT ARE MULTIPLE EQUILIBRIA?
      If the same threshold gives very different outcomes depending on
      which random nodes start as seeds, that means the cascade outcome
      is UNSTABLE — small changes in starting conditions lead to
      drastically different results.

      High variance → multiple equilibria exist
      Low variance  → outcome is predictable

    Args:
        results_df: DataFrame from threshold_sweep

    Returns:
        pd.DataFrame with columns:
          [threshold, mean_adoption, std_adoption, min_adoption,
           max_adoption, variance, cv (coefficient of variation)]
    """
    print("\n📊 Variance Analysis (Multiple Equilibria Detection)")

    stats = results_df.groupby("threshold")["adoption_fraction"].agg(
        mean_adoption="mean",
        std_adoption="std",
        min_adoption="min",
        max_adoption="max",
        variance="var"
    ).reset_index()

    # Coefficient of variation: std/mean (higher = more variable)
    stats["cv"] = stats["std_adoption"] / stats["mean_adoption"].replace(0, 1)

    print(f"\n   {'Threshold':>10} {'Mean':>8} {'Std':>8} "
          f"{'Min':>8} {'Max':>8} {'CV':>8}")
    print(f"   {'─'*10} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")

    for _, row in stats.iterrows():
        flag = " ⚡" if row["cv"] > 0.3 else ""
        print(f"   {row['threshold']:>10.2f} "
              f"{row['mean_adoption']:>8.3f} "
              f"{row['std_adoption']:>8.3f} "
              f"{row['min_adoption']:>8.3f} "
              f"{row['max_adoption']:>8.3f} "
              f"{row['cv']:>8.3f}{flag}")

    # Flag thresholds with high variance
    high_var = stats[stats["cv"] > 0.3]
    if len(high_var) > 0:
        print(f"\n   ⚡ Multiple equilibria detected at thresholds: "
              f"{list(high_var['threshold'].values)}")
    else:
        print(f"\n   ✓ No strong multiple equilibria detected")

    return stats


def homophily_experiment(G, thresholds=None, homophily_values=None,
                         n_seeds=10, n_runs=10):
    """
    Compare cascade outcomes with different homophily strengths.

    This answers: "Does same-department bias help or hurt diffusion?"

    Args:
        G: NetworkX graph
        thresholds: Threshold values to test
        homophily_values: List of homophily weights to compare
        n_seeds: Seeds per run
        n_runs: Runs per condition

    Returns:
        pd.DataFrame with columns:
          [threshold, homophily_weight, run, adoption_fraction, ...]
    """
    from simulation import run_cascade

    if thresholds is None:
        thresholds = [0.1, 0.2, 0.3, 0.4, 0.5]
    if homophily_values is None:
        homophily_values = [0.0, 0.25, 0.5, 1.0, 2.0]

    print(f"\n📊 Homophily Experiment")
    print(f"   Homophily values: {homophily_values}")
    print(f"   Thresholds: {thresholds}")

    records = []

    for hw in homophily_values:
        for threshold in thresholds:
            for run in range(n_runs):
                result = run_cascade(
                    G, threshold=threshold, n_seeds=n_seeds,
                    homophily_weight=hw
                )
                records.append({
                    "threshold": threshold,
                    "homophily_weight": hw,
                    "run": run,
                    "adoption_fraction": result["adoption_fraction"],
                    "n_adopted": result["n_adopted"],
                    "converged_at": result["converged_at"],
                })

        avg = np.mean([r["adoption_fraction"] for r in records
                       if r["homophily_weight"] == hw])
        print(f"   h={hw:.2f}: avg adoption = {avg:.1%}")

    df = pd.DataFrame(records)
    print(f"\n   ✓ Homophily experiment complete: {len(records)} simulations")
    return df


def weak_tie_experiment(G, threshold=0.2, fractions=None,
                        n_seeds=10, n_runs=10):
    """
    Compare cascades when bridge edges vs redundant edges are removed.

    This answers Granovetter's question:
      "Are weak ties (bridges) more important for diffusion
       than strong ties (redundant local connections)?"

    Args:
        G: NetworkX graph
        threshold: Adoption threshold
        fractions: Edge removal fractions to test
        n_seeds: Seeds per run
        n_runs: Runs per condition

    Returns:
        pd.DataFrame
    """
    from simulation import run_cascade, select_seeds
    from weak_ties import remove_edges_by_betweenness

    if fractions is None:
        fractions = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3]

    print(f"\n📊 Weak Tie Experiment")
    print(f"   Threshold: {threshold}")
    print(f"   Edge removal fractions: {fractions}")

    records = []

    for mode in ["high", "low"]:
        for frac in fractions:
            if frac == 0:
                G_test = G.copy()
            else:
                G_test = remove_edges_by_betweenness(G, fraction=frac,
                                                      mode=mode)

            for run in range(n_runs):
                result = run_cascade(
                    G_test, threshold=threshold, n_seeds=n_seeds
                )
                records.append({
                    "mode": mode if frac > 0 else "original",
                    "fraction_removed": frac,
                    "run": run,
                    "adoption_fraction": result["adoption_fraction"],
                    "n_adopted": result["n_adopted"],
                    "converged_at": result["converged_at"],
                })

        avg_high = np.mean([r["adoption_fraction"] for r in records
                            if r["mode"] == mode])
        print(f"   Mode={mode}: avg adoption = {avg_high:.1%}")

    df = pd.DataFrame(records)
    print(f"\n   ✓ Weak tie experiment complete: {len(records)} simulations")
    return df


# ─── TEST ──────────────────────────────────────────────────

if __name__ == "__main__":
    from data_loader import load_and_build

    print("=" * 60)
    print("  Step 6: Running Experiments")
    print("=" * 60)

    G, contacts, departments = load_and_build()

    # Quick threshold sweep (fewer runs for speed)
    sweep_df = threshold_sweep(G, n_seeds=15, n_runs=5)

    # Variance analysis
    var_df = variance_analysis(sweep_df)

    print("\n✅ Experiments module working!")
