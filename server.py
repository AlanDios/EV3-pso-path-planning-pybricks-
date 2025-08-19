from socket import socket, timeout, SO_REUSEADDR, SOCK_STREAM, SOL_SOCKET, AF_INET, SOCK_DGRAM
from typing import Dict, Tuple
import numpy as np
import threading
import time

from robot import Robot

# -- Configurações do Servidor --
HOST = '0.0.0.0'  # Escuta em todas as interfaces
TCP_PORT = 65432
UDP_PORT = 65431
DISCOVERY_REQUEST = b"EV3_DISCOVERY_REQUEST"
DISCOVERY_RESPONSE = b"EV3_SERVER_HERE"

# -- Parâmetros PSO --
MAX_ITERATIONS = 5
W = 0.5   # Inércia
C1 = 1.5  # Coeficiente cognitivo (pessoal)
C2 = 1.5  # Coeficiente social (global)
BOUNDS = [[0, 0], [3, 6]]
PSO_ITERATION_INTERVAL = 20

# -- Variáveis Globais --
particulas: Dict[Tuple[str, int], Robot] = {}
client_threads = []
running = True
start_pso = False
global_best_pos = None
global_best_val = float('inf')

# --- Função Objetiva ---
def objective_function(x, y):
    target_x, target_y = 1, 3
    return np.sqrt((x - target_x)**2 + (y - target_y)**2)

# --- Threads de Rede ---
def listen_for_discovery():
    with socket(AF_INET, SOCK_DGRAM) as s:
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind((HOST, UDP_PORT))
        s.settimeout(1.0)
        print(f"[DISCOVERY] Escutando por broadcasts na porta UDP {UDP_PORT}")
        while running:
            try:
                data, addr = s.recvfrom(1024)
                if data == DISCOVERY_REQUEST:
                    print(f"[DISCOVERY] Recebido pedido de {addr}. Respondendo...")
                    s.sendto(DISCOVERY_RESPONSE, addr)
            except timeout:
                continue
            except Exception as e:
                if running:
                    print(f"[DISCOVERY] Erro: {e}")

def handle_client(conn, addr):
    print(f"[NOVA CONEXÃO TCP] {addr} conectado.")
    particulas[addr] = Robot((0,0), conn)
    try:
        while running:
            data = conn.recv(1024)
            if not data: break
            message = data.decode('utf-8')
            print(f"[{addr}] Enviou: {message}")
            if message.startswith("pos:"):
                try:
                    parts = message.split(':')[1].split(';')
                    x, y = int(parts[0]), int(parts[1])
                    particulas[addr].update_position(x, y)
                    print(f"[ATUALIZAÇÃO] Posição de {addr} confirmada em ({x},{y})")
                except (ValueError, IndexError, KeyError) as e:
                    print(f"[ERRO] Formato de mensagem de posição inválido de {addr}: {e}")
            elif message == 'desligar':
                break
    except ConnectionResetError:
        print(f"[CONEXÃO PERDIDA] {addr} desconectou abruptamente.")
    finally:
        print(f"[FIM DA CONEXÃO] {addr} desconectado.")
        if addr in particulas:
            del particulas[addr]
        conn.close()


# --- Thread de Comandos do Usuário ---
def command_handler():
    """Thread que lida com os comandos digitados pelo usuário no terminal."""
    global running, start_pso

    while running:
        command = input("Comando [ pso | list | exit ] > ")
        if not running:
            break

        if command.lower() == 'pso':
            if not start_pso:
                print("[CONTROLE] Comando 'pso' recebido. Iniciando o algoritmo...")
                start_pso = True
            else:
                print("[CONTROLE] O PSO já está em execução.")

        elif command.lower() == 'pso_pause':
            if start_pso:
                print("[CONTROLE] Pausando algoritmo. ")
                start_pso = False

        elif command.lower() == 'list':
            if not particulas:
                print("\nNenhum robô conectado.")
            else:
                print("\n--- Robôs Conectados ---")
                for addr, robot in particulas.items():
                    print(f"- Cliente: {addr} | {robot}")
                print("------------------------\n")

        elif command.lower() == 'exit':
            print("[CONTROLE] Comando 'exit' recebido. Encerrando o servidor...")
            running = False
            break
        
        else:
            print(f"Comando '{command}' desconhecido.")


# --- Thread do PSO (MODIFICADA) ---
def pso_main_loop():
    global running, global_best_pos, global_best_val

    # Esta parte está correta: a thread fica aqui esperando o comando 'pso'
    print("[PSO] Thread iniciada. Aguardando comando 'pso' para começar...")
    while not start_pso and running:
        time.sleep(1)

    if not running: return
    print(f"[PSO] {len(particulas)} robôs conectados. Iniciando o algoritmo!")

    for iteration in range(MAX_ITERATIONS):
        if not running: break
        print(f"\n--- [PSO] ITERAÇÃO {iteration + 1}/{MAX_ITERATIONS} ---")

        # 1. Para cada robô, calcular o próximo alvo e enviar o comando
        for addr, robot in list(particulas.items()):
            r1, r2 = np.random.random(2), np.random.random(2)
            
            ## CALCULO VETORIAIS
            cognitive_vel = C1 * r1 * (robot.pbest_pos - robot.position)
            social_vel = C2 * r2 * (global_best_pos - robot.position) if global_best_pos is not None else 0
            robot.velocity = W * robot.velocity + cognitive_vel + social_vel
            
            target_pos = robot.position + robot.velocity
            target_pos[0] = np.clip(target_pos[0], BOUNDS[0][0], BOUNDS[0][1])
            target_pos[1] = np.clip(target_pos[1], BOUNDS[1][0], BOUNDS[1][1])

            command = f"ir:{int(target_pos[0])};{int(target_pos[1])}"
            try:
                robot.conn.sendall(command.encode('utf-8'))
            except Exception as e:
                print(f"[PSO] Erro ao enviar comando para {addr}: {e}")
        
        print("[PSO] Comandos enviados. Aguardando movimentos...")
        time.sleep(PSO_ITERATION_INTERVAL) 
        
        # 3. Atualizar P-Best e G-Best
        for addr, robot in list(particulas.items()):
            robot.fitness = objective_function(robot.position[0], robot.position[1])

            if robot.fitness < robot.pbest_val:
                robot.pbest_val = robot.fitness
                robot.pbest_pos = robot.position
                print(f"[PSO] Novo P-Best para {addr}: {robot.pbest_val:.2f}")

            if robot.fitness < global_best_val:
                global_best_val = robot.fitness
                global_best_pos = robot.position
                print(f"--- [PSO] NOVO G-BEST GLOBAL ENCONTRADO POR {addr}! Valor: {global_best_val:.2f} ---")
        
    
    if running:
        print("\n[PSO] Algoritmo finalizado!")
        running = False


# --- Lógica Principal do Servidor ---
if __name__ == "__main__":
    discovery_thread = threading.Thread(target=listen_for_discovery, daemon=True)
    discovery_thread.start()

    pso_thread = threading.Thread(target=pso_main_loop)
    pso_thread.start()

    command_thread = threading.Thread(target=command_handler)
    command_thread.start()

    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.bind((HOST, TCP_PORT))
    server_socket.listen()

    print(f"[ESCUTANDO TCP] Servidor está escutando em {HOST}:{TCP_PORT}")
    server_socket.settimeout(1.0)

    try:
        while running:
            try:
                conn, addr = server_socket.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
                client_threads.append(thread)
            except timeout:
                continue
    except KeyboardInterrupt:
        print("\n[INTERRUPÇÃO] Recebido Ctrl+C. Desligando...")
        running = False
    finally:
        print("[DESLIGANDO] Fechando o servidor...")
        for robot in list(particulas.values()):
            try:
                robot.conn.sendall(b'desligar')
                robot.conn.close()
            except Exception:
                pass
        
        pso_thread.join(timeout=2.0)
        command_thread.join(timeout=1.0) 
        server_socket.close()
        print("[FINALIZADO] Servidor desligado.")