import socket

HOST = '192.168.1.100'  # Escuta em todas as interfaces
PORT = 65432

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print("Aguardando conexão do EV3...")
    conn, addr = s.accept()

    with conn:
        print(f"Conectado por {addr}")
        while True:
            cmd = input("Comando (start, stop, shutdown): ").strip()
            if cmd:
                conn.sendall(cmd.encode('utf-8'))
            if cmd == 'shutdown':
                print("Finalizando servidor.")
                break
