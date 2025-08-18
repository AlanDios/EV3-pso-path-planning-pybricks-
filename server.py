import socket
import threading
import time

# -- Configurações do Servidor --
HOST = '0.0.0.0'  # Escuta em todas as interfaces
TCP_PORT = 65432    # Porta principal para comandos (TCP)
UDP_PORT = 65431    # Porta para descoberta (UDP)
DISCOVERY_REQUEST = b"EV3_DISCOVERY_REQUEST"
DISCOVERY_RESPONSE = b"EV3_SERVER_HERE"

clients = []
client_threads = []
posicao =[] # lista de dict
pos_lock = threading.Lock()   # protege a lista `posicao`
# posicao já existe como lista global: posicao = []

def listen_for_discovery():
    """Thread que escuta por broadcasts UDP e responde com o IP do servidor."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, UDP_PORT))
        print(f"[DISCOVERY] Escutando por broadcasts na porta UDP {UDP_PORT}")
        while running:
            try:
                data, addr = s.recvfrom(1024)
                if data == DISCOVERY_REQUEST:
                    print(f"[DISCOVERY] Recebido pedido de {addr}. Respondendo...")
                    s.sendto(DISCOVERY_RESPONSE, addr)
            except Exception as e:
                print(f"[DISCOVERY] Erro: {e}")

def handle_client(conn, addr):
    """Função para lidar com a comunicação de um cliente EV3 individual (TCP)."""
    print(f"[NOVA CONEXÃO TCP] {addr} conectado.")
    clients.append(conn)
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break

            message = data.decode('utf-8', errors='ignore').strip()
            print(f"[{addr}] Enviou: {message}")

            # se for resposta de posição, parseia e armazena e pula o input()
            if parse_and_store_posicao(conn, message):
                continue

            # comportamento original — input interativo para enviar comandos ao cliente
            command = input("Comando> ")
            try:
                conn.sendall(command.encode('utf-8'))
            except Exception as e:
                print(f"[ERRO] Falha ao enviar comando para {addr}: {e}")
                break

    except ConnectionResetError:
        print(f"[CONEXÃO PERDIDA] {addr} desconectou.")
    finally:
        print(f"[FIM DA CONEXÃO] {addr} desconectado.")
        try:
            clients.remove(conn)
        except ValueError:
            pass
        conn.close()



def send_command_to_ev3(idx, message):
    """Envia uma mensagem para um cliente específico ou para todos. 
    Se 'exit', encerra o servidor e desconecta todos.
    """
    global running

    if not clients:
        print("[AVISO] Nenhum EV3 conectado.")
        return

    if message.lower() == "exit":
        print("[SERVIDOR] Encerrando conexões com todos os EV3s...")
        for client_conn in list(clients):
            try:
                client_conn.sendall(b'desligar')
                client_conn.close()
            except:
                pass
        clients.clear()
        running = False
        return

    if idx == "all":
        print(f"[ENVIO] Mandando '{message}' para todos os EV3s...")
        for client_conn in list(clients):
            try:
                client_conn.sendall(message.encode('utf-8'))
            except Exception as e:
                print(f"[ERRO] Falha ao enviar para um cliente: {e}")
                clients.remove(client_conn)
    else:
        try:
            conn = clients[idx]
            conn.sendall(message.encode('utf-8'))
            print(f"[ENVIO] Mensagem '{message}' enviada para EV3 #{idx}")
        except IndexError:
            print(f"[ERRO] Não existe cliente no índice {idx}")
        except Exception as e:
            print(f"[ERRO] Falha ao enviar mensagem para EV3 #{idx}: {e}")


def command_input_loop():
    """Loop para ler comandos do terminal e enviá-los via send_message_to_ev3."""
    print("\nDigite um comando para enviar ('all' = todos os EV3s)")
    print("Digite 'exit' para fechar o servidor.")
    while running:
        target = input("Destino (índice ou 'all')> ").strip()
        if target.isdigit():
            idx = int(target)
        else:
            idx = target

        cmd = input("Comando> ").strip()
        send_command_to_ev3(idx, cmd)

def parse_and_store_posicao(conn, message):
    """
    Tenta parsear `message` no formato "x=NUM,y=NUM".
    Se for válido, atualiza posicao[idx] onde idx = clients.index(conn).
    Retorna True se foi mensagem de posição, False caso contrário.
    """
    message = message.strip()
    if not (message.startswith("x=") and "y=" in message):
        return False

    try:
        parts = message.split(',')
        x = int(parts[0].split('=')[1])
        y = int(parts[1].split('=')[1])
    except Exception as e:
        print(f"[ERRO parse posicao] {e}")
        return False

    # determina índice do cliente (atenção: índices mudam se clientes entrarem/sair)
    try:
        idx = clients.index(conn)
    except ValueError:
        idx = None

    if idx is not None:
        with pos_lock:
            while len(posicao) <= idx:
                posicao.append({'x': None, 'y': None})
            posicao[idx] = {'x': x, 'y': y}
        print(f"[POSIÇÃO ATUALIZADA] cliente#{idx} -> x={x}, y={y}")

    return True


def call_send_command(idx, message, wait_for_pos=False, timeout=5.0, poll_interval=0.05):
    """
    Envia send_command_to_ev3(idx, message).
    - Se message == 'posicao' ou wait_for_pos True -> faz polling em posicao[idx] até timeout e retorna o dict {'x':..., 'y':...} ou None.
    - Caso contrário, dispara o envio e retorna None.
    OBS: `idx` aqui é o índice na lista clients (como no seu código atual).
    """
    # envia (usa sua função existente)
    send_command_to_ev3(idx, message)

    # decide se devemos aguardar update de posicao
    if not wait_for_pos and message.strip().lower() != 'posicao':
        return None

    # polling simples esperando posicao ser preenchida
    start = time.time()
    try:
        target_idx = int(idx)
    except Exception:
        print("[call_send_command] idx inválido para esperar posição.")
        return None

    while (time.time() - start) < timeout:
        with pos_lock:
            if 0 <= target_idx < len(posicao):
                p = posicao[target_idx]
                if p and p.get('x') is not None and p.get('y') is not None:
                    return p.copy()   # devolve cópia para evitar race
        time.sleep(poll_interval)

    print(f"[call_send_command] TIMEOUT aguardando posicao de cliente#{idx}")
    return None


# --- Lógica Principal do Servidor ---
running = True

# Inicia a thread de descoberta UDP
discovery_thread = threading.Thread(target=listen_for_discovery, daemon=True)
discovery_thread.start()

# Inicia a thread para broadcast de comandos
command_thread = threading.Thread(target=command_input_loop, daemon=True)
command_thread.start()

# Inicia o servidor principal TCP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, TCP_PORT))
server_socket.listen()
print(f"[ESCUTANDO TCP] Servidor está escutando em {HOST}:{TCP_PORT}")
server_socket.settimeout(1.0)

while running:
    try:
        conn, addr = server_socket.accept()
        print(conn)
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        client_threads.append(thread)
    except socket.timeout:
        continue

print("[DESLIGANDO] Fechando o servidor...")
server_socket.close()

# Representa o uso das novas funcoes para obter a posicao e já guardá-la no dict.
# chamar essa funcao no computador central que executa o PSO
################## pos = call_send_command(idx, 'posicao', timeout=5.0) ##########################
# print(pos)  # vai esperar até 5 segundos ou até a posição ser atualizada
# A ideia dessa funcao é mandar a string 'posicao' para o ev3. Com isso, o ev3 irá responder com a posicao (x = {} y ={})
# A resposta do ev3 então chega em server.py em handle_client. Essa funcao está modificada para receber a posicao e já preencher o dicionario
# posicao.
# A posicao preenchida é retornada por call_send_command, o que torna possível chamar essa funcao por fora do arquivo server.py