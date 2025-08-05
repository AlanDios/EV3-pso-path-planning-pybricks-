import socket
import threading

# -- Configurações do Servidor --
HOST = '0.0.0.0'  # Escuta em todas as interfaces
TCP_PORT = 65432    # Porta principal para comandos (TCP)
UDP_PORT = 65431    # Porta para descoberta (UDP)
DISCOVERY_REQUEST = b"EV3_DISCOVERY_REQUEST"
DISCOVERY_RESPONSE = b"EV3_SERVER_HERE"

clients = []
client_threads = []

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
            if not data: break
            message = data.decode('utf-8')
            print(f"[{addr}] Enviou: {message}")
    except ConnectionResetError:
        print(f"[CONEXÃO PERDIDA] {addr} desconectou.")
    finally:
        print(f"[FIM DA CONEXÃO] {addr} desconectado.")
        clients.remove(conn)
        conn.close()

def broadcast_commands():
    """Função para enviar comandos para todos os EV3s conectados."""
    print("\nDigite um comando para enviar a todos os EV3s")
    print("Digite 'exit' para fechar o servidor.")
    while True:
        command = input("Comando> ")
        if command.lower() == 'exit':
            for client_conn in clients:
                try:
                    client_conn.sendall(b'desligar')
                    client_conn.close()
                except: pass
            break
        if not clients:
            print("Nenhum EV3 conectado.")
            continue
        print(f"Enviando '{command}' para {len(clients)} EV3s...")
        for client_conn in list(clients):
            try:
                client_conn.sendall(command.encode('utf-8'))
            except:
                print(f"Falha ao enviar para um cliente. Removendo.")
                clients.remove(client_conn)
    global running
    running = False

# --- Lógica Principal do Servidor ---
running = True

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
server_socket.settimeout(1.0)

while running:
    try:
        conn, addr = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        client_threads.append(thread)
    except socket.timeout:
        continue

print("[DESLIGANDO] Fechando o servidor...")
server_socket.close()