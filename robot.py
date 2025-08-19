import numpy as np
from socket import socket
from typing import Tuple

class Robot:
  """Representa um robô para ser usado em um algoritmo de Otimização por Enxame de Partículas (PSO).

  Esta classe armazena o estado completo de uma partícula, incluindo sua
  posição e velocidade no espaço de busca, sua melhor posição pessoal
  encontrada (`pbest`), e o objeto de conexão de rede para se comunicar
  com o agente físico (robô).

  Attributes:
    conn (socket.socket): O objeto de socket de conexão do robotcliente/partícula.
    position (np.ndarray): Vetor da posição atual `[x, y]` da partícula.
    velocity (np.ndarray): Vetor da velocidade atual `[vx, vy]` da partícula.
    pbest_pos (np.ndarray): A melhor posição `[x, y]` já encontrada por esta partícula.
    pbest_val (float): O valor de fitness (aptidão) associado à `pbest_pos`.
    fitness (float): O valor de fitness da partícula em sua `position` atual.
  """
  def __init__(self, initial_pos, conn):
    self.conn: socket = conn
    self.position: tuple = initial_pos
    self.nextPosition: tuple = initial_pos
    self.velocity: float = np.random.uniform(-1, 1, size=2)
    self.pbest_pos: tuple = np.copy(self.position)
    self.pbest_val: float = -float('inf')
    self.fitness: float = -float('inf')
    
  def update_position(self, x,y):
    self.position = (x,y)