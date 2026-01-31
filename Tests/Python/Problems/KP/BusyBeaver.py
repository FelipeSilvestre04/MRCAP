import numpy as np
import time
import sys
import os
sys.path.append(os.path.abspath("C:\\Users\\felip\\Documents\\GitHub\\RKO\\Python"))
from RKO_v2 import RKO
import numpy as np
import math
import random
from collections import defaultdict

class BusyBeaverProblem:
    def __init__(self, num_states):
        """
        Inicializa o ambiente para o problema Busy Beaver.
        Args:
            num_states (int): O número de estados da Máquina de Turing.
        """
        self.num_states = num_states
        self.instance_name = f'BusyBeaver_{num_states}_states'

        # Para cada estado, precisamos de 6 chaves para definir as duas transições.
        # [Novo Estado, Símbolo, Movimento] para ler '0' e [Novo Estado, Símbolo, Movimento] para ler '1'.
        self.tam_solution = self.num_states * 6

        # Parâmetros de execução do RKO
        self.LS_type = 'Best'
        self.max_time = 120 # Tempo máximo de execução em segundos
        self.dict_best = None # Dicionário para armazenar melhores resultados conhecidos (se houver)

        # Parâmetros para a simulação da MT
        self.max_steps = 5000 # Limite de passos para evitar loops infinitos
        self.max_ones = 500  # Limite de "1s" para otimizar a parada

    def decoder(self, keys):
        """
        Decodifica um vetor de chaves aleatórias para uma tabela de transição de uma
        Máquina de Turing, garantindo que ela esteja em Forma Normal de Árvore (TNF).
        """
        transition_table = {}
        key_iterator = 0
        
        # O estado N+1 é o estado de parada (HALT)
        num_total_states = self.num_states + 1

        states_to_define = [1] # Fila de estados cujas transições precisam ser definidas
        visited_states = {1}
        next_available_state = 2

        while states_to_define:
            current_state = states_to_define.pop(0)
            transition_table[current_state] = {}

            # Processa as duas transições possíveis para o estado atual (ler 0 e ler 1)
            for read_symbol in [0, 1]:
                if key_iterator + 3 > len(keys):
                    # Se não houver chaves suficientes, a transição fica indefinida
                    continue
                
                # Consome 3 chaves para definir uma transição completa
                key_next_state = keys[key_iterator]
                key_write_symbol = keys[key_iterator + 1]
                key_move = keys[key_iterator + 2]
                key_iterator += 3

                # Decodifica as chaves
                write_symbol = 1 if key_write_symbol >= 0.5 else 0
                move = 1 if key_move >= 0.5 else -1 # 1 para Direita, -1 para Esquerda

                # Decodifica o próximo estado e aplica a lógica TNF
                raw_next_state = int(key_next_state * num_total_states) + 1
                
                final_next_state = raw_next_state
                if raw_next_state > next_available_state:
                    final_next_state = next_available_state
                
                # Adiciona o novo estado à fila se ele for novo e não for o de parada
                if final_next_state not in visited_states and final_next_state <= self.num_states:
                    visited_states.add(final_next_state)
                    states_to_define.append(final_next_state)
                    next_available_state += 1
                
                transition_table[current_state][read_symbol] = (final_next_state, write_symbol, move)
        
        # print(transition_table)
        # while True:
        #     i = 0
        #     i += 1
        return transition_table


    def cost(self, transition_table, verbose=False):
        """
        Simula a Máquina de Turing e calcula seu custo. O custo é o negativo da produtividade.
        O objetivo é maximizar o número de '1s', então minimizamos seu valor negativo.
        """
        tape = defaultdict(int) # A fita é infinita e inicializada com '0's (Brancos)
        head_position = 0
        current_state = 1
        steps = 0

        while steps < self.max_steps:
            # Condição de parada: HALT (estado N+1)
            if current_state > self.num_states:
                break
            
            read_symbol = tape[head_position]

            # Se a transição para o estado/símbolo atual não foi definida, a máquina para.
            if current_state not in transition_table or read_symbol not in transition_table[current_state]:
                break

            # Executa a transição
            next_state, write_symbol, move = transition_table[current_state][read_symbol]
            
            tape[head_position] = write_symbol
            head_position += move
            current_state = next_state
            steps += 1

            # Otimização para parar cedo se a produtividade exceder o limite
            if sum(tape.values()) > self.max_ones:
                return self.max_ones # Retorna um custo alto (produtividade alta)

        # Calcula a produtividade (número de '1s' na fita)
        if self.max_steps <= steps:
            return self.max_ones # Retorna um custo alto (produtividade alta)
        productivity = sum(tape.values())


        # A função de custo retorna o negativo da produtividade, pois o RKO minimiza.
        return -1 * productivity

if __name__ == '__main__':
    tempo = 1000
    env = BusyBeaverProblem(5)
    solver = RKO(env)

    cost,sol, temp = solver.solve(5000,0.3,0.5,tempo,8,2,1,1,2,2)
        
