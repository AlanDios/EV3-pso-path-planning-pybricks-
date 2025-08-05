from pybricks.hubs import EV3Brick
from pybricks.messaging import BluetoothMailboxClient, TextMailbox
import time

ev3 = EV3Brick()

# Nome do robô (cada robô precisa usar nome diferente: robot_0, robot_1, etc)
robot_id = 0  # Mude para 1 ou 2 nos outros robôs
mbox_name = f"robot_{robot_id}"

# Conecta ao PC (coloca aqui o nome Bluetooth do PC)
client = BluetoothMailboxClient()
mbox = TextMailbox(mbox_name, client)

client.connect('NOME_DO_PC')  # Exemplo: 'RATINHO_PC'

ev3.screen.print("Conectado ao PC!")

# Posição inicial
x, y = 0.0, 0.0

# Loop: manda posição, espera nova posição, move
iterations = 10
for t in range(iterations):
    # Manda posição atual
    pos_str = f"{x},{y}"
    mbox.send(pos_str)

    # Espera nova posição
    mbox.wait()
    new_pos_str = mbox.read()
    new_x_str, new_y_str = new_pos_str.split(',')
    new_x, new_y = float(new_x_str), float(new_y_str)

    ev3.screen.print(f"Recebi nova posição: ({new_x:.2f}, {new_y:.2f})")

    # Simula movimento: vai direto para nova posição
    # Na prática, aqui você colocaria comandos de motor para se mover
    x, y = new_x, new_y

    ev3.speaker.beep()  # faz um beep pra mostrar que moveu
    time.sleep(0.5)  # espera um pouco para a próxima iteração

ev3.screen.print("PSO concluído!")