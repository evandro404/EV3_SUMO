#!/usr/bin/env pybricks-micropython
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import (Motor, ColorSensor, UltrasonicSensor, InfraredSensor)
from pybricks.parameters import Port, Stop, Button
from pybricks.tools import wait, StopWatch
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
right_color_sensor = ColorSensor(Port.S4) # Sensor da direita
left_color_sensor = ColorSensor(Port.S3)  # Sensor da esquerda

# Base do Robô
robot = DriveBase(left_motor, right_motor, wheel_diameter=56, axle_track=120)

# --- 2. CONSTANTES E CALIBRAÇÃO ---
# Ajuste estes valores para otimizar o robô NO LOCAL DA COMPETIÇÃO!
WHITE_LINE_THRESHOLD =  50     # Limite de reflexão para a linha branca

# Constantes de Ataque
IR_ATTACK_PROXIMITY = 75        # Limite de proximidade para o ataque do IR (0-100). MENOR = MAIS PERTO.
US_ATTACK_DISTANCE_MM = 180     # Distância em mm para o ataque do Ultrassônico.
# Reduzido para permitir frenagem a tempo
ATTACK_SPEED = -1000             # Velocidade de ataque padrão/longa distância (reduzida).
IR_ATTACK_SPEED = -1000          # Velocidade de ataque a curta distância (reduzida).

# Constantes de Manobra
RETREAT_DISTANCE = 150         # Distância de recuo ao ver a linha.
SMART_TURN_ANGLE = 120          # Ângulo de giro para a fuga da borda.

# Constantes de Busca Ativa
SEARCH_SPEED = -150             # Velocidade de avanço durante a busca (reduzida para segurança).
SEARCH_CURVE_RATE = 100         # Agressividade da curva na busca.

STARTUP_SCAN_DURATION_MS = 2000  # tempo total de varredura inicial
STARTUP_STEP_ANGLE = 25          # pequeno giro para varrer o campo
STARTUP_STEP_WAIT = 150          # espera entre passos de varredura (ms)

# Giro rápido para evasão (graus por segundo)
# Aumentado conforme solicitado — teste na pista por segurança
FAST_TURN_RATE = 1200           # deg/s — velocidade de giro aumentada
FAST_RETREAT_SPEED = -800       # mm/s para recuo rápido
OPPOSITE_TURN_ANGLE = 400       # graus para girar para o lado oposto da detecção

# Se os motores estiverem invertidos (frente/reverso trocados), ajuste para True
# Quando True, os sinais de distância para recuar precisam ser invertidos
MOTORS_INVERTED = True
RETREAT_SIGN = 1 if MOTORS_INVERTED else -1
# Se a orientação física do giro estiver invertida (mapeamento de sinal), ajuste este multiplicador
TURN_DIRECTION_SIGN = -1 if MOTORS_INVERTED else 1

# Helper: frenagem ativa com pequena espera para estabilizar antes de manobrar
def emergency_stop():
    # Usa frenagem (não coast) e aguarda para reduzir inércia
    robot.stop(Stop.BRAKE)
    wait(80)  # espera menor para resposta mais rápida

# Polling rápido para loops mais responsivos (ms)
POLL_MS = 5

# Estado anterior para debouncing de logs
last_state = None

# Varredura inicial para captar o oponente logo após o start
def startup_scan():
    steps = max(1, STARTUP_SCAN_DURATION_MS // STARTUP_STEP_WAIT)
    for i in range(steps):
        # leituras rápidas
        l = left_color_sensor.reflection()
        r = right_color_sensor.reflection()
        ir = infrared_sensor.distance()
        us = ultrasonic_sensor.distance()

        # se há linha, aborta a varredura para não cair
        if l > WHITE_LINE_THRESHOLD or r > WHITE_LINE_THRESHOLD:
            return False

        # detecção imediata via IR (topo, angulado) — detecta partes altas do oponente
        if ir is not None and ir < IR_ATTACK_PROXIMITY:
            print("Startup: alvo detectado por IR — ataque imediato")
            robot.drive(IR_ATTACK_SPEED, 0)
            return True

        # detecção via Ultrassônico — detecta frente baixa do oponente
        if us is not None and us < US_ATTACK_DISTANCE_MM:
            print("Startup: alvo detectado por US — aproximação imediata")
            robot.drive(ATTACK_SPEED, 0)
            return True

        # pequeno giro para varrer a arena rapidamente
        angle = STARTUP_STEP_ANGLE if (i % 2) == 0 else -STARTUP_STEP_ANGLE
        robot.turn(angle)
        wait(STARTUP_STEP_WAIT)

    return False

ev3.screen.clear()
ev3.screen.print("Pressione o botao")
ev3.screen.print("central para")
ev3.screen.print("iniciar.")

# Espera até que o botão do centro seja pressionado
while Button.CENTER not in ev3.buttons.pressed():
    wait(100) # Pausa para não sobrecarregar o processador

# Confirmação de início
ev3.speaker.beep()
ev3.screen.clear()
ev3.screen.print("INICIANDO!")
wait(5200) # Pequena pausa para o operador se afastar

# --- 3. PROGRAMA PRINCIPAL ---
# Executa a varredura inicial logo após o comando do operador
startup_scan()

# Loop principal de combate (otimizado: leituras únicas, estado para logs, polling rápido)
while True:
    # leituras únicas por iteração
    left_ref = left_color_sensor.reflection()
    right_ref = right_color_sensor.reflection()
    ir_dist = infrared_sensor.distance()
    us_dist = ultrasonic_sensor.distance()

    left_sees_line = left_ref > WHITE_LINE_THRESHOLD
    right_sees_line = right_ref > WHITE_LINE_THRESHOLD

    state = None

    # --- PRIORIDADE 1: EVITAR A BORDA ---
    if left_sees_line and right_sees_line:
        state = "EDGE_BOTH"
        if state != last_state:
            print("Borda detectada em AMBOS! Perigo!")
        # parada imediata e estabilização
        robot.stop(Stop.BRAKE)
        wait(40)

        # Recuo bloqueante rápido (usa straight para evitar dirigir para frente)
        try:
            robot.settings(straight_speed=abs(FAST_RETREAT_SPEED), straight_acceleration=3000)
        except Exception:
            pass
        # Ajuste de direção considerando motores invertidos
        robot.straight(RETREAT_SIGN * RETREAT_DISTANCE)
        try:
            robot.settings(straight_speed=300, straight_acceleration=1000)
        except Exception:
            pass

        # Decide direção lógica: sempre virar para o centro (lado oposto à borda detectada)
        # Quando ambos detectam, escolhemos virar para a direita por padrão
        desired_dir = 1  # 1 = direita, -1 = esquerda
        # Calcula taxa física levando em conta possível inversão de giro
        physical_rate = FAST_TURN_RATE * desired_dir * TURN_DIRECTION_SIGN
        # Gira rapidamente usando abordagem drive/stop com fallback para motores
        debug_sw = StopWatch()
        try:
            robot.drive(0, physical_rate)
        except Exception:
            # fallback direto nos motores (usa sinais compatíveis com physical_rate)
            left_motor.run(physical_rate)
            right_motor.run(-physical_rate)
        # calcula duração aproximada para cobrir o angulo desejado (usa magnitude)
        duration_ms = int(abs(OPPOSITE_TURN_ANGLE) / (FAST_TURN_RATE / 1000.0))
        # espera enquanto monitora (curto sleep para responsividade)
        while debug_sw.time() < duration_ms:
            wait(5)
        # garante parada
        try:
            robot.stop(Stop.BRAKE)
        except Exception:
            left_motor.stop(Stop.BRAKE)
            right_motor.stop(Stop.BRAKE)
        wait(80)
        emergency_stop()
        last_state = state
        continue

    elif left_sees_line or right_sees_line:
        state = "EDGE_SIDE"
        if state != last_state:
            print("Borda lateral detectada! Recuo rápido e giro oposto de 240°.")
        # parada imediata e estabilização
        robot.stop(Stop.BRAKE)
        wait(40)

        # Recuo bloqueante rápido
        try:
            robot.settings(straight_speed=abs(FAST_RETREAT_SPEED), straight_acceleration=3000)
        except Exception:
            pass
        # Ajuste de direção considerando motores invertidos
        robot.straight(RETREAT_SIGN * RETREAT_DISTANCE)
        try:
            robot.settings(straight_speed=300, straight_acceleration=1000)
        except Exception:
            pass

        # decide direção lógica: se o sensor esquerdo viu a borda -> virar para a direita (centro)
        if left_sees_line and not right_sees_line:
            desired_dir = 1
        elif right_sees_line and not left_sees_line:
            desired_dir = -1
        else:
            desired_dir = 1

        # calcula taxa física considerando inversão global de giro
        physical_rate = FAST_TURN_RATE * desired_dir * TURN_DIRECTION_SIGN
        # executa giro com fallback
        debug_sw = StopWatch()
        try:
            robot.drive(0, physical_rate)
        except Exception:
            left_motor.run(physical_rate)
            right_motor.run(-physical_rate)
        duration_ms = int(abs(OPPOSITE_TURN_ANGLE) / (FAST_TURN_RATE / 1000.0))
        while debug_sw.time() < duration_ms:
            wait(5)
        try:
            robot.stop(Stop.BRAKE)
        except Exception:
            left_motor.stop(Stop.BRAKE)
            right_motor.stop(Stop.BRAKE)
        wait(80)
        emergency_stop()
        last_state = state
        continue

    # --- PRIORIDADE 2: ATAQUE CURTA DISTÂNCIA (SENSOR INFRAVERMELHO) ---
    if ir_dist is not None and ir_dist < IR_ATTACK_PROXIMITY:
        state = "IR_ATTACK"
        if state != last_state:
            print("ALVO PRÓXIMO (IR)! ATAQUE TOTAL!")
        robot.drive(IR_ATTACK_SPEED, 0)
        last_state = state
        wait(POLL_MS)
        continue

    # --- PRIORIDADE 3: ATAQUE LONGA DISTÂNCIA (SENSOR ULTRASSÔNICO) ---
    if us_dist is not None and us_dist < US_ATTACK_DISTANCE_MM:
        state = "US_ATTACK"
        if state != last_state:
            print("Oponente a distância (US)! Aproximando...")
        # Controle simples: reduz velocidade quando muito perto
        try:
            factor = max(0.5, min(1.0, (US_ATTACK_DISTANCE_MM - us_dist) / US_ATTACK_DISTANCE_MM + 0.5))
            speed = int(ATTACK_SPEED * factor)
        except Exception:
            speed = ATTACK_SPEED
        robot.drive(speed, 0)
        last_state = state
        wait(POLL_MS)
        continue

    # --- PRIORIDADE 4: PROCURAR OPONENTE (BUSCA ATIVA) ---
    state = "SEARCH"
    if state != last_state:
        print("Procurando oponente...")
    robot.drive(SEARCH_SPEED, SEARCH_CURVE_RATE)
    last_state = state

    wait(POLL_MS)