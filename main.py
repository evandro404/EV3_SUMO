#!/usr/bin/env pybricks-micropython
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import (Motor, ColorSensor, UltrasonicSensor, InfraredSensor)
from pybricks.parameters import Port, Stop
from pybricks.tools import wait
from pybricks.robotics import DriveBase
from pybricks.media.ev3dev import SoundFile

# --- 1. INICIALIZAÇÃO DOS OBJETOS ---
ev3 = EV3Brick()

# Motores (Portas B e C)
left_motor = Motor(Port.B)
right_motor = Motor(Port.C)

# --- ATENÇÃO: Portas atualizadas conforme sua nova montagem! ---
infrared_sensor = InfraredSensor(Port.S1)
ultrasonic_sensor = UltrasonicSensor(Port.S2)
right_color_sensor = ColorSensor(Port.S3) # Sensor da direita
left_color_sensor = ColorSensor(Port.S4)  # Sensor da esquerda

# Base do Robô
robot = DriveBase(left_motor, right_motor, wheel_diameter=56, axle_track=120)

# --- 2. CONSTANTES E CALIBRAÇÃO ---
# Ajuste estes valores para otimizar o robô NO LOCAL DA COMPETIÇÃO!
WHITE_LINE_THRESHOLD = 50       # Limite de reflexão para a linha branca

# Constantes de Ataque
IR_ATTACK_PROXIMITY = 40        # Limite de proximidade para o ataque do IR (0-100). MENOR = MAIS PERTO.
US_ATTACK_DISTANCE_MM = 400     # Distância em mm para o ataque do Ultrassônico.
# Reduzido para permitir frenagem a tempo
ATTACK_SPEED = -400             # Velocidade de ataque padrão/longa distância (reduzida).
IR_ATTACK_SPEED = -700          # Velocidade de ataque a curta distância (reduzida).

# Constantes de Manobra
RETREAT_DISTANCE = -150         # Distância de recuo ao ver a linha.
SMART_TURN_ANGLE = 120          # Ângulo de giro para a fuga da borda.

# Constantes de Busca Ativa
SEARCH_SPEED = -150             # Velocidade de avanço durante a busca (reduzida para segurança).
SEARCH_CURVE_RATE = 100         # Agressividade da curva na busca.

# Helper: frenagem ativa com pequena espera para estabilizar antes de manobrar
def emergency_stop():
    # Usa frenagem (não coast) e aguarda para reduzir inércia
    robot.stop(Stop.BRAKE)
    wait(150)

# --- 3. PROGRAMA PRINCIPAL ---
wait(1000)

# Loop principal de combate
while True:
    # --- PRIORIDADE 1: EVITAR A BORDA ---
    left_sees_line = left_color_sensor.reflection() > WHITE_LINE_THRESHOLD
    right_sees_line = right_color_sensor.reflection() > WHITE_LINE_THRESHOLD

    if left_sees_line and right_sees_line:
        print("Borda detectada em AMBOS! Perigo!")
        emergency_stop()
        robot.straight(RETREAT_DISTANCE)
        robot.turn(180) # Manobra de emergência
        continue

    elif left_sees_line:
        print("Borda à ESQUERDA! Virando para a direita.")
        emergency_stop()
        robot.straight(RETREAT_DISTANCE)
        robot.turn(SMART_TURN_ANGLE)
        continue
    
    elif right_sees_line:
        print("Borda à DIREITA! Virando para a esquerda.")
        emergency_stop()
        robot.straight(RETREAT_DISTANCE)
        robot.turn(-SMART_TURN_ANGLE)
        continue

    # --- PRIORIDADE 2: ATAQUE CURTA DISTÂNCIA (SENSOR INFRAVERMELHO) ---
    if infrared_sensor.distance() < IR_ATTACK_PROXIMITY:
        print("ALVO PRÓXIMO (IR)! ATAQUE TOTAL!")
        robot.drive(IR_ATTACK_SPEED, 0)
        continue

    # --- PRIORIDADE 3: ATAQUE LONGA DISTÂNCIA (SENSOR ULTRASSÔNICO) ---
    if ultrasonic_sensor.distance() < US_ATTACK_DISTANCE_MM:
        print("Oponente a distância (US)! Aproximando...")
        robot.drive(ATTACK_SPEED, 0)
        continue

    # --- PRIORIDADE 4: PROCURAR OPONENTE (BUSCA ATIVA) ---
    else:
        print("Procurando oponente...")
        robot.drive(SEARCH_SPEED, SEARCH_CURVE_RATE)

    wait(10)