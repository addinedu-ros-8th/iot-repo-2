import RPi.GPIO as GPIO
import socket
from time import sleep
import threading

# Servo motor configuration
SERVO_PIN = 38
SERVO_MIN_DUTY = 3
SERVO_MAX_DUTY = 12

# GPIO setup
GPIO.setmode(GPIO.BOARD)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# Initialize PWM for the servo motor
servo = GPIO.PWM(SERVO_PIN, 50)  # 50Hz PWM
servo.start(0)  # Start with duty cycle 0

# Function to set the servo angle
def set_servo_degree(degree):
    degree = max(0, min(degree, 180))  # Limit to 0-180 degrees
    duty = SERVO_MIN_DUTY + (degree * (SERVO_MAX_DUTY - SERVO_MIN_DUTY) / 180)
    print(f"Setting servo to {degree} degrees -> Duty cycle: {duty}")

    servo.ChangeDutyCycle(duty)
    sleep(0.1)  # Allow servo movement
    servo.ChangeDutyCycle(0)  # Stop signal (prevent jittering)

# Server configuration
SERVER_IP = '0.0.0.0'  # Listen on all available interfaces
SERVER_PORT = 6000
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Enable port reuse
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server.bind((SERVER_IP, SERVER_PORT))
server.listen(5)  # Allow up to 5 simultaneous connections
print(f"Listening for incoming connections on {SERVER_IP}:{SERVER_PORT}")

# Function to handle incoming client connections
def handle_client(client_socket, addr):
    print(f"New connection from {addr}")
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if not message:
                break

            print(f"Received message: {message}")

            # Control the servo based on the received message
            if 'parking/1/flame1/detected' in message:
                set_servo_degree(120)
            elif 'parking/1/flame2/detected' in message:
                set_servo_degree(140)
            elif 'parking/1/flame3/detected' in message:
                set_servo_degree(40)
            elif 'parking/1/flame4/detected' in message:
                set_servo_degree(70)
            # If 'none' is received, set to 90 degrees
            elif 'parking/1/flame' in message and 'none' in message:
                set_servo_degree(90)

        except ConnectionResetError:
            print(f"Connection lost with {addr}")
            break

    client_socket.close()

# Main loop to accept client connections (from ESP32 or other devices)
try:
    while True:
        client_socket, addr = server.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
        client_thread.daemon = True  # Make the thread daemon so it exits when the main program exits
        client_thread.start()

except KeyboardInterrupt:
    print("Program interrupted")

finally:
    servo.stop()
    GPIO.cleanup()
    server.close()
