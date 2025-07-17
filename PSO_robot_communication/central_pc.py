from pybricks.messaging import BluetoothMailboxServer, TextMailbox
import random

N = 3  # número de robôs
iterations = 10

# Parâmetros do PSO
w = 0.5
c1 = 1.5
c2 = 1.5

# Inicialização: posições aleatórias e velocidades zeradas
positions = [ [random.uniform(-10,10), random.uniform(-10,10)] for _ in range(N) ]
velocities = [ [0.0, 0.0] for _ in range(N) ]
pbest = positions.copy()
gbest = min(pbest, key=lambda pos: (pos[0]-1)*2 + (pos[1]-3)*2)

# Função objetivo
def f(x, y):
    return (x-1)*2 + (y-3)*2

# Configura servidor bluetooth
server = BluetoothMailboxServer()
mailboxes = []

print("Aguardando robôs conectarem...")

# Espera conexão de cada robô
for i in range(N):
    mbox = TextMailbox(f'robot_{i}', server)
    mailboxes.append(mbox)

print("Todos os robôs conectados!")

# Loop principal do PSO
for t in range(iterations):
    print(f"\nIteração {t+1}/{iterations}")

    # Recebe posições atuais de cada robô
    for i, mbox in enumerate(mailboxes):
        mbox.wait()
        pos_str = mbox.read()
        x_str, y_str = pos_str.split(',')
        positions[i] = [float(x_str), float(y_str)]

    # Atualiza pbest
    for i in range(N):
        if f(*positions[i]) < f(*pbest[i]):
            pbest[i] = positions[i].copy()

    # Atualiza gbest
    gbest = min(pbest, key=lambda pos: f(*pos))

    # Calcula nova velocidade e posição para cada robô
    for i in range(N):
        for d in range(2):  # para x e y
            r1 = random.random()
            r2 = random.random()
            velocities[i][d] = (
                w * velocities[i][d]
                + c1 * r1 * (pbest[i][d] - positions[i][d])
                + c2 * r2 * (gbest[d] - positions[i][d])
            )
            positions[i][d] += velocities[i][d]

    # Envia nova posição para cada robô
    for i, mbox in enumerate(mailboxes):
        pos_str = f"{positions[i][0]},{positions[i][1]}"
        mbox.send(pos_str)

    # Mostra resumo
    for i in range(N):
        print(f"Robô {i}: pos={positions[i]}, f={f(*positions[i]):.2f}")
    print(f"Melhor global: {gbest}, f={f(*gbest):.2f}")

print("\nPSO concluído!")