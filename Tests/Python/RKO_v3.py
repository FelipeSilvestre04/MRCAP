import os
import numpy as np
import time
import random
import copy
import math
import datetime
import bisect
import itertools
from colorama import init, Fore, Back, Style
from multiprocessing import Manager, Process, cpu_count

class SolutionPool():
    def __init__(self, size, pool, best_pair, lock=None, print=False, Best=None, env=None):
        self.size = size
        self.pool = pool
        self.best_pair = best_pair
        self.lock = lock
        self.start_time = time.time()    
        self.print = print 
        self.best_possible = Best
        self.env = env
        
    def insert(self, entry_tuple, metaheuristic_name, tag): 
        fitness = entry_tuple[0]
        keys = entry_tuple[1]
        # print(f"\rtempo = {round(time.time() - self.start_time,2)} ", end="")
        if self.print:
            print(f'[info] {metaheuristic_name} trying to insert solution with fitness {fitness} into pool, the best solution is {self.best_pair[0]}, at time: {round(self.start_time - time.time(), 2)}s', flush=True)
        with self.lock:
            if fitness < self.best_pair[0]: 
                # self.env.plot(legenda='[]')
                self.best_pair[0] = fitness          
                self.best_pair[1] = list(keys)        
                self.best_pair[2] = round(self.start_time - time.time(), 2)
                
                if self.print:
                    if tag == -1:
                        # if metaheuristic_name == 'pool':
                        print(f'[best] {metaheuristic_name} find a solution with fitness {fitness}, is the new best solution! time: {round(self.start_time - time.time(), 2)}s', flush=True)

                        # if self.best_possible is not None :
                        #     print(f"\n{metaheuristic_name} NOVO MELHOR: {fitness} - BEST: {self.best_possible} - Tempo: {round(self.start_time - time.time(), 2)}s - {len(self.pool)}", flush=True) 
                        # else:
                        #     print(f"\n{metaheuristic_name} NOVO MELHOR: {fitness} - Tempo: {round(self.start_time - time.time(), 2)}s - {len(self.pool)}", flush=True)    
                    else:
                        print(f'[best] {metaheuristic_name} find a solution with fitness {fitness}, is the new best solution! time: {round(self.start_time - time.time(), 2)}s', flush=True)

                        # if self.best_possible is not None :
                        #     print(f"\n{metaheuristic_name} NOVO MELHOR: {fitness} - BEST: {self.best_possible} - Tempo: {round(self.start_time - time.time(), 2)}s - {len(self.pool)}", flush=True) 
                        # else:
                        #     print(f"\n{metaheuristic_name} NOVO MELHOR: {fitness} - Tempo: {round(self.start_time - time.time(), 2)}s - {len(self.pool)}", flush=True)                
            bisect.insort(self.pool, entry_tuple) 
            if len(self.pool) > self.size:
                self.pool.pop()

class RKO():
    def __init__(self, env, print_best=False, save_directory=None):
        self.env = env
        self.__MAX_KEYS = self.env.tam_solution
        self.LS_type = self.env.LS_type
        self.start_time = time.time()
        self.max_time = self.env.max_time
        self.rate = 1
        
        self.print_best = print_best
        
        self.save_directory = save_directory
        
        self.q_managers = {}

        # Dentro da classe RKO
    def _setup_parameters(self, metaheuristic_name, params_config):
        is_online = any(len(v) > 1 for v in params_config.values())

        if is_online:
            if metaheuristic_name not in self.q_managers:
                # PASSA OS NOVOS ARGUMENTOS
                self.q_managers[metaheuristic_name] = QLearningManager(
                    parameters_config=params_config, 
                    max_time=self.max_time,
                    metaheuristic_name=metaheuristic_name,
                    save_report=self.env.save_q_learning_report # Lê da classe de ambiente
                )

            q_manager = self.q_managers[metaheuristic_name]
            initial_params = q_manager.get_current_parameters()
            return q_manager, initial_params
        else:
            static_params = {k: v[0] for k, v in params_config.items()}
            return None, static_params
        
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
        metaheuristic_name = f"MS {tag}"
        start_time = time.time()
        tempo_max = self.max_time
        
        keys = self.random_keys()
        best_keys = keys
        solution = self.env.decoder(keys)
        best_cost = self.env.cost(solution)
        
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition( best_cost, metaheuristic_name, tag, pool = pool):
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
                
                if self.stop_condition(best_cost, metaheuristic_name, tag, pool = pool):
                        return [], best_keys, best_cost

        final_cost_solution = self.env.decoder(best_keys)
        final_cost_value = self.env.cost(final_cost_solution, True)
        
        return [], best_keys, final_cost_value
    
# Adicione/substitua este método em sua classe RKO

    def SimulatedAnnealing(self, tag, pool):
        """
        Implementa o Simulated Annealing (SA) integrado ao framework RKO,
        com controle de parâmetros online opcional via Q-Learning.
        """
        metaheuristic_name = f"SA {tag}"
        tempo_max = self.max_time
        
        # 1. SETUP DE PARÂMETROS
        # ----------------------------------------------------------------
        q_manager, params = self._setup_parameters(metaheuristic_name, self.env.SA_parameters)
    
        
        
        
        # Parâmetros que serão usados (fixos ou como ponto de partida)
        SAmax = params['SAmax']
        Temperatura = params['T0']
        alpha = params['alphaSA']
        beta_min = params['betaMin']
        beta_max = params['betaMax']
        TemperaturaMaxAtual = Temperatura
        # 2. INICIALIZAÇÃO DA SOLUÇÃO
        # ----------------------------------------------------------------
        start_time = time.time()
        
        keys = self.random_keys()
        # keys = self.RVND(metaheuristic_name=metaheuristic_name, pool=pool, keys=keys)
        s = keys # Solução atual
        best_keys = keys

        cost = self.env.cost(self.env.decoder(s))
        s_cost = cost
        best_cost = cost
        
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag, pool = pool):
            return [], best_keys, best_cost
        
        # 3. LOOP PRINCIPAL DO SA
        # ----------------------------------------------------------------
        while time.time() - start_time < tempo_max:
            
            # --- SEÇÃO DE CONTROLE DE PARÂMETROS (Q-LEARNING) ---
            if q_manager is not None:
                
                current_time = time.time() - self.start_time
                new_params = q_manager.select_action(current_time)
                SAmax = new_params['SAmax']
                Temperatura = new_params['T0']
                alpha = new_params['alphaSA']
                beta_min = new_params['betaMin']
                beta_max = new_params['betaMax']
            # ----------------------------------------------------------

          
            T = Temperatura
            best_cost_in_cycle = best_cost
            improvement_flag = 0

            # Loop de resfriamento
            while T > 0.0001 and (time.time() - start_time < tempo_max):
                iter_at_temp = 0
                best_ofv_in_temp = float('inf')

                while iter_at_temp < SAmax:
                    iter_at_temp += 1
                    
                    new_keys = self.shaking(s, beta_min, beta_max)
                    new_cost = self.env.cost(self.env.decoder(new_keys))
                    
                    if new_cost < best_ofv_in_temp:
                        best_ofv_in_temp = new_cost

                    delta = new_cost - s_cost
                    
                    if delta < 0:
                        s = new_keys
                        s_cost = new_cost
                        if s_cost < best_cost:
                            best_cost = s_cost
                            best_keys = s
                            improvement_flag = 1
                            pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                            if self.stop_condition(best_cost, metaheuristic_name, tag, pool = pool):
                                return [], best_keys, best_cost
                    else:
                        if random.random() < math.exp(-delta / T):
                            s = new_keys
                            s_cost = new_cost

                # Aplica busca local (RVND) antes de reduzir a temperatura
                # s = self.RVND(keys=s, pool=pool, metaheuristic_name=metaheuristic_name)
                s = self.NelderMeadSearch(pool=pool, keys=s, metaheuristic_name=metaheuristic_name)
                s_cost = self.env.cost(self.env.decoder(s))
                if s_cost < best_cost:
                    best_cost = s_cost
                    best_keys = s
                    improvement_flag = 1
                    pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                    
                if self.stop_condition(best_cost, metaheuristic_name, tag, pool = pool):
                    return [], best_keys, best_cost

                T *= alpha

                if T < 0.0001:
                    TemperaturaMaxAtual = 0.8 * TemperaturaMaxAtual
                    T = TemperaturaMaxAtual
                
            # --- ATUALIZAÇÃO E FEEDBACK PARA O Q-LEARNING ---
            if q_manager:
                if improvement_flag:
                    reward = 1.0
                else:
                    reward = (best_cost_in_cycle - best_ofv_in_temp) / best_cost_in_cycle if best_cost_in_cycle > 0 else 0
                q_manager.update_q_value(reward, time.time() - self.start_time)
            # ----------------------------------------------------

        final_cost_solution = self.env.decoder(best_keys)
        final_cost_value = self.env.cost(final_cost_solution)
        
        #if q_manager:
          #  q_manager.save_final_policy_report(instance_name=self.env.instance_name)
         
        return [], best_keys, final_cost_value
# Adicione/substitua este método em sua classe RKO

    def VNS(self, limit_time, tag, pool):
        """
        Implementa o Variable Neighborhood Search (VNS) integrado ao framework RKO,
        com controle de parâmetros online opcional via Q-Learning.
        """
        metaheuristic_name = f"VNS {tag}"
        
        # 1. SETUP DE PARÂMETROS (DECIDE ENTRE ONLINE E OFFLINE)
        # ----------------------------------------------------------------
        q_manager, params = self._setup_parameters(metaheuristic_name, self.env.VNS_parameters)
        
        # Parâmetros iniciais
        k_max = params['kMax']
        beta_min = params['betaMin']
        
        # 2. INICIALIZAÇÃO DA SOLUÇÃO
        # ----------------------------------------------------------------
        start_time = time.time()
        
        keys = self.random_keys()
        keys = self.RVND(metaheuristic_name=metaheuristic_name, pool=pool, keys=keys)
        current_s = keys
        current_cost = self.env.cost(self.env.decoder(keys))
        best_cost = current_cost # best_cost rastreia o melhor global, current_cost o da iteração
        best_keys = keys

        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag, pool = pool):
            return [], best_keys, best_cost

        # 3. LOOP PRINCIPAL DO VNS
        # ----------------------------------------------------------------
        while time.time() - start_time < limit_time:
            
            # --- SEÇÃO DE CONTROLE DE PARÂMETROS (Q-LEARNING) ---
            if q_manager:
                current_time = time.time() - start_time
                new_params = q_manager.select_action(current_time)
                k_max = new_params['kMax']
                beta_min = new_params['betaMin']
            # ----------------------------------------------------------
            
            k = 1 # No VNS, 'k' é o contador da vizinhança, não 'idx_k'
            improvement_flag_global = 0
            cost_before_vns_cycle = current_cost

            while k <= k_max:
                if self.stop_condition(best_cost, metaheuristic_name, tag, pool = pool):
                    return [], best_keys, best_cost

                # Perturba a solução atual 's'
                s1 = self.shaking(current_s, k * beta_min, (k + 1) * beta_min)
                
                # Busca local a partir da solução perturbada
                s2 = self.RVND(metaheuristic_name=metaheuristic_name, pool=pool, keys=s1)
                
                cost = self.env.cost(self.env.decoder(s2))

                # Critério de Aceitação do VNS
                if cost < current_cost:
                    current_s = s2
                    current_cost = cost
                    k = 1 # Retorna para a primeira vizinhança
                    
                    if cost < best_cost:
                        best_cost = cost
                        best_keys = s2
                        improvement_flag_global = 1
                        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                else:
                    k += 1
            
            # --- ATUALIZAÇÃO E FEEDBACK PARA O Q-LEARNING ---
            if q_manager:
                if improvement_flag_global:
                    reward = 1.0
                else:
                    reward = (cost_before_vns_cycle - current_cost) / cost_before_vns_cycle if cost_before_vns_cycle > 0 else 0
                
                q_manager.update_q_value(reward, time.time() - start_time)
            # ----------------------------------------------------

        final_cost_solution = self.env.decoder(best_keys)
        final_cost_value = self.env.cost(final_cost_solution)
        
        #if q_manager:
          #  q_manager.save_final_policy_report(instance_name=self.env.instance_name)
         
        return [], best_keys, final_cost_value
    
# Adicione/substitua este método em sua classe RKO

    def LNS(self, limit_time, tag, pool):
        metaheuristic_name = f"LNS {tag}"
        
        # 1. SETUP DE PARÂMETROS
        # ----------------------------------------------------------------
        q_manager, params = self._setup_parameters(metaheuristic_name, self.env.LNS_parameters)
        
        beta_min = params['betaMin']
        beta_max = params['betaMax']
        T0 = params['TO']
        alphaLNS = params['alphaLNS']

        # 2. INICIALIZAÇÃO
        # ----------------------------------------------------------------
        Farey_Sequence = [0.00, 0.142857, 0.166667, 0.20, 0.25, 0.285714, 0.333333, 0.40, 0.428571, 0.50, 
                        0.571429, 0.60, 0.666667, 0.714286, 0.75, 0.80, 0.833333, 0.857143, 1.0]
        
        start_time = time.time()
        
        s = self.random_keys()
        s_cost = self.env.cost(self.env.decoder(s))
        best_keys = s
        best_cost = s_cost
        
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag, pool = pool):
            return [], best_keys, best_cost
        
        reanneling = False

        # 3. LOOP PRINCIPAL DO LNS
        # ----------------------------------------------------------------
        while time.time() - start_time < limit_time:
            
            # --- SEÇÃO DE CONTROLE DE PARÂMETROS (Q-LEARNING) ---
            if q_manager:
                current_time = time.time() - start_time
                new_params = q_manager.select_action(current_time)
                beta_min = new_params['betaMin']
                beta_max = new_params['betaMax']
                T0 = new_params['TO']
                alphaLNS = new_params['alphaLNS']
            # ----------------------------------------------------------
            
            improvement_flag_cycle = 0
            cost_before_cycle = best_cost

            if not reanneling:
                T = T0
            else:
                T = T0 * 0.3
            
            # Loop de resfriamento (inner loop)
            while T > 0.01 and (time.time() - start_time < limit_time):
                s_line = copy.deepcopy(s) # sLine = s
                
                # Fase de Destruição (shaking simplificado)
                intensity = int(random.uniform(beta_min * self.__MAX_KEYS, beta_max * self.__MAX_KEYS))
                RKorder = list(range(self.__MAX_KEYS))
                random.shuffle(RKorder)
                
                # Fase de Reparo (usando Farey)
                for k in range(intensity):
                    pos = RKorder[k]
                    rkBestCost = float('inf')
                    best_rk_val = s_line[pos]

                    for j in range(len(Farey_Sequence) - 1):
                        if self.stop_condition(best_cost, metaheuristic_name, tag, pool = pool): return [], best_keys, best_cost
                        
                        s_line[pos] = random.uniform(Farey_Sequence[j], Farey_Sequence[j+1])
                        new_cost = self.env.cost(self.env.decoder(s_line))
                        
                        if new_cost < rkBestCost:
                            rkBestCost = new_cost
                            best_rk_val = s_line[pos]
                    
                    s_line[pos] = best_rk_val
                
                # Busca Local (Intensificação)
                s_best_line = self.NelderMeadSearch(keys=s_line, pool=pool)
                best_cost_s1 = self.env.cost(self.env.decoder(s_best_line))
                
                # Critério de Aceitação (Metropolis)
                delta = best_cost_s1 - s_cost
                if delta <= 0:
                    s = s_best_line
                    s_cost = best_cost_s1
                    if s_cost < best_cost:
                        best_cost = s_cost
                        best_keys = s
                        improvement_flag_cycle = 1
                        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                else:
                    if random.random() < math.exp(-delta / T):
                        s = s_best_line
                        s_cost = best_cost_s1
                
                T *= alphaLNS

            reanneling = True

            # --- ATUALIZAÇÃO E FEEDBACK PARA O Q-LEARNING ---
            if q_manager:
                if improvement_flag_cycle:
                    reward = 1.0
                else:
                    # Recompensa baseada na melhoria do ciclo vs. o melhor global anterior
                    reward = (cost_before_cycle - best_cost) / cost_before_cycle if cost_before_cycle > 0 else 0
                
                q_manager.update_q_value(reward, time.time() - start_time)
            # ----------------------------------------------------

            if self.stop_condition(best_cost, metaheuristic_name, tag, pool = pool):
                return [], best_keys, best_cost

        final_cost_solution = self.env.decoder(best_keys)
        final_cost_value = self.env.cost(final_cost_solution)
        
        #if q_manager:
          #  q_manager.save_final_policy_report(instance_name=self.env.instance_name)
         
        return [], best_keys, final_cost_value

    def PSO(self, tag, pool):
        """
        Implementa o Particle Swarm Optimization (PSO) integrado ao framework RKO,
        com controle de parâmetros online opcional via Q-Learning.
        """
        metaheuristic_name = f"PSO {tag}"
        limit_time = self.max_time

        # 1. SETUP DE PARÂMETROS (DECIDE ENTRE ONLINE E OFFLINE)
        # ----------------------------------------------------------------
        q_manager, params = self._setup_parameters(metaheuristic_name, self.env.PSO_parameters)
        
        # Parâmetros iniciais
        Psize = params['PSize']
        c1 = params['c1']
        c2 = params['c2']
        w = params['w']

        # 2. INICIALIZAÇÃO DO ENXAME (SWARM)
        # ----------------------------------------------------------------
        start_time = time.time()
        
        # Inicializa as partículas (posições), melhores posições pessoais e velocidades
        X = [self.random_keys() for _ in range(Psize)]  # Posições
        Pbest = [None] * Psize  # Melhores posições pessoais (fitness, keys)
        V = [np.random.random(self.__MAX_KEYS) for _ in range(Psize)]  # Velocidades
        
        Gbest_keys = None
        Gbest_cost = float('inf')

        # Avalia a população inicial para definir Pbest e Gbest
        for i in range(Psize):
            cost_x = self.env.cost(self.env.decoder(X[i]))
            Pbest[i] = (cost_x, X[i])
            if cost_x < Gbest_cost:
                Gbest_cost = cost_x
                Gbest_keys = X[i]

        pool.insert((Gbest_cost, list(Gbest_keys)), metaheuristic_name, tag)
        if self.stop_condition(Gbest_cost, metaheuristic_name, tag, pool = pool):
            return [], Gbest_keys, Gbest_cost
        
        # 3. LOOP EVOLUTIVO PRINCIPAL
        # ----------------------------------------------------------------
        while time.time() - start_time < limit_time:
            
            # --- SEÇÃO DE CONTROLE DE PARÂMETROS (Q-LEARNING) ---
            if q_manager:
                current_time = time.time() - self.start_time
                new_params = q_manager.select_action(current_time)
                
                new_Psize = new_params['PSize']
                c1 = new_params['c1']
                c2 = new_params['c2']
                w = new_params['w']

                # --- LÓGICA DE AJUSTE DINÂMICO DO ENXAME (SWARM) ---
                if new_Psize != Psize:
                    # Lógica inspirada em UpdateParticleSize de PSO.h
                    if new_Psize < Psize:
                        # Reduz o enxame, mantendo as melhores partículas
                        sorted_indices = sorted(range(Psize), key=lambda i: Pbest[i][0])
                        X = [X[i] for i in sorted_indices[:new_Psize]]
                        Pbest = [Pbest[i] for i in sorted_indices[:new_Psize]]
                        V = [V[i] for i in sorted_indices[:new_Psize]]
                    else: # new_Psize > Psize
                        # Aumenta o enxame com novas partículas aleatórias
                        num_new = new_Psize - Psize
                        for _ in range(num_new):
                            new_keys = self.random_keys()
                            new_cost = self.env.cost(self.env.decoder(new_keys))
                            X.append(new_keys)
                            Pbest.append((new_cost, new_keys))
                            V.append(np.random.random(self.__MAX_KEYS))
                            if new_cost < Gbest_cost:
                                Gbest_cost, Gbest_keys = new_cost, new_keys
                    Psize = new_Psize
            # ----------------------------------------------------------

            best_cost_in_generation = float('inf')
            improvement_flag = 0

            for i in range(Psize):
                if self.stop_condition(Gbest_cost, metaheuristic_name, tag, pool = pool):
                    return [], Gbest_keys, Gbest_cost
                
                r1, r2 = random.random(), random.random()
                
                # Atualiza a velocidade da partícula
                V[i] = w * V[i] + c1 * r1 * (Pbest[i][1] - X[i]) + c2 * r2 * (Gbest_keys - X[i])
                
                # Atualiza a posição da partícula
                old_keys = X[i]
                X[i] = X[i] + V[i]
                
                # Garante que as chaves permaneçam no intervalo [0, 1)
                for j in range(self.__MAX_KEYS):
                    if not (0.0 <= X[i][j] < 1.0):
                        X[i][j] = old_keys[j]
                        V[i][j] = 0.0

                cost_x = self.env.cost(self.env.decoder(X[i]))
                
                if cost_x < Pbest[i][0]:
                    Pbest[i] = (cost_x, X[i])
                
                if cost_x < Gbest_cost:
                    Gbest_cost = cost_x
                    Gbest_keys = X[i]
                    improvement_flag = 1
                    pool.insert((Gbest_cost, list(Gbest_keys)), metaheuristic_name, tag)
                
                if cost_x < best_cost_in_generation:
                    best_cost_in_generation = cost_x

            # Aplica busca local a uma partícula aleatória (como no seu código)
            if Psize > 0:
                chosen_pbest_index = random.randint(0, Psize - 1)
                improved_keys = self.NelderMeadSearch(keys=Pbest[chosen_pbest_index][1], pool=pool)
                improved_cost = self.env.cost(self.env.decoder(improved_keys))
                
                if improved_cost < best_cost_in_generation:
                    best_cost_in_generation = improved_cost

                if improved_cost < Gbest_cost:
                    Gbest_keys = improved_keys
                    Gbest_cost = improved_cost
                    improvement_flag = 1
                    pool.insert((Gbest_cost, list(Gbest_keys)), metaheuristic_name, tag)

            # --- ATUALIZAÇÃO E FEEDBACK PARA O Q-LEARNING ---
            if q_manager:
                if improvement_flag:
                    reward = 1.0
                else:
                    reward = (Gbest_cost - best_cost_in_generation) / Gbest_cost if Gbest_cost > 0 else 0
                
                q_manager.update_q_value(reward, time.time() - start_time)
            # -------------------------------------------------
        
        #if q_manager:
          #  q_manager.save_final_policy_report(instance_name=self.env.instance_name)
 
        return [], Gbest_keys, Gbest_cost

    # Adicione/substitua este método em sua classe RKO
 
    def BRKGA(self, tag, pool):
        metaheuristic_name = f"BRKGA {tag}"
        limit_time = self.max_time
        generation = 0
        half_time_restart_done = False

        # --- Setup inicial: Q-Learning ou parâmetros fixos ---
        q_manager, params = self._setup_parameters(metaheuristic_name, self.env.BRKGA_parameters)
        pop_size = params['p']
        elite_pop = params['pe']
        chance_elite = params['rhoe']
        tam_elite = max(1, int(pop_size * elite_pop))

        population = [self.random_keys() for _ in range(pop_size)]
        best_keys_overall = None
        best_fitness_overall = float('inf')

        start_time = time.time()

        while time.time() - start_time < limit_time:
            resize_pending = None

            # --- Controle online de parâmetros ---
            if q_manager:
                elapsed = time.time() - start_time
                new_params = q_manager.select_action(elapsed)

                elite_pop = new_params.get('pe', elite_pop)
                chance_elite = new_params.get('rhoe', chance_elite)
                tam_elite = max(1, int(pop_size * elite_pop)) if elite_pop > 0 else 0

                new_pop_size = new_params.get('p', pop_size)
                if new_pop_size != pop_size:
                    resize_pending = new_pop_size

            # --- Restart na metade do tempo ---
            if not half_time_restart_done and (time.time() - start_time) > (limit_time / 2):
                population = [self.random_keys() for _ in range(pop_size)]
                half_time_restart_done = True

            generation += 1

            # --- Avaliação da população ---
            evaluated_population = []
            best_fitness_in_generation = float('inf')
            improvement_flag = 0

            for key in population:
                sol = self.env.decoder(key)
                fitness = self.env.cost(sol)
                evaluated_population.append((key, sol, fitness))

                if fitness < best_fitness_in_generation:
                    best_fitness_in_generation = fitness

                if fitness < best_fitness_overall:
                    best_fitness_overall = fitness
                    best_keys_overall = key
                    improvement_flag = 1
                    pool.insert((best_fitness_overall, list(best_keys_overall)), metaheuristic_name, tag)

                if self.stop_condition(best_fitness_overall, metaheuristic_name, tag):
                    return [], best_keys_overall, fitness

            # --- Aplicar resize após avaliação ---
            if resize_pending is not None:
                if resize_pending < pop_size:
                    evaluated_population.sort(key=lambda x: x[2])
                    population = [ind[0] for ind in evaluated_population[:resize_pending]]
                else:
                    num_new = resize_pending - pop_size
                    population.extend([self.random_keys() for _ in range(num_new)])
                pop_size = resize_pending
                tam_elite = max(1, int(pop_size * elite_pop)) if elite_pop > 0 else 0
                resize_pending = None

            # --- Seleção de elite ---
            evaluated_population.sort(key=lambda x: x[2])
            elite_keys = [item[0] for item in evaluated_population[:tam_elite]] if tam_elite > 0 else []

            # --- Nova geração ---
            new_population = elite_keys[:1] if elite_keys else []

            while len(new_population) < pop_size:
                if random.random() < 0.5 and len(pool.pool) > 0:
                    parent1 = random.choice(list(pool.pool))[1]
                else:
                    parent1 = random.choice(population)

                if len(elite_keys) > 0:
                    parent2 = random.choice(elite_keys)
                else:
                    parent2 = random.choice(population)

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

            # --- Atualiza Q-Learning ---
            if q_manager:
                elapsed = time.time() - start_time
                if improvement_flag:
                    reward = 1.0 + (1.0 / pop_size)
                else:
                    reward = ((best_fitness_overall - best_fitness_in_generation) / best_fitness_overall
                            if best_fitness_overall not in [0, float('inf')] else 0.0)
                q_manager.update_q_value(reward, elapsed)

        final_cost_solution = self.env.decoder(best_keys_overall)
        final_cost_value = self.env.cost(final_cost_solution)
        return [], best_keys_overall, best_fitness_overall


    # Adicione/substitua este método em sua classe RKO

    def ILS(self, limit_time, tag, pool): # Assinatura modificada para remover os betas hardcoded
        metaheuristic_name = f"ILS {tag}"
        
        # 1. SETUP DE PARÂMETROS (DECIDE ENTRE ONLINE E OFFLINE)
        # ----------------------------------------------------------------
        # Esta seção determina se o Q-Learning será usado.
        q_manager, params = self._setup_parameters(metaheuristic_name, self.env.ILS_parameters)
        
        # Parâmetros que serão usados (fixos no modo offline ou o ponto de partida no modo online)
        beta_min = params['betaMin']
        beta_max = params['betaMax']
        
        # 2. INICIALIZAÇÃO DA SOLUÇÃO (Lógica original mantida)
        # ----------------------------------------------------------------
        start_time = time.time()
        
        keys = self.random_keys()
        # Adicionei o 'tag' na chamada do RVND, pois ele provavelmente precisará dele para o pool.
        keys = self.RVND(metaheuristic_name=metaheuristic_name, pool=pool, keys=keys)
        best_keys = keys
        best_cost = self.env.cost(self.env.decoder(keys))
        
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag, pool = pool): # Assumindo que stop_condition foi simplificado
            return [], best_keys, best_cost

        # 3. LOOP PRINCIPAL DO ILS
        # ----------------------------------------------------------------
        while time.time() - start_time < limit_time:
            
            # --- Q-LEARNING: SELEÇÃO DE PARÂMETROS ---
            if q_manager:
                current_time = time.time() - self.start_time
                new_params = q_manager.select_action(current_time)
                beta_min = new_params['betaMin']
                beta_max = new_params['betaMax']
            # ----------------------------------------
            
            cost_before_iteration = best_cost
            improvement_flag = 0
            
            s1 = self.shaking(best_keys, beta_min, beta_max)
            
            s2 = self.RVND(metaheuristic_name=metaheuristic_name, pool=pool, keys=s1)
            
            sol2 = self.env.decoder(s2)
            cost = self.env.cost(sol2)

            if cost < best_cost: # Melhoria estrita para a recompensa máxima
                improvement_flag = 1
            
            if cost <= best_cost:
                best_cost = cost
                best_keys = s2
                pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)

            if self.stop_condition(best_cost, metaheuristic_name, tag, pool = pool):
                return [], best_keys, best_cost
            
            # --- Q-LEARNING: ATUALIZAÇÃO E APRENDIZADO ---
            if q_manager:
                if improvement_flag:
                    reward = 1.0
                else:
                    reward = (cost_before_iteration - cost) / cost_before_iteration if cost_before_iteration > 0 else 0
                
                q_manager.update_q_value(reward, time.time() - self.start_time)
            # ----------------------------------------------

        final_cost_solution = self.env.decoder(best_keys)
        final_cost_value = self.env.cost(final_cost_solution)
        
        #if q_manager:
          #  q_manager.save_final_policy_report(instance_name=self.env.instance_name)
        
        return [], best_keys, final_cost_value

# Adicione/substitua este método em sua classe RKO

    def GA(self, tag, pool):
        """
        Executa uma busca usando um Algoritmo Genético (GA) padrão, adaptado para o framework RKO,
        com controle de parâmetros online opcional via Q-Learning.
        """
        metaheuristic_name = f"GA {tag}"
        limit_time = self.max_time
        
        # 1. SETUP DE PARÂMETROS (DECIDE ENTRE ONLINE E OFFLINE)
        # ----------------------------------------------------------------
        q_manager, params = self._setup_parameters(metaheuristic_name, self.env.GA_parameters)
        
        # Parâmetros iniciais
        pop_size = params['sizePop']
        prob_cros = params['probCros']
        prob_mut = params['probMut']

        # 2. INICIALIZAÇÃO DA POPULAÇÃO
        # ----------------------------------------------------------------
        population = []
        best_keys_overall = None
        best_fitness_overall = float('inf')

        for _ in range(pop_size):
            keys = self.random_keys()
            cost = self.env.cost(self.env.decoder(keys))
            population.append({'keys': keys, 'cost': cost})
            if cost < best_fitness_overall:
                best_fitness_overall = cost
                best_keys_overall = keys

        pool.insert((best_fitness_overall, list(best_keys_overall)), metaheuristic_name, tag)
        if self.stop_condition(best_fitness_overall, metaheuristic_name, tag, pool = pool):
            return [], best_keys_overall, best_fitness_overall
        
        start_time = time.time()
        num_generations = 0

        # 3. LOOP EVOLUTIVO PRINCIPAL
        # ----------------------------------------------------------------
        while time.time() - start_time < limit_time:
            num_generations += 1
            
            # --- SEÇÃO DE CONTROLE DE PARÂMETROS (Q-LEARNING) ---
            if q_manager:
                current_time = time.time() - self.start_time
                new_params = q_manager.select_action(current_time)
                
                new_pop_size = new_params['sizePop']
                prob_cros = new_params['probCros']
                prob_mut = new_params['probMut']
                
                # --- LÓGICA DE AJUSTE DINÂMICO DA POPULAÇÃO ---
                if new_pop_size != pop_size:
                    population.sort(key=lambda p: p['cost'])
                    if new_pop_size < pop_size:
                        # Reduz a população, matando aleatoriamente exceto o melhor
                        current_best = population[0]
                        others = population[1:]
                        random.shuffle(others)
                        population = [current_best] + others[:new_pop_size - 1]
                    else: # new_pop_size > pop_size
                        # Aumenta a população com novos indivíduos aleatórios
                        num_new = new_pop_size - pop_size
                        for _ in range(num_new):
                            new_keys = self.random_keys()
                            new_cost = self.env.cost(self.env.decoder(new_keys))
                            population.append({'keys': new_keys, 'cost': new_cost})
                    pop_size = new_pop_size
            # ----------------------------------------------------------

            # Seleção por Torneio
            parents = []
            for _ in range(pop_size):
                p1, p2, p3 = random.sample(population, 3)
                melhor_pai = min([p1, p2, p3], key=lambda p: p['cost'])
                parents.append(melhor_pai)
            
            new_population_data = []
            best_of_current_gen_cost = float('inf')
            improvement_flag = 0

            # Crossover e Mutação
            for i in range(0, pop_size, 2):
                if i + 1 >= len(parents): # Garante que não haja erro com população ímpar
                    new_population_data.append(parents[i])
                    continue

                parent1_keys, parent2_keys = parents[i]['keys'], parents[i+1]['keys']
                child1_keys, child2_keys = copy.deepcopy(parent1_keys), copy.deepcopy(parent2_keys)

                if random.random() < prob_cros:
                    # Crossover Uniforme (mantido como em seu código)
                    for j in range(self.__MAX_KEYS):
                        if random.random() < 0.5:
                            child1_keys[j], child2_keys[j] = child2_keys[j], child1_keys[j]
                    
                    # Mutação (aplicada apenas se houve crossover, como no C++)
                    for j in range(self.__MAX_KEYS):
                        if random.random() <= prob_mut: child1_keys[j] = random.random()
                        if random.random() <= prob_mut: child2_keys[j] = random.random()
                
                cost1 = self.env.cost(self.env.decoder(child1_keys))
                cost2 = self.env.cost(self.env.decoder(child2_keys))
                
                new_population_data.extend([{'keys': child1_keys, 'cost': cost1}, {'keys': child2_keys, 'cost': cost2}])
                
                if cost1 < best_of_current_gen_cost: best_of_current_gen_cost = cost1
                if cost2 < best_of_current_gen_cost: best_of_current_gen_cost = cost2

            # Aplica busca local no melhor indivíduo da nova população
            if new_population_data:
                new_population_data.sort(key=lambda p: p['cost'])
                best_new_individual = new_population_data[0]
                
                improved_keys = self.RVND(keys=best_new_individual['keys'], pool=pool, metaheuristic_name=metaheuristic_name) # Usando RVND padronizado
                improved_cost = self.env.cost(self.env.decoder(improved_keys))
                
                if improved_cost < best_new_individual['cost']:
                    best_new_individual['keys'] = improved_keys
                    best_new_individual['cost'] = improved_cost
                    if improved_cost < best_of_current_gen_cost:
                        best_of_current_gen_cost = improved_cost
            
            # Substituição da população com elitismo
            population.sort(key=lambda p: p['cost'])
            if new_population_data and population[0]['cost'] < new_population_data[0]['cost']:
                new_population_data[-1] = population[0] # O melhor antigo sobrevive
            
            population = new_population_data
            
            # Atualiza a melhor solução global
            current_best_gen_individual = min(population, key=lambda p: p['cost'])
            if current_best_gen_individual['cost'] < best_fitness_overall:
                best_fitness_overall = current_best_gen_individual['cost']
                best_keys_overall = current_best_gen_individual['keys']
                improvement_flag = 1
                pool.insert((best_fitness_overall, list(best_keys_overall)), metaheuristic_name, tag)
                # print(f"GA {tag} - Geração {num_generations}: Nova melhor solução encontrada: {best_fitness_overall}")

            if self.stop_condition(best_fitness_overall, metaheuristic_name, tag, pool = pool):
                return [], best_keys_overall, best_fitness_overall

            # --- ATUALIZAÇÃO E FEEDBACK PARA O Q-LEARNING ---
            if q_manager:
                if improvement_flag:
                    reward = 1.0
                else:
                    reward = (best_fitness_overall - best_of_current_gen_cost) / best_fitness_overall if best_fitness_overall > 0 else 0
                
                q_manager.update_q_value(reward, time.time() - start_time)
            # ----------------------------------------------------
        
        final_cost_solution = self.env.decoder(best_keys_overall)
        final_cost_value = self.env.cost(final_cost_solution)
        
        #if q_manager:
          #  q_manager.save_final_policy_report(instance_name=self.env.instance_name)
        return [], best_keys_overall, final_cost_value

    def stop_condition(self, best_cost, metaheuristic_name, tag, pool = None):
        if time.time() - self.start_time > self.max_time:
            if self.print_best and tag != -1:
                print(f"{metaheuristic_name}: ENCERRADO", flush=True)
            return True
        
        
        if pool is not None and pool.best_pair[0] == self.env.dict_best[self.env.instance_name]:
            
            print(f"Melhor solução já encontrada: {pool.best_pair[0]}")
            
            return True


        if self.env.dict_best is not None:
            
            if best_cost == self.env.dict_best[self.env.instance_name]:
                
                if self.print_best and tag != -1:
                    print(f"Metaheurística {metaheuristic_name} encontrou a melhor solução: {best_cost}")
                return True
        
            

        
        return False
        
    def solve(self, time_total,brkga=0, ms=0, sa=0, vns=0, ils=0,lns=0,pso=0,ga=0, restart=1, runs = 1):
        solutions = []
        times = []
        costs = []
        for i in range(runs):
            time_act = time.time()
            data_str = datetime.datetime.fromtimestamp(time_act).strftime('%d/%m/%Y %H:%M:%S')
            # print(data_str)
            print(f'Instancia: {self.env.instance_name}, Execução: {i+1}/{runs}, {data_str}', flush=True)
            limit_time = time_total * restart
            
            restarts = int(1/restart)
          
            
            self.max_time = limit_time
            
            manager = Manager()
            shared = manager.Namespace()
            
            shared.best_pair = manager.list([float('inf'), None, None])
            shared.best_pool = manager.list()
            
            shared.pool = SolutionPool(20, shared.best_pool, shared.best_pair, lock=manager.Lock(), print=self.print_best, Best=self.env.dict_best[self.env.instance_name], env=self.env)
            for i in range(20):
                keys = self.random_keys()
                cost = self.env.cost(self.env.decoder(keys))
                shared.pool.insert((cost, list(keys)), 'pool', -1)
            
            lock = manager.Lock()
            processes = []
            
            for k in range(restarts):
                # print(f'RESTART {k + 1}', flush=True)
                
                tag = 0
                self.start_time = time.time()
                if self.stop_condition(shared.pool.best_pair[0], 'RKO', tag, pool=shared.pool):
                    break
                
                shared.pool.pool = manager.list()
                for _ in range(brkga):
                    p = Process(
                        target=_brkga_worker,
                        args=(self.env, shared.pool,tag, self.print_best, self.save_directory)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()
                for _ in range(ms):
                    p = Process(
                        target=_MS_worker,
                        args=(self.env, shared.pool,tag, self.print_best, self.save_directory)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()
                for _ in range(sa):
                    p = Process(
                        target=_SA_worker,
                        args=(self.env,  shared.pool,tag, self.print_best, self.save_directory)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()
                for _ in range(vns):
                    p = Process(
                        target=_VNS_worker,
                        args=(self.env, self.max_time, shared.pool,tag, self.print_best, self.save_directory)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()
                for _ in range(ils):
                    p = Process(
                        target=_ILS_worker,
                        args=(self.env, self.max_time, shared.pool,tag, self.print_best, self.save_directory)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()
                    
                for _ in range(lns):
                    p = Process(
                        target=_LNS_worker,
                        args=(self.env, self.max_time, shared.pool,tag, self.print_best, self.save_directory)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()
                    
                for _ in range(pso):
                    p = Process(
                        target=_PSO_worker,
                        args=(self.env, shared.pool , tag, self.print_best, self.save_directory)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()
                    
                for _ in range(ga):
                    p = Process(
                        target=_GA_worker,
                        args=(self.env, shared.pool , tag, self.print_best, self.save_directory)
                    )
                    tag += 1
                    processes.append(p)
                    p.start()

                for p in processes:
                    p.join(timeout=self.max_time)
                    
                for p in processes:
                    if p.is_alive():
                        # print(f"Processo {p.pid} estourou o tempo e será terminado.", flush=True)
                        p.terminate() # Força o encerramento do processo
                        
                # print(f'RESTART {k + 1} END - COST {shared.pool.best_pair[0]}', flush=True)

            cost = shared.pool.best_pair[0]
            solution = shared.pool.best_pair[1]     
            time_elapsed = shared.pool.best_pair[2]

            solutions.append(solution)
            costs.append(round(cost,2))
            times.append(round(-1 * time_elapsed,2))
            # print(f'{time_total}, {self.env.instance_name}, {round(sum(costs)/len(costs),2)}, {costs}, {round(sum(times)/len(times),2)}, {times}')
            
        directory = os.path.dirname(self.save_directory)

        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.save_directory, 'a', newline='') as f:
            f.write(f'{time_total}, {self.env.instance_name}, {round(sum(costs)/len(costs),2)}, {costs}, {round(sum(times)/len(times),2)}, {times}\n')
        

        return cost, solution, time_elapsed
        
def _brkga_worker(env, pool,tag, print_best, save_directory):
    runner = RKO(env, print_best, save_directory)
    _, local_keys, local_best = runner.BRKGA(tag, pool)
    
def _MS_worker(env, pool,tag, print_best, save_directory):
    runner = RKO(env, print_best, save_directory)
    _, local_keys, local_best = runner.MultiStart(tag, pool)
    
def _GRASP_worker(env, pool,tag, print_best, save_directory):
    runner = RKO(env, print_best, save_directory)
    _, local_keys, local_best = runner.MultiStart(pool)
    
def _VNS_worker(env, limit_time, pool, tag, print_best, save_directory):
    runner = RKO(env, print_best, save_directory)
    _, local_keys, local_best = runner.VNS(limit_time,tag, pool)
    
def _ILS_worker(env, limit_time,  pool, tag, print_best, save_directory):
    runner = RKO(env, print_best, save_directory)
    _, local_keys, local_best = runner.ILS(limit_time,tag, pool)
    
def _SA_worker(env, pool,tag, print_best, save_directory):
    runner = RKO(env, print_best, save_directory)
    _, local_keys, local_best = runner.SimulatedAnnealing(tag = tag, pool = pool)
    
def _LNS_worker(env, limit_time, pool, tag, print_best, save_directory):
    runner = RKO(env, print_best, save_directory)
    _, local_keys, local_best = runner.LNS(limit_time=limit_time, tag = tag, pool = pool)
    
def _PSO_worker(env, pool, tag, print_best, save_directory):
    runner = RKO(env, print_best, save_directory)
    _, local_keys, local_best = runner.PSO(tag = tag, pool = pool)
    
def _GA_worker(env, pool, tag, print_best, save_directory):
    runner = RKO(env, print_best, save_directory)
    _, local_keys, local_best = runner.GA(tag = tag, pool = pool)
    

import random
import itertools
import math
import pandas as pd
import os

class QLearningManager:
    """
    Gerencia o controle de parâmetros online para meta-heurísticas do RKO
    usando Q-Learning. Inclui funcionalidade para salvar um relatório de convergência.
    """

    def __init__(self, parameters_config, max_time, metaheuristic_name, save_report=True, epsilon_min=0.1, df=0.8):
        """
        Inicializa o gerenciador de Q-Learning.

        Args:
            parameters_config (dict): Dicionário com os parâmetros e seus possíveis valores.
            max_time (int): Tempo máximo de execução da meta-heurística.
            metaheuristic_name (str): Nome da meta-heurística (ex: "ILS", "GA").
            save_report (bool): Se True, salva um relatório de convergência ao final.
            epsilon_min (float): Valor mínimo para epsilon.
            df (float): Fator de desconto.
        """
        self.param_keys = list(parameters_config.keys())
        self.max_time = max_time if max_time > 0 else 1.0
        self.epsilon_min = epsilon_min
        self.df = df
        
        # NOVOS ATRIBUTOS
        self.metaheuristic_name = metaheuristic_name
        self.save_report = save_report

        self._create_states_and_actions(parameters_config)

        self.current_state_idx = random.randint(0, self.num_states - 1)
        self.last_action_taken = None
        self.epsilon_max = 1.0
        self.restart_epsilon_period = self.max_time * 0.1
        self.next_restart_time = self.restart_epsilon_period

    def _create_states_and_actions(self, parameters_config):
        param_values = list(parameters_config.values())
        all_combinations = list(itertools.product(*param_values))
        self.num_states = len(all_combinations)

        self.states = []
        for i, combo in enumerate(all_combinations):
            self.states.append({'id': i, 'params': dict(zip(self.param_keys, combo))})

        self.q_table = {}
        for i in range(self.num_states):
            self.q_table[i] = {}
            for j in range(self.num_states):
                hamming_dist = sum(1 for k in self.param_keys if self.states[i]['params'][k] != self.states[j]['params'][k])
                if hamming_dist <= 1:
                    self.q_table[i][j] = random.uniform(0.01, 0.05)
        
        for i in range(self.num_states):
            self._update_max_q(i)

    def _update_max_q(self, state_idx):
        q_values_for_state = self.q_table.get(state_idx, {})
        if q_values_for_state:
            self.states[state_idx]['max_q'] = max(q_values_for_state.values())
        else:
            self.states[state_idx]['max_q'] = 0.0

    def get_current_parameters(self):
        return self.states[self.current_state_idx]['params']

    def select_action(self, current_time):
        if self.restart_epsilon_period > 0 and current_time > self.next_restart_time:
            self.next_restart_time += self.restart_epsilon_period
            self.epsilon_max = max(self.epsilon_min, self.epsilon_max - 0.1)

        time_in_period = current_time % self.restart_epsilon_period if self.restart_epsilon_period > 0 else 0
        epsilon = self.epsilon_min + 0.5 * (self.epsilon_max - self.epsilon_min) * \
                  (1 + math.cos(time_in_period / self.restart_epsilon_period * math.pi))

        possible_actions = list(self.q_table[self.current_state_idx].keys())
        if not possible_actions: return self.get_current_parameters()
        
        if random.random() > epsilon:
            q_values = self.q_table[self.current_state_idx]
            action = max(q_values, key=q_values.get)
        else:
            action = random.choice(possible_actions)

        self.last_action_taken = action
        return self.states[action]['params']

    def update_q_value(self, reward, current_time):
        lf = max(0.1, 1.0 - (0.9 * current_time / self.max_time))
        
        state_idx = self.current_state_idx
        action_idx = self.last_action_taken
        if action_idx is None: return

        next_state_idx = action_idx
        
        old_q_value = self.q_table[state_idx][action_idx]
        future_best_q = self.states[next_state_idx]['max_q']
        
        new_q_value = old_q_value + lf * (reward + self.df * future_best_q - old_q_value)
        self.q_table[state_idx][action_idx] = new_q_value
        
        self._update_max_q(state_idx)
        
        self.current_state_idx = next_state_idx
    
    # --- NOVO MÉTODO PARA SALVAR O RELATÓRIO FINAL ---
    def save_final_policy_report(self, instance_name, directory='C:\\Users\\felip\\Documents\\GitHub\\RKO\\Python'):
        """
        Salva um relatório final em CSV mostrando a política aprendida (Q-Table final)
        e o melhor parâmetro para cada estado.
        """
        if not self.save_report:
            return

        if not os.path.exists(directory):
            os.makedirs(directory)
            
        filepath = os.path.join(directory, f"policy_report_{self.metaheuristic_name}_{instance_name}.csv")
        
        report_data = []
        for state_idx, actions in self.q_table.items():
            state_params = self.states[state_idx]['params']
            
            # Encontra a melhor ação (parâmetro) para este estado
            if actions:
                best_action_for_state = max(actions, key=actions.get)
                best_params_for_state = self.states[best_action_for_state]['params']
            else:
                best_params_for_state = {}

            # Adiciona os dados ao relatório
            entry = {f'state_{k}': v for k, v in state_params.items()}
            entry['state_id'] = state_idx
            entry['best_next_state_id'] = best_action_for_state
            entry.update({f'best_param_{k}': v for k, v in best_params_for_state.items()})
            entry.update({f'Q(s,{a})': round(q, 4) for a, q in actions.items()})
            report_data.append(entry)

        try:
            df = pd.DataFrame(report_data).sort_values(by='state_id').set_index('state_id')
            df.to_csv(filepath)
            print(f"Relatório de convergência do Q-Learning salvo em: {filepath}")
        except Exception as e:
            print(f"Erro ao salvar relatório de convergência em {filepath}: {e}")
        
      