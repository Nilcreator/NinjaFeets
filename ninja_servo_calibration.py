import RPi.GPIO as GPIO
import time
import json
import sys
import curses

# ========== CONFIGURATION ==========
SERVO_PINS = {
    "s0": 16, "s1": 17, "s2": 18, "s3": 19,
}
PWM_FREQ = 50
CALIBRATION_FILE = "servo_calibration.json"

# Default duty cycles for a typical SG90 servo.
# These correspond to the physical 0, 90, and 180-degree positions.
DEFAULT_MIN_DUTY = 2.5   # Corresponds to logical -90
DEFAULT_CENTER_DUTY = 7.5  # Corresponds to logical 0
DEFAULT_MAX_DUTY = 12.5  # Corresponds to logical +90

# ========== HELPER FUNCTIONS ==========

def load_or_create_calibration_data():
    """Loads calibration data or creates a default file if it doesn't exist."""
    try:
        with open(CALIBRATION_FILE, 'r') as f:
            data = json.load(f)
            # Ensure all known servos have an entry
            for servo_id in SERVO_PINS:
                if servo_id not in data:
                    data[servo_id] = {
                        "min_duty": DEFAULT_MIN_DUTY,
                        "center_duty": DEFAULT_CENTER_DUTY,
                        "max_duty": DEFAULT_MAX_DUTY,
                    }
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"'{CALIBRATION_FILE}' not found or corrupt. Creating a new default file.")
        default_data = {}
        for servo_id in SERVO_PINS:
            default_data[servo_id] = {
                "min_duty": DEFAULT_MIN_DUTY,
                "center_duty": DEFAULT_CENTER_DUTY,
                "max_duty": DEFAULT_MAX_DUTY,
            }
        save_calibration_data(default_data)
        return default_data

def save_calibration_data(data):
    """Saves the calibration data to the JSON file."""
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def map_logical_to_duty(logical_angle, calib):
    """Maps a logical angle (-90 to +90) to a calibrated PWM duty cycle."""
    if logical_angle == 0:
        return calib['center_duty']
    elif logical_angle > 0:
        # Map from (0, 90] to (center_duty, max_duty]
        return calib['center_duty'] + (logical_angle / 90.0) * (calib['max_duty'] - calib['center_duty'])
    else: # logical_angle < 0
        # Map from [-90, 0) to [min_duty, center_duty)
        return calib['center_duty'] + (logical_angle / 90.0) * (calib['center_duty'] - calib['min_duty'])

def map_duty_to_logical(duty_cycle, calib):
    """Maps a duty cycle back to a logical angle for display."""
    if abs(duty_cycle - calib['center_duty']) < 0.01:
        return 0.0
    elif duty_cycle > calib['center_duty']:
        return (duty_cycle - calib['center_duty']) / (calib['max_duty'] - calib['center_duty']) * 90.0
    else:
        return (duty_cycle - calib['center_duty']) / (calib['center_duty'] - calib['min_duty']) * 90.0

def parse_servo_selection(args):
    """Parses command-line arguments to get a list of servos to calibrate."""
    if len(args) < 2:
        print("Error: Please specify which servo(s) to calibrate.")
        print(f"Usage: python3 {args[0]} [s0|s1,s2|all]")
        sys.exit(1)
    
    selection = args[1]
    if selection.lower() == 'all':
        return list(SERVO_PINS.keys())
    
    selected_servos = selection.split(',')
    for servo_id in selected_servos:
        if servo_id not in SERVO_PINS:
            print(f"Error: Unknown servo ID '{servo_id}'.")
            sys.exit(1)
    return selected_servos

def draw_ui(stdscr, servo_id, calib, current_duty, message=""):
    """Draws the user interface using curses."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    
    logical_angle = map_duty_to_logical(current_duty, calib)
    
    title = f"--- Ninja Servo Calibration (Calibrating: {servo_id}) ---"
    stdscr.addstr(0, (w - len(title)) // 2, title)
    
    stdscr.addstr(2, 1, f"GPIO Pin: {SERVO_PINS[servo_id]}")
    stdscr.addstr(3, 1, f"Current Duty Cycle: {current_duty:.2f}")
    stdscr.addstr(4, 1, f"Current Logical Angle: {logical_angle:.1f}°")
    
    stdscr.addstr(6, 1, "--- Calibration Values (Duty Cycle) ---")
    stdscr.addstr(7, 1, f"Min    (Logical -90°): {calib['min_duty']:.2f}")
    stdscr.addstr(8, 1, f"Center (Logical   0°): {calib['center_duty']:.2f}")
    stdscr.addstr(9, 1, f"Max    (Logical +90°): {calib['max_duty']:.2f}")
    
    stdscr.addstr(11, 1, "--- Controls ---")
    stdscr.addstr(12, 1, "[w/s] Hold to adjust angle | [x/c/v] Go to Min/Center/Max")
    stdscr.addstr(13, 1, "[X/C/V] Set Min/Center/Max | [n] Next Servo | [q] Quit & Save")
    
    if message:
        stdscr.addstr(h - 2, 1, message)
        
    stdscr.refresh()

def main(stdscr, servos_to_calibrate):
    """Main application logic, wrapped by curses."""
    # Curses setup
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(1)   # Make getch() non-blocking
    stdscr.timeout(100) # Timeout for getch() in ms

    # Load calibration data
    all_calib_data = load_or_create_calibration_data()

    # Initialize all servos and move to center
    pwm_objects = {}
    for servo_id, pin in SERVO_PINS.items():
        GPIO.setup(pin, GPIO.OUT)
        p = GPIO.PWM(pin, PWM_FREQ)
        p.start(0)
        pwm_objects[servo_id] = p
        
        # Move to calibrated center position
        center_duty = all_calib_data[servo_id]['center_duty']
        p.ChangeDutyCycle(center_duty)
    
    time.sleep(1) # Wait for servos to center
    for p in pwm_objects.values():
        p.ChangeDutyCycle(0) # Stop pulses to reduce jitter

    # Loop through each servo selected for calibration
    for servo_id in servos_to_calibrate:
        active_pwm = pwm_objects[servo_id]
        calib = all_calib_data[servo_id]
        current_duty = calib['center_duty']
        
        message = f"Starting calibration for {servo_id}. Press 'n' for next, 'q' to quit."

        # Calibration loop for the current servo
        while True:
            draw_ui(stdscr, servo_id, calib, current_duty, message)
            message = "" # Clear message after one display

            key = stdscr.getch()

            if key == ord('q'):
                # Save and exit entire program
                save_calibration_data(all_calib_data)
                return
            elif key == ord('n'):
                # Move to the next servo in the list
                break
            
            # Continuous movement handling
            if key == ord('w'):
                current_duty += 0.1
            elif key == ord('s'):
                current_duty -= 0.1
            
            # Go to presets
            elif key == ord('x'): current_duty = calib['min_duty']
            elif key == ord('c'): current_duty = calib['center_duty']
            elif key == ord('v'): current_duty = calib['max_duty']
            
            # Set presets
            elif key == ord('X'):
                calib['min_duty'] = round(current_duty, 2)
                message = f"Set {servo_id} MIN to {current_duty:.2f}"
            elif key == ord('C'):
                calib['center_duty'] = round(current_duty, 2)
                message = f"Set {servo_id} CENTER to {current_duty:.2f}"
            elif key == ord('V'):
                calib['max_duty'] = round(current_duty, 2)
                message = f"Set {servo_id} MAX to {current_duty:.2f}"

            # Apply the new duty cycle
            if key != -1: # A key was pressed or held
                # Clamp the duty cycle to a safe absolute range
                current_duty = max(1.0, min(14.0, current_duty))
                active_pwm.ChangeDutyCycle(current_duty)
            else: # No key pressed, stop pulse to reduce jitter
                active_pwm.ChangeDutyCycle(0)

    # After loop finishes
    save_calibration_data(all_calib_data)
    stdscr.addstr(curses.LINES - 1, 0, "All selected servos calibrated. Exiting...")
    stdscr.refresh()
    time.sleep(2)


if __name__ == "__main__":
    # 1. Parse Arguments
    servos_to_calibrate = parse_servo_selection(sys.argv)
    
    # 2. Setup GPIO
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    
    try:
        # 3. Run curses application
        curses.wrapper(main, servos_to_calibrate)
    finally:
        # 4. Cleanup
        print("Cleaning up GPIO...")
        GPIO.cleanup()
        print("Done.")
