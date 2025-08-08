#!/usr/bin/env pybricks-micropython
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import (Motor, ColorSensor, UltrasonicSensor)
from pybricks.parameters import Port, Stop
from pybricks.tools import wait
from pybricks.robotics import DriveBase
from pybricks.media.ev3dev import SoundFile


# --- 1. INICIALIZAÇÃO DOS OBJETOS ---
ev3 = EV3Brick()

# Motores (Verifique se as portas B e C estão corretas)
left_motor = Motor(Port.B)
right_motor = Motor(Port.C)

# Sensores: Assumindo a posição dos sensores. Altere conforme sua montagem.
# Corrigido: Adicionado o prefixo "Port." que estava faltando.
left_color_sensor = ColorSensor(Port.S3)  # Sensor da esquerda
right_color_sensor = ColorSensor(Port.S2) # Sensor da direita
ultrasonic_sensor = UltrasonicSensor(Port.S4)

# Base do Robô (Meça e ajuste o diâmetro da roda e a distância entre eixos)
robot = DriveBase(left_motor, right_motor, wheel_diameter=56, axle_track=120)

# --- 2. CONSTANTES E CALIBRAÇÃO ---
# Ajuste estes valores para otimizar o robô.
WHITE_LINE_THRESHOLD = 50  # Limite de reflexão para a linha branca
ATTACK_DISTANCE_MM = 400   # Distância em mm para iniciar o ataque
ATTACK_SPEED = -1000       # Velocidade de ataque (negativa para ir para frente)
RETREAT_DISTANCE = -200    # Distância de recuo (negativa para ir para trás)
SEARCH_TURN_RATE = 170     # Velocidade de giro ao procurar
SMART_TURN_ANGLE = 100     # Ângulo de giro para a retirada inteligente

# --- 3. PROGRAMA PRINCIPAL ---
#ev3.speaker.set_volume(50)
#ev3.speaker.play_file(SoundFile.HORN_1)
print("Pronto para o combate!")
wait(1000)

# Loop principal de combate
while True:
    # --- PRIORIDADE 1: EVITAR A BORDA (LÓGICA MELHORADA) ---
    # Verifica de forma inteligente qual sensor detectou a linha
    if left_color_sensor.reflection() > WHITE_LINE_THRESHOLD:
        print("Borda detectada à ESQUERDA! Virando para a direita.")
        robot.stop()
        robot.straight(RETREAT_DISTANCE / 2) # Recua um pouco
        robot.turn(SMART_TURN_ANGLE)         # Vira para a direita para escapar
        continue
    
    elif right_color_sensor.reflection() > WHITE_LINE_THRESHOLD:
        print("Borda detectada à DIREITA! Virando para a esquerda.")
        robot.stop()
        robot.straight(RETREAT_DISTANCE / 2) # Recua um pouco
        robot.turn(-SMART_TURN_ANGLE)        # Vira para a esquerda para escapar
        continue


    # --- PRIORIDADE 2: ATACAR OPONENTE ---
    if ultrasonic_sensor.distance() < ATTACK_DISTANCE_MM:
        print("Oponente detectado! Atacar!")
        robot.drive(ATTACK_SPEED, 0)
        continue

    # --- PRIORIDADE 3: PROCURAR OPONENTE ---
    else:
        print("Procurando...")
        robot.drive(0, SEARCH_TURN_RATE)

    wait(10)