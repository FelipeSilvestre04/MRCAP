import os
import numpy as np
import time
import random
import copy
import math
import datetime
import bisect
from abc import ABC, abstractmethod
from multiprocessing import Manager, Process, cpu_count

"""
This script provides a Python implementation of the Random-Key Optimizer (RKO), a versatile and modular framework designed to solve complex combinatorial optimization problems.
The core philosophy is the separation of the metaheuristic (the search strategy) from the problem-specific logic (the decoder). 

Key implemented components of the RKO framework include:

Core Framework & Parallelism:
    -   A central `RKO` class that encapsulates the main optimization logic.
    -   A parallel execution engine managed by the `solve` method, which launches different metaheuristics as separate processes using Python's `multiprocessing` library.
    -   A shared `ElitePoolManager` (managed via `multiprocessing.Manager`) that allows different search strategies to exchange promising solutions.
    -   A standardized `shaking` mechanism for solution perturbation (Swap, Swap Neighbor, Invert/Mirror, Random)
    -   A `Blending` function for crossover, enabling the combination of parent solutions to create new offspring, a key component used in Nelder-Mead and genetic-based algorithms.

Intensification & Local Search:
    -   The script uses Random Variable Neighborhood Descent (RVND) as its primary local search engine.  
    -   The `RVND` is powered by a suite of problem-independent local search heuristics that operate directly on the random-key space:
        -   `SwapLS`: Explores the solution space by swapping pairs of keys.
        -   `InvertLS`: Inverts key values (1 - key), analogous to the "Mirror" move.
        -   `FareyLS`: Adjusts keys using values derived from the Farey sequence, allowing for fine-tuned, structured exploration of the search space.
        -   `NelderMeadSearch`: A sophisticated simplex-based optimization heuristic adapted for the random-key space, which uses the `Blending` method to perform reflection, expansion, and contraction moves.

Implemented Metaheuristics:
    -   The framework includes several classic metaheuristics, all adapted to operate on random-key vectors and utilize the core `shaking` and `RVND` components:
        -   `SimulatedAnnealing (SA)`: Uses `shaking` for generating new candidate solutions and `RVND` before the temperature is lowered.
        -   `Iterated Local Search (ILS)`: Alternates between a perturbation step (`shaking`) and an intensification step (`RVND`).
        -   `Variable Neighborhood Search (VNS)`: Employs `shaking` with varying intensity levels (controlled by the neighborhood index `k`) and applies `RVND` to explore the perturbed solution's surroundings.
        -   `Biased Random-Key Genetic Algorithm (BRKGA)`: A functional implementation of this evolutionary algorithm is included, managing a population of solutions and performing crossover.

This implementation successfully transitions the robust, modular, and high-performance concepts of the RKO framework into a flexible Python environment.

--- Next Steps & Missing Components ---

Additional Metaheuristics:
    To achieve full feature parity with the C++ version, the following metaheuristics need to be implemented:
        - `GRASP` (Greedy Randomized Adaptive Search Procedure) 
        - `GA` (standard Genetic Algorithm using blending)
        - `PSO` (Particle Swarm Optimization) 
        - `LNS` (Large Neighborhood Search) 

Online Parameter Control:
    A crucial missing component is the `Q-Learning` module for online parameter control. 
    This would allow each metaheuristic to dynamically adapt its parameters during the search, 
    reducing the need for manual tuning and improving robustness, as detailed in the reference paper. 
"""



class Problem(ABC):
    """
    Abstract Base Class for defining a problem to be solved by the RKO framework.

    This class serves as a template, ensuring that any problem-specific environment
    provides the necessary methods and attributes that the RKO solver depends on.
    """
    def __init__(self, instance_path):
        """
        Initializes the problem environment by loading instance data.
        
        This constructor should:
        1. Load all data from the specified instance file.
        2. Set the required attributes for the RKO solver.
        """
        # --- Required Attributes ---

        # Name of the specific instance being solved.
        self.instance_name: str = ""

        # The size of the random-key vector for this problem.
        self.tam_solution: int = 0
        
        # The strategy for local search heuristics ('Best' or 'First' improvement).
        self.LS_type: str = 'Best'

        # Maximum execution time in seconds for the solver.
        self.max_time: int = 60

        # Optional: A dictionary of known best solutions {instance_name: cost}.
        # Used for logging and for the stop_condition method.
        self.dict_best: dict | None = None

        # --- Abstract Methods (Must be implemented by subclasses) ---
        super().__init__()

    @abstractmethod
    def decoder(self, keys: list[float]) -> object:
        """
        Converts a random-key vector into a feasible solution for the problem.
        
        This is the most critical part of the problem-specific implementation. It defines
        the mapping from the continuous search space [0, 1) to the discrete solution space.

        Args:
            keys: A list or numpy array of random keys.

        Returns:
            An object representing the decoded solution in a problem-specific format.
        """
        pass

    @abstractmethod
    def cost(self, solution: object) -> float:
        """
        Calculates the objective function value (cost) of a decoded solution.

        The RKO framework assumes a minimization problem, so for maximization
        problems, you should return the negative of the objective value.

        Args:
            solution: A decoded solution object, as returned by the `decoder` method.

        Returns:
            A float representing the cost of the solution. Lower is better.
        """
        pass


class SolutionPool():
    """Manages a shared pool of elite solutions for the RKO framework."""
    def __init__(self, size, pool, best_pair, lock=None):
        """Initializes the SolutionPool instance."""
        
        self.size = size
        self.pool = pool
        self.best_pair = best_pair
        self.lock = lock
        self.start_time = time.time()    
        
    def insert(self, entry_tuple, metaheuristic_name, tag): 
        """Atomically inserts a solution, updating the pool and the global best."""
        
        fitness = entry_tuple[0]
        keys = entry_tuple[1]
        # print(f"INSERINDO: {fitness} - {metaheuristic_name} - {tag} - {len(self.pool)}")
        print(f"\rtempo = {round(time.time() - self.start_time,2)} ", end="")
        with self.lock:
            # print(f"\n{metaheuristic_name} {tag}")  
            if fitness < self.best_pair[0]: 
                self.best_pair[0] = fitness          
                self.best_pair[1] = list(keys)         
                self.best_pair[2] = round(self.start_time - time.time(), 2)
                
                print(f"\n{metaheuristic_name} {tag} BEST: {self.best_pair[0]} - Time: {round(self.start_time - time.time(), 2)}s - {len(self.pool)}")    
                               
            bisect.insort(self.pool, entry_tuple) 
            if len(self.pool) > self.size:
                self.pool.pop()

class RKO():
    """
    Implements the main components of the Random-Key Optimizer (RKO) framework.

    This class encapsulates the core logic for creating and manipulating solutions
    (represented as random-key vectors) and includes the standardized methods for
    perturbation ('shaking') as defined in the RKO paper.
    """
    def __init__(self, env):
        """
        Initializes the RKO solver.

        Args:
            env: An environment object that provides problem-specific details,
                 such as the solution size (`tam_solution`), local search strategy (`LS_type`),
                 and total execution time (`max_time`). Also, it should implement the `cost` and `decoder` 
                 methods for evaluating solutions.
        """
        self.env = env
        self.__MAX_KEYS = self.env.tam_solution
        self.LS_type = self.env.LS_type
        self.start_time = time.time()
        self.max_time = self.env.max_time
        self.rate = 1
        
        
    
    def random_keys(self):
        """ Generates a new random solution represented by a vector of random keys. """
        
        return np.random.random(self.__MAX_KEYS)        
    
    def shaking(self, keys, beta_min, beta_max):
        """
        Applies a controlled perturbation to a solution. This method is the 
        standardized diversification engine of the RKO framework.
        It modifies a fraction of the keys (determined by beta) by applying one of
        four different moves, chosen randomly. This helps the search escape from
        local optima.

        Args:
            keys (np.ndarray): The random-key vector (solution) to be perturbed.
            beta_min (float): The minimum perturbation rate.
            beta_max (float): The maximum perturbation rate.

        Returns:
            np.ndarray: A new, perturbed random-key vector.
        """
        
        beta = random.uniform(beta_min, beta_max)
        new_keys = copy.deepcopy(keys)
        
        numero_pertubacoes = max(1, int(self.__MAX_KEYS * beta))
        for _ in range(numero_pertubacoes):
            
            tipo = random.choice(['Swap', 'SwapN', 'Invert', 'Random'])
            
            
            if tipo == 'Swap':
                idx1, idx2 = random.sample(range(self.__MAX_KEYS), 2)
                new_keys[idx1], new_keys[idx2] = new_keys[idx2], new_keys[idx1]
                
            
            elif tipo == 'SwapN':
                idx = random.randint(0, self.__MAX_KEYS - 1)
                
                if idx == 0:
                    new_keys[idx], new_keys[idx + 1] = new_keys[idx + 1], new_keys[idx]                   
                elif idx == self.__MAX_KEYS - 1:
                    new_keys[idx], new_keys[idx - 1] = new_keys[idx - 1], new_keys[idx]                    
                else:
                    idx2 = random.choice([idx - 1, idx + 1])
                    new_keys[idx], new_keys[idx2] = new_keys[idx2], new_keys[idx]
                               
            elif tipo == 'Invert':
                idx = random.randint(0, self.__MAX_KEYS - 1)
                
                key = new_keys[idx]
                new_keys[idx] = 1 - key  
                            
            elif tipo == 'Random':                
                idx = random.randint(0, self.__MAX_KEYS - 1)
                new_keys[idx] = random.random()
                
            # print(f"Perturbação: {tipo} - Chave: {len(new_keys) == self.__MAX_KEYS} - Valor: {self.env.cost(self.env.decoder(new_keys))}")
        
        return new_keys
    
    def SwapLS(self, keys):
        """
        Performs a local search by systematically swapping pairs of random keys.

        This heuristic explores the neighborhood of a solution by exchanging the values
        at two different positions in the key vector. It can operate in two modes:
        - 'Best': Evaluates all possible swaps and applies the one that yields the greatest improvement.
        - 'First': Applies the very first swap that results in any improvement and immediately returns.

        Args:
            keys (np.ndarray): The initial random-key vector to improve.

        Returns:
            np.ndarray: The best random-key vector found in the neighborhood.
        """
        if self.LS_type == 'Best':
            # --- Best Improvement Strategy ---
            # Creates a randomized order to iterate through the keys, ensuring a different path each time.
            swap_order = [i for i in range(int(self.rate * self.__MAX_KEYS))]
            random.shuffle(swap_order)
            
            best_keys = copy.deepcopy(keys)
            best_cost = self.env.cost(self.env.decoder(best_keys))
            
            # Iterates through all possible pairs of keys to find the best possible swap.
            for idx1 in swap_order:
                for idx2 in reversed(swap_order):
                    # Early exit if a stop condition (e.g., time limit, optimal found) is met.
                    if self.stop_condition(best_cost, "SwapLS", -1):
                            return best_keys

                    # Creates a new candidate solution by swapping the keys.
                    new_keys = copy.deepcopy(best_keys)
                    new_keys[idx1], new_keys[idx2] = new_keys[idx2], new_keys[idx1]
                    new_cost = self.env.cost(self.env.decoder(new_keys))
                    
                    # If the swap improves the solution, it becomes the new best for this search.
                    if new_cost < best_cost:
                        best_keys = new_keys
                        best_cost = new_cost    
            
            return best_keys
    
        elif self.LS_type == 'First':
            # --- First Improvement Strategy ---
            swap_order = [i for i in range(int(self.rate * self.__MAX_KEYS))]
            random.shuffle(swap_order)
            
            best_keys = copy.deepcopy(keys)
            best_cost = self.env.cost(self.env.decoder(best_keys))
            
            # Iterates through pairs but will exit as soon as an improvement is found.
            for idx1 in swap_order:
                for idx2 in reversed(swap_order):
                    if self.stop_condition(best_cost, "SwapLS", -1):
                        return best_keys
                        
                    new_keys = copy.deepcopy(best_keys)
                    new_keys[idx1], new_keys[idx2] = new_keys[idx2], new_keys[idx1]
                    new_cost = self.env.cost(self.env.decoder(new_keys))
                    
                    # If an improving swap is found, accept it and return immediately.
                    if new_cost < best_cost:
                        return new_keys
                    
            return best_keys
            
    def FareyLS(self, keys):
        """
        Performs a local search by adjusting key values based on the Farey sequence.

        This heuristic explores the neighborhood by assigning new values to keys, drawn from
        uniform distributions between consecutive elements of the Farey sequence. This creates
        a structured, fine-grained search of the continuous solution space.

        Args:
            keys (np.ndarray): The initial random-key vector to improve.

        Returns:
            np.ndarray: The best random-key vector found in the neighborhood.
        """
        # The Farey sequence of order 7, used to create structured intervals for generating new key values.
        Farey_Squence = [0.00, 0.142857, 0.166667, 0.20, 0.25, 0.285714, 0.333333, 0.40, 0.428571, 0.50, 
                         0.571429, 0.60, 0.666667, 0.714286, 0.75, 0.80, 0.833333, 0.857143, 1.0]
        
        if self.LS_type == 'Best':
            # --- Best Improvement Strategy ---
            swap_order = [i for i in range(int(self.rate * self.__MAX_KEYS))]
            random.shuffle(swap_order)
            
            best_keys = copy.deepcopy(keys)
            best_cost = self.env.cost(self.env.decoder(best_keys))
            
            # Tests every key with a new value from every Farey interval.
            for idx in swap_order:
                for i in range(len(Farey_Squence) - 1):
                    if self.stop_condition(best_cost, "FareyLS", -1):
                        return best_keys

                    # Generates a new key value from a Farey-defined interval.
                    new_keys = copy.deepcopy(best_keys)
                    new_keys[idx] = random.uniform(Farey_Squence[i], Farey_Squence[i+1])
                    new_cost = self.env.cost(self.env.decoder(new_keys))
                    
                    # Updates the best solution found so far.
                    if new_cost < best_cost:
                        best_keys = new_keys
                        best_cost = new_cost    
            
            return best_keys
            
        elif self.LS_type == 'First':
            # --- First Improvement Strategy ---
            swap_order = [i for i in range(int(self.rate * self.__MAX_KEYS))]
            random.shuffle(swap_order)
            
            best_keys = copy.deepcopy(keys)
            best_cost = self.env.cost(self.env.decoder(best_keys))
            
            # Iterates until the first improvement is found.
            for idx in swap_order:
                for i in range(len(Farey_Squence) - 1):
                    if self.stop_condition(best_cost, "FareyLS", -1):
                        return best_keys
                        
                    new_keys = copy.deepcopy(best_keys)
                    new_keys[idx] = random.uniform(Farey_Squence[i], Farey_Squence[i+1])
                    new_cost = self.env.cost(self.env.decoder(new_keys))
                    
                    # Accepts the first better solution and returns immediately.
                    if new_cost < best_cost:
                        return new_keys
                        
            return best_keys
    
    def InvertLS(self, keys):
        """
        Performs a local search by inverting the value of keys (mirror search).

        This heuristic explores the neighborhood by replacing each key with its complement (1 - key).
        This can cause significant, structured changes to the decoded solution.

        Args:
            keys (np.ndarray): The initial random-key vector to improve.

        Returns:
            np.ndarray: The best random-key vector found in the neighborhood.
        """
        if self.LS_type == 'Best':
            # --- Best Improvement Strategy ---
            swap_order = [i for i in range(int(self.__MAX_KEYS))]
            random.shuffle(swap_order)
            
            best_keys = copy.deepcopy(keys)
            best_cost = self.env.cost(self.env.decoder(best_keys))
            
            # The logic here is slightly different: it tests inverting blocks of keys.
            blocks = []
            while swap_order:
                block = swap_order[:int(self.rate * self.__MAX_KEYS)]
                swap_order = swap_order[int(self.rate * self.__MAX_KEYS):]
                blocks.append(block)

            # Evaluates the effect of inverting each block of keys.
            for block in blocks:
                if self.stop_condition(best_cost, "InvertLS", -1):
                    return best_keys

                new_keys = copy.deepcopy(best_keys)
                for idx in block:
                    new_keys[idx] = 1 - new_keys[idx]
                
                new_cost = self.env.cost(self.env.decoder(new_keys))
                
                if new_cost < best_cost:
                    best_keys = new_keys
                    best_cost = new_cost    
            
            return best_keys
    
        elif self.LS_type == 'First':
            # --- First Improvement Strategy ---
            swap_order = [i for i in range(int(self.rate * self.__MAX_KEYS))]
            random.shuffle(swap_order)
            
            best_keys = copy.deepcopy(keys)
            best_cost = self.env.cost(self.env.decoder(best_keys))
            
            # Tests inverting each key individually.
            for idx in swap_order:
                if self.stop_condition(best_cost, "InvertLS", -1):
                    return best_keys
                        
                new_keys = copy.deepcopy(best_keys)
                new_keys[idx] = 1 - new_keys[idx]
                new_cost = self.env.cost(self.env.decoder(new_keys))
                    
                # Accepts the first improvement found and returns.
                if new_cost < best_cost:
                    return new_keys
                
            return best_keys
            
    def Blending(self, keys1, keys2, factor):
        """
        Creates a new solution by combining two parent solutions using a uniform crossover-like method.

        This method generates an offspring by inheriting keys from two parent solutions. It also includes
        a mutation operator and a 'factor' to allow for more complex transformations, such as using the
        complement of a parent's key, which is essential for the Nelder-Mead search.

        Args:
            keys1 (np.ndarray): The first parent solution (random-key vector).
            keys2 (np.ndarray): The second parent solution (random-key vector).
            factor (int): A parameter that modulates the contribution of the second parent.
                          If factor is -1, the complement of the key is used.

        Returns:
            np.ndarray: The resulting offspring (new random-key vector).
        """
        new_keys = np.zeros(self.__MAX_KEYS)
        
        for i in range(self.__MAX_KEYS):
            # Mutation: with a small probability (2%), a key is replaced by a new random value.
            if random.random() < 0.02: 
                new_keys[i] = random.random()
            else:               
                # Crossover: with 50% probability, inherit the key from the first parent.
                if random.random() < 0.5:
                    new_keys[i] = keys1[i]
                else:
                    # Otherwise, inherit from the second parent, potentially transformed by the factor.
                    if factor == -1:
                        # If factor is -1, use the complement of the key, clamped to the [0, 1) interval.
                        new_keys[i] = max(0.0, min(1.0 - keys2[i], 0.9999999))
                    else:
                        new_keys[i] = keys2[i] 
        
        return new_keys
    
    def NelderMeadSearch(self, keys, pool = None):
        """
        Performs a local search using the Nelder-Mead method, adapted for the RKO framework.

        This heuristic navigates the continuous search space by iteratively transforming a simplex
        (a geometric shape of N+1 vertices in an N-dimensional space) of solutions. It uses
        operations like reflection, expansion, contraction, and shrinking to find a local minimum.
        It does not require gradient information, making it suitable for complex objective functions.

        Args:
            keys (np.ndarray): The current solution to be improved, which becomes one vertex of the initial simplex.
            pool (SolutionPool, optional): The elite solution pool, used to select other vertices for the simplex.
                                           If None, random solutions are generated.

        Returns:
            np.ndarray: The best solution found by the search.
        """
        improved = 0
        improvedX1 = 0
        keys_origem = copy.deepcopy(keys)
        
        # --- Initialize the Simplex ---
        # The first vertex (x1) is the current solution.
        x1 = copy.deepcopy(keys)
        
        # The other two vertices (x2, x3) are selected from the elite pool to guide the search.
        if pool is None:
            x2 = self.random_keys()
            x3 = self.random_keys()
        else:
            x2 = random.sample(list(pool.pool), 1)[0][1]  
            x3 = random.sample(list(pool.pool), 1)[0][1]
            while x2 == x3: # Ensure the vertices are unique.
                x2 = random.sample(list(pool.pool), 1)[0][1]
        
        # --- Evaluate and Sort the Initial Simplex ---
        fit1 = self.env.cost(self.env.decoder(x1))
        fit2 = self.env.cost(self.env.decoder(x2))
        fit3 = self.env.cost(self.env.decoder(x3))
        
        # Sort the vertices by fitness: x1 is the best, x3 is the worst.
        if fit1 > fit2:
            x1, x2, fit1, fit2 = x2, x1, fit2, fit1
        if fit1 > fit3:
            x1, x3, fit1, fit3 = x3, x1, fit3, fit1
        if fit2 > fit3:
            x2, x3, fit2, fit3 = x3, x2, fit3, fit2
        
        xBest = copy.deepcopy(x1)
        fitBest = fit1
        
        # --- Main Loop: Iteratively Transform the Simplex ---
        # Calculate the centroid of the simplex (excluding the worst point, x3).
        x0 = self.Blending(x1, x2, 1)
        fit0 = self.env.cost(self.env.decoder(x0))
        if fit0 < fitBest:
            xBest, fitBest, improved = copy.deepcopy(x0), fit0, 1
            
        iter_count = 1
        
        # The stopping criterion is based on the problem size, as in the C++ implementation.
        max_iter = int(self.__MAX_KEYS * math.exp(-2))
        
        while iter_count <= (max_iter * self.rate):
            if self.stop_condition(fitBest, "NM", -1):
                return xBest
                
            shrink = 0
            
            # 1. Reflection: Reflect the worst point (x3) through the centroid (x0).
            x_r = self.Blending(x0, x3, -1)
            fit_r = self.env.cost(self.env.decoder(x_r))
            if fit_r < fitBest:
                xBest, fitBest, improved, improvedX1 = copy.deepcopy(x_r), fit_r, 1, 1

            # Case 1: Reflection produced a new best solution.
            if fit_r < fit1:
                # 2. Expansion: Try to expand even further in this promising direction.
                x_e = self.Blending(x_r, x0, -1)
                fit_e = self.env.cost(self.env.decoder(x_e))
                if fit_e < fitBest:
                    xBest, fitBest, improved, improvedX1 = copy.deepcopy(x_e), fit_e, 1, 1
                
                # Accept the better of the expansion or reflection points.
                if fit_e < fit_r:
                    x3, fit3 = copy.deepcopy(x_e), fit_e  # Expand
                else:
                    x3, fit3 = copy.deepcopy(x_r), fit_r  # Reflect
            
            # Case 2: Reflection is not the best, but better than the second-worst.
            elif fit_r < fit2:
                x3, fit3 = copy.deepcopy(x_r), fit_r # Reflect
            
            # Case 3: Reflection is not a good improvement.
            else:
                # 3. Contraction: The simplex might be too large, so contract it.
                if fit_r < fit3: # Outside Contraction
                    x_c = self.Blending(x_r, x0, 1)
                    fit_c = self.env.cost(self.env.decoder(x_c))
                    if fit_c < fitBest:
                        xBest, fitBest, improved, improvedX1 = copy.deepcopy(x_c), fit_c, 1, 1
                    
                    if fit_c < fit_r:
                        x3, fit3 = copy.deepcopy(x_c), fit_c
                    else:
                        shrink = 1 # If contraction fails, shrink the simplex.
                else: # Inside Contraction
                    x_c = self.Blending(x0, x3, 1)
                    fit_c = self.env.cost(self.env.decoder(x_c))
                    if fit_c < fitBest:
                        xBest, fitBest, improved, improvedX1 = copy.deepcopy(x_c), fit_c, 1, 1
                        
                    if fit_c < fit3:
                        x3, fit3 = copy.deepcopy(x_c), fit_c
                    else:
                        shrink = 1 # If contraction fails, shrink the simplex.
            
            # 4. Shrinking: If all other moves fail, shrink the entire simplex towards the best point (x1).
            if shrink:
                x2 = self.Blending(x1, x2, 1)
                fit2 = self.env.cost(self.env.decoder(x2))
                if fit2 < fitBest:
                    xBest, fitBest, improved, improvedX1 = copy.deepcopy(x2), fit2, 1, 1

                x3 = self.Blending(x1, x3, 1)
                fit3 = self.env.cost(self.env.decoder(x3))
                if fit3 < fitBest:
                    xBest, fitBest, improved, improvedX1 = copy.deepcopy(x3), fit3, 1, 1
            
            # Re-sort the vertices of the new simplex for the next iteration.
            if fit1 > fit2:
                x1, x2, fit1, fit2 = x2, x1, fit2, fit1
            if fit1 > fit3:
                x1, x3, fit1, fit3 = x3, x1, fit3, fit1
            if fit2 > fit3:
                x2, x3, fit2, fit3 = x3, x2, fit3, fit2
            
            # Calculate the new centroid.
            x0 = self.Blending(x1, x2, 1)
            fit0 = self.env.cost(self.env.decoder(x0))
            if fit0 < fitBest:
                xBest, fitBest, improved, improvedX1 = copy.deepcopy(x0), fit0, 1, 1
            
            # Reset the iteration counter if an improvement was made, otherwise increment it.
            if improved == 1:
                improved = 0
                iter_count = 0
            else:
                iter_count += 1
        
        # Return the best solution found during the search.
        if improvedX1 == 1:
            return xBest
        else:
            return keys_origem      
        
        
 
    def RVND(self, keys, pool=None):
        """
        Performs a Random Variable Neighborhood Descent (RVND) local search.

        RVND is the primary intensification engine of the RKO framework. It systematically
        and randomly explores a set of different neighborhood structures (local search heuristics)
        to improve a given solution. If an improvement is found in any neighborhood, the search
        is restarted from the new, better solution, using the full set of neighborhoods again.
        This process continues until no neighborhood can yield a better solution.

        Args:
            keys (np.ndarray): The initial random-key vector to be improved.
            pool (SolutionPool, optional): The shared elite solution pool.

        Returns:
            np.ndarray: The best solution found after exploring all neighborhoods.
        """
        best_keys = copy.deepcopy(keys)
        best_cost = self.env.cost(self.env.decoder(best_keys))

        # Defines the list of available local search heuristics (neighborhoods).
        neighborhoods = ['SwapLS', 'NelderMeadSearch', 'FareyLS', 'InvertLS']
        # `not_used_nb` tracks which neighborhoods have not yet been tried in the current iteration.
        not_used_nb = copy.deepcopy(neighborhoods)
        
        while not_used_nb:
            # Randomly select a neighborhood to explore from the list of available ones.
            current_neighborhood = random.choice(not_used_nb)
            
            # --- Apply the selected local search heuristic ---
            if current_neighborhood == 'SwapLS':
                new_keys = self.SwapLS(best_keys)
            elif current_neighborhood == 'NelderMeadSearch':               
                new_keys = self.NelderMeadSearch(best_keys, pool)           
            elif current_neighborhood == 'FareyLS':
                new_keys = self.FareyLS(best_keys)
            elif current_neighborhood == 'InvertLS':
                new_keys = self.InvertLS(best_keys)
                
            new_cost = self.env.cost(self.env.decoder(new_keys))
            
            # --- Check for improvement ---
            if new_cost < best_cost:
                # If the new solution is better, update the best solution.
                best_keys = new_keys
                best_cost = new_cost
                
                # Reset the list of neighborhoods to restart the exploration from the new best solution.
                not_used_nb = copy.deepcopy(neighborhoods)
                
                # Insert the newly found best solution into the shared elite pool.
                if pool is not None:
                    pool.insert((best_cost, list(best_keys)), "RVND", -1)
            else:
                # If no improvement was found, remove the current neighborhood from the list to try another.
                not_used_nb.remove(current_neighborhood)
            
            # Check for global stop conditions (e.g., time limit) during the search.
            if self.stop_condition(best_cost, "RVND", -1):
                return best_keys
        
        # Return the best solution found after the search is complete.
        return best_keys         
    
    def MultiStart(self, tag, pool):
        """
        Performs a continuous search by repeatedly perturbing elite solutions and applying local search.

        This method instead of generating a completely new random solution at each iteration, it selects a high-quality solution
        from the elite pool, applies a perturbation (`shaking`), and then intensifies the search with `RVND`.

        Args:
            tag (int): An identifier for the worker process, used for logging.
            pool (SolutionPool): The shared elite solution pool.

        Returns:
            tuple: A tuple containing the final solution details.
        """
        metaheuristic_name = "MS"
        start_time = time.time()
        tempo_max = self.max_time
        
        # Initializes with a single random solution.
        keys = self.random_keys()
        best_keys = keys
        solution = self.env.decoder(keys)
        best_cost = self.env.cost(solution)
        
        # Inserts the initial solution into the pool.
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag):
            return [], best_keys, best_cost
            
        # Main loop continues until the time limit is reached.
        while time.time() - start_time < tempo_max:
                # Selects a random elite solution from the pool to start a new search cycle.
                k1 = random.sample(list(pool.pool), 1)[0][1]
                
                # Perturbs the elite solution to escape the current local optimum.
                new_keys = self.shaking(k1, 0.1, 0.3)
                
                # Applies intensive local search (RVND) to the perturbed solution.
                new_keys = self.RVND(pool=pool, keys=new_keys)
                
                new_solution = self.env.decoder(new_keys)
                new_cost = self.env.cost(new_solution)
                
                # If the local search yields a better solution, update the best-known solution.
                if new_cost < best_cost:
                    best_keys = new_keys
                    best_cost = new_cost
                    
                    # Adds the new best solution to the shared elite pool.
                    pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                
                # Checks for the global stop condition after each iteration.
                if self.stop_condition(best_cost, metaheuristic_name, tag):
                        return [], best_keys, best_cost

        final_cost_solution = self.env.decoder(best_keys)
        final_cost_value = self.env.cost(final_cost_solution, True)
        
        return [], best_keys, final_cost_value
    
    def SimulatedAnnealing(self, SAmax=10, Temperatura=1000, alpha=0.95,  beta_min=0.05, beta_max=0.25, tag = 0, pool=None):
        """
        Performs a search using Simulated Annealing (SA), enhanced with RKO components.

        This implementation starts with an initial solution improved by RVND. It then follows
        the classic SA process of generating and probabilistically accepting solutions.
        A key feature is the application of Nelder-Mead search after each temperature reduction
        to further intensify the search.

        Args:
            SAmax (int): Number of iterations at each temperature level.
            Temperatura (float): The initial temperature.
            alpha (float): The cooling rate for the temperature.
            beta_min (float): Minimum perturbation rate for shaking.
            beta_max (float): Maximum perturbation rate for shaking.
            tag (int): An identifier for the worker process.
            pool (SolutionPool): The shared elite solution pool.

        Returns:
            tuple: The final solution details.
        """
        metaheuristic_name = "SA"
        tempo_max = self.max_time

        # Generates a random initial solution and immediately improves it with local search.
        keys = self.random_keys()
        keys = self.RVND(pool=pool, keys=keys)
        best_keys = keys

        solution = self.env.decoder(keys)
        cost = self.env.cost(solution)
        best_cost = cost
        
        # Inserts the initial solution into the shared elite pool.
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag):
                return [], best_keys, best_cost
            
        start_time = time.time()
        T = Temperatura

        # The main loop continues until the time limit is reached.
        while time.time() - start_time < tempo_max:
            iter_at_temp = 0
            # Inner loop: performs a fixed number of iterations at the current temperature.
            while iter_at_temp < SAmax:
                iter_at_temp += 1

                # Generates a neighboring solution by perturbing the current one.
                new_keys = self.shaking(keys, beta_min, beta_max)
                new_solution = self.env.decoder(new_keys)
                new_cost = self.env.cost(new_solution)
                
                delta = new_cost - cost
                
                # If the new solution is a global best, update and record it.
                if new_cost < best_cost:
                    best_keys = new_keys
                    best_cost = new_cost
                    pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                    if self.stop_condition(best_cost, metaheuristic_name, tag):
                            return [], best_keys, best_cost

                # Metropolis acceptance criterion.
                if delta <= 0:
                    # Always accept better or equal solutions.
                    keys = new_keys
                    cost = new_cost
                else:
                    # Probabilistically accept worse solutions to escape local optima.
                    if random.random() < math.exp(-delta / T):
                        keys = new_keys
                        cost = new_cost

            # After completing iterations at a given temperature, reduce the temperature.
            T = T * alpha
            
            # --- RKO Enhancement: Apply an intensive local search after cooling ---
            keys = self.NelderMeadSearch(pool=pool, keys=keys)
            new_cost = self.env.cost(self.env.decoder(keys))
            
            # Check if this intensified search found a new global best.
            if new_cost < best_cost:
                best_keys = keys
                best_cost = new_cost
                pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)

        final_cost_solution = self.env.decoder(best_keys)
        final_cost_value = self.env.cost(final_cost_solution, True)
        
        return [], best_keys, final_cost_value

    def VNS(self, limit_time, x, tag, pool, beta_min=0.05, k_max=6):
        """
        Performs a search using the Variable Neighborhood Search (VNS) metaheuristic.

        VNS systematically explores neighborhoods of increasing size to escape local optima.
        It starts with a good initial solution, then repeatedly applies two main steps:
        1.  **Shaking**: Perturbs the current best solution to jump to a random point in a given neighborhood `k`.
        2.  **Local Search**: Applies an intensive local search (RVND) to find the optimum in that neighborhood.
        If an improvement is found, the search returns to the first neighborhood (k=1); otherwise,
        it proceeds to the next, larger neighborhood (k=k+1).

        Args:
            limit_time (int): The maximum execution time in seconds.
            x (any): This parameter appears to be unused.
            tag (int): An identifier for the worker process.
            pool (SolutionPool): The shared elite solution pool.
            beta_min (float): The base perturbation rate, which is scaled by the neighborhood index `k`.
            k_max (int): The maximum number of neighborhood structures to explore.

        Returns:
            tuple: The final solution details.
        """
        metaheuristic_name = "VNS"

        idx_k = 0 # The current neighborhood index, from 0 to k_max-1.
        start_time = time.time()
        
        # Generates and improves an initial solution to start the search.
        keys = self.random_keys()
        keys = self.RVND(pool=pool, keys=keys)
        best_keys = keys
        best_cost = self.env.cost(self.env.decoder(keys))
        
        # Adds the initial solution to the shared elite pool.
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag):
            return [], best_keys, best_cost

        # The main VNS loop continues until the time limit is reached.
        while time.time() - start_time < limit_time:
            # If all neighborhoods have been explored without improvement, restart from the first one.
            if idx_k >= k_max:
                idx_k = 0

            # 1. Shaking: Perturb the current best solution. The neighborhood size increases with `idx_k`.
            s1 = self.shaking(best_keys, idx_k * beta_min, (idx_k + 1) * beta_min)
            
            # 2. Local Search: Apply RVND to find the best solution in the new neighborhood.
            s2 = self.RVND(pool=pool, keys=s1)
            
            sol2 = self.env.decoder(s2)
            cost = self.env.cost(sol2)

            # 3. Move or Change Neighborhood:
            if cost <= best_cost:
                # If an improvement is found, update the best solution and return to the first neighborhood (k=1).
                best_cost = cost
                best_keys = s2
                pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                idx_k = 0 # Reset to the first neighborhood.
            else:
                # If no improvement, move to the next, larger neighborhood.
                idx_k += 1
            
            # Checks for the global stop condition after each iteration.
            if self.stop_condition(best_cost, metaheuristic_name, tag):
                return [], best_keys, best_cost

        final_cost_solution = self.env.decoder(best_keys)
        final_cost_value = self.env.cost(final_cost_solution)
        
        return [], best_keys, final_cost_value


    def BRKGA(self, pop_size, elite_pop, chance_elite,  tag, pool):
        """
        Performs a search using the Biased Random-Key Genetic Algorithm (BRKGA).

        BRKGA is an evolutionary algorithm that maintains a population of solutions (random-key vectors).
        In each generation, it creates a new population by combining elite solutions with offspring
        generated through a biased crossover, where one parent is always from the elite set. This
        implementation also includes a restart mechanism and interaction with the shared elite pool.

        Args:
            pop_size (int): The total number of solutions in the population.
            elite_pop (float): The fraction of the population to be considered elite.
            chance_elite (float): The probability of inheriting a key from the elite parent during crossover.
            tag (int): An identifier for the worker process.
            pool (SolutionPool): The shared elite solution pool.

        Returns:
            tuple: The final solution details.
        """
        metaheuristic_name = "BRKGA"
        limit_time = self.max_time
        generation = 0
        tam_elite = int(pop_size * elite_pop) # Calculate the number of elite individuals.
        half_time_restart_done = False

        # Initializes the population with random solutions.
        population = [self.random_keys() for _ in range(pop_size)]
        best_keys_overall = None
        best_fitness_overall = float('inf')

        start_time = time.time()

        while time.time() - start_time < limit_time:
            # --- Restart Mechanism ---
            # At the halfway point of the execution time, restart the population to introduce diversity.
            if not half_time_restart_done and (time.time() - start_time) > (limit_time / 2):
                population = [self.random_keys() for _ in range(pop_size)]
                half_time_restart_done = True

            generation += 1
            
            # --- Evaluate Population ---
            evaluated_population = []
            for key in population:
                sol = self.env.decoder(key)
                fitness = self.env.cost(sol)
                evaluated_population.append((key, sol, fitness))

                # Update the global best solution if a new one is found.
                if fitness < best_fitness_overall:
                    best_fitness_overall = fitness
                    best_keys_overall = key
                    pool.insert((best_fitness_overall, list(best_keys_overall)), metaheuristic_name, tag)

                if self.stop_condition(best_fitness_overall, metaheuristic_name, tag):
                    return [], best_keys_overall, fitness
            
            # --- Selection ---
            # Sort the population by fitness to identify the elite solutions.
            evaluated_population.sort(key=lambda x: x[2])
            elite_keys = [item[0] for item in evaluated_population[:tam_elite]]

            # --- Create New Generation ---
            # The new population starts with the best solution from the elite set (elitism).
            new_population = [elite_keys[0]]

            # Generate the rest of the new population through crossover.
            while len(new_population) < pop_size:
                # Select Parent 1: can be from the general population or the global elite pool.
                if random.random() < 0.5 and len(pool.pool) > 0:
                    parent1 = random.sample(list(pool.pool), 1)[0][1]
                else:
                    parent1 = random.sample(population, 1)[0]

                # Select Parent 2: can be from the current generation's elite set or the general population.
                if random.random() < 0.5 and len(elite_keys) > 0:
                    parent2 = random.sample(elite_keys, 1)[0]
                else:
                    parent2 = random.sample(population, 1)[0]

                # Biased Crossover: each key is inherited from the elite parent (parent2) with `chance_elite` probability.
                child = np.zeros(self.__MAX_KEYS)
                for i in range(len(child)):
                    if random.random() < chance_elite:
                        child[i] = parent2[i] # Inherit from the elite parent.
                    else:
                        child[i] = parent1[i] # Inherit from the other parent.
                
                # Mutation: apply a small chance of mutation to each key in the new child.
                for idx in range(len(child)):
                    if random.random() < 0.05:
                        child[idx] = random.random()

                new_population.append(child)
            
            population = new_population[:pop_size]

        final_cost_solution = self.env.decoder(best_keys_overall)
        final_cost_value = self.env.cost(final_cost_solution)
        
        return [], best_keys_overall, best_fitness_overall


    def ILS(self, limit_time, x, tag, pool, beta_min=0.1, beta_max=0.5):
        """
        Performs a search using the Iterated Local Search (ILS) metaheuristic.

        ILS is a simple yet powerful metaheuristic that iterates through a sequence of
        solutions generated by two main steps:
        1.  **Perturbation**: A 'shaking' move is applied to the current best solution to escape its local optimum.
        2.  **Local Search**: An intensive local search (RVND) is applied to the perturbed solution to find a new local optimum.
        The new solution is accepted if it's an improvement.

        Args:
            limit_time (int): The maximum execution time in seconds.
            x (any): This parameter appears to be unused.
            tag (int): An identifier for the worker process.
            pool (SolutionPool): The shared elite solution pool.
            beta_min (float): Minimum perturbation rate for the shaking phase.
            beta_max (float): Maximum perturbation rate for the shaking phase.

        Returns:
            tuple: The final solution details.
        """
        metaheuristic_name = "ILS"
        start_time = time.time()
        
        # Generates and improves an initial solution to start the search process.
        keys = self.random_keys()
        keys = self.RVND(pool=pool, keys=keys)
        best_keys = keys
        best_cost = self.env.cost(self.env.decoder(keys))
        
        # Adds the initial solution to the shared elite pool.
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag):
            return [], best_keys, best_cost

        # Main ILS loop continues until the time limit is reached.
        while time.time() - start_time < limit_time:
            # 1. Perturbation: Shake the current best solution to jump to a new region of the search space.
            s1 = self.shaking(best_keys, beta_min, beta_max)
            
            # 2. Local Search: Apply RVND to find the local optimum of the perturbed solution.
            s2 = self.RVND(pool=pool, keys=s1)
            
            sol2 = self.env.decoder(s2)
            cost = self.env.cost(sol2)

            # 3. Acceptance Criterion: A


    def stop_condition(self, best_cost, metaheuristic_name, tag):
        if time.time() - self.start_time > self.max_time:
            print(f"{metaheuristic_name} {tag}: ENCERRADO")
            
            return True
        if self.env.dict_best is not None:
            if best_cost == self.env.dict_best[self.env.instance_name]:
                print(f"Metaheurística {metaheuristic_name} com tag {tag} encontrou a melhor solução: {best_cost}")
                return True
            else:
                return False
        return False
        
        
    def solve(self, pop_size, elite_pop, chance_elite, time_total, n_workers=None,brkga=1, ms=1, sa=1, vns=1, ils=1, restart=1):
        """
        Initializes and runs the RKO framework with parallel metaheuristics.

        This is the main execution method. It sets up the shared resources,
        launches the specified number of worker processes for each algorithm,
        and waits for them to complete. The best solution found across all
        processes is then returned.

        Args:
            pop_size (int): Population size for algorithms like BRKGA.
            elite_pop (float): Fraction of elite solutions.
            chance_elite (float): Crossover inheritance probability.
            time_total (int): Total execution time in seconds.
            n_workers (int, optional): Number of parallel processes.
            brkga, ms, sa, vns, ils (int): Number of workers for each metaheuristic.
            restart (float): Controls the restart strategy (e.g., 0.5 for two runs).

        Returns:
            tuple: The final best cost, solution keys, and time elapsed.
        """
        
        limit_time = time_total * restart
        restarts = int(1/restart)
        
        if n_workers is None:
            n_workers = cpu_count()
        self.max_time = limit_time
        
        # --- Setup Shared Resources ---
        manager = Manager()
        shared = manager.Namespace()
        
        shared.best_pair = manager.list([float('inf'), None, None])
        shared.best_pool = manager.list()
        
        # Initialize the shared solution pool.
        shared.pool = SolutionPool(20, shared.best_pool, shared.best_pair, lock=manager.Lock())
        for i in range(20):
            keys = self.random_keys()
            cost = self.env.cost(self.env.decoder(keys))
            shared.pool.insert((cost, list(keys)), 'pool', -1)
            
        processes = []
        tag = 0
        
        # --- Launch Worker Processes ---
        for k in range(restarts):
            self.start_time = time.time()
            shared.pool.pool = manager.list() # Reset pool for each restart.
            
            # Create and start processes for each specified metaheuristic.
            for _ in range(brkga):
                p = Process(target=_brkga_worker, args=(self.env, pop_size, elite_pop, chance_elite, shared.pool,tag))
                processes.append(p)
                p.start()
            for _ in range(ms):
                p = Process(target=_MS_worker, args=(self.env,10000,100,shared.pool,tag))
                processes.append(p)
                p.start()
            for _ in range(sa):
                p = Process(target=_SA_worker, args=(self.env, pop_size, elite_pop, chance_elite, shared.pool,tag))
                processes.append(p)
                p.start()
            for _ in range(vns):
                p = Process(target=_VNS_worker, args=(self.env, limit_time,pop_size, shared.pool,tag))
                processes.append(p)
                p.start()
            for _ in range(ils):
                p = Process(target=_ILS_worker, args=(self.env, limit_time,pop_size, shared.pool,tag))
                processes.append(p)
                p.start()

            # Wait for all processes to complete.
            for p in processes:
                p.join()

        # Retrieve the final best result from the shared object.
        cost = shared.pool.best_pair[0]
        solution = shared.pool.best_pair[1]      
        time_elapsed = shared.pool.best_pair[2]
        
        return cost, solution, time_elapsed
        
def _brkga_worker(env, pop_size, elite_pop, chance_elite, pool,tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.BRKGA(pop_size, elite_pop, chance_elite,tag, pool)
    


def _MS_worker(env, max_itr, x, pool,tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.MultiStart(tag, pool)
    

def _GRASP_worker(env, max_itr, x, pool,tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.MultiStart( max_itr,x,pool)
    

            
def _VNS_worker(env, limit_time, x, pool, tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.VNS(limit_time,x,tag, pool)
    

def _ILS_worker(env, limit_time, x, pool, tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.ILS(limit_time,x,tag, pool)
    


def _SA_worker(env, pop_size, elite_pop, chance_elite, pool,tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.SimulatedAnnealing(tag = tag, pool = pool)
    

      
        

