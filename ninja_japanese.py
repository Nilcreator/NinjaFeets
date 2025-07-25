from ninja_buzzer import BuzzerController
import time
import re
import RPi.GPIO as GPIO

# ========== 1. MUSICAL & LINGUISTIC MAPPING (ENHANCED) ==========

# --- Rhythm and Tempo ---
BPM = 120
QUARTER_NOTE_DURATION = 60 / BPM
NOTE_DURATIONS = {
    "whole": QUARTER_NOTE_DURATION * 4,
    "half": QUARTER_NOTE_DURATION * 2,
    "quarter": QUARTER_NOTE_DURATION,
    "eighth": QUARTER_NOTE_DURATION / 2,
    "sixteenth": QUARTER_NOTE_DURATION / 4, # Added for more precise rests
}
# --- UPDATED: Changed rest duration between words ---
# The rest is now a "quarter rest" in name, but corresponds to a 16th note in duration (~0.125s)
# to match the requested timing.
INTER_WORD_REST_DURATION = NOTE_DURATIONS["sixteenth"]

# --- Redefined Mood Templates ---
MOOD_TEMPLATES = {
    "happy": ["quarter"],
    "sad": ["whole"],
    "excited": ["eighth"],
    "angry": ["half"],
}
DEFAULT_RHYTHM = MOOD_TEMPLATES["happy"]

# --- Japanese Hiragana to Phonetic/Musical Maps (Unchanged) ---
VOWEL_NOTE_MAP = {'a': 'C4', 'i': 'D4', 'u': 'E4', 'e': 'G4', 'o': 'A4'}
CONSONANT_NOTE_MAP = {'': 'P', 'k': 'C5', 's': 'D5', 't': 'E5', 'n': 'F5', 'h': 'G5', 'm': 'A5', 'y': 'B5', 'r': 'C6', 'w': 'D6'}
HIRAGANA_MAP = {
    'あ': ('', 'a'), 'い': ('', 'i'), 'う': ('', 'u'), 'え': ('', 'e'), 'お': ('', 'o'), 'か': ('k', 'a'), 'き': ('k', 'i'), 'く': ('k', 'u'), 'け': ('k', 'e'), 'こ': ('k', 'o'),
    'さ': ('s', 'a'), 'し': ('s', 'i'), 'す': ('s', 'u'), 'せ': ('s', 'e'), 'そ': ('s', 'o'), 'た': ('t', 'a'), 'ち': ('t', 'i'), 'つ': ('t', 'u'), 'て': ('t', 'e'), 'と': ('t', 'o'),
    'な': ('n', 'a'), 'に': ('n', 'i'), 'ぬ': ('n', 'u'), 'ね': ('n', 'e'), 'の': ('n', 'o'), 'は': ('h', 'a'), 'ひ': ('h', 'i'), 'ふ': ('h', 'u'), 'へ': ('h', 'e'), 'ほ': ('h', 'o'),
    'ま': ('m', 'a'), 'み': ('m', 'i'), 'む': ('m', 'u'), 'め': ('m', 'e'), 'も': ('m', 'o'), 'や': ('y', 'a'), 'ゆ': ('y', 'u'), 'よ': ('y', 'o'),
    'ら': ('r', 'a'), 'り': ('r', 'i'), 'る': ('r', 'u'), 'れ': ('r', 'e'), 'ろ': ('r', 'o'), 'わ': ('w', 'a'), 'を': ('w', 'o'), 'ん': ('n_moraic', ''),
}
ALL_HIRAGANA = "".join(HIRAGANA_MAP.keys())

# ========== 2. TRANSLATION & PARSING LOGIC (Unchanged) ==========

def translate_word_to_music(hiragana_word, rhythm_pattern):
    music_sequence = []
    last_pair_and_duration = (('P', 'P'), NOTE_DURATIONS["quarter"])
    mora_index = 0
    for char in hiragana_word:
        if char == 'ん':
            music_sequence.append(last_pair_and_duration)
            mora_index += 1
            continue
        duration_name = rhythm_pattern[mora_index % len(rhythm_pattern)]
        duration_sec = NOTE_DURATIONS.get(duration_name, QUARTER_NOTE_DURATION)
        consonant_group, vowel = HIRAGANA_MAP[char]
        harmony_note = CONSONANT_NOTE_MAP.get(consonant_group, 'P')
        melody_note = VOWEL_NOTE_MAP.get(vowel, 'P')
        current_data = ((harmony_note, melody_note), duration_sec)
        music_sequence.append(current_data)
        last_pair_and_duration = current_data
        mora_index += 1
    return music_sequence

def parse_input(user_input):
    text = user_input
    rhythm = DEFAULT_RHYTHM
    mood_match = re.search(r'--mood\s+(\w+)', text)
    if mood_match:
        mood = mood_match.group(1).lower()
        if mood in MOOD_TEMPLATES:
            rhythm = MOOD_TEMPLATES[mood]
            print(f"Info: Using '{mood}' mood rhythm.")
        else:
            print(f"Warning: Mood '{mood}' not found. Using default 'happy' rhythm.")
        text = re.sub(r'--mood\s+\w+', '', text).strip()
    custom_rhythm_match = re.search(r'\[(.*?)\]', text)
    if custom_rhythm_match:
        rhythm_str = custom_rhythm_match.group(1)
        custom_rhythm = [r.strip() for r in rhythm_str.split(',')]
        if all(r in NOTE_DURATIONS for r in custom_rhythm):
            rhythm = custom_rhythm
            print("Info: Using custom rhythm.")
        else:
            print("Warning: Invalid custom rhythm. Using default.")
        text = re.sub(r'\[.*?\]', '', text).strip()
    return text, rhythm

def show_help():
    """Displays the help guide with updated rest information."""
    help_text = f"""
--- Japanese Hiragana to Music Translator Help ---

This script translates hiragana text into musical notes with rhythm and plays it.

**BASIC USAGE**
Simply type the hiragana text and press Enter. The default mood is 'happy'.
> さくら

**WORD SEPARATION**
Use spaces or any non-hiragana character to separate words. A short quarter-rest
(approx. {INTER_WORD_REST_DURATION:.3f}s) will be automatically inserted between them.
> あなた ありがとう

**SPECIFYING A MOOD**
Use the '--mood' flag to apply a predefined rhythm to all notes.
> にんじゃ --mood excited

Available Moods:
  - happy:    Quarter notes (Default)
  - sad:      Whole notes
  - excited:  Eighth notes
  - angry:    Half notes

**SPECIFYING A CUSTOM RHYTHM**
Provide a comma-separated list of durations in square brackets.
> ゆめ [whole,half]

Available Durations:
  - whole, half, quarter, eighth, sixteenth

**OTHER COMMANDS**
  - help: Shows this help message.
  - quit: Exits the program.
"""
    print(help_text)

# ========== 3. MAIN APPLICATION (Updated Rest Logic) ==========

def main():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    buzzer = BuzzerController()
    
    print("--- Japanese Hiragana to Music Translator (v3.1) ---")
    print("Type 'help' for instructions or 'quit' to exit.")

    try:
        while True:
            user_input = input("\nHiragana > ").strip()
            if not user_input: continue
            
            if user_input.lower() == 'quit': break
            if user_input.lower() == 'help':
                show_help()
                continue

            hiragana_text, rhythm_pattern = parse_input(user_input)
            
            parts = re.split(f'([^{ALL_HIRAGANA}]+)', hiragana_text)
            
            full_music_sequence = []
            is_first_part = True
            for part in parts:
                if not part: continue

                if part[0] in ALL_HIRAGANA:
                    word_sequence = translate_word_to_music(part, rhythm_pattern)
                    full_music_sequence.extend(word_sequence)
                elif not is_first_part:
                    # Use the new, shorter quarter-rest duration
                    full_music_sequence.append((('P', 'P'), INTER_WORD_REST_DURATION))
                
                is_first_part = False

            if not full_music_sequence:
                print("No valid hiragana found in input.")
                continue

            # Create a readable version of the sequence for printing
            # This part is a bit complex but makes the output user-friendly
            duration_to_name = {v: k for k, v in NOTE_DURATIONS.items()}
            printable_sequence = []
            for (pair, sec) in full_music_sequence:
                # Find the closest duration name for printing
                duration_name = duration_to_name.get(sec, f"{sec:.3f}s")
                printable_sequence.append((pair, duration_name))

            print(f"Translation: {printable_sequence}")
            
            print("Playing...")
            for (harmony, melody), duration in full_music_sequence:
                buzzer.play_note_pair(harmony, melody, total_duration=duration)
            print("Playback complete.")

    except KeyboardInterrupt:
        print("\nProgram interrupted.")
    finally:
        print("\nCleaning up GPIO...")
        GPIO.cleanup()

if __name__ == "__main__":
    main()
