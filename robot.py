import numpy as np
from socket import socket
from typing import Tuple

class Robot:
    """
    Representa um robo sendo uma partícula do PSO, armazenando seu estado e funções necessárias
    """
    def __init__(self, initial_pos: Tuple[int, int], conn: socket):
        """
        Inicializa o estado da partícula (robô).

        Args:
            initial_pos (Tuple[int, int]): A posição inicial (x, y) do robô.
            conn (socket): O objeto de conexão de socket com este robô.
        """
        self.conn: socket = conn

        # --- Atributos de Estado e PSO ---
        self.position: np.ndarray = np.array(initial_pos, dtype=float)
        self.velocity: np.ndarray = np.random.uniform(-1, 1, size=2)
        self.pbest_pos: np.ndarray = np.copy(self.position)
        
        # Para um problema de MINIMIZAÇÃO, valor inicial é infinito positivo
        self.pbest_val: float = float('inf')
        self.fitness: float = float('inf')

    def update_position(self, x: int, y: int):
        """
        Atualiza a posição atual do robô.
        """
        self.position = np.array([x, y], dtype=float)

    def __repr__(self) -> str:
        pos_str = f"[{self.position[0]:.1f}, {self.position[1]:.1f}]"
        pbest_val_str = f"{self.pbest_val:.2f}" if self.pbest_val != float('inf') else "inf"
        return f"Robot(Pos: {pos_str}, P-Best Value: {pbest_val_str})"