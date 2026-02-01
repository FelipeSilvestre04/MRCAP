# MRCAP - Maximum Remaining Continuous Area Problem

This repository contains the source code and datasets for the paper submitted to **ITOR (International Transactions in Operational Research)**.

## Overview

We address a real-world industrial challenge in 2D irregular packing by proposing:
- **MRCAP**: A new problem definition focused on remnant material reuse
- **MCA (Maximum Continuous Area)**: A novel metric to measure and maximize continuous unused area in layouts
- **MCCA (Maximum Continuous Convex Area)**: An enhanced metric weighting by convexity factor

Our methodology optimizes the placement policy using an 11-heuristic portfolio within the Random-Key Optimizer (RKO) framework.

## Repository Structure

```
ITOR/
├── KP/                  # 2D Irregular Knapsack Problem
│   ├── code/            # Knapsack2D solver
│   │   └── NFPs/        # Pre-computed No-Fit Polygons
│   ├── instances/       # Benchmark + ED-C1 to ED-C5 instances
│   └── output/          # Results
├── SPP/                 # Strip Packing Problem
│   ├── code/            # SPP2D solver
│   │   └── NFPs/        # Pre-computed NFPs
│   ├── instances/       # Classic benchmark datasets
│   └── output/          # Results
├── MRCAP/               # Maximum Remaining Continuous Area Problem
│   ├── code/            # MRCAP_MCA.py and MRCAP_MCCA.py solvers
│   │   └── NFPs/        # Pre-computed NFPs for ED instances
│   ├── instances/       # 14 industrial instances (ED-1 to ED-14)
│   └── output/          # Results and visualizations
├── utils/               # Shared utilities
│   ├── RKO_v3.py        # Random-Key Optimizer framework
│   ├── nfp_teste.py     # NFP calculation functions
│   └── botao.py         # Visualization utilities
└── requirements.txt     # Python dependencies
```

## Instances

| Problem | Instances | Description |
|---------|-----------|-------------|
| MRCAP   | ED-1 to ED-14 | Industrial 2D irregular cutting instances |
| KP      | Classic + ED-C1 to ED-C5 | Knapsack with custom instances |
| SPP     | Classic benchmarks | fu, jackobs, shapes, swim, etc. |

## Key Features

- **Multiple Decoders**: D0 (basic), D1_A (with placement rules), D2 (shrink factor)
- **NFP-based Collision Detection**: Pre-computed No-Fit Polygons for efficiency
- **Piece Rotation**: Support for 0°, 90°, 180°, 270° rotations
- **MCA/MCCA Metrics**: Morphological operations for continuous area calculation
- **Pairwise Clustering**: Optional piece pairing for improved solutions
- **RKO Framework**: 11-heuristic portfolio (BRKGA, MS, SA, VNS, ILS, LNS, PSO, GA)

## Quick Start

```bash
# Install dependencies
pip install -r ITOR/requirements.txt

# Run MRCAP-MCA solver
cd ITOR/MRCAP/code
python MRCAP_MCA.py

# Run MRCAP-MCCA solver
python MRCAP_MCCA.py

# Run Knapsack 2D solver
cd ITOR/KP/code
python Knapsack2D.py
```

## Requirements

- Python 3.8+
- NumPy, SciPy, Shapely, Matplotlib, OpenCV, Pillow

## Citation

If you use this code in your research, please cite our paper (reference to be added upon publication).

## License

MIT License
