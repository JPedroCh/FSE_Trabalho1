#!/usr/bin/env python3

import socket
import sys
from _thread import *
import threading
import json
import time
# import board
# import adafruit_dht
# import RPi.GPIO as GPIO

listen_lock = threading.Lock()
dht22_lock = threading.Lock()
count_lock = threading.Lock()
first_message = True
actual_status = {}
outputs_status = []
temp = 0
hum = 0
qtd_pessoas = 0
alarm_system = False
seconds_counter = 0
config_data = {}
start_time_entering = 0
end_time_entering = 0
start_time_leaving = 0
end_time_leaving = 0
s = []


# thread function
def listen_socket():
    global s
    while True:
        data = s.recv(1024)
        if not data:
            print('Message not received')
             
            break
        
        # trata a mensagem recebida
        decode_message(data)

        time.sleep(1)
        # treat the data received
        # read_message_received()


def read_dht22():
    temp = 0
    hum = 0
    global config_data
    if(config_data["sensor_temperatura"][0]["gpio"] == 4):
      gpio = board.D4
    elif(config_data["sensor_temperatura"][0]["gpio"] == 18):
      gpio = board.D18
    while True:
        dht = adafruit_dht.DHT22(gpio,use_pulseio = False)
        temp = dht.temperature
        hum = dht.humidity
        actual_status["temp"] = temp
        actual_status["hum"] = hum
        time.sleep(2)
    
  
def fake_read_dht22():
  global temp, hum, actual_status
  temp = 1
  hum = 3
  while True:
      actual_status["temp"] = temp
      actual_status["hum"] = hum
      temp += 2
      hum += 1
      time.sleep(2)

def fake_count_people():
  global qtd_pessoas, actual_status
  qtd_pessoas = 0
  while True:
      actual_status["pessoas"] = qtd_pessoas
      qtd_pessoas += 1
      time.sleep(2)

def count_entering_people():
  global qtd_pessoas, actual_status, config_data

  # 0.1s ~ 0.3s = 1 pessoa 
  pauser = False

  entering_pin = config_data["inputs"][4]["gpio"]
  if(actual_status["inputs"][4]["status"] == False):
    while True:
        GPIO.add_event_detect(entering_pin, GPIO.BOTH)
        if GPIO.event_detected(entering_pin):
              entering_clicker(pauser)
              pauser = True

def entering_clicker(pauser):
  global start_time_entering, end_time_entering
  if(pauser == False):
    start_time_entering = time.time()
  else:
    end_time_entering = time.time()
    calculate_number_people_entering()

def calculate_number_people_entering():
  global start_time_entering, end_time_entering
  full_time = end_time_entering - start_time_entering
  qtd_pessoas += round(full_time/0.2)

def count_leaving_people():
  global qtd_pessoas, actual_status, config_data

  # 0.1s ~ 0.3s = 1 pessoa 
  pauser = False

  leaving_pin = config_data["inputs"][5]["gpio"]
  if(actual_status["inputs"][5]["status"] == False):
    while True:
        GPIO.add_event_detect(leaving_pin, GPIO.BOTH)
        if GPIO.event_detected(leaving_pin):
              leaving_clicker(pauser)
              pauser = True

def leaving_clicker(pauser):
  global start_time_leaving, end_time_leaving
  if(pauser == False):
    start_time_leaving = time.time()
  else:
    end_time_leaving = time.time()
    calculate_number_people_leaving()

def calculate_number_people_leaving():
  global start_time_leaving, end_time_leaving
  full_time = end_time_leaving - start_time_leaving
  qtd_pessoas -= round(full_time/0.2)


def run_app( data_config):
  global actual_status, outputs_status, seconds_counter, s
  actual_status = data_config
  actual_status["temp"] = -1
  actual_status["hum"] = -1
  actual_status["pessoas"] = 0
  # thread de ouvir o socket
  listen_lock.acquire()
  start_new_thread(listen_socket, ())
  # thread de leitura do DHT22
  dht22_lock.acquire()
  # start_new_thread(read_dht22, ())
  start_new_thread(fake_read_dht22, ())
  # thread de contagem de pessoas
  count_lock.acquire()
  # start_new_thread(count_entering_people, ())
  # start_new_thread(count_leaving_people, ())
  start_new_thread(fake_count_people, ())

  #desliga todos os outputs
  for y in data_config["outputs"]:
      # GPIO.output(y["gpio"], False)
      outputs_status.append(False)

  while(True):
    input_values = []
    global first_message

    # lê os valores da gpio
    for x in data_config["inputs"]:
      # input_t = GPIO.input(x["gpio"])
      input_t = 1
      if(input_t == 1):
        input_values.append(True)
      elif(input_t == 0):
        input_values.append(False)
    
    for i, x in enumerate(actual_status["inputs"]):
      x["status"] = input_values[i]
    
    for i, x in enumerate(actual_status["outputs"]):
      x["status"] = outputs_status[i]

    if(input_values[0] == True and alarm_system == True):
      activate_buzzer()

   # [WIP] acende as duas lâmpadas da sala por 15 segundos e depois apaga
    #if(input_values[0] == True and alarm_system == True):

    # envia a mensagem para o socket
    # print("MENSAGEM ENVIADA, sent = ", build_json_message())
    try:
      sent = s.send(build_json_message().encode('utf-8')) 
    except:
      print("Erro ao tentar enviar mensagem, tentando novamento...")
      s.close()
      init_socket()
      
    first_message = False

    # dorme por 1s
    seconds_counter += 1
    time.sleep(1)
  
  # libera as threads
  listen_lock.release()
  dht22_lock.release()
  count_lock.release()

def init_socket():
  global config_data, s, first_message
  first_message = True
  host = config_data["ip_servidor_central"]
  port = config_data["porta_servidor_central"]
  while(1):
    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.connect((host, port))
      print('Connected to :', config_data["ip_servidor_central"], ':', config_data["porta_servidor_central"])
      break
    except:
      print("Erro ao conectar, tentando novamente...")
      time.sleep(1)


def main():
  print("Running main...")
  global config_data, s
  # Ler o arquivo de configuracao
  config_data = load_config()

  # Inicializa o socket
  init_socket()

  # Iniciar a gpio
  # initialize_gpio(config_data)

  # Rodar o loop do servidor distribuido com as threads
  run_app( config_data)
  # GPIO.cleanup()

def load_config():
  f = open('config.json')
  config_data = json.load(f)
  f.close()
  return config_data

def initialize_gpio(config_data):
  inputs = config_data['inputs']
  outputs = config_data['outputs']

  GPIO.setmode(GPIO.BCM)

  for x in config_data['inputs']:
    GPIO.setup(x["gpio"], GPIO.IN)
  
  for y in config_data['outputs']:
    GPIO.setup(y["gpio"], GPIO.OUT)

def activate_buzzer():
  global actual_status
  # GPIO.output(actual_status["outputs"][4]["gpio"], GPIO.HIGH)
  actual_status["outputs"][4]["status"] = True

 # acende as duas lâmpadas da sala por 15 segundos e depois apaga;
def turn_all_lights(status):
  global actual_status
  pins = [actual_status["outputs"][0]["gpio"], actual_status["outputs"][1]["gpio"]]
  # GPIO.output(pins, status)
  actual_status["outputs"][0]["status"] = status
  actual_status["outputs"][1]["status"] = status

def build_json_message():
  global first_message, temp, hum, actual_status
  message_json = {"ip_servidor_distribuido": actual_status["ip_servidor_distribuido"]}
  message_json["porta_servidor_distribuido"] =  actual_status["porta_servidor_distribuido"]
  message_json["nome"] = actual_status["nome"]
  message_json["inputs"] = actual_status["inputs"]
  message_json["outputs"] = actual_status["outputs"]
  message_json["config_message"] = first_message
  message_json["temp"] = actual_status["temp"]
  message_json["hum"] = actual_status["hum"]
  message_json["pessoas"] = actual_status["pessoas"]

  jsonString = json.dumps(message_json)
  return jsonString

def decode_message(data):
  global actual_status, alarm_system
  message = json.loads(data)
  print("\n\n COMMAND = ", message)
  command = message["comando"]

  if(command["ordem"] == True):
    # GPIO.output(command["alvo"], GPIO.HIGH)
    for i, output in enumerate(actual_status["outputs"]):
      for alvo in command["alvo"]:
        if(output["gpio"] == alvo):
          actual_status["outputs"][i]["status"] = True
  elif (command["ordem"] == False):
    # GPIO.output(command["alvo"], GPIO.LOW)
    for i, output in enumerate(actual_status["outputs"]):
      for alvo in command["alvo"]:
        if(output["gpio"] == alvo):
          actual_status["outputs"][i]["status"] = False
  elif (command["ordem"] == "sistema de alarme ligado"):
    alarm_system = True
  elif (command["ordem"] == "sistema de alarme desligado"):
    alarm_system = False

main()
