from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor
from pybricks.parameters import Port, Stop
from pybricks.tools import wait
from pybricks.iodevices import UARTDevice
from pybricks.iodevices import PUPDevice
from pybricks.iodevices import WiFi
import usocket as socket

# Inicializa o EV3 e o motor
ev3 = EV3Brick()
motor = Motor(Port.A)

# Conectar no Wi-Fi
ev3.screen.print("Conectando Wi-Fi...")
wifi = WiFi()
wifi.connect("Enxames", "roboenxame")
while not wifi.is_connected():
    wait(100)

ev3.screen.clear()
ev3.screen.print("Wi-Fi Conectado!")

# Conectar no servidor
SERVER_IP = "192.168.1.100"
TCP_PORT = 65432

sock = socket.socket()
sock.connect((SERVER_IP, TCP_PORT))

ev3.speaker.beep()
ev3.screen.clear()
ev3.screen.print("Servidor OK")

# Loop principal
while True:
    data = sock.recv(1024)
    if not data:
        break

    command = data.decode('utf-8').strip()
    ev3.screen.clear()
    ev3.screen.print("Cmd: " + command)

    if command == "start":
        motor.run(400)
    elif command == "stop":
        motor.stop()
    elif command == "shutdown":
        break

motor.stop()
sock.close()
ev3.screen.clear()
ev3.screen.print("Desconectado.")
ev3.speaker.beep()
wait(1000)
