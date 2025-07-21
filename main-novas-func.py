#!/usr/bin/env pybricks-micropython
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import (Motor, TouchSensor, ColorSensor,
                                 InfraredSensor, UltrasonicSensor, GyroSensor)
from pybricks.parameters import Port, Stop, Direction, Button, Color
from pybricks.tools import wait, StopWatch, DataLog
from pybricks.robotics import DriveBase
from pybricks.media.ev3dev import SoundFile, ImageFile

# --- Variáveis de controle da aplicação ---
VELOCIDADE_DE_MOVIMENTO = 200
posicao_inicial = [0,0]
posicao_atual = posicao_inicial
fitas_detectadas = [0,0]
cores_permitidas = [Color.BLACK, Color.GREEN]
direcoes_cardinais = ['N', 'L', 'S', 'O']
direcao_cardinal = 'N'

# --- Inicialização ---

## Dispositivos conectados
motorA = Motor(Port.A)
motorB = Motor(Port.B)
left_motor = motorA
right_motor = motorB
colorSensor = ColorSensor(Port.S2)

## Configuração do drive
ev3 = EV3Brick()
robot = DriveBase(left_motor, right_motor, wheel_diameter=56, axle_track=120)
robot.settings(straight_speed=VELOCIDADE_DE_MOVIMENTO, straight_acceleration=100, turn_rate=100)


def mover_e_detectar_cores(distancia_cm):
    """
    Move o robô uma determinada distancia, enquanto detecta e conta fitas coloridas.
    param: distancia_cm Distancia a ser percorrida pelo robo, caso negativo ele vai para trás
    return: listas_detectadas retorna as fitas que foram detectadas até agora
    """
    ################################################
    ##  OBS: NÃO FOI TESTADO VALOR NEGATIVO AINDA  #
    ################################################

    global fitas_detectadas
    global cores_permitidas

    cor_anterior = 0

    # Para tudo antes de executar novas ações com o robo
    robot.reset()
    
    # Converte para mm porque a função drive o parâmetros em mm
    distancia_alvo_mm = distancia_cm * 10

    robot.drive(VELOCIDADE_DE_MOVIMENTO, 0)

    while robot.distance() < distancia_alvo_mm:
        corAtual = colorSensor.color()

        if(corAtual != cor_anterior):
            cor_anterior = corAtual
            if(corAtual in cores_permitidas):
                ev3.screen.print(corAtual)
                id_cor = cores_permitidas.index(corAtual)
                fitas_detectadas[id_cor] = fitas_detectadas[id_cor] + 1
                ev3.screen.print(corAtual)
        
        wait(30)

    robot.stop()
    return fitas_detectadas

def processa_posicao():
    """
    Processa localização do Robo, considerando as fitas passadas até o momento atual.

    :param fitas_detectadas: Fitas que o robo passou até o momento.
    """
    global fitas_detectadas
    x = fitas_detectadas[1]
    y = fitas_detectadas[0]

    return [x,y]

def girar_direita():
    """
    Gira o robô 90 graus na direita.

    O método robot.turn() é bloqueante, o que significa que o script
    esperará o giro terminar antes de continuar.
    """
    wait(2000)
    atualizar_direcao('direita')
    robot.turn(90)
    
    
def girar_esquerda():
    """
    Gira o robô 90 graus na esquerda.

    O método robot.turn() é bloqueante, o que significa que o script
    esperará o giro terminar antes de continuar.
    """
    wait(2000)
    atualizar_direcao('esquerda')
    robot.turn(-90)

direcoes_cardinais = ['N', 'L', 'S', 'O']

def atualizar_direcao(giro):
    # Encontra o índice da direção atual
    global direcao_cardinal
    global direcoes_cardinais

    indice_atual = direcoes_cardinais.index(direcao_cardinal)
    
    if giro.lower() == 'direita':
        nova_direcao = direcoes_cardinais[(indice_atual + 1) % len(direcoes_cardinais)]
    elif giro.lower() == 'esquerda':
        nova_direcao = direcoes_cardinais[(indice_atual - 1) % len(direcoes_cardinais)]
    else:
        raise ValueError("O giro deve ser 'esquerda' ou 'direita'")
    
    return nova_direcao

# Exemplo de uso
direcao = 'N'
direcao = atualizar_direcao(direcao, 'direita')  # Resultado: 'L'
direcao = atualizar_direcao(direcao, 'esquerda') # Resultado: 'N'
print(direcao)




# --- BLOCO DE EXECUÇÃO PRINCIPAL ---
ev3.screen.print("inicio: x=" + str(posicao_inicial[0]) +" y=" + str(posicao_inicial[1]) )

mover_e_detectar_cores(56)

posicao_atual = processa_posicao()

ev3.screen.print("Posição " + str(posicao_atual))

girar_esquerda()

mover_e_detectar_cores(56)

posicao_atual = processa_posicao()

ev3.screen.print("Posição " + str(posicao_atual))

girar_direita()

mover_e_detectar_cores(56)

posicao_atual = processa_posicao(fitas_detectadas)

ev3.screen.print("Posição " + str(posicao_atual))

wait(10000)