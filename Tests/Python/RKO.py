import os
import numpy as np
import time
import random
import copy
import math
import datetime
import bisect
from multiprocessing import Manager, Process, cpu_count

class SolutionPool():
    def __init__(self, size, pool, best_pair, lock=None, print=False, Best=None):
        self.size = size
        self.pool = pool
        self.best_pair = best_pair
        self.lock = lock
        self.start_time = time.time()    
        self.print = print 
        self.best_possible = Best
        
    def insert(self, entry_tuple, metaheuristic_name, tag): 
        fitness = entry_tuple[0]
        keys = entry_tuple[1]
        # print(f"\rtempo = {round(time.time() - self.start_time,2)} ", end="")
        with self.lock:
            if fitness < self.best_pair[0]: 
                self.best_pair[0] = fitness          
                self.best_pair[1] = list(keys)        
                self.best_pair[2] = round(self.start_time - time.time(), 2)
                
                if self.print:
                    if self.best_possible is not None:
                        print(f"\n{metaheuristic_name} {tag} NOVO MELHOR: {fitness} - BEST: {self.best_possible} - Tempo: {round(self.start_time - time.time(), 2)}s - {len(self.pool)}") 
                    else:
                        print(f"\n{metaheuristic_name} {tag} NOVO MELHOR: {fitness} - Tempo: {round(self.start_time - time.time(), 2)}s - {len(self.pool)}")                
            bisect.insort(self.pool, entry_tuple) 
            if len(self.pool) > self.size:
                self.pool.pop()

class RKO():
    def __init__(self, env, print=False, save_directory=None):
        self.env = env
        self.__MAX_KEYS = self.env.tam_solution
        self.LS_type = self.env.LS_type
        self.start_time = time.time()
        self.max_time = self.env.max_time
        self.rate = 1
        
        self.print = print
        self.save_directory = save_directory
        
    def random_keys(self):
        return np.random.random(self.__MAX_KEYS)        
    
    def shaking(self, keys, beta_min, beta_max):
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
                
        return new_keys
    
    def SwapLS(self, keys, metaheuristic_name="SwapLS"):
        if self.LS_type == 'Best':
            swap_order = [i for i in range(int(self.rate * self.__MAX_KEYS))]
            random.shuffle(swap_order)
            
            best_keys = copy.deepcopy(keys)
            best_cost = self.env.cost(self.env.decoder(best_keys))
            
            for idx1 in swap_order:
                for idx2 in reversed(swap_order):
                    if self.stop_condition(best_cost, metaheuristic_name, -1):
                            return best_keys

                    new_keys = copy.deepcopy(best_keys)
                    new_keys[idx1], new_keys[idx2] = new_keys[idx2], new_keys[idx1]
                    new_cost = self.env.cost(self.env.decoder(new_keys))
                    
                    if new_cost < best_cost:
                        best_keys = new_keys
                        best_cost = new_cost    
            
            return best_keys
    
        elif self.LS_type == 'First':
            swap_order = [i for i in range(int(self.rate * self.__MAX_KEYS))]
            random.shuffle(swap_order)
            
            best_keys = copy.deepcopy(keys)
            best_cost = self.env.cost(self.env.decoder(best_keys))
            
            for idx1 in swap_order:
                for idx2 in reversed(swap_order):
                    if self.stop_condition(best_cost, metaheuristic_name, -1):
                        return best_keys
                        
                    new_keys = copy.deepcopy(best_keys)
                    new_keys[idx1], new_keys[idx2] = new_keys[idx2], new_keys[idx1]
                    new_cost = self.env.cost(self.env.decoder(new_keys))
                    
                    if new_cost < best_cost:
                        return new_keys
                    
            return best_keys
            
    def FareyLS(self, keys, metaheuristic_name="FareyLS"):
        Farey_Squence = [0.00, 0.142857, 0.166667, 0.20, 0.25, 0.285714, 0.333333, 0.40, 0.428571, 0.50, 
                         0.571429, 0.60, 0.666667, 0.714286, 0.75, 0.80, 0.833333, 0.857143, 1.0]
        
        if self.LS_type == 'Best':
            swap_order = [i for i in range(int(self.rate * self.__MAX_KEYS))]
            random.shuffle(swap_order)
            
            best_keys = copy.deepcopy(keys)
            best_cost = self.env.cost(self.env.decoder(best_keys))
            
            for idx in swap_order:
                for i in range(len(Farey_Squence) - 1):
                    if self.stop_condition(best_cost, metaheuristic_name, -1):
                        return best_keys

                    new_keys = copy.deepcopy(best_keys)
                    new_keys[idx] = random.uniform(Farey_Squence[i], Farey_Squence[i+1])
                    new_cost = self.env.cost(self.env.decoder(new_keys))
                    
                    if new_cost < best_cost:
                        best_keys = new_keys
                        best_cost = new_cost    
            
            return best_keys
            
        elif self.LS_type == 'First':
            swap_order = [i for i in range(int(self.rate * self.__MAX_KEYS))]
            random.shuffle(swap_order)
            
            best_keys = copy.deepcopy(keys)
            best_cost = self.env.cost(self.env.decoder(best_keys))
            
            for idx in swap_order:
                for i in range(len(Farey_Squence) - 1):
                    if self.stop_condition(best_cost, metaheuristic_name, -1):
                        return best_keys
                        
                    new_keys = copy.deepcopy(best_keys)
                    new_keys[idx] = random.uniform(Farey_Squence[i], Farey_Squence[i+1])
                    new_cost = self.env.cost(self.env.decoder(new_keys))
                    
                    if new_cost < best_cost:
                        return new_keys
                        
            return best_keys
    
    def InvertLS(self, keys, metaheuristic_name="InvertLS"):
        if self.LS_type == 'Best':
            swap_order = [i for i in range(int(self.__MAX_KEYS))]
            random.shuffle(swap_order)
            
            best_keys = copy.deepcopy(keys)
            best_cost = self.env.cost(self.env.decoder(best_keys))
            
            blocks = []
            while swap_order:
                block = swap_order[:int(self.rate * self.__MAX_KEYS)]
                swap_order = swap_order[int(self.rate * self.__MAX_KEYS):]
                blocks.append(block)

            for block in blocks:
                if self.stop_condition(best_cost, metaheuristic_name, -1):
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
            swap_order = [i for i in range(int(self.rate * self.__MAX_KEYS))]
            random.shuffle(swap_order)
            
            best_keys = copy.deepcopy(keys)
            best_cost = self.env.cost(self.env.decoder(best_keys))
            
            for idx in swap_order:
                if self.stop_condition(best_cost, metaheuristic_name, -1):
                    return best_keys
                        
                new_keys = copy.deepcopy(best_keys)
                new_keys[idx] = 1 - new_keys[idx]
                new_cost = self.env.cost(self.env.decoder(new_keys))
                    
                if new_cost < best_cost:
                    return new_keys
                
            return best_keys
            
    def Blending(self, keys1, keys2, factor):
        new_keys = np.zeros(self.__MAX_KEYS)
        
        for i in range(self.__MAX_KEYS):
            if random.random() < 0.02: 
                new_keys[i] = random.random()
            else:               
                if random.random() < 0.5:
                    new_keys[i] = keys1[i]
                else:
                    if factor == -1:
                        new_keys[i] = max(0.0, min(1.0 - keys2[i], 0.9999999))
                    else:
                        new_keys[i] = keys2[i] 
        
        return new_keys
    
    def NelderMeadSearch(self, keys, pool = None, metaheuristic_name="NelderMeadSearch"):
        improved = 0
        improvedX1 = 0
        keys_origem = copy.deepcopy(keys)
        
        x1 = copy.deepcopy(keys)
        
        if pool is None:
            x2 = self.random_keys()
            x3 = self.random_keys()
        else:
            x2 = random.sample(list(pool.pool), 1)[0][1]  
            x3 = random.sample(list(pool.pool), 1)[0][1]
            while x2 == x3:
                x2 = random.sample(list(pool.pool), 1)[0][1]
        
        fit1 = self.env.cost(self.env.decoder(x1))
        fit2 = self.env.cost(self.env.decoder(x2))
        fit3 = self.env.cost(self.env.decoder(x3))
        
        if fit1 > fit2:
            x1, x2, fit1, fit2 = x2, x1, fit2, fit1
        if fit1 > fit3:
            x1, x3, fit1, fit3 = x3, x1, fit3, fit1
        if fit2 > fit3:
            x2, x3, fit2, fit3 = x3, x2, fit3, fit2
        
        xBest = copy.deepcopy(x1)
        fitBest = fit1
        
        x0 = self.Blending(x1, x2, 1)
        fit0 = self.env.cost(self.env.decoder(x0))
        if fit0 < fitBest:
            xBest, fitBest, improved = copy.deepcopy(x0), fit0, 1
            
        iter_count = 1
        
        max_iter = int(self.__MAX_KEYS * math.exp(-2))
        
        while iter_count <= (max_iter * self.rate):
            if self.stop_condition(fitBest, metaheuristic_name, -1):
                return xBest
                
            shrink = 0
            
            x_r = self.Blending(x0, x3, -1)
            fit_r = self.env.cost(self.env.decoder(x_r))
            if fit_r < fitBest:
                xBest, fitBest, improved, improvedX1 = copy.deepcopy(x_r), fit_r, 1, 1

            if fit_r < fit1:
                x_e = self.Blending(x_r, x0, -1)
                fit_e = self.env.cost(self.env.decoder(x_e))
                if fit_e < fitBest:
                    xBest, fitBest, improved, improvedX1 = copy.deepcopy(x_e), fit_e, 1, 1
                
                if fit_e < fit_r:
                    x3, fit3 = copy.deepcopy(x_e), fit_e
                else:
                    x3, fit3 = copy.deepcopy(x_r), fit_r
            
            elif fit_r < fit2:
                x3, fit3 = copy.deepcopy(x_r), fit_r
            
            else:
                if fit_r < fit3:
                    x_c = self.Blending(x_r, x0, 1)
                    fit_c = self.env.cost(self.env.decoder(x_c))
                    if fit_c < fitBest:
                        xBest, fitBest, improved, improvedX1 = copy.deepcopy(x_c), fit_c, 1, 1
                    
                    if fit_c < fit_r:
                        x3, fit3 = copy.deepcopy(x_c), fit_c
                    else:
                        shrink = 1
                else:
                    x_c = self.Blending(x0, x3, 1)
                    fit_c = self.env.cost(self.env.decoder(x_c))
                    if fit_c < fitBest:
                        xBest, fitBest, improved, improvedX1 = copy.deepcopy(x_c), fit_c, 1, 1
                        
                    if fit_c < fit3:
                        x3, fit3 = copy.deepcopy(x_c), fit_c
                    else:
                        shrink = 1
            
            if shrink:
                x2 = self.Blending(x1, x2, 1)
                fit2 = self.env.cost(self.env.decoder(x2))
                if fit2 < fitBest:
                    xBest, fitBest, improved, improvedX1 = copy.deepcopy(x2), fit2, 1, 1

                x3 = self.Blending(x1, x3, 1)
                fit3 = self.env.cost(self.env.decoder(x3))
                if fit3 < fitBest:
                    xBest, fitBest, improved, improvedX1 = copy.deepcopy(x3), fit3, 1, 1
            
            if fit1 > fit2:
                x1, x2, fit1, fit2 = x2, x1, fit2, fit1
            if fit1 > fit3:
                x1, x3, fit1, fit3 = x3, x1, fit3, fit1
            if fit2 > fit3:
                x2, x3, fit2, fit3 = x3, x2, fit3, fit2
            
            x0 = self.Blending(x1, x2, 1)
            fit0 = self.env.cost(self.env.decoder(x0))
            if fit0 < fitBest:
                xBest, fitBest, improved, improvedX1 = copy.deepcopy(x0), fit0, 1, 1
            
            if improved == 1:
                improved = 0
                iter_count = 0
            else:
                iter_count += 1
        
        if improvedX1 == 1:
            return xBest
        else:
            return keys_origem       
        
    def RVND(self, keys, pool=None, metaheuristic_name="RVND"):
        best_keys = copy.deepcopy(keys)
        best_cost = self.env.cost(self.env.decoder(best_keys))

        neighborhoods = ['SwapLS', 'NelderMeadSearch', 'FareyLS', 'InvertLS']
        not_used_nb = copy.deepcopy(neighborhoods)
        
        while not_used_nb:
            current_neighborhood = random.choice(not_used_nb)
            
            if current_neighborhood == 'SwapLS':
                new_keys = self.SwapLS(best_keys, metaheuristic_name=metaheuristic_name)
            elif current_neighborhood == 'NelderMeadSearch':               
                new_keys = self.NelderMeadSearch(best_keys, pool, metaheuristic_name=metaheuristic_name)           
            elif current_neighborhood == 'FareyLS':
                new_keys = self.FareyLS(best_keys, metaheuristic_name=metaheuristic_name)
            elif current_neighborhood == 'InvertLS':
                new_keys = self.InvertLS(best_keys, metaheuristic_name=metaheuristic_name)
                
            new_cost = self.env.cost(self.env.decoder(new_keys))
            
            if new_cost < best_cost:
                best_keys = new_keys
                best_cost = new_cost
                
                not_used_nb = copy.deepcopy(neighborhoods)
                
                if pool is not None:
                    pool.insert((best_cost, list(best_keys)), metaheuristic_name, -1)
            else:
                not_used_nb.remove(current_neighborhood)
            
            if self.stop_condition(best_cost, metaheuristic_name, -1):
                return best_keys
        
        return best_keys
    
    def MultiStart(self, tag, pool):
        metaheuristic_name = "MS"
        start_time = time.time()
        tempo_max = self.max_time
        
        keys = self.random_keys()
        best_keys = keys
        solution = self.env.decoder(keys)
        best_cost = self.env.cost(solution)
        
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag, True):
            return [], best_keys, best_cost
            
        while time.time() - start_time < tempo_max:
                k1 = random.sample(list(pool.pool), 1)[0][1]
                
                new_keys = self.shaking(k1, 0.1, 0.3)
                
                new_keys = self.RVND(metaheuristic_name = metaheuristic_name ,pool=pool, keys=new_keys)
                
                new_solution = self.env.decoder(new_keys)
                new_cost = self.env.cost(new_solution)
                
                if new_cost < best_cost:
                    best_keys = new_keys
                    best_cost = new_cost
                    
                    pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                
                if self.stop_condition(best_cost, metaheuristic_name, tag, True):
                        return [], best_keys, best_cost

        final_cost_solution = self.env.decoder(best_keys)
        final_cost_value = self.env.cost(final_cost_solution, True)
        
        return [], best_keys, final_cost_value
    
    def SimulatedAnnealing(self, SAmax=10, Temperatura=1000, alpha=0.95,  beta_min=0.05, beta_max=0.25, tag = 0, pool=None):
        metaheuristic_name = "SA"
        tempo_max = self.max_time

        keys = self.random_keys()
        keys = self.RVND(metaheuristic_name = metaheuristic_name ,pool=pool, keys=keys)
        best_keys = keys

        solution = self.env.decoder(keys)
        cost = self.env.cost(solution)
        best_cost = cost
        
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag, True):
                return [], best_keys, best_cost
            
        start_time = time.time()
        T = Temperatura

        while time.time() - start_time < tempo_max:
            iter_at_temp = 0
            while iter_at_temp < SAmax:
                iter_at_temp += 1

                new_keys = self.shaking(keys, beta_min, beta_max)
                new_solution = self.env.decoder(new_keys)
                new_cost = self.env.cost(new_solution)
                
                delta = new_cost - cost
                
                if new_cost < best_cost:
                    best_keys = new_keys
                    best_cost = new_cost
                    pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                    if self.stop_condition(best_cost, metaheuristic_name, tag, True):
                            return [], best_keys, best_cost

                if delta <= 0:
                    keys = new_keys
                    cost = new_cost
                else:
                    if random.random() < math.exp(-delta / T):
                        keys = new_keys
                        cost = new_cost

            T = T * alpha
            
            keys = self.NelderMeadSearch(pool=pool, keys=keys, metaheuristic_name=metaheuristic_name)
            new_cost = self.env.cost(self.env.decoder(keys))
            
            if new_cost < best_cost:
                best_keys = keys
                best_cost = new_cost
                pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)

        final_cost_solution = self.env.decoder(best_keys)
        final_cost_value = self.env.cost(final_cost_solution, True)
        
        return [], best_keys, final_cost_value

    def VNS(self, limit_time, x, tag, pool, beta_min=0.05, k_max=6):
        metaheuristic_name = "VNS"

        idx_k = 0
        start_time = time.time()
        
        keys = self.random_keys()
        keys = self.RVND(metaheuristic_name = metaheuristic_name ,pool=pool, keys=keys)
        best_keys = keys
        best_cost = self.env.cost(self.env.decoder(keys))
        
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag, True):
            return [], best_keys, best_cost

        while time.time() - start_time < limit_time:
            if idx_k >= k_max:
                idx_k = 0

            s1 = self.shaking(best_keys, idx_k * beta_min, (idx_k + 1) * beta_min)
            
            s2 = self.RVND(metaheuristic_name = metaheuristic_name ,pool=pool, keys=s1)
            
            sol2 = self.env.decoder(s2)
            cost = self.env.cost(sol2)

            if cost <= best_cost:
                best_cost = cost
                best_keys = s2
                pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                idx_k = 0
            else:
                idx_k += 1
            
            if self.stop_condition(best_cost, metaheuristic_name, tag, True):
                return [], best_keys, best_cost

        final_cost_solution = self.env.decoder(best_keys)
        final_cost_value = self.env.cost(final_cost_solution)
        
        return [], best_keys, final_cost_value
    
    def LNS(self, limit_time, tag, pool, beta_min=0.05, beta_max=0.25, T0=1000, alphaLNS=0.95, k_max=6):
        metaheuristic_name = "LNS"
        
        Farey_Squence = [0.00, 0.142857, 0.166667, 0.20, 0.25, 0.285714, 0.333333, 0.40, 0.428571, 0.50, 
                         0.571429, 0.60, 0.666667, 0.714286, 0.75, 0.80, 0.833333, 0.857143, 1.0]
        T = T0
        reanneling = False
        start_time = time.time()
        
        keys = self.random_keys()
        s = keys
        best_keys = keys
        best_cost = self.env.cost(self.env.decoder(keys))
        s_cost = best_cost
        
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag, True):
            return [], best_keys, best_cost

        while time.time() - start_time < limit_time:
            if not reanneling:
                T = T0
            else:
                T = T0*0.3
                
            while T > 0.01 and (time.time() - start_time < limit_time):
                
                s1 = s
                s1_cost = s_cost
                
                
                intensity = int(random.uniform(beta_min * self.__MAX_KEYS, beta_max* self.__MAX_KEYS))
                
                RKorder = [i for i in range(self.__MAX_KEYS)]
                random.shuffle(RKorder)
            
                for k in range(intensity):
                    pos = RKorder[k]
                    rkBest = None
                    rkBestCost = float('inf')
                    
                    
                    for j in range(len(Farey_Squence) - 1):
                        if self.stop_condition(best_cost, metaheuristic_name, tag):
                            return [], best_keys, best_cost
                        
                        s1[pos] = random.uniform(Farey_Squence[j], Farey_Squence[j+1])
                        new_cost = self.env.cost(self.env.decoder(s1))
                        
                        if new_cost < rkBestCost:
                            rkBest = copy.deepcopy(s1)
                            rkBestCost = new_cost
                            
                    
                    s1 = copy.deepcopy(rkBest)
                    s1_cost = rkBestCost
                    
                    
                best_s1 = copy.deepcopy(s1)
                best_cost_s1 = s1_cost
                
                best_s1 = self.NelderMeadSearch(best_s1, pool=pool, metaheuristic_name=metaheuristic_name)
                best_cost_s1 = self.env.cost(self.env.decoder(best_s1))
                
                delta = best_cost_s1 - s_cost
                
                if delta <= 0:
                    s = best_s1
                    
                    if best_cost_s1 < best_cost:
                        best_keys = best_s1
                        best_cost = best_cost_s1
                        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                        
                else:
                    if random.random() < math.exp(-delta / T):
                        s = copy.deepcopy(best_s1)
                        s_cost = best_cost_s1
                 
                    
            

            reanneling = True
            if self.stop_condition(best_cost, metaheuristic_name, tag, True):
                return [], best_keys, best_cost

        final_cost_solution = self.env.decoder(best_keys)
        final_cost_value = self.env.cost(final_cost_solution)
        
        return [], best_keys, final_cost_value
    
    
    def PSO(self, Psize=100, c1=2.05, c2=2.05, w=0.73, tag=0, pool=None):
        metaheuristic_name = "PSO"
        limit_time = self.max_time

        # Initialize population of particles and their data structures
        X = [self.random_keys() for _ in range(Psize)]
        Pbest = [copy.deepcopy(p) for p in X]
        V = [np.random.random(self.__MAX_KEYS) for _ in range(Psize)]
        
        Gbest = None
        best_cost_pso = float('inf')

        # Evaluate initial population and find initial Pbest and Gbest
        for i in range(Psize):
            cost_x = self.env.cost(self.env.decoder(X[i]))
            Pbest[i] = (cost_x, X[i])
            if cost_x < best_cost_pso:
                best_cost_pso = cost_x
                Gbest = X[i]

        pool.insert((best_cost_pso, list(Gbest)), metaheuristic_name, tag)
        if self.stop_condition(best_cost_pso, metaheuristic_name, tag, True):
            return [], Gbest, best_cost_pso
        
        start_time = time.time()

        # Run the PSO evolutionary process
        while time.time() - start_time < limit_time:
            best_of_current_gen = float('inf')

            for i in range(Psize):
                if self.stop_condition(best_cost_pso, metaheuristic_name, tag, True):
                    return [], Gbest, best_cost_pso
                
                # Update velocity
                r1 = random.random()
                r2 = random.random()

                # V[i][j] = w * V[i][j] + c1 * r1 * (Pbest[i].rk[j] - X[i].rk[j]) + c2 * r2 * (Gbest.rk[j] - X[i].rk[j])
                V[i] = w * V[i] + c1 * r1 * (Pbest[i][1] - X[i]) + c2 * r2 * (Gbest - X[i])
                
                # Update position
                old_keys = copy.deepcopy(X[i])
                X[i] = X[i] + V[i]
                
                # Enforce boundary constraints [0, 1)
                for j in range(self.__MAX_KEYS):
                    if not (0.0 <= X[i][j] < 1.0):
                        X[i][j] = old_keys[j]
                        V[i][j] = 0.0

                # Evaluate new position
                cost_x = self.env.cost(self.env.decoder(X[i]))
                
                # Update Pbest
                if cost_x < Pbest[i][0]:
                    Pbest[i] = (cost_x, X[i])
                
                # Update Gbest
                if cost_x < best_cost_pso:
                    Gbest = X[i]
                    best_cost_pso = cost_x
                    pool.insert((best_cost_pso, list(Gbest)), metaheuristic_name, tag)
                
                if cost_x < best_of_current_gen:
                    best_of_current_gen = cost_x

            # RKO Enhancement: Apply Nelder-Mead to a random Pbest particle
            chosen_pbest_index = random.randint(0, Psize - 1)
            pbest_keys_to_improve = Pbest[chosen_pbest_index][1]
            improved_pbest_keys = self.NelderMeadSearch(keys=pbest_keys_to_improve, pool=pool)
            improved_pbest_cost = self.env.cost(self.env.decoder(improved_pbest_keys))
            
            # Update Gbest if the local search improved the solution
            if improved_pbest_cost < best_cost_pso:
                Gbest = improved_pbest_keys
                best_cost_pso = improved_pbest_cost
                pool.insert((best_cost_pso, list(Gbest)), metaheuristic_name, tag)

        return [], Gbest, best_cost_pso

    def BRKGA(self, pop_size, elite_pop, chance_elite,  tag, pool):
        metaheuristic_name = "BRKGA"
        limit_time = self.max_time
        generation = 0
        tam_elite = int(pop_size * elite_pop)
        half_time_restart_done = False

        population = [self.random_keys() for _ in range(pop_size)]
        best_keys_overall = None
        best_fitness_overall = float('inf')

        start_time = time.time()

        while time.time() - start_time < limit_time:
            if not half_time_restart_done and (time.time() - start_time) > (limit_time / 2):
                population = [self.random_keys() for _ in range(pop_size)]
                half_time_restart_done = True

            generation += 1
            
            evaluated_population = []
            for key in population:
                sol = self.env.decoder(key)
                fitness = self.env.cost(sol)
                evaluated_population.append((key, sol, fitness))

                if fitness < best_fitness_overall:
                    best_fitness_overall = fitness
                    best_keys_overall = key
                    pool.insert((best_fitness_overall, list(best_keys_overall)), metaheuristic_name, tag)

                if self.stop_condition(best_fitness_overall, metaheuristic_name, tag, True):
                    return [], best_keys_overall, fitness
            
            evaluated_population.sort(key=lambda x: x[2])
            elite_keys = [item[0] for item in evaluated_population[:tam_elite]]

            new_population = [elite_keys[0]]

            while len(new_population) < pop_size:
                if random.random() < 0.5 and len(pool.pool) > 0:
                    parent1 = random.sample(list(pool.pool), 1)[0][1]
                else:
                    parent1 = random.sample(population, 1)[0]

                if random.random() < 0.5 and len(elite_keys) > 0:
                    parent2 = random.sample(elite_keys, 1)[0]
                else:
                    parent2 = random.sample(population, 1)[0]

                child = np.zeros(self.__MAX_KEYS)
                for i in range(len(child)):
                    if random.random() < chance_elite:
                        child[i] = parent2[i]
                    else:
                        child[i] = parent1[i]
                
                for idx in range(len(child)):
                    if random.random() < 0.05:
                        child[idx] = random.random()

                new_population.append(child)
            
            population = new_population[:pop_size]

        final_cost_solution = self.env.decoder(best_keys_overall)
        final_cost_value = self.env.cost(final_cost_solution)
        
        return [], best_keys_overall, best_fitness_overall

    def ILS(self, limit_time, x, tag, pool, beta_min=0.1, beta_max=0.5):
        metaheuristic_name = "ILS"
        start_time = time.time()
        
        keys = self.random_keys()
        keys = self.RVND(metaheuristic_name = metaheuristic_name ,pool=pool, keys=keys)
        best_keys = keys
        best_cost = self.env.cost(self.env.decoder(keys))
        
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag, True):
            return [], best_keys, best_cost

        while time.time() - start_time < limit_time:
            s1 = self.shaking(best_keys, beta_min, beta_max)
            
            s2 = self.RVND(metaheuristic_name = metaheuristic_name ,pool=pool, keys=s1)
            
            sol2 = self.env.decoder(s2)
            cost = self.env.cost(sol2)

            if cost <= best_cost:
                best_cost = cost
                best_keys = s2
                pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)

            if self.stop_condition(best_cost, metaheuristic_name, tag, True):
                    return [], best_keys, best_cost

        final_cost_solution = self.env.decoder(best_keys)
        final_cost_value = self.env.cost(final_cost_solution)
        
        return [], best_keys, final_cost_value
    
    def GA(self, pop_size=40, probCros=0.98, probMut=0.005, tag=0, pool=None):
        """
        Performs a search using a standard Genetic Algorithm (GA), adapted for the RKO framework.

        This implementation uses tournament selection, uniform crossover, and mutation to evolve
        a population of random-key vectors. It also incorporates a local search step on the
        best individual of each generation to intensify the search.

        Args:
            pop_size (int): The total number of solutions in the population.
            probCros (float): The probability of crossover.
            probMut (float): The probability of mutation for each gene.
            tag (int): An identifier for the worker process.
            pool (SolutionPool): The shared elite solution pool.

        Returns:
            tuple: The final solution details (cost, keys).
        """
        metaheuristic_name = "GA"
        limit_time = self.max_time
        
        population = []
        best_keys_overall = None
        best_fitness_overall = float('inf')

        # 1. Cria a população inicial com chaves aleatórias
        for _ in range(pop_size):
            keys = self.random_keys()
            cost = self.env.cost(self.env.decoder(keys))
            population.append({'keys': keys, 'cost': cost})
            if cost < best_fitness_overall:
                best_fitness_overall = cost
                best_keys_overall = keys

        pool.insert((best_fitness_overall, list(best_keys_overall)), metaheuristic_name, tag)
        if self.stop_condition(best_fitness_overall, metaheuristic_name, tag, True):
            return [], best_keys_overall, best_fitness_overall
        
        start_time = time.time()
        num_generations = 0

        while time.time() - start_time < limit_time:
            num_generations += 1
            
            # 2. Seleção de pais usando o método de torneio
            parents = []
            for _ in range(pop_size):
                p1, p2, p3 = random.sample(population, 3)
                melhor_pai = min([p1, p2, p3], key=lambda p: p['cost'])
                parents.append(melhor_pai)
            
            new_population_data = []
            best_of_current_gen = float('inf')

            # 3. Crossover e Mutação
            for i in range(0, pop_size - 1, 2):
                parent1_keys = parents[i]['keys']
                parent2_keys = parents[i+1]['keys']
                child1_keys = copy.deepcopy(parent1_keys)
                child2_keys = copy.deepcopy(parent2_keys)

                if random.random() < probCros:
                    # Crossover Uniforme
                    for j in range(self.__MAX_KEYS):
                        if random.random() < 0.5:
                            child1_keys[j], child2_keys[j] = child2_keys[j], child1_keys[j]
                    
                    # Mutação
                    for j in range(self.__MAX_KEYS):
                        if random.random() <= probMut:
                            child1_keys[j] = random.random()
                        if random.random() <= probMut:
                            child2_keys[j] = random.random()
                
                # Avalia os filhos
                cost1 = self.env.cost(self.env.decoder(child1_keys))
                cost2 = self.env.cost(self.env.decoder(child2_keys))
                
                new_population_data.append({'keys': child1_keys, 'cost': cost1})
                new_population_data.append({'keys': child2_keys, 'cost': cost2})

                if cost1 < best_of_current_gen:
                    best_of_current_gen = cost1
                if cost2 < best_of_current_gen:
                    best_of_current_gen = cost2

            # 4. Aplica busca local no melhor indivíduo da nova população
            new_population_data.sort(key=lambda p: p['cost'])
            best_new_individual = new_population_data[0]
            
            improved_keys = self.NelderMeadSearch(keys=best_new_individual['keys'], pool=pool)
            improved_cost = self.env.cost(self.env.decoder(improved_keys))
            
            # Atualiza o melhor indivíduo da nova população
            if improved_cost < best_new_individual['cost']:
                best_new_individual['keys'] = improved_keys
                best_new_individual['cost'] = improved_cost

            # 5. Substitui a população antiga pela nova (com elitismo)
            population = new_population_data
            
            # Atualiza a melhor solução global se houver uma melhoria
            if best_new_individual['cost'] < best_fitness_overall:
                best_fitness_overall = best_new_individual['cost']
                best_keys_overall = best_new_individual['keys']
                pool.insert((best_fitness_overall, list(best_keys_overall)), metaheuristic_name, tag)

            if self.stop_condition(best_fitness_overall, metaheuristic_name, tag, True):
                return [], best_keys_overall, best_fitness_overall
        
        final_cost_solution = self.env.decoder(best_keys_overall)
        final_cost_value = self.env.cost(final_cost_solution)
        
        return [], best_keys_overall, final_cost_value

    def stop_condition(self, best_cost, metaheuristic_name, tag, print_best=False):
        if time.time() - self.start_time > self.max_time:
            if print_best:
                print(f"{metaheuristic_name} {tag}: ENCERRADO")
            return True
        if self.env.dict_best is not None:
            if best_cost == self.env.dict_best[self.env.instance_name]:
                
                if print_best:
                    print(f"Metaheurística {metaheuristic_name} com tag {tag} encontrou a melhor solução: {best_cost}")
                return True
            else:
                return False
        return False
        
    def solve(self, pop_size, elite_pop, chance_elite, time_total,brkga=0, ms=0, sa=0, vns=0, ils=0,lns=0,pso=0,ga=0, restart=1, runs = 1):
        solutions = []
        times = []
        costs = []
        for i in range(runs):
            print(f'Instancia: {self.env.instance_name}, Execução: {i+1}/{runs}')
            limit_time = time_total * restart
            restarts = int(1/restart)
            
            self.max_time = limit_time
            
            manager = Manager()
            shared = manager.Namespace()
            
            shared.best_pair = manager.list([float('inf'), None, None])
            shared.best_pool = manager.list()
            
            shared.pool = SolutionPool(20, shared.best_pool, shared.best_pair, lock=manager.Lock(), print=self.print, Best=self.env.dict_best[self.env.instance_name])
            for i in range(20):
                keys = self.random_keys()
                cost = self.env.cost(self.env.decoder(keys))
                shared.pool.insert((cost, list(keys)), 'pool', -1)
            
            lock = manager.Lock()
            processes = []
            tag = 0
            for k in range(restarts):
                self.start_time = time.time()
                shared.pool.pool = manager.list()
                for _ in range(brkga):
                    p = Process(
                        target=_brkga_worker,
                        args=(self.env, pop_size, elite_pop, chance_elite, shared.pool,tag)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()
                for _ in range(ms):
                    p = Process(
                        target=_MS_worker,
                        args=(self.env,10000,100,shared.pool,tag)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()
                for _ in range(sa):
                    p = Process(
                        target=_SA_worker,
                        args=(self.env, pop_size, elite_pop, chance_elite, shared.pool,tag)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()
                for _ in range(vns):
                    p = Process(
                        target=_VNS_worker,
                        args=(self.env, limit_time,pop_size, shared.pool,tag)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()
                for _ in range(ils):
                    p = Process(
                        target=_ILS_worker,
                        args=(self.env, limit_time,pop_size, shared.pool,tag)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()
                    
                for _ in range(lns):
                    p = Process(
                        target=_LNS_worker,
                        args=(self.env, limit_time, shared.pool,tag)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()
                    
                for _ in range(pso):
                    p = Process(
                        target=_PSO_worker,
                        args=(self.env, shared.pool , tag)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()
                    
                for _ in range(ga):
                    p = Process(
                        target=_GA_worker,
                        args=(self.env, shared.pool , tag)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()

                for p in processes:
                    p.join()

            cost = shared.pool.best_pair[0]
            solution = shared.pool.best_pair[1]     
            time_elapsed = shared.pool.best_pair[2]

            solutions.append(solution)
            costs.append(round(cost,2))
            times.append(round(-1 * time_elapsed,2))
            
        with open(self.save_directory, 'a', newline='') as f:
            f.write(f'{self.max_time}, {self.env.instance_name}, {round(sum(costs)/len(costs),2)}, {costs}, {round(sum(times)/len(times),2)}, {times}\n')
        
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
    
def _LNS_worker(env, limit_time, pool, tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.LNS(limit_time=limit_time, tag = tag, pool = pool)
    
def _PSO_worker(env, pool, tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.PSO(tag = tag, pool = pool)
    
def _GA_worker(env, pool, tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.GA(tag = tag, pool = pool)