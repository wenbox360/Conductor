import lgpio
import time
import threading
import sys

# --- Pin Definitions (using BCM numbering) ---
# Please change these to the actual BCM pin numbers you have connected
LED_PIN = None
SERVO_PIN = None
BUZZER_PIN = None


from pins import *
# NOTE: The IR_PIN from the Arduino code is an analog pin.
# Raspberry Pi does not have a built-in Analog-to-Digital Converter (ADC).
# To read from an analog IR sensor, you will need an external ADC module
# like an MCP3008. The `ir_sensor_reading` function is a placeholder.

# --- Global Variables ---
h = None  # Handle for the GPIO chip
last_ir_send_time = 0
IR_INTERVAL = 0.2  # 200ms in seconds

def setup():
    """
    Initializes GPIO using the lgpio library for Raspberry Pi 5.
    """
    global h, last_ir_send_time

    # Open the default GPIO chip (chip 0 on RPi 5)
    h = lgpio.gpiochip_open(0)

    # Claim the LED pin for output
    if LED_PIN is not None:
        lgpio.gpio_claim_output(h, LED_PIN)

    # The servo and buzzer pins are controlled via PWM functions,
    # which handle claiming the pins implicitly.

    last_ir_send_time = time.time()
    print("Setup complete using lgpio.")

def servo_write(angle):
    """
    Sets the servo to a specific angle using lgpio.
    Converts angle (0-180) to a pulse width in microseconds (500-2500).
    """
    if h is None: return
    # Clamp angle to a safe range
    angle = max(0, min(180, angle))
    # Map angle to pulse width
    pulse_width_us = int(500 + (angle / 180.0) * 2000)

    # Send the servo pulse. 50Hz is the standard frequency for servos.
    if SERVO_PIN is not None:
        lgpio.tx_servo(h, SERVO_PIN, pulse_width_us, 50)
        print(f"Servo set to {angle} degrees (pulse width {pulse_width_us}us).")

    # Allow time for the servo to move to the position
    time.sleep(0.5)

    # Stop sending the PWM signal to prevent servo jitter and save power
    lgpio.tx_servo(h, SERVO_PIN, 0, 50)

def ir_sensor_reading():
    """
    Placeholder for reading from an IR sensor via an ADC.
    *** IMPLEMENTATION REQUIRED ***
    You need to add the code here to read from your specific ADC module.
    For an MCP3008, you might use the 'spidev' or 'adafruit-circuitpython-mcp3xxx' library.
    """
    # For now, it returns a dummy value.
    return 512

def buzzer_duration(duration_ms):
    """
    Turns on the buzzer for a specified duration using lgpio's PWM.
    """
    if h is None: return
    frequency = 1000  # 1kHz
    duty_cycle = 50   # 50% "volume"

    # Start PWM signal
    if BUZZER_PIN is None:
        return
    lgpio.tx_pwm(h, BUZZER_PIN, frequency, duty_cycle)
    time.sleep(duration_ms / 1000.0)

    # Stop PWM signal (by setting duty cycle to 0)
    lgpio.tx_pwm(h, BUZZER_PIN, frequency, 0)
    print(f"Buzzer on for {duration_ms}ms.")

def led_on():
    """Turns the LED on."""
    if h is None: return
    if LED_PIN is None: return
    lgpio.gpio_write(h, LED_PIN, 1)
    print("LED ON.")

def led_off():
    """Turns the LED off."""
    if h is None: return
    if LED_PIN is None: return
    lgpio.gpio_write(h, LED_PIN, 0)
    print("LED OFF.")

def process_command(cmd):
    """
    Parses and executes a command received from standard input.
    """
    print(f"Processing command: '{cmd}'")
    try:
        command = 0
        param = 0

        # Split command and parameter if a comma is present
        if ',' in cmd:
            parts = cmd.split(',')
            command = int(parts[0])
            param = int(parts[1])
        else:
            command = int(cmd)

        # --- Command Handling ---
        if command == 2:  # Piezo test
            buzzer_duration(200)
            print("A", flush=True)
        elif command == 20:  # Servo write
            servo_write(param)
            print("A", flush=True)
        elif command == 30:  # LED write
            if param == 1:
                led_on()
            else:
                led_off()
            print("A", flush=True)
        else:
            print("E", flush=True) # Unknown command
            print(f"Unknown command code: {command}")

    except (ValueError, IndexError) as e:
        print("E", flush=True) # Malformed command
        print(f"Error processing command '{cmd}': {e}")


def command_reader_thread():
    """
    A dedicated thread to read commands from standard input (e.g., SSH).
    """
    print("\nReady for commands. Type a command and press Enter.")
    for line in sys.stdin:
        command = line.strip()
        if command:
            process_command(command)

def main_loop():
    """
    The main execution loop, responsible for periodically sending IR data.
    """
    global last_ir_send_time
    while True:
        current_time = time.time()
        # Check if it's time to send the IR reading
        if current_time - last_ir_send_time >= IR_INTERVAL:
            last_ir_send_time = current_time
            ir_value = ir_sensor_reading()

            # Construct and send the message to standard output
            #message = f"40,{ir_value}"
            #print(message, flush=True)

        time.sleep(0.05)


if __name__ == '__main__':
    try:
        setup()
        # Start the command reader in its own thread
        reader = threading.Thread(target=command_reader_thread, daemon=True)
        reader.start()
        print("Starting main loop...")
        main_loop()
    except KeyboardInterrupt:
        print("\nProgram interrupted. Cleaning up...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # This cleanup is crucial to release GPIO resources.
        if h:
            # Explicitly stop any running PWM signals
            if BUZZER_PIN is not None:
                lgpio.tx_pwm(h, BUZZER_PIN, 1000, 0)
            if SERVO_PIN is not None:
                lgpio.tx_servo(h, SERVO_PIN, 0, 50)

            # Close the GPIO chip handle, which releases all claimed resources
            lgpio.gpiochip_close(h)
            print("GPIO cleaned up. Exiting.")