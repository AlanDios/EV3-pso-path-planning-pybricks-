import socket
import threading
import time
import random
import numpy as np # Usado para facilitar cálculos vetoriais

# -- Configurações do Servidor --
HOST = '0.0.0.0'  # Escuta em todas as interfaces
TCP_PORT = 65432    # Porta principal para comandos (TCP)
UDP_PORT = 65431    # Porta para descoberta (UDP)
DISCOVERY_REQUEST = b"EV3_DISCOVERY_REQUEST"
DISCOVERY_RESPONSE = b"EV3_SERVER_HERE"
BUFFER_SIZE = 1024

# -- Estruturas de Dados Globais --
robots = {}  # Dicionário para armazenar o estado de cada robô
robots_lock = threading.Lock() # Lock para acesso seguro à estrutura 'robots'
running = True
pso_thread = None
pso_running = threading.Event()

# -- Parâmetros do PSO --
# Função objetivo: O alvo que o enxame deve encontrar.
# Neste exemplo, o alvo é o ponto (200, 150).
# Você pode alterar esta função para qualquer outra que represente seu problema.
def objective_function(x, y):
    target_x, target_y = 1, 3
    return np.sqrt((x - target_x)**2 + (y - target_y)**2)

# Parâmetros clássicos do PSO
W = 0.5   # Inércia
C1 = 1.5  # Coeficiente cognitivo (pessoal)
C2 = 1.5  # Coeficiente social (global)
PSO_ITERATION_INTERVAL = 2 # segundos entre cada iteração do PSO

# Melhor posição global encontrada pelo enxame
gbest_position = None
gbest_value = float('inf')

def listen_for_discovery():
    """Thread que escuta por broadcasts UDP e responde com o IP do servidor."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, UDP_PORT))
        print(f"[DISCOVERY] Escutando por broadcasts na porta UDP {UDP_PORT}")
        while running:
            try:
                data, addr = s.recvfrom(BUFFER_SIZE)
                if data == DISCOVERY_REQUEST:
                    print(f"[DISCOVERY] Recebido pedido de {addr}. Respondendo...")
                    s.sendto(DISCOVERY_RESPONSE, addr)
            except Exception as e:
                print(f"[DISCOVERY] Erro: {e}")

def handle_client(conn, addr):
    """Lida com a comunicação de um robô, recebendo sua posição e atualizando o estado."""
    global gbest_position, gbest_value
    ip, port = addr
    print(f"[NOVA CONEXÃO] Robô {ip}:{port} conectado.")

    with robots_lock:
        robots[addr] = {
            "conn": conn,
            "ip": ip,
            "position": None, # Posição [x, y]
            "velocity": np.array([0.0, 0.0]), # Velocidade [vx, vy]
            "pbest_position": None, # Melhor posição pessoal
            "pbest_value": float('inf')
        }

    try:
        while running:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            message = data.decode('utf-8').strip()
            print(f"[{ip}] Enviou: {message}")

            # Protocolo: Robô envia sua posição como "POS:x,y"
            if message.startswith("POS:"):
                try:
                    _, pos_str = message.split(':')
                    x_str, y_str = pos_str.split(',')
                    current_pos = np.array([float(x_str), float(y_str)])

                    with robots_lock:
                        robots[addr]['position'] = current_pos
                        
                        # Avalia a nova posição
                        current_value = objective_function(current_pos[0], current_pos[1])

                        # Atualiza a melhor posição pessoal (pbest)
                        if current_value < robots[addr]['pbest_value']:
                            robots[addr]['pbest_value'] = current_value
                            robots[addr]['pbest_position'] = current_pos
                            print(f"[PSO] Robô {ip} atualizou seu pbest para {current_pos} (valor: {current_value:.2f})")

                        # Atualiza a melhor posição global (gbest)
                        if current_value < gbest_value:
                            gbest_value = current_value
                            gbest_position = current_pos
                            print(f"[PSO] NOVO GBEST GLOBAL ENCONTRADO por {ip}: {gbest_position} (valor: {gbest_value:.2f})")

                except (ValueError, IndexError) as e:
                    print(f"[ERRO] Mensagem de posição mal formatada de {ip}: {message}. Erro: {e}")

    except ConnectionResetError:
        print(f"[CONEXÃO PERDIDA] Robô {ip} desconectou.")
    finally:
        print(f"[FIM DA CONEXÃO] {ip} desconectado.")
        with robots_lock:
            robots.pop(addr, None)
        conn.close()

def run_pso_swarm():
    """Thread principal do algoritmo PSO. Calcula e envia novas posições para os robôs."""
    global gbest_position

    print("\n[PSO] Thread do enxame iniciada. Aguardando posições iniciais dos robôs...")

    while pso_running.is_set():
        time.sleep(PSO_ITERATION_INTERVAL)
        
        with robots_lock:
            if not robots or gbest_position is None:
                # Pula a iteração se não houver robôs ou se o gbest ainda não foi definido
                continue
            
            print(f"\n--- Iteração PSO --- (Gbest: {gbest_position}, Valor: {gbest_value:.2f})")

            # Itera sobre uma cópia para evitar problemas de concorrência se um robô desconectar
            active_robots = list(robots.items())

            for addr, robot_data in active_robots:
                if robot_data['position'] is None or robot_data['pbest_position'] is None:
                    continue

                # Extrai dados do robô
                pos = robot_data['position']
                vel = robot_data['velocity']
                pbest = robot_data['pbest_position']

                # --- FÓRMULA CLÁSSICA DO PSO ---
                r1 = np.random.rand(2) # Vetor de 2 números aleatórios [0, 1]
                r2 = np.random.rand(2) # Vetor de 2 números aleatórios [0, 1]

                # Atualiza a velocidade
                cognitive_component = C1 * r1 * (pbest - pos)
                social_component = C2 * r2 * (gbest_position - pos)
                new_vel = W * vel + cognitive_component + social_component
                
                # Atualiza a posição (calcula o novo alvo)
                new_pos = pos + new_vel

                # Armazena a nova velocidade para a próxima iteração
                robots[addr]['velocity'] = new_vel

                # Envia a nova posição alvo para o robô
                command = f"GOTO:{new_pos[0]},{new_pos[1]}"
                try:
                    robot_data['conn'].sendall(command.encode('utf-8'))
                    print(f" -> Enviado para {robot_data['ip']}: {command} (Posição antiga: {pos})")
                except (ConnectionResetError, BrokenPipeError):
                    print(f" -> Falha ao enviar para {robot_data['ip']}. Será removido.")
                    # A thread handle_client cuidará da remoção completa

    print("[PSO] Thread do enxame finalizada.")


def server_commands():
    """Função para receber comandos do administrador do servidor."""
    global running, pso_thread

    print("\n--- Controle do Servidor ---")
    print("Comandos disponíveis: start_pso, stop_pso, status, exit")

    while True:
        command = input("Comando> ").lower().strip()
        
        if command == 'exit':
            print("[DESLIGANDO] Enviando comando de desligamento para os robôs...")
            pso_running.clear() # Para a thread do PSO
            if pso_thread:
                pso_thread.join()
            
            with robots_lock:
                for addr, robot_data in robots.items():
                    try:
                        robot_data['conn'].sendall(b'desligar')
                        robot_data['conn'].close()
                    except: pass
            running = False
            break

        elif command == 'start_pso':
            if pso_running.is_set():
                print("[AVISO] O PSO já está em execução.")
                continue
            
            # Verifica se temos ao menos um robô com posição para iniciar
            with robots_lock:
                if not any(r['position'] is not None for r in robots.values()):
                    print("[ERRO] Não é possível iniciar o PSO. Nenhum robô reportou sua posição inicial.")
                    continue
            
            print("[CONTROLE] Iniciando a thread do PSO...")
            pso_running.set()
            pso_thread = threading.Thread(target=run_pso_swarm, daemon=True)
            pso_thread.start()

        elif command == 'stop_pso':
            if not pso_running.is_set():
                print("[AVISO] O PSO não está em execução.")
                continue
            print("[CONTROLE] Parando a thread do PSO...")
            pso_running.clear()
            if pso_thread:
                pso_thread.join() # Espera a thread terminar
            pso_thread = None
            print("[CONTROLE] PSO parado.")

        elif command == 'status':
            print("\n--- Status dos Robôs ---")
            with robots_lock:
                if not robots:
                    print("Nenhum robô conectado.")
                else:
                    for ip, data in robots.items():
                        pos = data['position'] if data['position'] is not None else "N/A"
                        pbest = data['pbest_position'] if data['pbest_position'] is not None else "N/A"
                        print(f"Robô: {data['ip']} | Posição Atual: {pos} | PBest: {pbest}")
                    print(f"Melhor Posição Global (gbest): {gbest_position}")
            print("------------------------\n")
            
        else:
            print(f"Comando '{command}' não reconhecido.")


# --- Lógica Principal do Servidor ---
if __name__ == "__main__":
    # Inicia a thread de descoberta UDP
    discovery_thread = threading.Thread(target=listen_for_discovery, daemon=True)
    discovery_thread.start()

    # Inicia a thread para comandos do servidor
    command_thread = threading.Thread(target=server_commands)
    command_thread.start()

    # Inicia o servidor principal TCP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, TCP_PORT))
    server_socket.listen()
    print(f"[ESCUTANDO TCP] Servidor está escutando em {HOST}:{TCP_PORT}")
    server_socket.settimeout(1.0) # Timeout para permitir a verificação da flag 'running'

    client_threads = []
    while running:
        try:
            conn, addr = server_socket.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
            client_threads.append(thread)
        except socket.timeout:
            continue
    
    print("[DESLIGANDO] Aguardando threads finalizarem...")
    command_thread.join()
    for t in client_threads:
        t.join()
    server_socket.close()
    print("[SERVIDOR DESLIGADO]")