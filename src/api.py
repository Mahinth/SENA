"""
Flask API for the Network Cascade Lab
======================================

This provides a REST API that the Angular frontend uses to:
  1. Get network information
  2. Run simulations with custom parameters
  3. Run threshold sweep experiments

Endpoints:
  GET  /api/network-info       → Graph statistics
  POST /api/simulate           → Run single cascade
  POST /api/threshold-sweep    → Run threshold sweep
  GET  /api/departments        → List departments
"""

import os
import sys
import json
import random

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from flask_cors import CORS

from data_loader import load_and_build
from simulation import run_cascade, select_seeds
from experiments import threshold_sweep, variance_analysis

# ─── Initialize ────────────────────────────────────────────

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)  # Allow cross-origin requests from Angular

@app.route("/")
def serve_index():
    """Serve the index.html from the frontend folder."""
    return app.send_static_file("index.html")

# Load data once at startup
print("🔄 Loading network data...")
G, contacts, departments = load_and_build()
print("✅ API ready!\n")


# ─── Endpoints ─────────────────────────────────────────────

@app.route('/api/network-info', methods=['GET'])
def network_info():
    """Return basic network statistics."""
    from collections import defaultdict

    dept_counts = defaultdict(int)
    for _, data in G.nodes(data=True):
        dept_counts[data.get('department', 'UNKNOWN')] += 1

    degrees = [d for _, d in G.degree()]

    return jsonify({
        "n_nodes": G.number_of_nodes(),
        "n_edges": G.number_of_edges(),
        "density": round(float(__import__('networkx').density(G)), 4),
        "avg_degree": round(sum(degrees) / len(degrees), 1),
        "departments": dict(sorted(dept_counts.items())),
        "n_departments": len(dept_counts),
    })


@app.route('/api/departments', methods=['GET'])
def get_departments():
    """List all departments."""
    from collections import defaultdict
    dept_counts = defaultdict(int)
    for _, data in G.nodes(data=True):
        dept_counts[data.get('department', 'UNKNOWN')] += 1
    return jsonify(dict(sorted(dept_counts.items())))


@app.route('/api/simulate', methods=['POST'])
def simulate():
    """
    Run a single cascade simulation.

    POST body (JSON):
      {
        "threshold": 0.3,         (required)
        "n_seeds": 10,            (optional, default 10)
        "seed_strategy": "random", (optional)
        "homophily_weight": 0.0,  (optional)
        "max_steps": 100          (optional)
      }
    """
    data = request.get_json()

    threshold = float(data.get("threshold", 0.3))
    n_seeds = int(data.get("n_seeds", 10))
    seed_strategy = data.get("seed_strategy", "random")
    homophily_weight = float(data.get("homophily_weight", 0.0))
    max_steps = int(data.get("max_steps", 100))

    result = run_cascade(
        G,
        threshold=threshold,
        n_seeds=n_seeds,
        seed_strategy=seed_strategy,
        homophily_weight=homophily_weight,
        max_steps=max_steps
    )

    # Convert sets to lists for JSON serialization
    steps_data = [len(s) for s in result["steps"]]
    adoption_per_step = [len(s) / result["n_total"] * 100
                         for s in result["steps"]]

    return jsonify({
        "threshold": threshold,
        "n_seeds": n_seeds,
        "homophily_weight": homophily_weight,
        "seed_strategy": seed_strategy,
        "adoption_fraction": round(result["adoption_fraction"] * 100, 2),
        "n_adopted": result["n_adopted"],
        "n_total": result["n_total"],
        "converged_at": result["converged_at"],
        "steps_adopter_count": steps_data,
        "steps_adoption_pct": [round(x, 2) for x in adoption_per_step],
        "seeds": list(result["seeds"]),
        "final_adopters": list(result["final_adopters"]),
    })


@app.route('/api/threshold-sweep', methods=['POST'])
def sweep():
    """
    Run threshold sweep experiment.

    POST body (JSON):
      {
        "n_seeds": 10,              (optional)
        "n_runs": 5,                (optional)
        "homophily_weight": 0.0,    (optional)
        "thresholds": [0.1, 0.2...] (optional)
      }
    """
    data = request.get_json() or {}

    n_seeds = int(data.get("n_seeds", 10))
    n_runs = int(data.get("n_runs", 5))
    homophily_weight = float(data.get("homophily_weight", 0.0))
    thresholds = data.get("thresholds", None)

    if thresholds:
        thresholds = [float(t) for t in thresholds]

    df = threshold_sweep(G, thresholds=thresholds, n_seeds=n_seeds,
                         n_runs=n_runs, homophily_weight=homophily_weight)

    # Aggregate results
    stats = df.groupby("threshold")["adoption_fraction"].agg(
        ["mean", "std", "min", "max"]).reset_index()

    return jsonify({
        "thresholds": stats["threshold"].tolist(),
        "mean_adoption": [round(x * 100, 2) for x in stats["mean"].tolist()],
        "std_adoption": [round(x * 100, 2) for x in stats["std"].tolist()],
        "min_adoption": [round(x * 100, 2) for x in stats["min"].tolist()],
        "max_adoption": [round(x * 100, 2) for x in stats["max"].tolist()],
        "n_seeds": n_seeds,
        "n_runs": n_runs,
        "homophily_weight": homophily_weight,
    })


# ─── Run Server ────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🌐 Starting Network Cascade Lab API...")
    print("   http://localhost:5000")
    print("   Endpoints:")
    print("     GET  /api/network-info")
    print("     POST /api/simulate")
    print("     POST /api/threshold-sweep")
    print("     GET  /api/departments")
    app.run(debug=True, port=5000, host='0.0.0.0')
