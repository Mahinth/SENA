# 🌐 Network Cascade Lab

**Simulation of Idea Diffusion using Coordination Games on Real-World Social Networks**

A complete simulation platform for studying how ideas, behaviors, and innovations spread through social networks using game-theoretic models. Built on the SocioPatterns workplace dataset.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![NetworkX](https://img.shields.io/badge/NetworkX-3.0+-green)
![Flask](https://img.shields.io/badge/Flask-3.0+-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📖 Overview

### What is this?

This project simulates **idea diffusion** — how a new behavior (like adopting a messaging app) spreads through a workplace social network. It uses a **threshold-based coordination game** from game theory:

> Each person adopts a new behavior if **enough of their colleagues** have already adopted it.

### Key Concepts

| Concept | Explanation |
|---------|-------------|
| **Coordination Game** | Each person decides to adopt based on their neighbors' behavior |
| **Threshold** | The minimum fraction of neighbors that must adopt for a person to switch |
| **Homophily** | People are more influenced by same-department colleagues |
| **Weak Ties** | Infrequent connections (bridges) that connect different groups |
| **Cascade** | The chain reaction of adoptions spreading through the network |
| **Multiple Equilibria** | Same conditions can lead to different outcomes depending on starting conditions |

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Download/Generate Dataset

```bash
python data/download_data.py
```

### 3. Run Full Pipeline

```bash
python main.py
```

This will:
- Load the social network dataset
- Run cascade simulations at various thresholds
- Run homophily and weak-tie experiments
- Generate all visualization plots in `outputs/`
- Print key insights to the console

### 4. Start Web Interface (Optional)

```bash
# Terminal 1: Start API server
python src/api.py

# Terminal 2: Open frontend
# Open frontend/index.html in your browser
```

---

## 📁 Project Structure

```
SENA/
├── main.py                  # 🎯 Main entry point — runs everything
├── requirements.txt         # Python dependencies
├── README.md                # This file
│
├── data/                    # Dataset files
│   ├── download_data.py     # Download or generate dataset
│   ├── tij_InVS15.dat       # Contact data (t i j)
│   └── metadata_InVS15.txt  # Department data (i Di)
│
├── src/                     # Source modules
│   ├── __init__.py
│   ├── data_loader.py       # Load data & build NetworkX graphs
│   ├── simulation.py        # Threshold coordination game engine
│   ├── weak_ties.py         # Edge betweenness & bridge analysis
│   ├── experiments.py       # Threshold sweep, homophily, variance
│   ├── visualization.py     # Matplotlib plots & network diagrams
│   └── api.py               # Flask REST API
│
├── frontend/                # Web interface
│   ├── index.html           # Main page
│   ├── styles.css           # CSS styles
│   └── app.js               # Frontend logic & charts
│
└── outputs/                 # Generated plots (auto-created)
    ├── adoption_vs_threshold.png
    ├── cascade_over_time.png
    ├── network_visualization.png
    ├── homophily_comparison.png
    └── weak_tie_comparison.png
```

---

## 🔬 Experiments

### 1. Threshold Sweep
Varies the adoption threshold from 0.05 to 0.80 and measures final cascade size. Reveals the **phase transition** — the critical threshold where cascades stop succeeding.

### 2. Homophily Effect
Compares cascades with different same-department influence weights. Tests whether departmental bias helps or hurts idea spread.

### 3. Weak Tie Analysis
Based on Granovetter's "Strength of Weak Ties" theory. Removes bridge edges (high betweenness centrality) vs. redundant edges and compares cascade outcomes.

### 4. Multiple Equilibria
Runs the same experiment multiple times with different random seeds. High variance indicates that cascade outcomes are unstable and depend heavily on starting conditions.

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/network-info` | Network statistics |
| `GET` | `/api/departments` | Department list |
| `POST` | `/api/simulate` | Run single cascade |
| `POST` | `/api/threshold-sweep` | Run threshold sweep |

### Example API Call

```bash
curl -X POST http://localhost:5000/api/simulate \
  -H "Content-Type: application/json" \
  -d '{"threshold": 0.3, "n_seeds": 10, "homophily_weight": 0.5}'
```

---

## 📊 Dataset

**SocioPatterns Workplace Dataset** — Records face-to-face contacts in a French office building (2015).

- **Contact file** (`tij_InVS15.dat`): `t i j` — person `i` and `j` in contact at time `t`
- **Department file** (`metadata_InVS15.txt`): `i Di` — person `i` in department `Di`

If the real dataset can't be downloaded, the script generates synthetic data with similar properties.

---

## 📝 License

MIT License — free to use, modify, and distribute.

---

## 🙏 Acknowledgments

- **SocioPatterns** — for the workplace interaction dataset
- **Mark Granovetter** — "The Strength of Weak Ties" (1973)
- **NetworkX** — graph analysis library
