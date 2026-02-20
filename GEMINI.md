# Project Overview: pi_osc

`pi_osc` is a project focused on integrating Raspberry Pi hardware with the Open Sound Control (OSC) protocol. It is designed to facilitate communication between physical hardware (such as sensors, switches, or actuators connected via GPIO) and networked devices or applications (e.g., DAWs, visual software, or other controllers).

## Main Technologies
- **Raspberry Pi**: The target hardware platform.
- **Python**: Core development language.
- **OSC (Open Sound Control)**: Networking protocol for communication.
- **python-osc**: Standard library for implementing OSC in Python environments.

## Building and Running
### Setup
1. Create a virtual environment: `python -m venv .venv`
2. Activate it: `source .venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Start the pigpio daemon on the Pi:
```bash
sudo pigpiod -t 1
```

### Syncing to Raspberry Pi
To sync local changes to the Pi:
```bash
rsync -avz --exclude 'venv' --exclude '.git' ./ hpi:~/Projects/pi_osc/
```

### Running
To start the OSC receiver:
```bash
python receive_osc.py --ip 0.0.0.0 --port 5005
```

## Testing Utilities
### Soft PWM Test
The `softpwm_test.py` script is used to verify and tune software PWM settings on the Raspberry Pi.
- **Usage**: `python softpwm_test.py`
- **Functionality**:
  - Connects to the `pigpio` daemon.
  - Sets PWM on GPIO pins 5, 6, 16, and 26.
  - Interactively prompts for a period (in ms) to adjust the frequency dynamically.
  - Enter a non-number or press Enter on an empty line to exit and stop PWM.

## Development Conventions
- **Hardware Integration**: Focus on efficient, low-latency interaction with Raspberry Pi GPIO pins.
- **Network Reliability**: Prioritize the use of static IPs or MDNS (Avahi/Bonjour) for stable discovery of OSC endpoints.
- **Modularity**: Separate hardware interface logic from OSC messaging logic to allow for easier testing and hardware simulation.
- **Testing**: Implement unit tests for message parsing and integration tests for end-to-end hardware-to-network communication.
