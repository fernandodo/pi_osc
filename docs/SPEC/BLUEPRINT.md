# System Specification: pi_osc

## 1. Overview
The `pi_osc` system acts as a bridge between Open Sound Control (OSC) messages and hardware PWM signals on a Raspberry Pi. It listens for incoming network commands to control GPIO pins (specifically for devices requiring precise on-time control like servos or ESCs) and sends status notifications to external services.

## 2. Hardware Configuration
Based on `softpwm_test.py`, the system targets the following configuration:
- **GPIO Pins**: 5, 6, 16, 26 (BCM numbering)
- **PWM Frequency**: 71 Hz
- **PWM Range**: 1000 (0-1000 resolution)
- **Control Parameter**: `on_time_ms` (Milliseconds of on-time per cycle)

## 3. Architecture Modules

### A. OSC Server (`osc_server.py`)
- **Role**: Listens for UDP packets.
- **Address**: `0.0.0.0` (All interfaces)
- **Port**: `5005` (Default)
- **Message Handling**: Parses OSC addresses and arguments to drive the PWM controller and trigger notifications.

### B. PWM Controller (`pwm_controller.py`)
- **Library**: `pigpio` (Daemon mode via `pigpiod`)
- **Functionality**:
    - Initialize connection to `pigpiod`.
    - Configure Pins 5, 6, 16, 26 with frequency 71Hz and range 1000.
    - **Logic**: Convert `on_time_ms` input to Duty Cycle.
      - Formula: `duty = (frequency * range * on_time_ms) / 1000`
      - Simplified: `duty = 71 * on_time_ms`
    - Safety: Clamp values to safe ranges to prevent hardware damage.

### C. Notifier (`notifier.py`)
- **Role**: Send alerts based on system state or specific OSC commands.
- **Triggers**:
    - System Start/Stop.
    - specific OSC message (e.g., `/notify <message>`).
- **Channels**:
    - **Telegram**: Via HTTP Bot API (requires Token & Chat ID).
    - **OpenClaw**: (Integration details TBD - assuming HTTP/TCP interface).

## 4. OSC API Design

| OSC Address | Arguments | Description |
| :--- | :--- | :--- |
| `/pwm/set` | `pin` (int), `on_time_ms` (float) | Set specific pin to on-time (e.g., `/pwm/set 5 1.5`) |
| `/pwm/all` | `on_time_ms` (float) | Set all configured pins (5,6,16,26) to same on-time |
| `/notify` | `message` (string) | Send a custom notification via configured channels |
| `/system/stop`| `none` | Stop PWM and shutdown safely |

## 5. Configuration (`config.py` or `.env`)
- `PIGPIO_HOST`: localhost
- `PIGPIO_PORT`: 8888
- `TELEGRAM_TOKEN`: (User to provide)
- `TELEGRAM_CHAT_ID`: (User to provide)
- `OPENCLAW_ENDPOINT`: (User to provide)
