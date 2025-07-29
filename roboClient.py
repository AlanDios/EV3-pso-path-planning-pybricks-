#!/usr/bin/env pybricks-micropython
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor
from pybricks.parameters import Port, Stop, Color
from pybricks.tools import wait

import usocket as socket
import network

# --- Configurações do Cliente ---
TCP_PORT = 65432
UDP_PORT = 65431
DISCOVERY_REQUEST = b"EV3_DISCOVERY_REQUEST"
DISCOVERY_RESPONSE = b"EV3_SERVER_HERE"

WIFI_SSID = 'REDE_EV3'
WIFI_PASSWORD = 'robo_IA_IFMG'

# --- Inicialização do Robô ---
ev3 = EV3Brick()
motor_a = Motor(Port.A)
ev3.speaker.beep()

# --- Conexão Wi-Fi ---
wlan = network.WLAN(network.STA_IF)
if not wlan.isconnected():
    ev3.screen.print("Conectando WiFi...")
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    while not wlan.isconnected(): wait(100)
ev3.screen.clear()
ev3.screen.print("WiFi Conectado!")
my_ip = wlan.ifconfig()[0]
ev3.screen.print(my_ip)
wait(1000)

# --- Descoberta do Servidor (UDP Broadcast) ---
server_ip = None
while server_ip is None:
    ev3.screen.clear()
    ev3.screen.print("Procurando servidor...")
    ev3.light.on(Color.ORANGE)

    # Cria um socket UDP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(2.0) # Espera 2 segundos por uma resposta

    try:
        # Calcula o endereço de broadcast (ex: 192.168.1.255)
        ip_parts = my_ip.split('.')
        broadcast_address = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"
        
        # Envia a mensagem de descoberta
        s.sendto(DISCOVERY_REQUEST, (broadcast_address, UDP_PORT))
        
        # Espera pela resposta
        data, addr = s.recvfrom(1024)
        if data == DISCOVERY_RESPONSE:
            server_ip = addr[0] # Pega o IP de quem respondeu
            ev3.screen.clear()
            ev3.screen.print("Servidor encontrado!")
            ev3.screen.print(server_ip)
            ev3.light.on(Color.GREEN)
            wait(1000)
    except OSError as e:
        # Timeout ou outro erro, tenta novamente
        print("Timeout, tentando de novo...")
        ev3.light.off()
        wait(1000)
    finally:
        s.close()

# --- Conexão com o Servidor (TCP) ---
try:
    ev3.screen.clear()
    ev3.screen.print("Conectando TCP...")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    addr = socket.getaddrinfo(server_ip, TCP_PORT)[0][-1]
    client_socket.connect(addr)
    
    ev3.screen.clear()
    ev3.screen.print("Conectado!")
    client_socket.sendall(b"Ola, sou um EV3!")

    # --- Loop Principal de Comandos ---
    while True:
        command_bytes = client_socket.recv(1024)
        if not command_bytes: break
        
        command = command_bytes.decode('utf-8')
        ev3.screen.print(f"Cmd: {command}")

        if command == 'start': motor_a.run(500)
        elif command == 'stop': motor_a.stop()
        elif command == 'shutdown': break
finally:
    ev3.screen.clear()
    ev3.screen.print("Desconectado.")
    ev3.light.on(Color.RED)
    motor_a.stop()
    client_socket.close()
    wait(2000)