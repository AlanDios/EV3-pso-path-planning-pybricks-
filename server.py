import socket
import threading

# -- Configurações do Servidor --
HOST = '0.0.0.0'  # Escuta em todas as interfaces
TCP_PORT = 65432    # Porta principal para comandos (TCP)
UDP_PORT = 65431    # Porta para descoberta (UDP)
DISCOVERY_REQUEST = b"EV3_DISCOVERY_REQUEST"
DISCOVERY_RESPONSE = b"EV3_SERVER_HERE"

clients = {}
client_threads = []
running = True

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
                if running:
                    print(f"[DISCOVERY] Erro: {e}")

def handle_client(conn, addr):
    """Função para lidar com a comunicação de um cliente EV3 individual (TCP)."""
    print(f"[NOVA CONEXÃO TCP] {addr} conectado.")
    
    clients[addr] = {
        'conn': conn,
        'posicao': (0,0), 
        'p_best': (0,0)
    }

    try:
        while True:
            data = conn.recv(1024)
            if not data: break
            message = data.decode('utf-8')
            print(f"[{addr}] Enviou: {message}")
            if message.startswith("pos:"):
                try:
                    parts = message.split(':')[1].split(';')
                    new_pos = (int(parts[0]), int(parts[1]))
                    clients[addr]['posicao'] = new_pos
                    print(f"[ATUALIZAÇÃO] Posição de {addr} atualizada para {new_pos}")
                except (ValueError, IndexError) as e:
                    print(f"[ERRO] Formato de mensagem de posição inválido de {addr}: {e}")
                
    except ConnectionResetError:
        print(f"[CONEXÃO PERDIDA] {addr} desconectou abruptamente.")
    finally:
        print(f"[FIM DA CONEXÃO] {addr} desconectado.")
        if addr in clients:
            del clients[addr]
        conn.close()

def broadcast_commands():
    """Função para enviar comandos para todos os EV3s conectados via input."""
    global running
    print("\nDigite um comando para enviar a todos os EV3s")
    print("Use 'list' para ver os clientes conectados.")
    print("Use 'exit' para fechar o servidor.")
    
    while running:
        command = input("Comando> ")
        if not running:
            break

        if command.lower() == 'exit':
            running = False # Sinaliza para as outras threads pararem
            print("[SAINDO] Enviando comando de desligamento para todos...")
            # Itera sobre uma cópia dos valores do dicionário para evitar erros de tamanho
            for client_data in list(clients.values()):
                try:
                    client_data['conn'].sendall(b'desligar')
                    client_data['conn'].close()
                except Exception as e:
                    print(f"Erro ao desconectar cliente: {e}")
            break # Sai do loop de comando

        if command.lower() == 'list':
            if not clients:
                print("Nenhum cliente conectado.")
            else:
                print("\n--- Clientes Conectados ---")
                for addr, data in clients.items():
                    print(f"Cliente: {addr}")
                    print(f"  Posição: {data['posicao']}")
                    print(f"  P-Best: {data['p_best']}")
                print("---------------------------\n")
            continue

        if not clients:
            print("Nenhum EV3 conectado.")
            continue
            
        print(f"Enviando '{command}' para {len(clients)} EV3s...")
        # Itera sobre uma cópia das chaves para poder remover itens durante a iteração
        for addr in list(clients.keys()):
            try:
                clients[addr]['conn'].sendall(command.encode('utf-8'))
            except Exception as e:
                print(f"Falha ao enviar para {addr}. Removendo. Erro: {e}")
                clients[addr]['conn'].close()
                del clients[addr]

def send_command_to_ev3(addr, message):
    """
    Envia uma mensagem para um cliente específico pelo seu endereço (addr).
    """
    if addr not in clients:
        print(f"[ERRO] Não existe cliente com o endereço {addr}")
        return

    try:
        conn = clients[addr]['conn']
        conn.sendall(message.encode('utf-8'))
        print(f"[ENVIO] Mensagem '{message}' enviada para EV3 em {addr}")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar mensagem para EV3 em {addr}: {e}")
        clients[addr]['conn'].close()
        del clients[addr]


# --- Lógica Principal do Servidor ---

# Inicia a thread de descoberta UDP
discovery_thread = threading.Thread(target=listen_for_discovery, daemon=True)
discovery_thread.start()

# Inicia a thread para broadcast de comandos
command_thread = threading.Thread(target=broadcast_commands, daemon=True)
command_thread.start()

# Inicia o servidor principal TCP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, TCP_PORT))
server_socket.listen()

print(f"[ESCUTANDO TCP] Servidor está escutando em {HOST}:{TCP_PORT}")
server_socket.settimeout(1.0) # Timeout para permitir a verificação da flag 'running'

try:
    while running:
        try:
            conn, addr = server_socket.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
            client_threads.append(thread)
        except socket.timeout:
            continue 
except KeyboardInterrupt:
    print("\n[INTERRUPÇÃO] Recebido Ctrl+C. Desligando...")
    running = False

# --- Finalização ---
print("[DESLIGANDO] Fechando o servidor...")
command_thread.join(timeout=2.0)

# Fecha o socket principal
server_socket.close()

print("[FINALIZADO] Servidor desligado.")