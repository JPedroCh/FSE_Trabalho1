#!/usr/bin/env python3

import socket
import sys
from _thread import *
from threading import Thread
from datetime import datetime
import json
import sys,os
import curses
from curses.textpad import rectangle
import time

salas_info = []
command = -1
fire_alarm = False
alarm_buzz = False
alarm_system = False
selected_sala = -1
message_backup = {}
turn_on_commands = [
  [1, 'Ligar Lâmpada 01'], [2, 'Ligar Lâmpada 02'], [3, 'Ligar Projeto Multimídia'], 
  [4, 'Ligar Ar-Condicionado'], [5,'Ligar todas as lâmpadas'], [6, 'Ligar todos aparelhos']
]
turn_off_commands = [
  ['b', 'Desligar Lâmpada 01'], ['c', 'Desligar Lâmpada 02'], ['d', 'Desligar Projeto Multimídia'], 
  ['e', 'Desligar Ar-Condicionado'], ['f','Desligar todas as lâmpadas'], ['g', 'Desligar todos aparelhos']
]

def decode_command (code, outputs):
  global selected_sala
  decoded_command = []

  # ligar
  if(code == ord("1")):
    decoded_command = [True, [outputs[0]["gpio"]]]
    add_to_log(f"Ligar lâmpada 01 da {selected_sala}")
  elif(code == ord("2")):
    decoded_command = [True, [outputs[1]["gpio"]]]
    add_to_log(f"Ligar lâmpada 02 da {selected_sala}")
  elif(code == ord("3")):
    decoded_command = [True, [outputs[2]["gpio"]]]
    add_to_log(f"Ligar projetor da {selected_sala}")
  elif(code == ord("4")):
    decoded_command = [True, [outputs[3]["gpio"]]]
    add_to_log(f"Ligar ar-condicionado da {selected_sala}")
  # todas as lâmpadas
  elif(code == ord("5")):
    decoded_command = [True, [outputs[0]["gpio"], outputs[1]["gpio"]]]
    add_to_log(f"Ligar todas as lâmpadas da {selected_sala}")
  # todos os outputs
  elif(code == ord("6")):
    decoded_command = [True, [outputs[0]["gpio"], outputs[1]["gpio"], outputs[2]["gpio"], outputs[3]["gpio"]]]
    add_to_log(f"Ligar todos aparelhos da {selected_sala}")

  #desligar
  if(code == ord("b")):
    decoded_command = [False, [outputs[0]["gpio"]]]
    add_to_log(f"Desligar lâmpada 01 da {selected_sala}")
  elif(code == ord("c")):
    decoded_command = [False, [outputs[1]["gpio"]]]
    add_to_log(f"Desligar lâmpada 02 da {selected_sala}")
  elif(code == ord("d")):
    decoded_command = [False, [outputs[2]["gpio"]]]
    add_to_log(f"Desligar projetor da {selected_sala}")
  elif(code == ord("e")):
    decoded_command = [False, [outputs[3]["gpio"]]]
    add_to_log(f"Desligar ar-condicionado da {selected_sala}")
  # todas as lampadas
  elif(code == ord("f")):
    decoded_command = [False, [outputs[0]["gpio"], outputs[1]["gpio"]]]
    add_to_log(f"Desligar todas as lâmpadas da {selected_sala}")
  # todos os outputs
  elif(code == ord("g")):
    decoded_command = [False, [outputs[0]["gpio"], outputs[1]["gpio"], outputs[2]["gpio"], outputs[3]["gpio"]]]
    add_to_log(f"Desligar todos aparelhos da {selected_sala}")
  return decoded_command

# cria mensagem de comando
def build_command_message(order, target, addr, nome_sala ):
  global message_backup
  message_json = {"comando": {}}
  temp = {}
  temp["ordem"] = order
  temp["alvo"] = target

  temp_addr = {}
  temp_addr["ip"] = addr[0]
  temp_addr["nome"] = nome_sala

  message_json["comando"] = [temp, temp_addr]
  message_backup = message_json
  return message_json

def main ():
  global salas_info
  if len(sys.argv) != 3:
    print(f"Uso: {sys.argv[0]} <host> <port>")
    sys.exit(1)

  host, port = sys.argv[1], int(sys.argv[2])

  socket_thread = Thread(target=init_socket, args=(str(host),int(port),))
  socket_thread.start()

  interface_thread = Thread(target= curses.wrapper, args=(render_interface,))
  interface_thread.start()
  interface_thread.join()


# envia comando
def send_command(conn, addr):
    global command, salas_info, fire_alarm, alarm_buzz, alarm_system

    gpio = -1
    value = -1
    while True:
        if(fire_alarm and not alarm_buzz):
            # chama o buzzer
            activate_buzzer(conn, addr)

        # time.sleep(0.09)

        # verifica se uma tecla foi pressionada (diff do valor inicial), 
        # se sim verifica se foi a tecla de escape do terminal (break no while)
        # ou se foi a tecla do alarme
        if(command == -1):
            continue
        elif(command == curses.ascii.ESC):
            break
        elif(command == ord('a')):
            if(not alarm_system):
                activate_alarm_system(conn, addr)
            else:
                alarm_system = False
                alarm_buzz = False
        
        # [WIP] desligar o sistema de alarme
        elif(command == ord('p')):
            if(not alarm_system):
                deactivate_alarm_system(conn, addr)
            else:
                alarm_system = False
                alarm_buzz = False
        
        # De acordo com a tecla pressionada gerar o log
        # e também gerar a mensagem para ser enviada com o comando
        message = ''
        for sala in salas_info:
          if(command == -1 or command == ord('0') or command == ord('9') or command == ord('a') or command == ord('p')): break
          # sala selecionada
          elif(selected_sala == sala["nome"]):
            decoded_message = decode_command(command, sala["outputs"])
            message = build_command_message(decoded_message[0], decoded_message[1], addr, selected_sala)
            break
        command = -1

        if(message != ''):
          
          message_sent = conn.send(json.dumps(message).encode('utf-8'))
          if not message_sent: break
        time.sleep(0.5)

def activate_buzzer(conn, addr):
    global salas_info, alarm_buzz
    for i, sala in enumerate(salas_info):
        for j, sala_output in enumerate(sala["outputs"]):
            if(sala_output["type"] == 'alarme'):
                if(not sala_output["status"]):
                    add_to_log(f"Ligar sirene")
                    message = build_command_message(True, [sala_output["gpio"]], addr, sala["nome"])
                    try:
                      
                      conn.send(json.dumps(message).encode('utf-8'))
                      salas_info[i]["outputs"][j]["status"] = True
                      alarm_buzz = True
                    except:
                      salas_info[i]["outputs"][j]["status"] = False

# sistema de alarme só é ativado se todos os inputs estiverem desligados
def activate_alarm_system(conn, addr):
    global salas_info, alarm_system, alarm_buzz
    alarm_system = not alarm_system
    if(alarm_system):
        for sala in salas_info:
            for sala_input in sala["inputs"]:
                if(sala_input["status"]):
                    alarm_system = False
                    break
    if(alarm_system):
        message = build_command_message("sistema de alarme ligado", [], addr, "Todas")
        
        conn.send(json.dumps(message).encode('utf-8'))
        add_to_log("Ligar sistema de alarme")
        alarm_system_thread = Thread(target=alarm_routine)
        alarm_system_thread.start()
    else:
        alarm_buzz = False

def deactivate_alarm_system(conn, addr):
    global alarm_system
    alarm_system = not alarm_system
    if(alarm_system):
        add_to_log("Desligar sistema de alarme")
        message = build_command_message("sistema de alarme desligado", [], addr, "Todas")
        
        conn.send(json.dumps(message).encode('utf-8'))
        alarm_system_thread.join()
    else:
        alarm_buzz = False

# rotina do sistema de alarme 
# se algum input detectar algo, o buzzer é acionado
def alarm_routine():
    global salas_info, alarm_system, alarm_buzz
    while alarm_system and not alarm_buzz:
        for sala in salas_info:
            for sala_input in sala["inputs"]:
                if(sala_input["status"] and not alarm_buzz):
                    alarm_buzz = True
                    activate_buzzer(conn, addr)
                    break
        if not alarm_system: break
        time.sleep(0.5)

def insert_into_salas_info(actual_status):
  global salas_info
  for i,sala in enumerate(salas_info):
    if(actual_status["nome"] == sala["nome"]):
      salas_info.remove(sala)
      salas_info.insert(i, actual_status)

def remove_from_salas_info(actual_status):
  global salas_info
  for i,sala in enumerate(salas_info):
    if(actual_status["nome"] == sala["nome"]):
      salas_info.remove(sala)



# funcao responsavel por ouvir o servidor distribuído
def listen_socket(conn, addr   ):
    global salas_info, fire_alarm
    while True:
        try:
          data = conn.recv(2048)
          actual_status = decode_message(data.decode('utf-8'))
          if(actual_status["config_message"] == True):
            salas_info.append(actual_status)
          else:  
            insert_into_salas_info(actual_status)
          
          if(actual_status["inputs"][1]["status"] == True):
            fire_alarm = True
          else:
            fire_alarm = False


          if not data:
              break
        except:
          remove_from_salas_info(actual_status)
          break
    conn.close()

def init_socket(host: str, port: int):

  
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  s.bind(('0.0.0.0', port))
  s.listen()

  while True:
      conn, addr  = s.accept()
      
      # thread para ouvir o servidor distribuído
      listen_socket_thread = Thread(target=listen_socket, args=(conn, addr ))
      listen_socket_thread.start()

      # thread para envio dos comandos
      send_command_thread = Thread(target=send_command, args=(conn, addr ))
      send_command_thread.start()

def decode_message(data):
  message = json.loads(data)
  return message


def render_interface(stdscr):
    global salas_info, command, alarm_buzz, alarm_buzz, alarm_system, selected_sala, message_backup

    stdscr.clear()
    stdscr.refresh()
    stdscr.nodelay(True)

    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.curs_set(0)

    while(command != curses.ascii.ESC):

        stdscr.erase()
        height, width = stdscr.getmaxyx()

        title = f"Servidor Central -> {sys.argv[1]}:{sys.argv[2]}"[:width-1]
        title_x = int((width // 2) - (len(title) // 2) - len(title) % 2)
        stdscr.addstr(0, title_x, title, curses.color_pair(1))
      

        if(len(salas_info) == 0):
          footer = "Pressione 'Esc' para sair"
        if(len(salas_info) == 1):
          n_sala = salas_info[0]["nome"]
          footer = f"Pressione 'Esc' para sair | 'a' para ligar alarme | 'p' para desligar alarme | '0' para selecionar {n_sala} "
        if(len(salas_info) > 1):
          n_sala = salas_info[0]["nome"]
          n_sala2 = salas_info[1]["nome"]
          footer = f"Pressione 'Esc' para sair | 'a' para ligar alarme | 'p' para desligar alarme | '0' para selecionar {n_sala} | '9' para seleciona {n_sala2} "
        stdscr.attron(curses.color_pair(3))
        stdscr.addstr(height-1, 0, footer)
        stdscr.addstr(height-1, len(footer), " " * (width - len(footer) - 1))
        stdscr.attroff(curses.color_pair(3))

        mid_x = width // 2
        subbar_h = 10
        rectangle_h = height - subbar_h
        margin_x = 2
        line = 5

        stdscr.attron(curses.color_pair(1))
        rectangle(stdscr, 1, 0, rectangle_h, mid_x)
        rectangle(stdscr, 1, mid_x, rectangle_h, width-1)
        rectangle(stdscr, rectangle_h+1, 0, rectangle_h+subbar_h-2, mid_x)
        rectangle(stdscr, rectangle_h+1, mid_x, rectangle_h+subbar_h-2, width-1)
        stdscr.attroff(curses.color_pair(1))

        stdscr.addstr(rectangle_h+1, margin_x, "Instruções")
        stdscr.addstr(rectangle_h+1, margin_x+mid_x, "Alarmes")
        stdscr.addstr(rectangle_h+2, margin_x, f"1 - Aperte a tecla mostrada no rodapé para selecionar a sala", curses.color_pair(2))
        stdscr.addstr(rectangle_h+3, margin_x, f"2 - Aperte a tecla corresponde ao comando que deseja executar", curses.color_pair(2))

        if(len(salas_info) >= 1):
            nome_sala0 = salas_info[0]["nome"]
            qtd_pessoas_sala0 = salas_info[0]["pessoas"]
            temp = salas_info[0]["temp"]
            hum = salas_info[0]["hum"]
            key_line = line+4+len(salas_info[0]["outputs"])+len(salas_info[0]["inputs"])
            stdscr.addstr(2, margin_x, f"Temperatura: {temp} Cº", curses.color_pair(2))
            stdscr.addstr(3, margin_x, f"Umidade: {hum} %", curses.color_pair(2))
            stdscr.addstr(4, margin_x, f"Quantidade de pessoas na sala: {qtd_pessoas_sala0}", curses.color_pair(2))
            print_IO(stdscr, line+2, margin_x, salas_info[0]["inputs"], "input")
            print_IO(stdscr, line+4+len(salas_info[0]["outputs"]), margin_x, salas_info[0]["outputs"], "output")
            print_command_keys(stdscr, key_line, margin_x)
        else:
            nome_sala0 = f"Sem conexão!"
        if(selected_sala == nome_sala0):
          stdscr.addstr(1, margin_x, nome_sala0, curses.color_pair(3))
        else:
          stdscr.addstr(1, margin_x, nome_sala0)

        if(len(salas_info) >= 2):
            nome_sala1 = salas_info[1]["nome"]
            qtd_pessoas_sala1 = salas_info[1]["pessoas"]
            temp = salas_info[1]["temp"]
            hum = salas_info[1]["hum"]
            stdscr.addstr(2, mid_x+margin_x, f"Temperatura: {temp} Cº", curses.color_pair(2))
            stdscr.addstr(3, mid_x+margin_x, f"Umidade: {hum} %", curses.color_pair(2))
            stdscr.addstr(4, mid_x+margin_x, f"Quantidade de pessoas na sala: {qtd_pessoas_sala1}", curses.color_pair(2))
            stdscr.addstr(5, mid_x+margin_x, f"Quantidade de pessoas no prédio: {qtd_pessoas_sala1 + qtd_pessoas_sala0} ", curses.color_pair(2))
            stdscr.addstr(5, margin_x, f"Quantidade de pessoas no prédio: {qtd_pessoas_sala1 + qtd_pessoas_sala0} ", curses.color_pair(2))
            print_IO(stdscr, line+2, mid_x+margin_x, salas_info[1]["inputs"], "input")
            print_IO(stdscr, line+4+len(salas_info[1]["outputs"]), mid_x+margin_x, salas_info[1]["outputs"], "output")
            print_command_keys(stdscr, key_line, mid_x+margin_x)
        else:
            nome_sala1 = f"Sem conexão!"
        if(selected_sala == nome_sala1):
          stdscr.addstr(1, margin_x+mid_x, nome_sala1, curses.color_pair(3))
        else:
          stdscr.addstr(1, margin_x+mid_x, nome_sala1)

        # alarme de incêndio
        stdscr.addstr(rectangle_h+2, margin_x+mid_x, f"Alarme de incêndio".ljust(28, '.'), curses.color_pair(2))
        if(fire_alarm):
            stdscr.addstr(rectangle_h+2, margin_x+mid_x+30, f"ON", curses.color_pair(5))
        else:
            stdscr.addstr(rectangle_h+2, margin_x+mid_x+30, f"OFF", curses.color_pair(6))

        # sirene
        stdscr.addstr(rectangle_h+3, margin_x+mid_x, f"Sirene".ljust(28, '.'), curses.color_pair(2))
        if(alarm_buzz):
          stdscr.addstr(rectangle_h+3, margin_x+mid_x+30, f"ON", curses.color_pair(5))
        else:  
          stdscr.addstr(rectangle_h+3, margin_x+mid_x+30, f"OFF", curses.color_pair(6))

        # sistema de alarme
        stdscr.addstr(rectangle_h+4, margin_x+mid_x, f"Sistema de alarme".ljust(28, '.'), curses.color_pair(2))
        if(alarm_system):
            stdscr.addstr(rectangle_h+4, margin_x+mid_x+30, f"ON", curses.color_pair(5))
        else:
            stdscr.addstr(rectangle_h+4, margin_x+mid_x+30, f"OFF", curses.color_pair(6))
            stdscr.addstr(rectangle_h+5, margin_x+mid_x, f"Para ativar feche todas portas e janelas e evacue todas pessoas", curses.color_pair(6))

        stdscr.refresh()
        command = stdscr.getch()
        if(command == ord("0")):
          selected_sala = n_sala
        elif(command == ord("9")):
          selected_sala = n_sala2

        time.sleep(0.09)

# apresenta os inputs e outputs e seus estados
def print_IO(stdscr, lineStart: int, margin_x: int, ios: list, IO_type: str):
    for i, io in enumerate(ios):
        input_status = io["status"]
        io_color = curses.color_pair(5)
        if(input_status == True):
          input_status = "ON"
        else:
          input_status = "OFF"
          io_color = curses.color_pair(6)
        input_tag = io["tag"].ljust(50, ".")
        
        stdscr.addstr(lineStart, margin_x+5, f"{input_tag}", curses.color_pair(2))
        stdscr.addstr(lineStart, margin_x+ 60, f"{input_status}", io_color)
        lineStart += 1

# apresenta as teclas e os comandos
def print_command_keys(stdscr, lineStart: int, margin_x: int):
    global turn_on_commands, turn_off_commands

    stdscr.addstr(lineStart, margin_x+5, f"COMANDO", curses.color_pair(2))
    stdscr.addstr(lineStart, margin_x+ 58, f"TECLA", curses.color_pair(2))
    lineStart += 1
    for i, command_key in enumerate(turn_on_commands):
        key_explanation = command_key[1].ljust(50, ".")
  
        stdscr.addstr(lineStart, margin_x+5, f"{key_explanation}", curses.color_pair(2))
        stdscr.addstr(lineStart, margin_x+ 60, f"{command_key[0]}", curses.color_pair(1))
        lineStart += 1
    lineStart += 1
    for i, command_key in enumerate(turn_off_commands):
        key_explanation = command_key[1].ljust(50, ".")
  
        stdscr.addstr(lineStart, margin_x+5, f"{key_explanation}", curses.color_pair(2))
        stdscr.addstr(lineStart, margin_x+ 60, f"{command_key[0]}", curses.color_pair(1))
        lineStart += 1

def add_to_log(text: str):
    log = open('log.csv', 'a')
    log.write(f"{datetime.now()}, {text}\n")
    log.close()

main()