#!/usr/bin/env python3
import socket
import time
from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B, SpeedRPM, MoveTank
from ev3dev2.sensor.lego import ColorSensor
from ev3dev2.sound import Sound
from ev3dev2.display import Display
from ev3dev2.led import Leds

# --- Variáveis de conexão ---
TCP_PORT = 65432
UDP_PORT = 65431
DISCOVERY_REQUEST = b"EV3_DISCOVERY_REQUEST"
DISCOVERY_RESPONSE = b"EV3_SERVER_HERE"

# --- Variáveis de controle ---
VELOCIDADE_DE_MOVIMENTO = 40 #Em ev3dev2, a velocidade é em porcentagem (0-100) ou RPM. Usaremos porcentagem.
posicao_inicial = [0,0]
posicao_atual = posicao_inicial
fitas_detectadas = [0,0]
cores_permitidas = ['Black', 'Green']
direcoes_cardinais = ['N', 'L', 'S', 'O']
direcao_atual = 'N'

# --- Inicialização ---
sound = Sound()
leds = Leds()
left_motor = LargeMotor(OUTPUT_A)
right_motor = LargeMotor(OUTPUT_B)
color_sensor = ColorSensor('in4')

# !!!! CASO TENHA SENSOR GIROSCÓPIO NO IF !!!
# Lembrar de importar o GyroSensor
#giroscopio = GyroSensor('in3')

sound = Sound()
screen = Display()
leds = Leds()

# A classe MoveTank é o equivalente do DriveBase
robot = MoveTank(OUTPUT_A, OUTPUT_B)
robot.wheel_diameter_mm = 56
robot.axle_track_mm = 120

def mover_e_detectar_cores(distancia_cm):
    """
    Move o robô uma determinada distancia, enquanto detecta e conta fitas coloridas.
    param: distancia_cm Distancia a ser percorrida pelo robo, caso negativo ele vai para trás
    return: listas_detectadas retorna as fitas que foram detectadas até agora
    """
    global fitas_detectadas, cores_permitidas, VELOCIDADE_DE_MOVIMENTO

    cor_anterior = ''
    
    robot.reset()
    distancia_alvo_mm = distancia_cm * 10

    if distancia_cm < 0:
        velocidade = SpeedRPM(-VELOCIDADE_DE_MOVIMENTO)
    else:
        velocidade = SpeedRPM(VELOCIDADE_DE_MOVIMENTO)

    # Inicia movimento
    robot.on(velocidade, velocidade)
    
    while abs(robot.left_motor.position * (robot.wheel_diameter_mm * 3.14159 / 360)) < abs(distancia_alvo_mm):
        cor_atual = color_sensor.color_name

        if cor_atual != cor_anterior:
            cor_anterior = cor_atual
            if cor_atual in cores_permitidas:
                screen.text_pixels(cor_atual, x=5, y=50)
                screen.update()
                
                id_cor = cores_permitidas.index(cor_atual)
                fitas_detectadas[id_cor] += 1
        
        time.sleep(0.03)

    robot.off()
    return fitas_detectadas

def processa_posicao():
    """
    Processa localização do Robo, considerando as fitas passadas até o momento atual.
    """
    global fitas_detectadas
    x = fitas_detectadas[1] # Fitas verdes (índice 1) no eixo X
    y = fitas_detectadas[0] # Fitas pretas (índice 0) no eixo Y
    return [x, y]

def girar_direita():
    """
    Gira o robô 90 graus na direita.
    """
    global direcao_atual
    time.sleep(2)

    #USAR ESSE CASO TENHA O SENSOR DE GIROSCÓPIO NO IF
    #robot.turn_degrees(SpeedRPM(VELOCIDADE_DE_MOVIMENTO), -90)
    
    # Calcula quantos graus o motor deve girar para o robô virar 90 graus
    graus_motor = (robot.axle_track_mm * 90) / robot.wheel_diameter_mm

    # Gira o motor esquerdo para frente e o direito para trás
    robot.on_for_degrees(SpeedRPM(VELOCIDADE_DE_MOVIMENTO), SpeedRPM(-VELOCIDADE_DE_MOVIMENTO), graus_motor)

    direcao_atual = atualizar_direcao('direita')
    
def girar_esquerda():
    """
    Gira o robô 90 graus na esquerda.
    """
    global direcao_atual
    time.sleep(2)
    
    #USAR ESSE CASO TENHA O SENSOR DE GIROSCÓPIO
    #robot.turn_degrees(SpeedRPM(30), -90)

    # Calcula quantos graus o motor deve girar para o robô virar 90 graus
    graus_motor = (robot.axle_track_mm * 90) / robot.wheel_diameter_mm

    # Gira o motor esquerdo para tras e o direito para frente
    robot.on_for_degrees(SpeedRPM(-VELOCIDADE_DE_MOVIMENTO), SpeedRPM(VELOCIDADE_DE_MOVIMENTO), graus_motor)

    direcao_atual = atualizar_direcao('esquerda')

def atualizar_direcao(giro):
    global direcao_atual, direcoes_cardinais
    indice_atual = direcoes_cardinais.index(direcao_atual)
    
    if giro.lower() == 'direita':
        nova_direcao = direcoes_cardinais[(indice_atual + 1) % len(direcoes_cardinais)]
    elif giro.lower() == 'esquerda':
        nova_direcao = direcoes_cardinais[(indice_atual - 1 + len(direcoes_cardinais)) % len(direcoes_cardinais)]
    else:
        raise ValueError("O giro deve ser 'esquerda' ou 'direita'")
    
    return nova_direcao

# !!! CASO TENHA SENSOR GIROSCÓPIO NO IF !!!
# robot.gyro = giroscopio

# print("Calibrando o giroscópio, não mova o robô...")
# robot.gyro.calibrate()
# print("Calibração concluída.")


sound.beep()
print("Inicializando...")

# --- Descoberta do Servidor (UDP Broadcast) ---
server_ip = None
while server_ip is None:
    print("Procurando servidor...")
    leds.set_color("LEFT", "ORANGE")
    leds.set_color("RIGHT", "ORANGE")

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(2.0)

    try:
        # Envia a mensagem de descoberta
        s.sendto(DISCOVERY_REQUEST, ('<broadcast>', UDP_PORT))
        
        data, addr = s.recvfrom(1024)
        if data == DISCOVERY_RESPONSE:
            server_ip = addr[0]
            print("Servidor encontrado em " + server_ip)
            leds.set_color("LEFT", "GREEN")
            leds.set_color("RIGHT", "GREEN")
            sound.speak("Server found")
            time.sleep(1)
            
    except socket.timeout:
        print("Timeout, tentando de novo...")
        leds.all_off()
        time.sleep(1)
        
    finally:
        s.close()

# --- Conexao com o Servidor ---
try:
    print("Conectando ao servidor")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, TCP_PORT))
    
    print("Conectado!")
    client_socket.sendall(b"Ola, sou um EV3 rodando ev3dev!")

    # --- Loop Principal de Comandos ---
    while True:
        command_bytes = client_socket.recv(1024)
        if not command_bytes or command_bytes.decode('utf-8') == 'desligar':
            break
        
        command = command_bytes.decode('utf-8')
        print("Comando recebido: " + command)

        if command == 'frente':
            mover_e_detectar_cores(50)
        elif command == 'tras':
            mover_e_detectar_cores(-50)
        elif command == 'esquerda':
            girar_esquerda()
        elif command == 'direita':
            girar_direita()
        elif command == 'posicao':
            posicao_atual = processa_posicao()
            mensagem = "x={},y={}".format(posicao_atual[0], posicao_atual[1])
            client_socket.sendall(mensagem.encode('utf-8'))


finally:
    print("Desconectado.")
    leds.set_color("LEFT", "RED")
    leds.set_color("RIGHT", "RED")
    robot.off
    client_socket.close()
    sound.speak("Disconnected")
    time.sleep(2)