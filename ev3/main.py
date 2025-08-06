#!/usr/bin/env python3
import socket
import time
from ev3dev2.motor import LargeMotor, OUTPUT_C, OUTPUT_D, SpeedRPM, MoveTank
from ev3dev2.sensor.lego import ColorSensor
# Removido GyroSensor pois não estava sendo usado na lógica principal de giro
from ev3dev2.sound import Sound
from ev3dev2.display import Display
from ev3dev2.led import Leds

# --- Variáveis de conexão ---
TCP_PORT = 65432
UDP_PORT = 65431
DISCOVERY_REQUEST = b"EV3_DISCOVERY_REQUEST"
DISCOVERY_RESPONSE = b"EV3_SERVER_HERE"
BUFFER_SIZE = 1024

# --- Variáveis de controle e estado do robô ---
VELOCIDADE_DE_MOVIMENTO = 40  # Velocidade em porcentagem
TAMANHO_CASA_CM = 20          # Distância entre as fitas no grid
posicao_atual = [0.0, 0.0]    # Posição (x, y), agora usando float para compatibilidade com PSO
fitas_detectadas = [0, 0]     # [Fitas Pretas (Eixo Y), Fitas Verdes (Eixo X)]
cores_permitidas = ['Black', 'Green']
direcoes_cardinais = ['N', 'L', 'S', 'O'] # Norte, Leste, Sul, Oeste
direcao_atual = 'N'

# --- Inicialização dos componentes EV3 ---
sound = Sound()
leds = Leds()
left_motor = LargeMotor(OUTPUT_C)
right_motor = LargeMotor(OUTPUT_D)
color_sensor = ColorSensor('in4')
# giroscopio = GyroSensor('in1') # Descomente se for usar
screen = Display()

# A classe MoveTank simplifica o controle dos dois motores
robot = MoveTank(OUTPUT_C, OUTPUT_D)
# Estas medidas são cruciais para a precisão dos movimentos
robot.wheel_diameter_mm = 56
robot.axle_track_mm = 120

def mover_distancia(distancia_cm):
    """
    Move o robô por uma distância específica em linha reta.
    O rastreamento de posição por fitas foi movido para uma função separada.
    """
    global posicao_atual, direcao_atual, TAMANHO_CASA_CM

    # Converte cm para graus de rotação do motor
    graus_motor = (distancia_cm * 10 / (robot.wheel_diameter_mm * 3.14159)) * 360
    velocidade = SpeedRPM(VELOCIDADE_DE_MOVIMENTO)

    if distancia_cm < 0:
        velocidade = -velocidade

    robot.on_for_degrees(velocidade, velocidade, abs(graus_motor), brake=True, block=True)

    # ATENÇÃO: Esta é uma atualização de posição baseada na odometria.
    # A posição real deve ser confirmada com sensores (fitas) quando possível.
    # Para o PSO, a odometria é um bom ponto de partida entre os alvos.
    delta_x, delta_y = 0.0, 0.0
    if direcao_atual == 'N': delta_y = distancia_cm / TAMANHO_CASA_CM
    elif direcao_atual == 'S': delta_y = -distancia_cm / TAMANHO_CASA_CM
    elif direcao_atual == 'L': delta_x = distancia_cm / TAMANHO_CASA_CM
    elif direcao_atual == 'O': delta_x = -distancia_cm / TAMANHO_CASA_CM

    posicao_atual[0] += delta_x
    posicao_atual[1] += delta_y


def girar(angulo_graus):
    """Gira o robô por um ângulo específico. Positivo para esquerda, negativo para direita."""
    robot.turn_degrees(
        speed=SpeedRPM(VELOCIDADE_DE_MOVIMENTO),
        degrees=angulo_graus,
        brake=True,
        error_margin=2,
        use_gyro=False # Mude para True se estiver usando o giroscópio
    )
    time.sleep(0.5) # Pausa para estabilizar


def orientar_para(direcao_desejada):
    """Gira o robô até que ele esteja apontando para a direção cardeal desejada."""
    global direcao_atual, direcoes_cardinais
    
    if direcao_atual == direcao_desejada:
        return

    indice_atual = direcoes_cardinais.index(direcao_atual)
    indice_alvo = direcoes_cardinais.index(direcao_desejada)
    
    diferenca = (indice_alvo - indice_atual + 4) % 4
    
    if diferenca == 1: # Gira 90 graus para a direita
        girar(-90)
    elif diferenca == 2: # Gira 180 graus
        girar(180)
    elif diferenca == 3: # Gira 90 graus para a esquerda
        girar(90)
    
    direcao_atual = direcao_desejada


def ir_para_xy(x_alvo, y_alvo):
    """Navega o robô da sua posição atual para as coordenadas (x_alvo, y_alvo)."""
    global posicao_atual

    print(f"Navegando de {posicao_atual} para ({x_alvo:.2f}, {y_alvo:.2f})")
    screen.clear()
    screen.draw.text((10, 10), f"Alvo: {x_alvo:.1f}, {y_alvo:.1f}")
    screen.update()

    # --- Mover no Eixo Y (Norte/Sul) ---
    delta_y = y_alvo - posicao_atual[1]
    if abs(delta_y) > 0.1: # Adiciona uma pequena margem para evitar movimentos desnecessários
        direcao_y = 'N' if delta_y > 0 else 'S'
        orientar_para(direcao_y)
        mover_distancia(delta_y * TAMANHO_CASA_CM)

    # --- Mover no Eixo X (Leste/Oeste) ---
    delta_x = x_alvo - posicao_atual[0]
    if abs(delta_x) > 0.1:
        direcao_x = 'L' if delta_x > 0 else 'O'
        orientar_para(direcao_x)
        mover_distancia(delta_x * TAMANHO_CASA_CM)

    # A posição atual foi atualizada dentro de mover_distancia
    print(f"Navegação concluída! Posição estimada: [{posicao_atual[0]:.2f}, {posicao_atual[1]:.2f}]")
    leds.set_color("LEFT", "GREEN")
    leds.set_color("RIGHT", "GREEN")
    time.sleep(0.5) # Pequena pausa antes de reportar


def send_position(sock):
    """Envia a posição atual para o servidor no formato correto."""
    global posicao_atual
    # Formata a posição para ter 2 casas decimais
    pos_str = f"POS:{posicao_atual[0]:.2f},{posicao_atual[1]:.2f}"
    print(f"Enviando posição: {pos_str}")
    sock.sendall(pos_str.encode('utf-8'))


# --- LÓGICA PRINCIPAL ---
def main():
    global posicao_atual
    client_socket = None

    try:
        # --- 1. Descoberta do Servidor (UDP Broadcast) ---
        server_ip = None
        while server_ip is None:
            print("Procurando servidor...")
            screen.clear()
            screen.draw.text((10, 10), "Procurando Servidor...")
            screen.update()
            leds.set_color("LEFT", "ORANGE", 1)
            leds.set_color("RIGHT", "ORANGE", 1)

            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.settimeout(10.0)
                try:
                    s.sendto(DISCOVERY_REQUEST, ('<broadcast>', UDP_PORT))
                    data, addr = s.recvfrom(BUFFER_SIZE)
                    if data == DISCOVERY_RESPONSE:
                        server_ip = addr[0]
                        print(f"Servidor encontrado em {server_ip}")
                        sound.beep()
                        leds.set_color("LEFT", "GREEN", 1)
                        leds.set_color("RIGHT", "GREEN", 1)
                        time.sleep(1)
                except socket.timeout:
                    print("Timeout, tentando de novo...")
                    leds.all_off()
                    time.sleep(1)

        # --- 2. Conexão TCP com o Servidor ---
        print(f"Conectando ao servidor em {server_ip}:{TCP_PORT}")
        screen.clear()
        screen.draw.text((10, 10), f"Conectando a {server_ip}...")
        screen.update()
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((server_ip, TCP_PORT))
        print("Conectado!")

        screen.clear()
        screen.draw.text((10, 10), "Conectado!")
        screen.update()


        # --- 3. Ciclo de Operação Principal ---
        # Envia a posição inicial (0,0) para se registrar no servidor
        send_position(client_socket)

        while True:
            #leds.set_color("LEFT", "AMBER", 1) # Sinaliza que está aguardando comando
            #leds.set_color("RIGHT", "AMBER", 1)
            print("\nAguardando alvo do servidor...")
            screen.clear()
            screen.draw.text((10,10), "Aguardando alvo...")
            screen.draw.text((10,30), f"Pos: {posicao_atual[0]:.1f}, {posicao_atual[1]:.1f}")
            screen.update()


            # Espera por um comando do servidor (bloqueante)
            command_bytes = client_socket.recv(BUFFER_SIZE)
            if not command_bytes:
                print("Conexão fechada pelo servidor.")
                break
            
            command = command_bytes.decode('utf-8').strip()
            print(f"Comando recebido: {command}")
            
            if command == 'desligar':
                print("Comando de desligamento recebido.")
                break

            # Protocolo: Servidor envia o novo alvo como "GOTO:x,y"
            if command.startswith("GOTO:"):
                leds.set_color("LEFT", "YELLOW", 1) # Sinaliza que está processando/movendo
                leds.set_color("RIGHT", "YELLOW", 1)
                try:
                    _, pos_str = command.split(':')
                    x_str, y_str = pos_str.split(',')
                    target_x = float(x_str)
                    target_y = float(y_str)
                    
                    # Move o robô para o alvo recebido
                    ir_para_xy(target_x, target_y)
                    
                    # Após mover, envia a nova posição de volta para o servidor
                    send_position(client_socket)

                except (ValueError, IndexError) as e:
                    print(f"ERRO: Comando GOTO mal formatado: {command}. Erro: {e}")
                    sound.speak("Command error")
            else:
                print(f"Comando desconhecido: {command}")

    except Exception as e:
        print(f"Ocorreu um erro fatal: {e}")
        sound.speak("Fatal error")
        leds.set_color("LEFT", "RED")
        leds.set_color("RIGHT", "RED")

    finally:
        print("Finalizando e desconectando.")
        if client_socket:
            client_socket.close()
        robot.off()
        leds.all_off()
        sound.speak("Disconnected")
        screen.clear()
        screen.draw.text((10, 10), "Desconectado.")
        screen.update()
        time.sleep(2)


# Ponto de entrada do programa
if __name__ == "__main__":
    main()