import RPi.GPIO as GPIO
import time
import curses

# This script has a dual purpose:
# 1. It can be IMPORTED by other scripts to use the BuzzerController class.
# 2. It can be RUN DIRECTLY to launch a full-featured interactive music toy.

class BuzzerController:
    """A controller class for the buzzer, handling note generation and playback."""
    
    NOTES = {
        'P': 0, 'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23, 'G4': 392.00, 'A4': 440.00, 'B4': 493.88,
        'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'F5': 698.46, 'G5': 783.99, 'A5': 880.00, 'B5': 987.77,
        'C6': 1046.50, 'D6': 1174.66, 'E6': 1318.51, 'F6': 1396.91, 'G6': 1567.98, 'A6': 1760.00, 'B6': 1975.53,
    }

    def __init__(self, pin=23):
        self.pin = pin
        # The class now ALWAYS sets up its own pin as an output.
        # The calling script is responsible for GPIO.setmode().
        GPIO.setup(self.pin, GPIO.OUT)
        
        self.pwm = GPIO.PWM(self.pin, 100)
        self.pwm.start(0)

    def play_note(self, note, duration):
        frequency = self.NOTES.get(note, 0)
        if frequency > 0:
            self.pwm.ChangeFrequency(frequency)
            self.pwm.ChangeDutyCycle(50)
            time.sleep(duration)
            self.pwm.ChangeDutyCycle(0)
        else:
            time.sleep(duration)

    def play_note_pair(self, harmony_note, melody_note, total_duration=0.4):
        self.play_note(harmony_note, total_duration * 0.25)
        self.play_note(melody_note, total_duration * 0.75)

    def cleanup(self):
        self.pwm.stop()
        # The class does not call GPIO.cleanup(), the main script does.
        # This allows multiple controllers to be used without conflict.

# --- The following code only runs when this script is executed directly ---
if __name__ == "__main__":

    KEY_NOTES_INTERACTIVE = {
        ord('a'): 'C4', ord('s'): 'D4', ord('d'): 'E4', ord('f'): 'F4', ord('g'): 'G4', ord('h'): 'A4', ord('j'): 'B4',
        ord('A'): 'C5', ord('S'): 'D5', ord('D'): 'E5', ord('F'): 'F5', ord('G'): 'G5', ord('H'): 'A5', ord('J'): 'B5',
    }

    def draw_main_screen(stdscr):
        stdscr.clear()
        stdscr.addstr(0, 0, "--- Ninja Buzzer Interactive Mode ---")
        stdscr.addstr(2, 0, "Type a command, 'help' for options, or 'quit' to exit.")
        stdscr.addstr(4, 0, "Input: ")
        stdscr.refresh()

    def draw_help_screen(stdscr):
        stdscr.clear()
        stdscr.addstr(0, 0, "--- Ninja Buzzer Help ---")
        stdscr.addstr(2, 0, "This is an interactive musical toy. There are two main modes:")
        stdscr.addstr(4, 0, "1. COMMAND MODE (Current)")
        stdscr.addstr(5, 2, "Type a command and press Enter.")
        stdscr.addstr(6, 4, "'live'      - Enter real-time Live Play Mode.")
        stdscr.addstr(7, 4, "'C4,D4,E5'  - Play a sequence of notes (comma-separated).")
        stdscr.addstr(8, 4, "'quit'      - Exit the program.")
        stdscr.addstr(10, 0, "2. LIVE PLAY MODE")
        stdscr.addstr(11, 2, "Once in Live Play Mode, press keys to play notes instantly.")
        stdscr.addstr(12, 4, "Press 'q' inside Live Play Mode to return here.")
        stdscr.addstr(14, 0, "KEYBOARD MAP FOR LIVE PLAY:")
        stdscr.addstr(15, 2, "Middle Octave: [a] [s] [d] [f] [g] [h] [j]")
        stdscr.addstr(16, 2, "High Octave:   [A] [S] [D] [F] [G] [H] [J] (Shift + key)")
        stdscr.addstr(curses.LINES - 1, 0, "Press any key to return to the main command screen...")
        stdscr.refresh()
        stdscr.getch()

    def live_play_mode(stdscr, buzzer):
        stdscr.clear()
        stdscr.addstr(0, 0, "--- Live Play Mode --- (Press 'q' to exit)")
        stdscr.addstr(2, 0, "Last Note: ")
        stdscr.refresh()
        
        while True:
            key = stdscr.getch()
            if key == ord('q'): break
            if key in KEY_NOTES_INTERACTIVE:
                note = KEY_NOTES_INTERACTIVE[key]
                stdscr.addstr(2, 11, f"{note}   ")
                stdscr.refresh()
                buzzer.play_note(note, 0.15)

    def interactive_main(stdscr):
        # The main interactive function creates the buzzer instance.
        # The `setup_gpio=False` argument has been removed.
        buzzer = BuzzerController(pin=23)
        while True:
            draw_main_screen(stdscr)
            curses.echo()
            cmd = stdscr.getstr(4, 7).decode('utf-8').strip()
            curses.noecho()

            if cmd.lower() == 'quit': break
            if cmd.lower() == 'help':
                draw_help_screen(stdscr)
                continue
            if cmd.lower() == 'live':
                live_play_mode(stdscr, buzzer)
                continue
            
            notes = cmd.split(',')
            for note in notes:
                buzzer.play_note(note.strip(), 0.3)

    # Setup and run the curses application
    try:
        # Set global GPIO settings here
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        curses.wrapper(interactive_main)
    finally:
        # Perform the final cleanup here
        print("\nCleaning up GPIO...")
        GPIO.cleanup()
