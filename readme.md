# Build a Musical, Expressive Robot with Raspberry Pi Zero

## Introduction

Welcome to the Ninja Robot project! This guide will walk you through every step of building an intelligent robot using a Raspberry Pi Zero 2 W. This isn't just a simple robot that moves; it's a platform for expression. By the end of this tutorial, your robot will be able to:

*   **Move precisely** using calibrated servo motors.
*   **"See" the world** around it with an ultrasonic distance sensor.
*   **Communicate with sound** using a musical buzzer.
*   **Translate Japanese hiragana into unique musical compositions** based on phonetic rules, rhythm, and emotional moods.

This project is perfect for beginners looking for a comprehensive introduction to robotics, as well as experienced makers who want to explore creative AI and hardware interactions. Let's begin!

---

## Part 1: Hardware Assembly

First, we'll gather our components and wire them together. Accuracy here is key to a successful build.

### Required Components

| Component | Links & Specifications | Quantity |
| :--- | :--- | :--- |
| **Raspberry Pi Zero 2 W** | [Product Brief](https://akizukidenshi.com/goodsaffix/raspberry-pi-zero-2-w-product-brief.pdf) | 1 |
| **DFRobot IO HAT for Zero** | [Wiki Page](https://wiki.dfrobot.com/I_O_Expansion_HAT_for_Pi_zero_V1_0_SKU_DFR0604) | 1 |
| **SG90 Servo Motors** | [Datasheet](https://akizukidenshi.com/goodsaffix/SG90_a.pdf) (Standard 180° servos) | 4 |
| **Ultrasonic Sensor** | HC-SR04 Module | 1 |
| **Buzzer (Active/Passive)** | CMI-1295IC-1285T or similar | 1 |
| **MicroSD Card** | 16GB or higher, Class 10 | 1 |
| **Power Supply** | 5V, 2.5A Micro USB adapter | 1 |
| **External 5V Supply (Recommended)** | 5V 2A+ BEC or adapter for servos | 1 |

### Wiring Everything Together

#### Safety First!
**Always ensure your Raspberry Pi is completely powered off and unplugged before connecting or disconnecting any components.**

Mount the DFRobot IO Expansion HAT onto your Raspberry Pi Zero's 40-pin GPIO header. All subsequent connections will be made to the HAT.

#### Servo Motors (SG90)
Connect the four servos to the digital PWM pins. Servos have three wires:
*   **Brown/Black:** GND (Ground)
*   **Red:** VCC (5V Power)
*   **Orange/Yellow:** Signal (PWM Data)

Connect all **Brown** wires to the **GND** rail on the HAT.
Connect all **Red** wires to the **5V** rail on the HAT.
Connect the **Signal** wires as follows:

| Servo Assignment | Signal Wire Destination | GPIO # |
| :--- | :--- | :--- |
| Left Leg (s0) | HAT Digital Pin 16 | GPIO 16 |
| Right Leg (s1) | HAT Digital Pin 17 | GPIO 17 |
| Left Foot (s2) | HAT Digital Pin 18 | GPIO 18 |
| Right Foot (s3) | HAT Digital Pin 19 | GPIO 19 |

#### Ultrasonic Sensor (HC-SR04)
**Wiring Update:** Many modern HC-SR04 modules can operate safely at 3.3V. This simplifies the wiring significantly by removing the need for a voltage divider.

| Sensor Pin | Connection | GPIO # |
| :--- | :--- | :--- |
| **VCC** | HAT **3.3V** Rail | 3.3V |
| **Trig** | HAT Digital Pin 21 | GPIO 21 |
| **Echo** | HAT Digital Pin 22 | GPIO 22 |
| **GND** | HAT GND Rail | GND |

*Note: If your sensor behaves erratically, it might require 5V. In that case, you must use the voltage divider method described in the previous tutorial version to protect your Pi's GPIO pins.*

#### Buzzer
| Buzzer Pin | Connection | GPIO # |
| :--- | :--- | :--- |
| **Signal (IO / +)** | HAT Digital Pin 23 | GPIO 23 |
| **GND (-)** | HAT GND Rail | GND |

---

## Part 2: Software Setup

### Step 1: Prepare Your Raspberry Pi OS
1.  Download the **Raspberry Pi Imager** from the [official website](https://www.raspberrypi.com/software/).
2.  Insert your microSD card into your computer.
3.  Run the Imager. Select "Raspberry Pi Zero 2 W" as the device and "Raspberry Pi OS (Legacy, 32-bit) Lite" as the OS. The Lite version is recommended as it's lightweight and perfect for robotics.
4.  Select your microSD card as the storage.

### Step 2: Initial Configuration (Headless Setup)
Before you flash the OS, click the gear icon in the Imager to pre-configure it. This is called a "headless" setup and saves a lot of time.
1.  **Enable SSH:** Check the box to enable SSH and set a secure password.
2.  **Configure Wi-Fi:** Enter your Wi-Fi network's SSID (name) and password.
3.  **Set Locale:** Set your timezone and keyboard layout.
4.  Click **Save**, then click **Write** to flash the OS to the microSD card.

### Step 3: First Boot and OS Update
1.  Eject the microSD card and insert it into your Raspberry Pi.
2.  Power on the Pi. Wait a few minutes for it to boot and connect to your Wi-Fi.
3.  Find your Pi's IP address from your router's admin page or using a network scanner app.
4.  Open a terminal on your computer and connect to the Pi via SSH:
    ```bash
    ssh pi@<YOUR_PI_IP_ADDRESS>
    ```
5.  Once logged in, update the system's package lists and installed software:
    ```bash
    sudo apt update && sudo apt upgrade -y
    ```

### Step 4: Set Up the Project Environment
Using a virtual environment is the best practice for managing project dependencies.

1.  **Install Git and Virtual Environment tools:**
    ```bash
    sudo apt install git python3-venv -y
    ```
2.  **Create the project folder:**
    ```bash
    mkdir NinjaRobot
    cd NinjaRobot
    ```
3.  **Create a Python virtual environment:**
    ```bash
    python3 -m venv .venv
    ```4.  **Activate the virtual environment:**
    ```bash
    source .venv/bin/activate
    ```    Your terminal prompt should now be prefixed with `(.venv)`, indicating the environment is active.

5.  **Install required Python libraries inside the virtual environment:**
    ```bash
    pip install RPi.GPIO
    ```

### Step 5: Download the Project Code
Clone the complete code repository from GitHub.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Nilcreator/NinjaFeets.git .
    ```
    *(Note the `.` at the end, which clones the files directly into your current `NinjaRobot` directory).*

2.  **Verify the files:**
    ```bash
    ls
    ```
    You should see `ninja_buzzer.py`, `ninja_japanese.py`, and all the other project files listed.

---

## Part 3: The Code - Bringing Your Robot to Life

Now we'll walk through each script, explaining its purpose and how to use it. Remember to activate your virtual environment (`source .venv/bin/activate`) in any new terminal session before running these scripts.

### Script 1: `ninja_servo_calibration.py` - Teaching Your Robot to Move
*   **Purpose:** Servos aren't perfect. This script helps you find the exact PWM signal values that correspond to the 0°, 90°, and 180° positions for *each individual servo*. This calibration is essential for precise movements.
*   **How to Run:** Run the script specifying which servo you want to calibrate (e.g., `s0`).
    ```bash
    python3 ninja_servo_calibration.py s0
    ```
*   **Calibration Process:**
    1.  The script provides a real-time interface.
    2.  Use the `w` and `s` keys to move the servo in small increments.
    3.  Move the servo to its physical minimum position. Press `Shift+X` to set this as the `-90°` point.
    4.  Move it to its center point and press `Shift+C` to set it as `0°`.
    5.  Move it to its maximum position and press `Shift+V` to set it as `+90°`.
    6.  Press `n` to move to the next servo in your list, or `q` to save and quit.
*   **The Output (`servo_calibration.json`):** This script creates a vital file named `servo_calibration.json`. It stores the unique duty cycle values for each servo's min, center, and max positions. All other scripts will read this file to know how to move the servos correctly.

### Script 2: `ninja_servo_movement.py` - Choreographing Motion
*   **Purpose:** This is your robot's motion controller. It reads the `servo_calibration.json` file and accepts commands to execute simple or complex, multi-servo movement sequences.
*   **How to Run:**
    ```bash
    python3 ninja_servo_movement.py
    ```
*   **Command Syntax:** Type `help` in the script's prompt for a full guide.
    *   **Simple Move:** `s0:90` (Move servo s0 to 90 degrees).
    *   **Sequence:** `s1:M,C,N;L3;S0.8` (Move s1 Max->Center->Min, Loop 3 times, at 80% speed).
    *   **Parallel Control:** `s0:M,C | s2:N,C` (Move servos s0 and s2 simultaneously).
    *   **Auto-Reset:** After a finite sequence completes, the robot will automatically return to its center position.

### Script 3: `ninja_ultrasonic.py` - Giving Your Robot Sight
*   **Purpose:** This script tests the HC-SR04 sensor. It works like a bat's sonar: it sends out a sound pulse (`Trig`) and listens for the echo (`Echo`). The time it takes for the echo to return is used to calculate distance.
*   **How to Run:**
    ```bash
    python3 ninja_ultrasonic.py
    ```
*   **Interpreting the Output:** The script will continuously print the distance to the nearest object in centimeters. This is the fundamental building block for obstacle avoidance.

### Script 4: `ninja_buzzer.py` - The Robot's Voice
*   **Purpose:** This script can be run directly as an interactive musical toy. It can also be imported as a library by other scripts.
*   **How to Run:**
    ```bash
    python3 ninja_buzzer.py
    ```
*   **Features:** Type `help` in the prompt.
    *   **Command Mode:** Type `C4,D4,E4` to play a sequence.
    *   **Live Play Mode:** Type `live` to enter a mode where keyboard presses (`a`, `s`, `d`, etc.) instantly play notes.

### Script 5: `ninja_japanese.py` - The Soul of the Machine
*   **Purpose:** This is the most unique script. It translates Japanese hiragana into a two-layered musical piece and plays it on the buzzer.
*   **Rules of Translation:**
    *   **Vowel → Melody:** The vowel of each mora (`a, i, u, e, o`) maps to a main note on a C-pentatonic scale (`C4, D4, E4, G4, A4`).
    *   **Consonant → Harmony:** The consonant (`k, s, t`, etc.) maps to a higher harmony note, played as a quick grace note before the melody.
    *   **Rhythm & Mood:** You can specify moods (`--mood happy`) or custom rhythms (`[whole,half]`) to control the timing and emotional feel of the output.
    *   **Rests:** Separating words with spaces automatically inserts a short rest, creating musical phrasing.
*   **How to Use:** Run the script and type `help` for a full guide.
    ```bash
    python3 ninja_japanese.py
    ```
    *   **Example:** `あなた ありがとう --mood sad` will translate the two words into a slow, melancholic melody.

---

## Next Steps

Congratulations! You have built and programmed a complex, expressive robot. From here, the possibilities are endless:
*   **Build a Body:** Design and 3D print a chassis to house the components.
*   **Integrate the Scripts:** Create a master script that uses the ultrasonic sensor's readings to trigger movements and sounds.
*   **AI Integration:** Use the Google Gemini API to generate new hiragana poems or song lyrics for `ninja_japanese.py` to play.
*   **Expand the Music:** Add more moods, scales, and songs to your buzzer scripts.

Happy building
