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
            # adiciona resposta
            command = input("Comando> ")
            conn.sendall(command.encode('utf-8'))

    except ConnectionResetError:
        print(f"[CONEXÃO PERDIDA] {addr} desconectou.")
    finally:
        print(f"[FIM DA CONEXÃO] {addr} desconectado.")
        clients.remove(conn)
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
        send_message_to_ev3(idx, cmd)

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