"""
MRCAP - Maximum Remaining Continuous Area Problem
Example script to run the MRCAP solver.

Usage:
    python run_mrcap.py [instance_name]

Example:
    python run_mrcap.py EB-1
"""

import sys
import os

# Add the code directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from SPP_Embreaer_Metric import SPP2D, dimensions, ler_poligonos, calcular_area_continua_nao_utilizada

def main():
    # Default instance
    instance = "EB-1"
    
    if len(sys.argv) > 1:
        instance = sys.argv[1]
    
    print(f"Running MRCAP solver for instance: {instance}")
    
    # Get dimensions for the instance
    base, altura, escala, graus = dimensions(instance)
    
    if base is None:
        print(f"Error: Instance '{instance}' not found in dimensions table.")
        print("Available instances: EB-1 to EB-14")
        return
    
    print(f"Dimensions: {base} x {altura}, Scale: {escala}, Rotations: {graus}")
    
    # Create solver instance
    env = SPP2D(
        dataset=instance,
        Base=base,
        Altura=altura,
        Escala=escala,
        Graus=graus,
        tempo=60  # 60 seconds timeout
    )
    
    print("Solver initialized successfully!")
    print(f"Number of pieces: {len(env.lista)}")

if __name__ == "__main__":
    main()
