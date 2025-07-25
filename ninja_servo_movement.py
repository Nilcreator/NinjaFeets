import RPi.GPIO as GPIO
import time
import json
import sys
import threading

# ========== CONFIGURATION ==========
CALIBRATION_FILE = "servo_calibration.json"
PWM_FREQ = 50
MIN_MOVE_DELAY = 0.04
MAX_MOVE_DELAY = 0.002

# ========== SERVO CONTROLLER CLASS (Unchanged) ==========

class ServoController:
    """Manages an individual servo motor, including its state and movement thread."""

    def __init__(self, servo_id, pin, calib_data):
        self.servo_id = servo_id
        self.pin = pin
        self.calib_data = calib_data
        
        GPIO.setup(self.pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pin, PWM_FREQ)
        self.pwm.start(0)
        
        self.current_duty = self.calib_data['center_duty']
        self.thread = None
        self.stop_event = threading.Event()

    def _map_logical_to_duty(self, angle_str):
        angle_str = str(angle_str).upper()
        if angle_str == 'M': return self.calib_data['max_duty']
        if angle_str == 'C': return self.calib_data['center_duty']
        if angle_str == 'N': return self.calib_data['min_duty']
        try:
            logical_angle = float(angle_str)
            logical_angle = max(-90.0, min(90.0, logical_angle))
            if logical_angle >= 0:
                return self.calib_data['center_duty'] + (logical_angle / 90.0) * (self.calib_data['max_duty'] - self.calib_data['center_duty'])
            else:
                return self.calib_data['center_duty'] + (logical_angle / 90.0) * (self.calib_data['center_duty'] - self.calib_data['min_duty'])
        except ValueError:
            print(f"Warning: Invalid angle '{angle_str}' for servo {self.servo_id}. Using center.")
            return self.calib_data['center_duty']

    def _move_to_duty(self, target_duty, speed):
        start_duty = self.current_duty
        steps = int(abs(target_duty - start_duty) / 0.1)
        if steps == 0:
            self.pwm.ChangeDutyCycle(0)
            return
        move_delay = MIN_MOVE_DELAY - (speed * (MIN_MOVE_DELAY - MAX_MOVE_DELAY))
        for i in range(steps + 1):
            if self.stop_event.is_set(): return
            duty = start_duty + (target_duty - start_duty) * (i / steps)
            self.pwm.ChangeDutyCycle(duty)
            time.sleep(move_delay)
        self.current_duty = target_duty
        self.pwm.ChangeDutyCycle(0)

    def _run_sequence_thread(self, angles, loop_count, speed):
        loops = 0
        while not self.stop_event.is_set() and (loop_count == 0 or loops < loop_count):
            for angle_str in angles:
                if self.stop_event.is_set(): break
                target_duty = self._map_logical_to_duty(angle_str)
                self._move_to_duty(target_duty, speed)
            loops += 1

    def start_sequence(self, angles, loop_count, speed):
        self.stop()
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run_sequence_thread, args=(angles, loop_count, speed))
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        if self.thread and self.thread.is_alive():
            self.stop_event.set()
            self.thread.join(timeout=0.5)
        self.pwm.ChangeDutyCycle(0)

    def center(self, speed=0.5):
        self.start_sequence(['C'], 1, speed)

    def cleanup(self):
        self.stop()
        self.pwm.stop()

# ========== NEW PARSING AND MAIN LOGIC ==========

def parse_command(command_str):
    """
    Parses a flexible command string into its components.
    Format: s{ID}:angles[,angles...][;L{loops}][;S{speed}]
    Returns a dictionary with parsed values or None if format is invalid.
    """
    try:
        servo_id, payload = command_str.split(':', 1)
    except ValueError:
        return None # Invalid format, missing ':'

    # Set defaults
    loop_count = 1
    speed = 0.5
    
    parts = payload.split(';')
    angles = parts[0].split(',')

    # Parse optional parameters (L and S)
    for part in parts[1:]:
        part = part.strip().upper()
        if not part: continue

        if part.startswith('L'):
            try:
                loop_count = int(part[1:])
            except ValueError:
                print(f"Warning: Invalid loop format '{part}'. Using default L1.")
        elif part.startswith('S'):
            try:
                speed = float(part[1:])
                if not (0.0 <= speed <= 1.0):
                    print(f"Warning: Speed '{part}' out of range (0.0-1.0). Clamping.")
                    speed = max(0.0, min(1.0, speed))
            except ValueError:
                print(f"Warning: Invalid speed format '{part}'. Using default S0.5.")
        else:
            print(f"Warning: Unknown parameter '{part}'. Ignoring.")
            
    return {
        "servo_id": servo_id,
        "angles": angles,
        "loop_count": loop_count,
        "speed": speed
    }

def reset_all_servos(controllers):
    """Stops all movements and smoothly moves all servos to their calibrated center positions."""
    print("Resetting all servos to their calibrated center positions...")
    threads = []
    for controller in controllers.values():
        controller.center(speed=0.7) 
        if controller.thread:
            threads.append(controller.thread)
    for t in threads:
        t.join()
    print("Reset complete.")

def main():
    """Main function to initialize servos and handle user commands."""
    try:
        with open(CALIBRATION_FILE, 'r') as f:
            all_calib_data = json.load(f)
    except FileNotFoundError:
        print(f"FATAL: Calibration file '{CALIBRATION_FILE}' not found.")
        sys.exit(1)

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    
    servo_pins = {"s0": 16, "s1": 17, "s2": 18, "s3": 19}
    controllers = {sid: ServoController(sid, pin, all_calib_data[sid]) for sid, pin in servo_pins.items() if sid in all_calib_data}
        
    reset_all_servos(controllers)
    print("\nReady for commands. Type 'help' for instructions or 'quit' to exit.")

    try:
        while True:
            user_input = input("> ").strip()
            
            if not user_input:
                for controller in controllers.values():
                    controller.stop()
                print("All movements stopped.")
                continue

            if user_input.lower() in ['quit', 'q', 'exit']:
                break
            
            if user_input.lower() == 'help':
                print("\n--- Command Help ---")
                print("Behavior: Robot executes command(s) then automatically resets to center.")
                print("Format:   s{ID}:<angles>[;L<loops>][;S<speed>]")
                print("  - angles: Comma-separated (M, C, N, or -90 to 90)")
                print("  - L<loops>: Optional loop count (e.g., L5, L0 for infinite). Default: L1")
                print("  - S<speed>: Optional speed (e.g., S0.75). Default: S0.5")
                print("\nExamples:")
                print("  s0:M,C,N;L2;S0.2  (Full command)")
                print("  s1:N,M;L3         (Default speed)")
                print("  s2:45,-45;S0.9    (Default loop)")
                print("  s3:C,M            (Default loop and speed)")
                print("\nOther Commands:")
                print("  Parallel:  command1 | command2")
                print("  Reset Now: reset")
                print("  Stop All:  Press Enter\n")
                continue
            
            if user_input.lower() == 'reset':
                reset_all_servos(controllers)
                continue

            finite_threads = []
            has_infinite_loop = False

            commands = [cmd.strip() for cmd in user_input.split('|')]
            for command in commands:
                # Use the new flexible parser
                parsed_data = parse_command(command)
                
                if parsed_data is None:
                    print(f"Error: Invalid command format for '{command}'. Type 'help'.")
                    continue

                servo_id = parsed_data["servo_id"]
                if servo_id not in controllers:
                    print(f"Error: Unknown servo ID '{servo_id}'")
                    continue
                
                controllers[servo_id].start_sequence(
                    parsed_data["angles"],
                    parsed_data["loop_count"],
                    parsed_data["speed"]
                )
                
                if parsed_data["loop_count"] != 0:
                    finite_threads.append(controllers[servo_id].thread)
                else:
                    has_infinite_loop = True
            
            if finite_threads:
                print("Executing command(s)... (waiting for completion)")
                for t in finite_threads:
                    t.join()
                
                if not has_infinite_loop:
                    print("Command sequence complete.")
                    reset_all_servos(controllers)
                else:
                    print("Finite movements complete. Infinite loops are still running.")

    finally:
        print("\nExiting. Cleaning up GPIO...")
        for controller in controllers.values():
            controller.cleanup()
        GPIO.cleanup()
        print("Done.")

if __name__ == "__main__":
    main()
