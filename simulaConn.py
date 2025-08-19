#!/usr/bin/env python3
import socket
import time

# --- Configurações (devem ser iguais às do robô e servidor) ---
TCP_PORT = 65432
UDP_PORT = 65431
DISCOVERY_REQUEST = b"EV3_DISCOVERY_REQUEST"
DISCOVERY_RESPONSE = b"EV3_SERVER_HERE"

# --- Variáveis de Estado do Robô Simulado ---
# Mantém o controle da posição e direção atuais do robô
posicao_atual = [0, 0]
direcoes_cardinais = ['N', 'L', 'S', 'O'] # Norte, Leste, Sul, Oeste
direcao_atual = 'N'

def discover_server():
  """Encontra o IP do servidor na rede local via broadcast UDP."""
  print("[DISCOVERY] Procurando pelo servidor na rede...")
  with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(5.0)  # Espera no máximo 5 segundos por uma resposta
    
    while True:
      try:
        print("[DISCOVERY] Enviando broadcast de descoberta...")
        s.sendto(DISCOVERY_REQUEST, ('<broadcast>', UDP_PORT))
        data, addr = s.recvfrom(1024)
        if data == DISCOVERY_RESPONSE:
          print(f"[DISCOVERY] Servidor encontrado em: {addr[0]}")
          return addr[0]
      except socket.timeout:
        print("[AVISO] Servidor não encontrado. Tentando novamente em 5s...")
        time.sleep(5)
      except Exception as e:
        print(f"[ERRO] Falha na descoberta: {e}")
        return None

def atualizar_direcao(giro):
  """Atualiza a direção cardeal do robô com base no giro."""
  global direcao_atual, direcoes_cardinais
  
  indice_atual = direcoes_cardinais.index(direcao_atual)
  
  if giro.lower() == 'direita':
    novo_indice = (indice_atual + 1) % len(direcoes_cardinais)
  elif giro.lower() == 'esquerda':
    novo_indice = (indice_atual - 1 + len(direcoes_cardinais)) % len(direcoes_cardinais)
  direcao_atual = direcoes_cardinais[novo_indice]

def simular_movimento_frente_tras(passos):
  """Simula o movimento para frente ou para trás atualizando a posição."""
  global posicao_atual, direcao_atual
  if direcao_atual == 'N':
    posicao_atual[1] += passos
  elif direcao_atual == 'S':
    posicao_atual[1] -= passos
  elif direcao_atual == 'L':
    posicao_atual[0] += passos
  elif direcao_atual == 'O':
    posicao_atual[0] -= passos

def processar_comandos(client_socket):
  """Loop principal para receber e processar comandos do servidor."""
  global posicao_atual, direcao_atual
  try:
    while True:
      # Espera por um comando do servidor
      command_bytes = client_socket.recv(1024)
      if not command_bytes:
        print("[CONEXÃO] O servidor fechou a conexão.")
        break
      
      command = command_bytes.decode('utf-8')
      print(f"\n[SERVIDOR] Comando recebido: '{command}'")

      # --- Processamento dos comandos ---
      if command.startswith("ir:"):
        try:
          _, coords = command.split(':')
          x_str, y_str = coords.split(';')
          x_alvo, y_alvo = int(x_str), int(y_str)

          print(f"--> Simulando movimento de {posicao_atual} para [{x_alvo}, {y_alvo}]...")
          time.sleep(2) # Simula o tempo que o robô leva para se mover
          posicao_atual = [x_alvo, y_alvo]
          print(f"--> Movimento concluído. Nova posição: {posicao_atual}")
          
          mensagem = f"pos:{posicao_atual[0]};{posicao_atual[1]}"
          client_socket.sendall(mensagem.encode('utf-8'))
          print(f"[ROBÔ] Posição atualizada enviada: '{mensagem}'")

        except Exception as e:
          print(f"[ERRO] Falha ao processar comando 'ir': {e}")
      
      elif command == 'frente':
        print("--> Simulando: Mover para frente...")
        simular_movimento_frente_tras(1)
        print(f"--> Nova posição: {posicao_atual}")

      elif command == 'tras':
        print("--> Simulando: Mover para trás...")
        simular_movimento_frente_tras(-1)
        print(f"--> Nova posição: {posicao_atual}")

      elif command == 'esquerda':
        print("--> Simulando: Girar para a esquerda...")
        atualizar_direcao('esquerda')
        print(f"--> Nova direção: {direcao_atual}")

      elif command == 'direita':
        print("--> Simulando: Girar para a direita...")
        atualizar_direcao('direita')
        print(f"--> Nova direção: {direcao_atual}")

      elif command == 'posicao':
        mensagem = f"pos:{posicao_atual[0]};{posicao_atual[1]}"
        client_socket.sendall(mensagem.encode('utf-8'))
        print(f"[ROBÔ] Posição atual enviada: '{mensagem}'")

      elif command == 'desligar':
        print("[ROBÔ] Comando de desligamento recebido. Encerrando.")
        break
      
      else:
        print(f"[AVISO] Comando desconhecido: '{command}'")

  except ConnectionResetError:
    print("[ERRO] Conexão com o servidor foi perdida.")
  except Exception as e:
    print(f"[ERRO] Ocorreu um erro inesperado na comunicação: {e}")


# --- Lógica Principal do Robô Simulado ---
if __name__ == "__main__":
  server_ip = discover_server()

  if server_ip:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
      # Conecta ao servidor
      print(f"[TCP] Conectando ao servidor em {server_ip}:{TCP_PORT}...")
      client_socket.connect((server_ip, TCP_PORT))
      print("[TCP] Conectado com sucesso!")

      # 1. Envia a mensagem de saudação inicial (como no robô real)
      client_socket.sendall(b"Ola, sou um EV3!")
      print("[ROBÔ] Mensagem de saudação enviada.")
      
      # 2. Envia a posição inicial (como no robô real)
      posicao_atual = [0, 0] 
      direcao_atual = 'N'
      initial_pos_msg = f"pos:{posicao_atual[0]};{posicao_atual[1]}"
      client_socket.sendall(initial_pos_msg.encode('utf-8'))
      print(f"[ROBÔ] Posição inicial ({posicao_atual}) e direção ('{direcao_atual}') definidas e enviadas.")
      
      # 3. Entra no loop de escuta e processamento de comandos
      processar_comandos(client_socket)

    except ConnectionRefusedError:
      print("[ERRO] Conexão recusada. Verifique se o servidor está rodando e acessível.")
    except KeyboardInterrupt:
      print("\n[SAINDO] Interrupção do usuário. Desconectando...")
    except Exception as e:
      print(f"[ERRO] Ocorreu um erro inesperado na execução principal: {e}")
    finally:
      print("[FIM] Fechando o socket do cliente.")
      client_socket.close()