"""
Simulation Engine: Threshold-Based Coordination Game
=====================================================

THE BIG IDEA:
  Imagine a new idea (like using a new messaging app) spreading
  through a workplace. Each person decides whether to adopt it
  based on how many of their colleagues already use it.

HOW IT WORKS:
  1. Start with a few "seed" adopters (early adopters)
  2. Each round, every non-adopter checks:
     "What fraction of my neighbors have adopted?"
  3. If that fraction ≥ my threshold → I adopt too!
  4. Repeat until no more people adopt (convergence)

COORDINATION GAME INTUITION:
  - If threshold = 0.3 → Easy to convince (30% of friends enough)
  - If threshold = 0.5 → Need half your friends to adopt first
  - If threshold = 0.8 → Very hard to convince (need 80% adoption)

  Lower threshold = faster/bigger cascades
  Higher threshold = cascades often fail or stay small

HOMOPHILY:
  People are more influenced by colleagues in the SAME department.
  We model this by giving same-department neighbors a higher weight.

  Example with homophily_weight = 0.5:
    - Same-department neighbor counts as 1.5 influence
    - Different-department neighbor counts as 1.0 influence
"""

import random
import networkx as nx


def select_seeds(G, n_seeds=5, strategy="random", target_department=None):
    """
    Choose the initial adopters (seeds) who start the cascade.

    Strategies:
      - "random":     Pick n_seeds random nodes
      - "high_degree": Pick the n_seeds most connected nodes
                       (they have the most influence potential)
      - "department":  Pick n_seeds from a specific department
      - "low_degree":  Pick least connected (to test weak starts)

    Args:
        G: NetworkX graph
        n_seeds: How many seed nodes to pick
        strategy: Selection method
        target_department: Used with "department" strategy

    Returns:
        set of seed node IDs
    """
    nodes = list(G.nodes())

    if strategy == "random":
        return set(random.sample(nodes, min(n_seeds, len(nodes))))

    elif strategy == "high_degree":
        # Sort by degree (number of connections), pick highest
        sorted_nodes = sorted(nodes, key=lambda n: G.degree(n), reverse=True)
        return set(sorted_nodes[:n_seeds])

    elif strategy == "low_degree":
        sorted_nodes = sorted(nodes, key=lambda n: G.degree(n))
        return set(sorted_nodes[:n_seeds])

    elif strategy == "department":
        # Pick seeds from a specific department
        dept_nodes = [n for n in nodes
                      if G.nodes[n].get('department') == target_department]
        if not dept_nodes:
            print(f"⚠ No nodes in department '{target_department}', "
                  f"falling back to random")
            return set(random.sample(nodes, min(n_seeds, len(nodes))))
        return set(random.sample(dept_nodes, min(n_seeds, len(dept_nodes))))

    else:
        raise ValueError(f"Unknown strategy: {strategy}")


def compute_adoption_fraction(G, node, adopters, homophily_weight=0.0):
    """
    Calculate what fraction of a node's influence has adopted.

    Without homophily (homophily_weight = 0):
      fraction = (# adopted neighbors) / (# total neighbors)

    With homophily (homophily_weight > 0):
      Same-department neighbors get extra weight.
      fraction = (weighted adopted) / (weighted total)

    Example:
      Node has 4 neighbors: A(same dept, adopted), B(diff dept, adopted),
                             C(same dept, not), D(diff dept, not)
      Without homophily: 2/4 = 0.50
      With homophily=0.5: (1.5 + 1.0) / (1.5 + 1.0 + 1.5 + 1.0) = 2.5/5.0 = 0.50
      But if A and C adopted instead: (1.5 + 1.5) / 5.0 = 0.60
      → Same-department adoption matters more!

    Args:
        G: NetworkX graph
        node: The node to check
        adopters: Set of nodes that have already adopted
        homophily_weight: Extra weight for same-department neighbors (0 = none)

    Returns:
        float: Weighted fraction of adopted neighbors (0.0 to 1.0)
    """
    neighbors = list(G.neighbors(node))
    if not neighbors:
        return 0.0

    node_dept = G.nodes[node].get('department', None)

    weighted_adopted = 0.0
    weighted_total = 0.0

    for neighbor in neighbors:
        # Base weight is 1.0
        weight = 1.0

        # Add homophily bonus if same department
        if homophily_weight > 0:
            neighbor_dept = G.nodes[neighbor].get('department', None)
            if node_dept and neighbor_dept and node_dept == neighbor_dept:
                weight += homophily_weight

        weighted_total += weight
        if neighbor in adopters:
            weighted_adopted += weight

    return weighted_adopted / weighted_total if weighted_total > 0 else 0.0


def run_cascade(G, threshold=0.3, seeds=None, n_seeds=5,
                seed_strategy="random", homophily_weight=0.0,
                max_steps=100, verbose=False):
    """
    Run the full cascade simulation.

    This is the main function. It simulates idea diffusion step by step:
      1. Start with seed adopters
      2. Each step: check all non-adopters → adopt if threshold met
      3. Stop when no new adoptions occur (convergence) or max steps

    Args:
        G: NetworkX graph (the social network)
        threshold: Adoption threshold (0.0 to 1.0)
            Lower = easier to adopt, Higher = harder
        seeds: Pre-selected seed nodes (set), or None to auto-select
        n_seeds: Number of seeds if auto-selecting
        seed_strategy: How to pick seeds ("random", "high_degree", etc.)
        homophily_weight: Extra weight for same-department influence (0 = off)
        max_steps: Maximum simulation steps (safety limit)
        verbose: Whether to print step-by-step progress

    Returns:
        dict with keys:
          - "steps": list of sets (adopters at each step)
          - "final_adopters": set of all adopters at convergence
          - "adoption_fraction": fraction of network that adopted
          - "converged_at": step number where cascade stopped
          - "seeds": the seed nodes used
          - "threshold": the threshold used
    """
    # Select seeds
    if seeds is None:
        seeds = select_seeds(G, n_seeds, seed_strategy)

    # Initialize: seeds adopt at step 0
    adopters = set(seeds)
    history = [set(seeds)]  # Record adopters at each step

    if verbose:
        n = G.number_of_nodes()
        print(f"\n🚀 Cascade started!")
        print(f"   Threshold: {threshold}")
        print(f"   Seeds: {len(seeds)} nodes")
        print(f"   Homophily weight: {homophily_weight}")
        print(f"   Step 0: {len(adopters)}/{n} adopted "
              f"({100*len(adopters)/n:.1f}%)")

    # Run simulation
    for step in range(1, max_steps + 1):
        new_adopters = set()

        # Check each non-adopter
        for node in G.nodes():
            if node in adopters:
                continue  # Already adopted, skip

            # Calculate adoption pressure
            fraction = compute_adoption_fraction(
                G, node, adopters, homophily_weight)

            # Adopt if enough neighbors have adopted
            if fraction >= threshold:
                new_adopters.add(node)

        # Update adopters
        adopters = adopters | new_adopters
        history.append(set(adopters))

        if verbose:
            n = G.number_of_nodes()
            print(f"   Step {step}: {len(adopters)}/{n} adopted "
                  f"({100*len(adopters)/n:.1f}%) "
                  f"[+{len(new_adopters)} new]")

        # Check convergence
        if not new_adopters:
            if verbose:
                print(f"   ✓ Converged at step {step} (no new adoptions)")
            break

    n_total = G.number_of_nodes()
    result = {
        "steps": history,
        "final_adopters": adopters,
        "adoption_fraction": len(adopters) / n_total if n_total > 0 else 0,
        "converged_at": len(history) - 1,
        "seeds": seeds,
        "threshold": threshold,
        "n_total": n_total,
        "n_adopted": len(adopters),
    }

    return result


def run_temporal_cascade(snapshots, threshold=0.3, seeds=None, n_seeds=5,
                         seed_strategy="random", homophily_weight=0.0,
                         verbose=False):
    """
    Run a cascade simulation over TEMPORAL SNAPSHOTS.

    In a temporal cascade:
      - Adoption only happens when nodes are ACTIVE in a specific time window.
      - If I have adopted, I can only influence my neighbors who are
        talking to me RIGHT NOW (in this snapshot).
      - Once a node adopts, they stay an adopter forever.

    Args:
        snapshots: List of (time, G) tuples from build_temporal_snapshots
        threshold: Adoption threshold
        seeds: Initial adopter set
        n_seeds: Number of seeds if seeds is None
        seed_strategy: Strategy to pick seeds
        homophily_weight: Same-department bias
        verbose: Print progress

    Returns:
        Similar dict to run_cascade but with temporal metrics.
    """
    if not snapshots:
        return None

    # Use the first snapshot's nodes to select seeds
    first_G = snapshots[0][1]
    if seeds is None:
        seeds = select_seeds(first_G, n_seeds, seed_strategy)

    adopters = set(seeds)
    history = [set(seeds)]
    time_points = [snapshots[0][0]]

    if verbose:
        print(f"\n⏱ Starting Temporal Cascade ({len(snapshots)} snapshots)")
        print(f"   Step 0 (T={snapshots[0][0]}): {len(adopters)} adopted")

    # Iterate through time snapshots
    for i, (t, G_t) in enumerate(snapshots):
        new_adopters = set()

        # In this specific time window, check non-adopters
        for node in G_t.nodes():
            if node in adopters:
                continue

            # Check neighbors in the CURRENT snapshot G_t
            # (Only people you are actually talking to in this window)
            fraction = compute_adoption_fraction(
                G_t, node, adopters, homophily_weight)

            if fraction >= threshold:
                new_adopters.add(node)

        # Update and record
        if new_adopters:
            adopters = adopters | new_adopters

        history.append(set(adopters))
        time_points.append(t)

        if verbose and (i % 5 == 0 or new_adopters):
            print(f"   Snapshot {i} (T={t}): {len(adopters)} total adopted "
                  f"[+{len(new_adopters)} new]")

    n_total = first_G.number_of_nodes()
    return {
        "steps": history,
        "time_points": time_points,
        "final_adopters": adopters,
        "adoption_fraction": len(adopters) / n_total if n_total > 0 else 0,
        "converged_at": len(history) - 1,
        "seeds": seeds,
        "n_total": n_total,
        "n_adopted": len(adopters)
    }


# ─── TEST THE SIMULATION ───────────────────────────────────

if __name__ == "__main__":
    from data_loader import load_and_build

    print("=" * 60)
    print("  Step 3: Testing the Coordination Game Simulation")
    print("=" * 60)

    # Load data
    G, contacts, departments = load_and_build()

    # Test 1: Easy threshold (should spread widely)
    print("\n" + "─" * 40)
    print("Test 1: Low threshold (0.2) — should cascade widely")
    result_easy = run_cascade(G, threshold=0.2, n_seeds=5,
                               seed_strategy="high_degree",
                               verbose=True)
    print(f"\n   Final adoption: {result_easy['adoption_fraction']:.1%}")

    # Test 2: Hard threshold (should mostly fail)
    print("\n" + "─" * 40)
    print("Test 2: High threshold (0.7) — cascade likely fails")
    result_hard = run_cascade(G, threshold=0.7, n_seeds=5,
                               seed_strategy="high_degree",
                               verbose=True)
    print(f"\n   Final adoption: {result_hard['adoption_fraction']:.1%}")

    # Test 3: With homophily
    print("\n" + "─" * 40)
    print("Test 3: Medium threshold (0.4) with homophily")
    result_homo = run_cascade(G, threshold=0.4, n_seeds=5,
                               seed_strategy="high_degree",
                               homophily_weight=0.5,
                               verbose=True)
    print(f"\n   Final adoption: {result_homo['adoption_fraction']:.1%}")

    print("\n✅ Simulation engine working!")
