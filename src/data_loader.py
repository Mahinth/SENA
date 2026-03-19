"""
Data Loader Module
==================

This module handles:
  1. Loading contact data (who talked to whom, and when)
  2. Loading department data (which department each person belongs to)
  3. Building NetworkX graphs from the data

Key Concepts:
  - AGGREGATED GRAPH: All contacts merged into one graph.
    Edge weight = how many times two people interacted.
  - TEMPORAL SNAPSHOTS: The day split into time windows.
    Each window is a separate graph, showing how the network
    evolves over time.
"""

import os
import networkx as nx
from collections import defaultdict


# ─── FILE PATHS ─────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CONTACT_FILE = os.path.join(DATA_DIR, "tij_InVS15.dat")
DEPARTMENT_FILE = os.path.join(DATA_DIR, "metadata_InVS15.txt")


# ─── LOADING RAW DATA ──────────────────────────────────────

def load_contacts(filepath=None):
    """
    Load contact events from the data file.

    Each line in the file looks like:
        t   i   j
    meaning person i and person j were face-to-face at time t.

    Returns:
        list of tuples: [(timestamp, person_i, person_j), ...]

    Example:
        >>> contacts = load_contacts()
        >>> contacts[0]
        (20, 3, 42)  # At time=20s, person 3 met person 42
    """
    if filepath is None:
        filepath = CONTACT_FILE

    contacts = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            t = int(parts[0])
            i = int(parts[1])
            j = int(parts[2])
            contacts.append((t, i, j))

    print(f"📂 Loaded {len(contacts):,} contact events from {os.path.basename(filepath)}")
    return contacts


def load_departments(filepath=None):
    """
    Load department assignments from the metadata file.

    Each line looks like:
        i   Di
    meaning person i belongs to department Di.

    Returns:
        dict: {person_id: department_name}

    Example:
        >>> depts = load_departments()
        >>> depts[42]
        'DMCT'
    """
    if filepath is None:
        filepath = DEPARTMENT_FILE

    departments = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            node_id = int(parts[0])
            dept = parts[1]
            departments[node_id] = dept

    # Count people per department
    dept_counts = defaultdict(int)
    for dept in departments.values():
        dept_counts[dept] += 1

    print(f"📂 Loaded {len(departments)} people across "
          f"{len(dept_counts)} departments")
    for dept, count in sorted(dept_counts.items()):
        print(f"   {dept}: {count} people")

    return departments


# ─── BUILDING GRAPHS ───────────────────────────────────────

def build_aggregated_graph(contacts, departments):
    """
    Build a single graph from ALL contact events.

    What this does:
      - Each person becomes a NODE
      - If two people ever met, they get an EDGE between them
      - Edge WEIGHT = how many times they interacted (contact frequency)
      - Each node stores its DEPARTMENT as an attribute

    Think of it as: "the overall social network of the workplace"

    Args:
        contacts: list of (timestamp, person_i, person_j)
        departments: dict of {person_id: department}

    Returns:
        nx.Graph: The aggregated social network
    """
    G = nx.Graph()

    # Count interactions per pair
    edge_weights = defaultdict(int)
    all_nodes = set()

    for t, i, j in contacts:
        edge_weights[(min(i, j), max(i, j))] += 1
        all_nodes.add(i)
        all_nodes.add(j)

    # Add nodes with department attribute
    for node_id in all_nodes:
        dept = departments.get(node_id, "UNKNOWN")
        G.add_node(node_id, department=dept)

    # Add edges with weight
    for (i, j), weight in edge_weights.items():
        G.add_edge(i, j, weight=weight)

    print(f"\n🔗 Aggregated graph built:")
    print_network_summary(G)

    return G


def build_temporal_snapshots(contacts, departments, window_seconds=3600):
    """
    Split contacts into time windows and build a graph for each.

    Why temporal snapshots?
      The network isn't static — people meet different colleagues
      at different times. Splitting into windows (e.g., 1-hour chunks)
      lets us see how the network evolves.

    Args:
        contacts: list of (timestamp, person_i, person_j)
        departments: dict of {person_id: department}
        window_seconds: size of each time window (default: 3600 = 1 hour)

    Returns:
        list of (time_start, nx.Graph) tuples, one per window
    """
    if not contacts:
        return []

    # Find time range
    times = [t for t, _, _ in contacts]
    t_min, t_max = min(times), max(times)

    # Group contacts by time window
    windows = defaultdict(list)
    for t, i, j in contacts:
        window_start = ((t - t_min) // window_seconds) * window_seconds + t_min
        windows[window_start].append((t, i, j))

    # Build a graph for each window
    snapshots = []
    for window_start in sorted(windows.keys()):
        window_contacts = windows[window_start]
        G = nx.Graph()

        # Add all known nodes (even if not active in this window)
        for node_id, dept in departments.items():
            G.add_node(node_id, department=dept)

        # Add edges for this window
        edge_weights = defaultdict(int)
        for t, i, j in window_contacts:
            edge_weights[(min(i, j), max(i, j))] += 1

        for (i, j), weight in edge_weights.items():
            G.add_edge(i, j, weight=weight)

        snapshots.append((window_start, G))

    print(f"\n⏱  Built {len(snapshots)} temporal snapshots "
          f"(window = {window_seconds}s = {window_seconds/3600:.1f}h)")
    if snapshots:
        edges_per_snap = [s[1].number_of_edges() for s in snapshots]
        print(f"   Edges per window: min={min(edges_per_snap)}, "
              f"max={max(edges_per_snap)}, "
              f"avg={sum(edges_per_snap)/len(edges_per_snap):.0f}")

    return snapshots


# ─── NETWORK STATISTICS ────────────────────────────────────

def print_network_summary(G):
    """
    Print key statistics about a network graph.

    This helps us understand:
      - How big the network is (nodes & edges)
      - How dense it is (what fraction of possible edges exist)
      - How connected it is (components, avg degree)
      - Department distribution
    """
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    # Density: fraction of all possible edges that actually exist
    # Density = 2E / (N*(N-1))  for undirected graphs
    density = nx.density(G)

    # Degree: how many connections each person has
    degrees = [d for _, d in G.degree()]
    avg_degree = sum(degrees) / len(degrees) if degrees else 0

    # Connected components
    components = list(nx.connected_components(G))

    print(f"   Nodes:      {n_nodes}")
    print(f"   Edges:      {n_edges}")
    print(f"   Density:    {density:.4f}")
    print(f"   Avg degree: {avg_degree:.1f}")
    print(f"   Components: {len(components)} "
          f"(largest: {len(max(components, key=len))} nodes)")

    # Department breakdown
    dept_counts = defaultdict(int)
    for _, data in G.nodes(data=True):
        dept_counts[data.get('department', 'UNKNOWN')] += 1

    if dept_counts:
        print(f"   Departments: {dict(sorted(dept_counts.items()))}")


# ─── CONVENIENCE FUNCTION ──────────────────────────────────

def load_and_build(contact_path=None, department_path=None):
    """
    One-stop function: load data + build aggregated graph.

    Usage:
        G, contacts, departments = load_and_build()
    """
    contacts = load_contacts(contact_path)
    departments = load_departments(department_path)
    G = build_aggregated_graph(contacts, departments)
    return G, contacts, departments


# ─── TEST IT ────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Step 1: Loading & Understanding the Dataset")
    print("=" * 60)

    # Load everything
    G, contacts, departments = load_and_build()

    # Build temporal snapshots too
    snapshots = build_temporal_snapshots(contacts, departments, window_seconds=3600)

    # Show some sample data
    print("\n📊 Sample contact events (first 5):")
    for t, i, j in contacts[:5]:
        dept_i = departments.get(i, "?")
        dept_j = departments.get(j, "?")
        print(f"   Time={t}s: Person {i} ({dept_i}) ↔ Person {j} ({dept_j})")

    print("\n✅ Data loading complete! Ready for simulation.")
