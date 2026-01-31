# MRCAP - Maximum Remaining Continuous Area Problem

This repository contains the source code and datasets for the paper submitted to **ITOR (International Transactions in Operational Research)**.

## Overview

We address a real-world industrial challenge in 2D irregular packing by proposing:
- **MRCAP**: A new problem definition focused on remnant material reuse
- **MCA (Maximum Continuous Area)**: A novel metric to measure and maximize continuous unused area in layouts

Our methodology optimizes the placement policy using an 11-heuristic portfolio within the Random-Key Optimizer (RKO) framework.

## Repository Structure

```
ITOR/
├── KP/          # 2D Irregular Knapsack Problem
│   ├── code/    # Solver implementation
│   ├── instances/  # Benchmark datasets
│   └── output/  # Results
├── SPP/         # Strip Packing Problem
│   ├── code/
│   ├── instances/
│   └── output/
└── MRCAP/       # Maximum Remaining Continuous Area Problem
    ├── code/    # Solver with MCA metric
    ├── instances/  # 14 real-world industrial instances (EB-1 to EB-14)
    └── output/
```

## Key Features

- Constructive heuristics with Bottom-Left and other placement rules
- No-Fit Polygon (NFP) calculation for collision detection
- Support for piece rotation
- Morphological operations for continuous area calculation

## Requirements

- Python 3.8+
- NumPy, Shapely, Matplotlib, OpenCV, SciPy

## Citation

If you use this code in your research, please cite our paper (reference to be added upon publication).

## License

MIT License
