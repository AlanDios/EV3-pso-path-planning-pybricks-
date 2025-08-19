#!/usr/bin/env python3
import socket
import time
from ev3dev2.motor import LargeMotor, OUTPUT_C, OUTPUT_D, SpeedRPM, MoveTank
from ev3dev2.sensor.lego import ColorSensor, GyroSensor
from ev3dev2.sound import Sound
from ev3dev2.display import Display
from ev3dev2.led import Leds
from ev3dev2.button import Button
from ev3dev2.fonts import load as load_font

# --- Variaveis de conexao ---
TCP_PORT = 65432
UDP_PORT = 65431
DISCOVERY_REQUEST = b"EV3_DISCOVERY_REQUEST"
DISCOVERY_RESPONSE = b"EV3_SERVER_HERE"

# --- Variaveis de controle ---
VELOCIDADE_DE_MOVIMENTO = 40
TAMANHO_CASA = 28
posicao_inicial = [0,0]
posicao_atual = posicao_inicial
fitas_detectadas = [0,0]
cores_permitidas = ['Black', 'Green']
direcoes_cardinais = ['N', 'L', 'S', 'O']
direcao_atual = 'N'

# --- Inicializacao ---
sound = Sound()
leds = Leds()
left_motor = LargeMotor(OUTPUT_C)
right_motor = LargeMotor(OUTPUT_D)
color_sensor = ColorSensor('in4')
giroscopio = GyroSensor('in1')
screen = Display()
btn = Button()
robot = MoveTank(OUTPUT_C, OUTPUT_D)
robot.wheel_diameter_mm = 56
robot.axle_track_mm = 120

# Carregando as fontes que voce escolheu
fonte_grande = load_font('helvB14')
fonte_pequena = load_font('lutBS10')

def definir_posicao_inicial():
    """
    Mostra uma interface na tela do EV3 para o usuario definir as coordenadas
    X e Y iniciais usando os botoes de seta. Pressione Enter para confirmar.
    """
    x, y = 0, 0
    sound.speak("Set initial position")

    while True:
        screen.text_pixels("Definir Posicao Inicial", font=fonte_pequena, x=5, y=10)
        screen.text_pixels("Use setas. Enter para OK.", font=fonte_pequena, x=5, y=30, clear_screen=False)
        screen.text_pixels("X: {}".format(x), font=fonte_grande, x=50, y=60, clear_screen=False)
        screen.text_pixels("Y: {}".format(y), font=fonte_grande, x=50, y=90, clear_screen=False)
        screen.update()

        if btn.up: y += 1; sound.beep()
        elif btn.down: y -= 1; sound.beep()
        elif btn.right: x += 1; sound.beep()
        elif btn.left: x -= 1; sound.beep()
        elif btn.enter:
            sound.speak("Position confirmed")
            screen.clear(); screen.update()
            break 
        time.sleep(0.15)
    return [x, y]

def definir_direcao_inicial():
    """
    Mostra uma interface na tela do EV3 para o usuario definir a direcao
    cardeal inicial. Pressione Enter para confirmar.
    """
    direcao_selecionada = 'N'
    sound.speak("Set initial direction")

    while True:
        screen.text_pixels("Definir Direcao Inicial", font=fonte_pequena, x=5, y=10)
        screen.text_pixels("Cima=N Baixo=S", font=fonte_pequena, x=5, y=30, clear_screen=False)
        screen.text_pixels("Dir=L Esq=O", font=fonte_pequena, x=5, y=45, clear_screen=False)
        screen.text_pixels(direcao_selecionada, font=fonte_grande, x=80, y=70, clear_screen=False)
        screen.update()

        if btn.up: direcao_selecionada = 'N'; sound.beep()
        elif btn.down: direcao_selecionada = 'S'; sound.beep()
        elif btn.right: direcao_selecionada = 'L'; sound.beep()
        elif btn.left: direcao_selecionada = 'O'; sound.beep()
        elif btn.enter:
            sound.speak("Direction confirmed")
            screen.clear(); screen.update()
            break
        time.sleep(0.15)
    return direcao_selecionada

# --- As suas funcoes de movimento (mover_e_detectar_cores, etc) continuam aqui sem alteracao ---
def mover_e_detectar_cores(distancia_cm):
    global fitas_detectadas, cores_permitidas, VELOCIDADE_DE_MOVIMENTO
    robot.reset()
    cor_anterior = color_sensor.color_name
    distancia_alvo_mm = distancia_cm * 10
    velocidade = SpeedRPM(VELOCIDADE_DE_MOVIMENTO if distancia_cm > 0 else -VELOCIDADE_DE_MOVIMENTO)
    robot.on(velocidade, velocidade)
    while abs(robot.left_motor.position * (robot.wheel_diameter_mm * 3.14159 / 360)) < abs(distancia_alvo_mm):
        cor_atual = color_sensor.color_name
        if cor_atual != cor_anterior:
            cor_anterior = cor_atual
            if cor_atual in cores_permitidas:
                id_cor = cores_permitidas.index(cor_atual)
                fitas_detectadas[id_cor] += 1
        time.sleep(0.03)
    robot.off()

def orientar_para(direcao_desejada):
    global direcao_atual
    rotacao_curta = {
        'N': {'L': 'direita', 'O': 'esquerda', 'S': 'direita'},
        'L': {'S': 'direita', 'N': 'esquerda', 'O': 'direita'},
        'S': {'O': 'direita', 'L': 'esquerda', 'N': 'direita'},
        'O': {'N': 'direita', 'S': 'esquerda', 'L': 'direita'}
    }
    
    while direcao_atual != direcao_desejada:
        giro_a_fazer = rotacao_curta[direcao_atual].get(direcao_desejada)
        if giro_a_fazer == 'direita': girar_direita()
        elif giro_a_fazer == 'esquerda': girar_esquerda()

def ir_para_xy(x_alvo, y_alvo):
    global posicao_atual
    delta_y = y_alvo - posicao_atual[1]
    if delta_y != 0:
        direcao_y = 'N' if delta_y > 0 else 'S'
        orientar_para(direcao_y)
        mover_e_detectar_cores(abs(delta_y) * TAMANHO_CASA)
    delta_x = x_alvo - posicao_atual[0]
    if delta_x != 0:
        direcao_x = 'L' if delta_x > 0 else 'O'
        orientar_para(direcao_x)
        mover_e_detectar_cores(abs(delta_x) * TAMANHO_CASA)
    pos_final = processa_posicao()
    if pos_final[0] != x_alvo or pos_final[1] != y_alvo:
        print("Erro ao movimentar ou calcular localizacao")
        leds.set_color("LEFT", "RED"); leds.set_color("RIGHT", "RED") 
        return
    posicao_atual = pos_final
    print("Navegacao concluida! Posicao final: {}".format(posicao_atual))

def processa_posicao():
    return posicao_atual
    global fitas_detectadas
    return [fitas_detectadas[1], fitas_detectadas[0]]

def girar_direita():
    global direcao_atual
    time.sleep(1)
    graus_motor = (robot.axle_track_mm * 90) / robot.wheel_diameter_mm
    robot.on_for_degrees(SpeedRPM(VELOCIDADE_DE_MOVIMENTO), SpeedRPM(-VELOCIDADE_DE_MOVIMENTO), graus_motor)
    direcao_atual = atualizar_direcao('direita')
    
def girar_esquerda():
    global direcao_atual
    time.sleep(1)
    graus_motor = (robot.axle_track_mm * 90) / robot.wheel_diameter_mm
    robot.on_for_degrees(SpeedRPM(-VELOCIDADE_DE_MOVIMENTO), SpeedRPM(VELOCIDADE_DE_MOVIMENTO), graus_motor)
    direcao_atual = atualizar_direcao('esquerda')

def atualizar_direcao(giro):
    global direcao_atual, direcoes_cardinais
    indice_atual = direcoes_cardinais.index(direcao_atual)
    if giro.lower() == 'direita':
        return direcoes_cardinais[(indice_atual + 1) % len(direcoes_cardinais)]
    elif giro.lower() == 'esquerda':
        return direcoes_cardinais[(indice_atual - 1 + len(direcoes_cardinais)) % len(direcoes_cardinais)]

def envia_posicao(conn):
    posicao_atual = processa_posicao()
    mensagem = "pos:{};{}".format(posicao_atual[0], posicao_atual[1])
    conn.sendall(mensagem.encode('utf-8'))
    

# --- FLUXO PRINCIPAL DO PROGRAMA ---
sound.beep()
print("Inicializando...")

posicao_inicial = definir_posicao_inicial()
posicao_atual = list(posicao_inicial)
print("Posicao inicial definida pelo usuario: {}".format(posicao_inicial))

direcao_atual = definir_direcao_inicial()
print("Direcao inicial definida pelo usuario: {}".format(direcao_atual))

# --- Descoberta do Servidor ---
server_ip = None
while server_ip is None:
    print("Procurando servidor...")
    leds.set_color("LEFT", "ORANGE"); leds.set_color("RIGHT", "ORANGE")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(2.0)
    try:
        s.sendto(DISCOVERY_REQUEST, ('<broadcast>', UDP_PORT))
        data, addr = s.recvfrom(1024)
        if data == DISCOVERY_RESPONSE:
            server_ip = addr[0]
            print("Servidor encontrado em " + server_ip)
            leds.set_color("LEFT", "GREEN"); leds.set_color("RIGHT", "GREEN")
            sound.speak("Server found")
            time.sleep(1)
    except socket.timeout:
        print("Timeout, tentando de novo...")
        leds.all_off()
        time.sleep(1)
    finally:
        s.close()

# --- Conexao com o Servidor ---
client_socket = None
try:
    print("Conectando ao servidor")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, TCP_PORT))
    print("Conectado!")

    # NOVA EXIBICAO DE TELA - MENSAGEM DE CONEXAO
    screen.clear()
    screen.text_pixels("Conectado ao Servidor!", font=fonte_pequena, x=10, y=50)
    screen.update()
    time.sleep(3) # Mostra a mensagem por 3 segundos
    
    client_socket.sendall(b"Ola, sou um EV3!")
    envia_posicao(client_socket)
    
    while True:
        command_bytes = client_socket.recv(1024)
        if not command_bytes or command_bytes.decode('utf-8') == 'desligar':
            break
        
        command = command_bytes.decode('utf-8')
        print("Comando recebido: " + command)

        screen.clear()
        screen.text_pixels("Executando Comando:", font=fonte_pequena, x=5, y=40, clear_screen=False)
        screen.text_pixels(command, font=fonte_grande, x=5, y=60)
        screen.update()

        # Processamento dos comandos
        if command.startswith("ir:"):
            try:
                _, coords = command.split(':')
                x_str, y_str = coords.split(';')
                x_alvo, y_alvo = float(x_str), float(y_str)
                ir_para_xy(int(x_alvo), int(y_alvo))
                envia_posicao()
            except Exception as e:
                print("Erro ao processar comando 'ir': {}".format(e))
        elif command == 'frente':
            mover_e_detectar_cores(50)
        elif command == 'tras':
            mover_e_detectar_cores(-50)
        elif command == 'esquerda':
            girar_esquerda()
        elif command == 'direita':
            girar_direita()
        elif command == 'posicao':
            envia_posicao(client_socket)

finally:
    print("Desconectado.")
    leds.set_color("LEFT", "RED"); leds.set_color("RIGHT", "RED")
    robot.off()
    if client_socket:
        client_socket.close()
    
    # Exibe mensagem final na tela
    screen.clear()
    screen.text_pixels("Desconectado.", font=fonte_grande, x=20, y=50)
    screen.update()
    
    sound.speak("Disconnected")
    time.sleep(3)