#!/usr/bin/env pybricks-micropython
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import (Motor, ColorSensor, UltrasonicSensor, InfraredSensor)
from pybricks.parameters import Port, Stop, Button
from pybricks.tools import wait, StopWatch
from pybricks.robotics import DriveBase

# Estratégia alternativa agressiva para Sumo LEGO
# Sensores e portas seguem o layout de main.py:
# - InfraredSensor: Port.S1 (topo, angulado)
# - UltrasonicSensor: Port.S2 (centro, baixo)
# - left ColorSensor: Port.S3
# - right ColorSensor: Port.S4

# --- Inicialização ---
ev3 = EV3Brick()
left_motor = Motor(Port.B)
right_motor = Motor(Port.C)
infrared_sensor = InfraredSensor(Port.S1)
ultrasonic_sensor = UltrasonicSensor(Port.S2)
left_color = ColorSensor(Port.S3)
right_color = ColorSensor(Port.S4)
robot = DriveBase(left_motor, right_motor, wheel_diameter=56, axle_track=120)

# --- Constantes ---
WHITE_LINE_THRESHOLD = 50
IR_DETECT = 75            # sensibilidade aumentada para detectar oponente alto
US_DETECT_MM = 200        # detecta até ~20 cm
FULL_ATTACK_SPEED = -900  # força total (mais seguro que -1100)
SPIN_RPM_FAST = 600       # velocidade de giro rápido (mais segura)
PUSH_MAX_MS = 2000        # tempo máximo de push contínuo
POLL_MS = 10

# Debugging
DEBUG = True

def debug_print(*args):
    if DEBUG:
        try:
            print(*args)
        except Exception:
            pass

# Helper: frenagem e estabilização
def emergency_stop(ms=120):
    robot.stop(Stop.BRAKE)
    wait(ms)

# Verifica borda e executa evasão imediata se detectada
def check_and_handle_edge():
    l = left_color.reflection()
    r = right_color.reflection()
    debug_print('EDGE CHECK -> left=', l, ' right=', r, ' threshold=', WHITE_LINE_THRESHOLD)
    if l > WHITE_LINE_THRESHOLD and r > WHITE_LINE_THRESHOLD:
        ev3.speaker.beep()
        debug_print('EDGE: BOTH detected - evasão 180')
        emergency_stop()
        robot.straight(150)
        robot.turn(180)
        return True
    if l > WHITE_LINE_THRESHOLD:
        debug_print('EDGE: LEFT detected - evasão direita')
        emergency_stop()
        robot.straight(120)
        robot.turn(90)
        return True
    if r > WHITE_LINE_THRESHOLD:
        debug_print('EDGE: RIGHT detected - evasão esquerda')
        emergency_stop()
        robot.straight(120)
        robot.turn(-90)
        return True
    return False

# Empurra com força total enquanto o oponente for detectado ou até timeout
def full_push_with_feedback(max_ms=PUSH_MAX_MS):
    start = StopWatch()
    robot.drive(FULL_ATTACK_SPEED, 0)  # força total
    debug_print('FULL PUSH start speed=', FULL_ATTACK_SPEED, ' max_ms=', max_ms)
    while start.time() < max_ms:
        # aborta se borda detectada
        if check_and_handle_edge():
            debug_print('FULL PUSH aborted due to edge')
            break
        # continua se ainda detectar oponente por IR ou US
        ir = infrared_sensor.distance()
        us = ultrasonic_sensor.distance()
        debug_print('FULL PUSH loop t=', start.time(), ' ir=', ir, ' us=', us)
        if (ir is None or ir >= IR_DETECT) and (us is None or us >= US_DETECT_MM):
            # perdeu o oponente; interrompe o push
            debug_print('FULL PUSH: alvo perdido -> interrompendo')
            break
        wait(POLL_MS)
    emergency_stop()
    debug_print('FULL PUSH ended')

# Gira rápido controlado e verifica sensores continuamente
# direction: 1 para direita, -1 para esquerda
def spin_and_scan(duration_ms=600, speed=SPIN_RPM_FAST, direction=1):
    debug_print('SPIN AND SCAN start duration=', duration_ms, ' speed=', speed, ' dir=', direction)
    target_turn = speed * direction
    # gira em torno do próprio eixo usando DriveBase.drive (velocidade 0, taxa de giro em deg/s)
    try:
        robot.drive(0, target_turn)
    except Exception:
        # fallback para controle direto dos motores se robot.drive não estiver disponível
        left_motor.run(speed * direction)
        right_motor.run(-speed * direction)
    sw = StopWatch()
    found = False
    while sw.time() < duration_ms:
        if check_and_handle_edge():
            found = False
            debug_print('SPIN aborted due to edge')
            break
        ir = infrared_sensor.distance()
        us = ultrasonic_sensor.distance()
        debug_print('SPIN loop t=', sw.time(), ' ir=', ir, ' us=', us)
        if (ir is not None and ir < IR_DETECT) or (us is not None and us < US_DETECT_MM):
            debug_print('SPIN: alvo detectado')
            found = True
            break
        wait(POLL_MS)
    # garante parada independente do método usado
    try:
        robot.stop(Stop.BRAKE)
    except Exception:
        left_motor.stop(Stop.BRAKE)
        right_motor.stop(Stop.BRAKE)
    wait(80)
    debug_print('SPIN AND SCAN end found=', found)
    return found

# Varredura focal: olha para um lado, gira rápido para o outro e ataca se encontrar
def aggressive_hunt_cycle():
    debug_print('HUNT CYCLE start')
    # 1) Olha levemente para a esquerda
    robot.turn(-30)
    wait(80)
    ir = infrared_sensor.distance()
    us = ultrasonic_sensor.distance()
    debug_print('HUNT look left ir=', ir, ' us=', us)
    if (ir is not None and ir < IR_DETECT) or (us is not None and us < US_DETECT_MM):
        debug_print('HUNT: alvo detectado ao virar para a esquerda -> push')
        full_push_with_feedback()
        return
    # 2) Gira rápido para a direita procurando alvo
    found = spin_and_scan(duration_ms=700, speed=SPIN_RPM_FAST, direction=1)
    if found:
        debug_print('HUNT: alvo detectado no spin para a direita -> push')
        full_push_with_feedback()
        return
    # 3) Olha para a direita
    robot.turn(60)
    wait(80)
    ir = infrared_sensor.distance()
    us = ultrasonic_sensor.distance()
    debug_print('HUNT look right ir=', ir, ' us=', us)
    if (ir is not None and ir < IR_DETECT) or (us is not None and us < US_DETECT_MM):
        debug_print('HUNT: alvo detectado ao virar para a direita -> push')
        full_push_with_feedback()
        return
    # 4) Gira rápido para a esquerda procurando alvo
    found = spin_and_scan(duration_ms=700, speed=SPIN_RPM_FAST, direction=-1)
    if found:
        debug_print('HUNT: alvo detectado no spin para a esquerda -> push')
        full_push_with_feedback()
        return
    # 5) Pequeno avanço agressivo para forçar contato caso seja um robô grande
    debug_print('HUNT: sem alvo - avanço agressivo curto')
    robot.drive(-600, 0)
    wait(300)
    emergency_stop()

# --- Inicio: mantém o esquema pedido ---
ev3.screen.clear()
ev3.screen.print('Pressione o botao')
ev3.screen.print('central para')
ev3.screen.print('iniciar.')

# Espera até que o botão do centro seja pressionado
while Button.CENTER not in ev3.buttons.pressed():
    wait(100)

# Confirmação de início
ev3.speaker.beep()
ev3.screen.clear()
ev3.screen.print('INICIANDO!')
wait(5200) # Pequena pausa para o operador se afastar

# Loop principal: caça agressiva com proteção de borda
while True:
    # Prioridade máxima: borda
    if check_and_handle_edge():
        continue

    # Checa sensores frontais rápidos; se detectar, ataque total
    ir = infrared_sensor.distance()
    us = ultrasonic_sensor.distance()
    debug_print('MAIN LOOP sensors ir=', ir, ' us=', us)
    if (ir is not None and ir < IR_DETECT) or (us is not None and us < US_DETECT_MM):
        debug_print('MAIN LOOP: alvo detectado -> full_push_with_feedback')
        full_push_with_feedback()
        continue

    # Executa ciclo de caça agressivo (olhar para um lado + giro rápido)
    aggressive_hunt_cycle()

    # pequena pausa para evitar loop demasiado apertado
    wait(50)
