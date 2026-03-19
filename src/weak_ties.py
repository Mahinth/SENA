"""
Weak Tie Analysis Module
=========================

THE GRANOVETTER HYPOTHESIS:
  Sociologist Mark Granovetter (1973) discovered that "weak ties"
  (acquaintances you don't see often) are surprisingly important
  for spreading information across a network.

  Why? Because weak ties act as BRIDGES between different groups.
  Without them, information stays trapped within tight-knit clusters.

HOW WE MEASURE IT:
  EDGE BETWEENNESS CENTRALITY tells us how important an edge is
  as a bridge. It counts how many shortest paths between ALL pairs
  of nodes pass through that edge.

  High betweenness → edge is an important bridge (weak tie)
  Low betweenness  → edge connects already-close nodes (strong tie)

EXPERIMENTS:
  We remove edges and see how cascade diffusion changes:
    - Remove HIGH betweenness edges → cut bridges → cascade should shrink
    - Remove LOW betweenness edges  → cut redundant links → less effect
"""

import networkx as nx
from collections import defaultdict


def compute_edge_betweenness(G):
    """
    Calculate edge betweenness centrality for all edges.

    What it measures:
      For each edge (u, v), count how many shortest paths between
      ANY two nodes in the network pass through this edge.
      Normalize by the total number of such paths.

    High value → edge is a critical bridge
    Low value  → edge is redundant (many alternative paths exist)

    Returns:
        dict: {(u, v): betweenness_score}
    """
    print("⏳ Computing edge betweenness centrality...")
    eb = nx.edge_betweenness_centrality(G, weight=None)

    # Print summary
    values = list(eb.values())
    print(f"   Computed for {len(eb)} edges")
    print(f"   Min: {min(values):.6f}")
    print(f"   Max: {max(values):.6f}")
    print(f"   Mean: {sum(values)/len(values):.6f}")

    return eb


def remove_edges_by_betweenness(G, fraction=0.1, mode="high"):
    """
    Remove a fraction of edges based on betweenness centrality.

    Args:
        G: NetworkX graph (will NOT be modified — returns a copy)
        fraction: What fraction of edges to remove (0.0 to 1.0)
        mode: "high" = remove bridges (high betweenness)
              "low"  = remove redundant edges (low betweenness)

    Returns:
        nx.Graph: New graph with edges removed
    """
    G_modified = G.copy()

    # Compute betweenness
    eb = nx.edge_betweenness_centrality(G_modified, weight=None)

    # Sort edges by betweenness
    sorted_edges = sorted(eb.items(), key=lambda x: x[1],
                          reverse=(mode == "high"))

    # Remove the specified fraction
    n_remove = int(len(sorted_edges) * fraction)
    edges_to_remove = [edge for edge, _ in sorted_edges[:n_remove]]

    G_modified.remove_edges_from(edges_to_remove)

    print(f"   Removed {n_remove} {mode}-betweenness edges "
          f"({fraction:.0%} of {len(sorted_edges)})")
    print(f"   Remaining edges: {G_modified.number_of_edges()}")

    # Check if graph is still connected
    n_components = nx.number_connected_components(G_modified)
    if n_components > 1:
        print(f"   ⚠ Graph split into {n_components} components")

    return G_modified


def compare_diffusion_with_without_weak_ties(G, threshold=0.3, seeds=None,
                                              n_seeds=10,
                                              homophily_weight=0.0,
                                              fractions=None):
    """
    Run cascade on original graph vs graph with edges removed.

    This lets us see the EFFECT of weak ties on diffusion:
      - If removing high-betweenness edges kills the cascade
        → weak ties were critical for spreading the idea
      - If removing low-betweenness edges has little effect
        → redundant local connections don't matter much

    Args:
        G: Original graph
        threshold: Adoption threshold
        seeds: Seed nodes (same seeds used for all experiments)
        n_seeds: Number of seeds
        homophily_weight: Homophily strength
        fractions: List of fractions to try (default: [0.05, 0.1, 0.2, 0.3])

    Returns:
        dict with results for each condition
    """
    from simulation import run_cascade, select_seeds

    if fractions is None:
        fractions = [0.05, 0.1, 0.2, 0.3]

    if seeds is None:
        seeds = select_seeds(G, n_seeds, "high_degree")

    results = {}

    # Baseline: original graph
    print("\n📊 Baseline (original graph):")
    baseline = run_cascade(G, threshold=threshold, seeds=seeds,
                           homophily_weight=homophily_weight)
    results["original"] = {
        "adoption_fraction": baseline["adoption_fraction"],
        "converged_at": baseline["converged_at"],
        "n_adopted": baseline["n_adopted"],
    }
    print(f"   Adoption: {baseline['adoption_fraction']:.1%}")

    # Remove high-betweenness edges
    print("\n🔪 Removing HIGH-betweenness edges (bridges):")
    for frac in fractions:
        G_mod = remove_edges_by_betweenness(G, fraction=frac, mode="high")
        result = run_cascade(G_mod, threshold=threshold, seeds=seeds,
                             homophily_weight=homophily_weight)
        key = f"high_removed_{frac}"
        results[key] = {
            "adoption_fraction": result["adoption_fraction"],
            "converged_at": result["converged_at"],
            "n_adopted": result["n_adopted"],
            "fraction_removed": frac,
            "mode": "high",
        }
        print(f"   {frac:.0%} removed → Adoption: "
              f"{result['adoption_fraction']:.1%}")

    # Remove low-betweenness edges
    print("\n🔪 Removing LOW-betweenness edges (redundant):")
    for frac in fractions:
        G_mod = remove_edges_by_betweenness(G, fraction=frac, mode="low")
        result = run_cascade(G_mod, threshold=threshold, seeds=seeds,
                             homophily_weight=homophily_weight)
        key = f"low_removed_{frac}"
        results[key] = {
            "adoption_fraction": result["adoption_fraction"],
            "converged_at": result["converged_at"],
            "n_adopted": result["n_adopted"],
            "fraction_removed": frac,
            "mode": "low",
        }
        print(f"   {frac:.0%} removed → Adoption: "
              f"{result['adoption_fraction']:.1%}")

    return results


# ─── TEST ──────────────────────────────────────────────────

if __name__ == "__main__":
    from data_loader import load_and_build

    print("=" * 60)
    print("  Step 5: Weak Tie Analysis")
    print("=" * 60)

    G, contacts, departments = load_and_build()

    # Compute edge betweenness
    eb = compute_edge_betweenness(G)

    # Show top 5 bridge edges
    sorted_eb = sorted(eb.items(), key=lambda x: x[1], reverse=True)
    print("\n🌉 Top 5 bridge edges (highest betweenness):")
    for (u, v), score in sorted_eb[:5]:
        dept_u = G.nodes[u].get('department', '?')
        dept_v = G.nodes[v].get('department', '?')
        print(f"   {u}({dept_u}) ↔ {v}({dept_v}): {score:.6f}")

    # Compare diffusion
    print("\n" + "─" * 40)
    results = compare_diffusion_with_without_weak_ties(
        G, threshold=0.15, n_seeds=15, homophily_weight=0.0)

    print("\n✅ Weak tie analysis complete!")
