import os
import numpy as np
import time
import random
import copy
import math
import datetime
import bisect
from multiprocessing import Manager, Process, cpu_count



class RKO():
    def __init__(self, env):
        self.env = env
        self.__MAX_KEYS = self.env.tam_solution
        
    
    def random_keys(self):
        return np.random.random(self.__MAX_KEYS)
    def inserir_em_elite(self, elite, fitness_elite, key, fitness, tam_elite, modo='maiores'):
        if modo == 'maiores':
            # Lista em ordem decrescente (maior no começo, menor no fim)
            comparar = lambda novo, atual: novo > atual
        elif modo == 'menores':
            # Lista em ordem crescente (menor no começo, maior no fim)
            comparar = lambda novo, atual: novo < atual
        else:
            raise ValueError("modo deve ser 'maiores' ou 'menores'")

        i = 0
        for value in fitness_elite:
            if comparar(fitness, value):
                break
            i += 1

        # Se ainda tem espaço, só insere na posição correta
        if len(elite) < tam_elite:
            elite.insert(i, key)
            fitness_elite.insert(i, fitness)
        else:
            # Se o novo fitness é melhor que o último (pior da elite), substitui
            if comparar(fitness, fitness_elite[-1]):
                elite.pop(-1)
                fitness_elite.pop(-1)
                elite.insert(i, key)
                fitness_elite.insert(i, fitness)

        if modo == 'maiores':
            elite.sort(key=lambda x: fitness_elite[elite.index(x)], reverse=True)
            fitness_elite.sort(reverse=True)
        else:
            elite.sort(key=lambda x: fitness_elite[elite.index(x)])
            fitness_elite.sort()
        return elite, fitness_elite


    def vizinhos(self, keys, min = 0.1, max = 0.25):
   
        new_keys = keys.copy()
        N = len(new_keys)

        # número de posições a perturbar
        min_p = int(min * N)
        max_p = int(max * N)
        n_perturb = random.randint(min_p, max_p)

        for _ in range(n_perturb):
            i = random.randrange(N)
            new_keys[i] = random.random()

        return new_keys
    def pertubacao(self, keys): #Realiza perturbações nas chaves, gerando vizinhos, soluções proximas/parecidas, para a solução atual.
        new_keys = copy.deepcopy(keys)
        prob = random.random()
        if prob < 0.5:
            alteracoes = math.ceil(self.__MAX_KEYS * 0.1) # altera 10% das chaves
            for _ in range(int(alteracoes)):
                idx1, idx2 = random.sample(range(self.__MAX_KEYS), 2)  # Escolhe dois índices distintos aleatórios
                new_keys[idx1], new_keys[idx2] = new_keys[idx2], new_keys[idx1]  # Realiza o swap


        elif prob < 0.7:
            alteracoes = math.ceil(self.__MAX_KEYS * 0.25) # altera 25% das chaves
            for _ in range(int(alteracoes)):
                idx1, idx2 = random.sample(range(self.__MAX_KEYS), 2)  # Escolhe dois índices distintos aleatórios
                new_keys[idx1], new_keys[idx2] = new_keys[idx2], new_keys[idx1]  # Realiza o swap


        elif  prob < 0.9:     
            for i, key in enumerate(new_keys):
                if random.random() > 0.5:
                    new_keys[i] = key + random.uniform(-0.5*key, 0.5*(1-key)) # aumenta ou diminui metade das chaves, mas com valores baixos
            
        else:
            
            for i, key in enumerate(new_keys):
                if random.random() > 0.7: # gera aleatouramente novos valores para 30% das chaves
                    new_keys[i] = random.random()
                    
        return new_keys
    
    def LocSearch(self, keys, x): # Busca local, recebe uma chave/solução e busca ao redor dela outras soluções, para ver se existe algum solução melhor
        iter = 0
        best_keys = keys
        solution = self.env.decoder(keys)
        best_cost = self.env.cost(solution)
        while iter < x:
            new_keys = self.vizinhos(best_keys)
            new_solution = self.env.decoder(new_keys)           
            new_cost = self.env.cost(new_solution)
            # print(f"x {iter}, Custo: {new_cost}")
            
            if new_cost < best_cost: 
                best_keys = new_keys
                best_cost = new_cost
                iter = 0
            else:
                iter += 1
        
        return best_keys
    
    def MultiStart(self,max_iter,x, tempo, tag,  pool,lock,best): # Multi Start, gera várias soluções aleatórias e aplica a busca local em cada uma delas, retornando a melhor solução encontrada
        best_keys = None
        best_cost = float('inf')
        best_ini_cost = float('inf')
        start_time = time.time()
        iter = 0
        random_keys = self.random_keys()
        ini_solution = self.env.decoder(random_keys)
        ini_cost = self.env.cost(ini_solution)
        with lock:
            entry = (ini_cost, random_keys)
            
            bisect.insort(pool, entry)       
            if len(pool) > 10:
                pool.pop() 

        while time.time() - start_time < tempo:
            
            
            iter += 1
            k = 0
            while True:
                k+=1
                # print(pool)
                with lock:
                    if len(pool) > 0:
                        # print("POOL")
                        break
            random_keys = random.sample(list(pool), 1)[0][1]
            ini_solution = self.env.decoder(random_keys)
            ini_cost = self.env.cost(ini_solution)
            if ini_cost < best_ini_cost:
                best_ini_cost = ini_cost
            
            keys = self.LocSearch(random_keys,x)

            solution = self.env.decoder(keys)
            cost = self.env.cost(solution)
            with lock:
                entry = (cost, keys)
                
                bisect.insort(pool, entry)       
                if len(pool) > 20:
                    pool.pop()

            # with lock:
            #     if cost < best[0]:
            #         best[0] = cost
            #         best[1] = keys
            #         print(f"\n MS {tag} NOVO MELHOR: {cost} BEST:{self.env.dict_best[self.env.instance_name]} - GAP: {round((cost - self.env.dict_best[self.env.instance_name]) / self.env.dict_best[self.env.instance_name] * 100, 2)}%") 
            
            print(f"\rtempo = {round(time.time() - start_time,2)}", end="")
            
            if cost < best_cost:
                best_cost = cost
                best_keys = keys
                
                print(f"\n MS {tag} NOVO MELHOR: {cost} BEST:{self.env.dict_best[self.env.instance_name]} - GAP: {round((cost - self.env.dict_best[self.env.instance_name]) / self.env.dict_best[self.env.instance_name] * 100, 2)}%") 
                if best_cost == self.env.dict_best[self.env.instance_name]:
                        # print(f" \n{tag} MELHOR: {fitness} - BEST:{self.env.dict_best[self.env.instance_name]} - GAP: {round((fitness - self.env.dict_best[self.env.instance_name]) / self.env.dict_best[self.env.instance_name] * 100, 2)}% -  Tempo: {round(time.time() - start_time,2)}s")

                        
                        solution = self.env.decoder(best_keys)
                        cost = self.env.cost(solution, True)  
                        
                            
                            
                        return self.env.bins_usados, best_keys, best_cost
        solution = self.env.decoder(best_keys)
        cost = self.env.cost(solution, True)
        # print(f"Melhor Custo: {best_cost}, Melhor Custo Inicial: {best_ini_cost}, tempo = {round(time.time() - start_time,2)}")  

        return self.env.bins_usados,best_keys, best_cost
        

    def SimulatedAnnealing(self,SAmax,Temperatura,alpha, tempo_max):
        keys = self.random_keys()
        best_keys = keys
        
        solution = self.env.decoder(keys)
        cost = self.env.cost(solution)
        best_cost = cost
        
        start_time = time.time()
        
        T = Temperatura
        iter_total = 0
        iter = 0
        while time.time() - start_time < tempo_max:
            
            while iter < SAmax:
                print(f"\rTempo: {round(time.time() - start_time,2):.1f}s  -  Temperatura {T:.1f}  -  ", end="")
                iter+= 1
                iter_total += 1
                                
                new_keys = self.vizinhos(keys)
                                        
                new_solution = self.env.decoder(new_keys)
                new_cost = self.env.cost(new_solution)
                
                
                delta = new_cost - cost
                
                if new_cost < best_cost:
                    best_keys = new_keys
                    best_cost = new_cost
                    
                    print(f" NOVO MELHOR: {best_cost}")
                    
                               
                if delta <= 0:
                    keys = new_keys
                    cost = new_cost
                else:
                    if random.random() < math.exp(-delta/T):
                        keys = new_keys
                        cost = new_cost
                        
            iter = 0
            T = T * alpha
            
        print(f"Melhor Custo: {best_cost}, tempo = {round(time.time() - start_time,2)}")
        solution = self.env.decoder(best_keys)
        cost = self.env.cost(solution, True)  
        
            
            
        return self.env.bins_usados, best_keys, best_cost
        
        
    def GRASP(self,max_iter,x, tempo = None): # GRASP, gera várias soluções semi gulosas e aplica a busca local em cada uma delas, retornando a melhor solução encontrada
        best_keys = None
        best_cost = float('inf')
        best_ini_cost = float('inf')
        start_time = time.time()
        iter = 0
        while iter < max_iter or time.time() - start_time < tempo:
            iter += 1
            random_keys = self.env.greedy_solution(10)
            ini_solution = self.env.decoder(random_keys)
            ini_cost = self.env.cost(ini_solution)
            if ini_cost < best_ini_cost:
                best_ini_cost = ini_cost
            
            keys = self.LocSearch(random_keys,x)

            solution = self.env.decoder(keys)
            cost = self.env.cost(solution)
            
            print(f"Iteração {iter}, Custo Inicial: {ini_cost}, Custo Final: {cost}, tempo = {time.time() - start_time}")
            
            if cost < best_cost:
                best_cost = cost
                best_keys = keys
        
        solution = self.env.decoder(best_keys)
        cost = self.env.cost(solution, True)
        print(f"Melhor Custo: {best_cost}, Melhor Custo Inicial: {best_ini_cost}, tempo = {time.time() - start_time}")  

        return best_keys, best_cost
    
    def VNS(self,limit_time,x, tag,  pool,lock,best):
        k = [[0.01, 0.2], [0.2, 0.4], [0.4, 0.6], [0.6, 0.8], [0.8, 0.99]]
        idx_k = 0
        start_time = time.time()
        bests_S = []
        if self.env.greedy:
            sol = self.env.ssp3()
            s = sol[1]
            bests_S.append(s)
            
            best_cost = sol[0]
            best_keys = s
            
            sol = self.env.greedy_solution_capacity(0)
            s = sol[1]
            bests_S.append(s)

        
            if best_cost > sol[0]:
                best_cost = sol[0]
                best_keys = s
            
            sol = self.env.greedy_solution_cost(0)
            s = sol[1]
            bests_S.append(s)
            
            if best_cost > sol[0]:
                best_cost = sol[0]
                best_keys = s
        else:
            keys = self.random_keys()
            best_keys = keys
            best_cost = self.env.cost(self.env.decoder(keys))
            bests_S.append(keys)
        
        
        
 
        
        print(f"VNS {tag} Melhor Custo: {best_cost} - tempo = {time.time() - start_time}")
        if self.env.dict_best is not None:
            if best_cost == self.env.dict_best[self.env.instance_name]:
                        print(f"VNS {tag} MELHOR: {best_cost} - BEST:{self.env.dict_best[self.env.instance_name]} - GAP: {round((best_cost - self.env.dict_best[self.env.instance_name]) / self.env.dict_best[self.env.instance_name] * 100, 2)}% tempo = {time.time() - start_time}")                        
                        print(f"VNS {tag} ENCERRADO")
                        solution = self.env.decoder(best_keys)
                        cost = self.env.cost(solution, True)  
                            
                                
                                
                        return [], best_keys, best_cost    
        
        while time.time() - start_time < limit_time:
            print(f"\rtempo = {round(time.time() - start_time,2)} ", end="")

            if idx_k >= len(k) + 1:
                idx_k = 0
                
            if random.random() < 0.1:
                    s1 = random.sample(list(pool), 1)[0][1]
            
            else:

                if idx_k == len(k):
                    s1 = self.pertubacao(bests_S[random.randint(0, len(bests_S)-1)])
                    # print("Pertubação")
                else:  
                    s1 = self.vizinhos(bests_S[random.randint(0, len(bests_S)-1)], k[idx_k][0], k[idx_k][1])
                    
            # print(s1)
            s2 = self.LocSearch(s1,x)
            
            sol2 = self.env.decoder(s2)
            cost = self.env.cost(sol2)
            # print(tag, cost,best_cost)
            
            if cost <= best_cost:
                best_cost = cost
                best_keys = s2
                
                bests_S.append(s2)
                # print(f"VNS {tag} Melhor Custo: {best_cost} - BEST:{self.env.dict_best[self.env.instance_name]} - GAP: {round((best_cost - self.env.dict_best[self.env.instance_name]) / self.env.dict_best[self.env.instance_name] * 100, 2)}% tempo = {time.time() - start_time}")
                with lock:
                    entry = (best_cost, list(best_keys))
                       
                    bisect.insort(pool, entry)  
                    
                    if len(pool) > 20:
                        pool.pop()
                        
                    if best_cost < best[0]:
                        best[0] = best_cost
                        best[1] = list(best_keys)
                        print(f"VNS {tag} NOVO MELHOR: {best_cost} - tempo = {time.time() - start_time}")
                        
                
                if self.env.dict_best is not None:
                    if best_cost == self.env.dict_best[self.env.instance_name]:
                        print(f"VNS {tag} MELHOR: {best_cost} - BEST:{self.env.dict_best[self.env.instance_name]} - GAP: {round((best_cost - self.env.dict_best[self.env.instance_name]) / self.env.dict_best[self.env.instance_name] * 100, 2)}% tempo = {time.time() - start_time}")                        
                        print(f"VNS {tag} ENCERRADO")
                        solution = self.env.decoder(best_keys)
                        cost = self.env.cost(solution, True)  
                            
                                
                                
                        return [], best_keys, best_cost        
            else:
                idx_k += 1

        solution = self.env.decoder(best_keys)
        cost = self.env.cost(solution)  
        
            
        print(f"VNS {tag} ENCERRADO")
        return [], best_keys, best_cost
            
    
    def ILS(self,limit_time,x, tag,  pool,lock,best):

        start_time = time.time()
        bests_S = []
        if self.env.greedy:
            sol = self.env.ssp3()
            s = sol[1]
            bests_S.append(s)
            
            best_cost = sol[0]
            best_keys = s
            
            sol = self.env.greedy_solution_capacity(0)
            s = sol[1]
            bests_S.append(s)

        
            if best_cost > sol[0]:
                best_cost = sol[0]
                best_keys = s
            
            sol = self.env.greedy_solution_cost(0)
            s = sol[1]
            bests_S.append(s)
            
            if best_cost > sol[0]:
                best_cost = sol[0]
                best_keys = s
        else:
            keys = self.random_keys()
            best_keys = keys
            best_cost = self.env.cost(self.env.decoder(keys))
            bests_S.append(keys)
        
        
        
 
        
        
        print(f"ILS {tag} Melhor Custo: {best_cost} - tempo = {time.time() - start_time}")
        if self.env.dict_best is not None:
            if best_cost == self.env.dict_best[self.env.instance_name]:
                        print(f"VNS {tag} MELHOR: {best_cost} - BEST:{self.env.dict_best[self.env.instance_name]} - GAP: {round((best_cost - self.env.dict_best[self.env.instance_name]) / self.env.dict_best[self.env.instance_name] * 100, 2)}% tempo = {time.time() - start_time}")                        
                        print(f"VNS {tag} ENCERRADO")
                        solution = self.env.decoder(best_keys)
                        cost = self.env.cost(solution, True)  
                            
                                
                                
                        return [], best_keys, best_cost    
        while time.time() - start_time < limit_time:
            print(f"\rtempo = {round(time.time() - start_time,2)} ", end="")


                
            if random.random() < 0.1:
                    s1 = random.sample(list(pool), 1)[0][1]
            
            else:
                if random.random() < 0.2:
                    s1 = self.pertubacao(bests_S[random.randint(0, len(bests_S)-1)])
                
                else:
                    min = random.random()          
                    max = random.uniform(min, 1.0) 
                    s1 = self.vizinhos(bests_S[random.randint(0, len(bests_S)-1)], min, max)
                    
            s2 = self.LocSearch(s1,x)
            
            sol2 = self.env.decoder(s2)
            cost = self.env.cost(sol2)
            
            
            if cost <= best_cost:
                best_cost = cost
                best_keys = s2
                
                bests_S.append(s2)
                # print(f"ILS {tag} Melhor Custo: {best_cost} - BEST:{self.env.dict_best[self.env.instance_name]} - GAP: {round((best_cost - self.env.dict_best[self.env.instance_name]) / self.env.dict_best[self.env.instance_name] * 100, 2)}% tempo = {time.time() - start_time}")
                with lock:
                    entry = (best_cost, list(best_keys))
                       
                    bisect.insort(pool, entry)  
                    
                    if len(pool) > 20:
                        pool.pop()
                    if best_cost < best[0]:
                        best[0] = best_cost
                        best[1] = list(best_keys)
                        print(f"ILS {tag} NOVO MELHOR: {best_cost} - tempo = {time.time() - start_time}")

                if self.env.dict_best is not None:
                    if best_cost == self.env.dict_best[self.env.instance_name]:
                        print(f"ILS {tag} MELHOR: {best_cost} - BEST:{self.env.dict_best[self.env.instance_name]} - GAP: {round((best_cost - self.env.dict_best[self.env.instance_name]) / self.env.dict_best[self.env.instance_name] * 100, 2)}% tempo = {time.time() - start_time}")
                        print(f"ILS {tag} ENCERRADO")
                            
                        solution = self.env.decoder(best_keys)
                        cost = self.env.cost(solution, True)  
                            
                                
                                
                        return [], best_keys, best_cost

        solution = self.env.decoder(best_keys)
        cost = self.env.cost(solution)  
        
            
        print(f"ILS {tag} ENCERRADO")
        return [], best_keys, best_cost
    

        
    def BRKGA(self, pop_size, elite_pop, chance_elite, limit_time,tag,pool,lock,best):
        generation = 0
        tam_elite = int(pop_size * elite_pop)
        metade = False
        
        
        if self.env.greedy:
            population = [self.random_keys() for _ in range(pop_size - 3)]
            cost,keys = self.env.ssp3()
            population.append(keys)
            cost,keys = self.env.greedy_solution_capacity(0)
            population.append(keys)
            cost,keys = self.env.greedy_solution_cost(0)
            population.append(keys)
        else:
            population = [self.random_keys() for _ in range(pop_size)]
        best_keys = None
        best_fitness = float('inf')
        
        start_time = time.time()
        
        pop = 0
        qnt = 0
        while time.time() - start_time < limit_time:
            if metade == False:
                metade = True
                if time.time() - start_time > limit_time/2:
                    population = [self.random_keys() for _ in range(pop_size)]
                    # with lock:
                    #     pool = []
            pop += 1
            generation += 1
            
            elite = []
            elite_sol = []
            fitness_elite = []
            
            fitness_values = []

                  
            
            
            for key in population:
                
                qnt += 1
                
                sol = self.env.decoder(key)
                fitness = self.env.cost(sol)
                
                fitness_values.append(fitness)
                

                
                if  not sol in elite_sol:
                    elite.append(key)
                    elite_sol.append(sol)
                    fitness_elite.append(fitness)
                
                
                


                
                if fitness < best_fitness:
                    pop = 0
                    best_keys = key
                    best_fitness = fitness
                    with lock:
                        entry = (best_fitness, list(best_keys))
                        # print(entry)
                        bisect.insort(pool, entry)  
                        # print(pool.type)     
                        if len(pool) > 20:
                            pool.pop()
                        if best_fitness < best[0]:
                            best[0] = best_fitness
                            best[1] = list(best_keys)
                            print(f"BRKGA {tag} NOVO MELHOR: {best_fitness} -  Tempo: {round(time.time() - start_time,2)}s")
          
                        
                    # print(f"BRKGA {tag} Melhor Custo: {fitness} - BEST:{self.env.dict_best[self.env.instance_name]} - GAP: {round((fitness - self.env.dict_best[self.env.instance_name]) / self.env.dict_best[self.env.instance_name] * 100, 2)}% -  Tempo: {round(time.time() - start_time,2)}s")
          
                    if self.env.dict_best is not None:
                        if fitness == self.env.dict_best[self.env.instance_name]:
                            print(f" \n{tag} MELHOR: {fitness} - BEST:{self.env.dict_best[self.env.instance_name]} - GAP: {round((fitness - self.env.dict_best[self.env.instance_name]) / self.env.dict_best[self.env.instance_name] * 100, 2)}% -  Tempo: {round(time.time() - start_time,2)}s")
                            print(f"BRKGA {tag} ENCERRADO")
                            
                            solution = self.env.decoder(best_keys)
                            cost = self.env.cost(solution, True)  
                            
                                
                                
                            return [], best_keys, best_fitness
        
            ordenado = sorted(zip(elite, fitness_elite), key=lambda x: x[1]) 
            elite, fitness_elite = zip(*ordenado)  

            elite = list(elite)
            fitness_elite = list(fitness_elite)
    
            elite = elite[:tam_elite]
            fitness_elite = fitness_elite[:tam_elite]
            
            
            # print(fitness_elite)

            best_local_fitness = fitness_elite[0]
            best_local_keys = elite[0]


            # with lock:
            #     if fitness_elite[0] < best[0]:
            #         best[0] = fitness_elite[0]
            #         best[1] = elite[0]
            #         print(f" \nBRKGA {tag} NOVO MELHOR: {fitness} - BEST:{self.env.dict_best[self.env.instance_name]} - GAP: {round((fitness - self.env.dict_best[self.env.instance_name]) / self.env.dict_best[self.env.instance_name] * 100, 2)}%")


                        
                        
                # print(pool)
                    
            new_population = [elite[0]]
  

            while len(new_population) < pop_size:
                
                if random.random() < 1:
                    parent1 = random.sample(population, 1)[0]
                else:
                    parent1 = random.sample(list(pool), 1)[0][1]
                    
                if random.random() < 1:
                    parent2 = random.sample(elite, 1)[0]
                else:
                    parent2 = random.sample(list(pool), 1)[0][1]
                    
                
               
                child1 = np.zeros(self.__MAX_KEYS)
                child2 = np.zeros(self.__MAX_KEYS)
                if random.random() < 0.95:
                    for i in range(len(child1)):
                        if random.random() < chance_elite:
                            child1[i] = parent2[i]
                            child2[i] = parent1[i]
                            
                        else:
                            child1[i] = parent1[i]
                            child2[i] = parent2[i]
                else:
                    child1 = parent1
                    child2 = parent2
                
                
                for idx in range(len(child1)):
                    if random.random() < 0.05:
                        
                        child1[idx] = random.random()
                    if random.random() < 0.05:
                        child2[idx] = random.random()                
                new_population.append(child1)
                new_population.append(child2)
            
   
                
     
            population = new_population
            population.pop(0)
            key_pool = random.sample(list(pool), 1)[0][1]
            population.append(key_pool)
            print(f"\rtempo = {round(time.time() - start_time,2)} ", end="")

            # print(f"\r{tag} Geração {generation + 1}: Melhor fitness = {best_fitness}  -  Tempo: {round(time.time() - start_time,2)}s")
            
            
        solution = self.env.decoder(best_keys)
        cost = self.env.cost(solution)  
        
            
        # print(qnt)
        print(f"BRKGA {tag} ENCERRADO")    
        return [], best_keys, best_fitness

    def solve(self, pop_size, elite_pop, chance_elite, limit_time, n_workers=None,brkga=1, ms=1, sa=1, vns=1, ils=1):
        """Roda múltiplas instâncias de BRKGA em paralelo e compartilha apenas best_solution."""
        if n_workers is None:
            n_workers = cpu_count()



        manager = Manager()
        shared = manager.Namespace()
        shared.best_keys = None
        shared.best_fitness = float('inf')
        shared.best_pair = manager.list([float('inf'), None])
        shared.best_pool = manager.list() 
        lock = manager.Lock()
        processes = []
        tag = 0
        for _ in range(brkga):
            p = Process(
                target=_brkga_worker,
                args=(self.env, pop_size, elite_pop, chance_elite, limit_time, shared, lock,tag)
            )
            tag += 1
            processes.append(p)
            p.start()
        for _ in range(ms):
            p = Process(
                target=_MS_worker,
                args=(self.env,10000,100,limit_time, shared, lock,tag)
            )
            tag += 1
            processes.append(p)
            p.start()
        for _ in range(sa):
            p = Process(
                target=_SA_worker,
                args=( limit_time, shared, lock,tag)
            )
            tag += 1
            processes.append(p)
            p.start()
        for _ in range(vns):
            p = Process(
                target=_VNS_worker,
                args=(self.env, limit_time,pop_size, shared, lock,tag)
            )
            tag += 1
            processes.append(p)
            p.start()
        for _ in range(ils):
            p = Process(
                target=_ILS_worker,
                args=(self.env, limit_time,pop_size, shared, lock,tag)
            )
            tag += 1
            processes.append(p)
            p.start()

        for p in processes:
            p.join()


        solution = self.env.decoder(shared.best_keys)
        
        cost = self.env.cost(solution)
        return cost, solution
        
def _brkga_worker(env, pop_size, elite_pop, chance_elite, limit_time, shared, lock,tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.BRKGA(pop_size, elite_pop, chance_elite, limit_time,tag,shared.best_pool,lock,shared.best_pair)
    
    with lock:
        if local_best < shared.best_fitness:
            shared.best_fitness = local_best
            shared.best_keys = local_keys

def _MS_worker(env, max_itr, x, limit_time, shared, lock,tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.MultiStart( max_itr,x,limit_time,tag,shared.best_pool,lock,shared.best_pair)
    
    with lock:
        if local_best < shared.best_fitness:
            shared.best_fitness = local_best
            shared.best_keys = local_keys
def _GRASP_worker(env, max_itr, x, limit_time, shared, lock,tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.MultiStart( max_itr,x,limit_time,tag,shared.best_pool,lock,shared.best_pair)
    
    with lock:
        if local_best < shared.best_fitness:
            shared.best_fitness = local_best
            shared.best_keys = local_keys
            
def _VNS_worker(env, limit_time, x, shared, lock,tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.VNS(limit_time,x,tag,shared.best_pool,lock,shared.best_pair)
    
    with lock:
        if local_best < shared.best_fitness:
            shared.best_fitness = local_best
            shared.best_keys = local_keys
def _ILS_worker(env, limit_time, x, shared, lock,tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.ILS(limit_time,x,tag,shared.best_pool,lock,shared.best_pair)
    
    with lock:
        if local_best < shared.best_fitness:
            shared.best_fitness = local_best
            shared.best_keys = local_keys

def _SA_worker(env, pop_size, elite_pop, chance_elite, limit_time, shared, lock,tag):
    runner = RKO(env)
    _, local_keys, local_best = runner.SimulatedAnnealing( limit_time,tag,shared.best_pool,lock)
    
    with lock:
        if local_best < shared.best_fitness:
            shared.best_fitness = local_best
            shared.best_keys = local_keys
      
