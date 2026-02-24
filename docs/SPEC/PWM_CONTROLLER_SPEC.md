# PWM Controller Specification (Functional)

## 1. Overview
A simplified, functional module to control PWM on Raspberry Pi. It manages a single global connection to `pigpiod` and abstracts Soft/Hard PWM logic.

## 2. Interface

### Module: `pwm_controller`

#### Global Variables
- `pi`: The shared `pigpio.pi` instance.
- `soft_freq_real`: Actual frequency achieved for software PWM (read back from hardware).

#### Functions

- **`init_pwm(soft_pins=[], period_ms=15, soft_range=1000, init_hard_channels=[0, 1])`**:
    - Connects to local `pigpiod`.
    - Derives `frequency` from `period_ms` (`1000 / period_ms`).
    - Configures all `soft_pins` with `frequency` and `soft_range`.
    - **Crucial**: Reads back and stores the *actual* frequency (`soft_freq_real`) for precise math.
    - Exports/Enables Hard PWM channels with `period_ns = period_ms * 1,000,000`.

- **`set_pwm(pin_or_channel, ms, is_hardware=False)`**:
    - **Input**: `pin_or_channel` (BCM GPIO for soft PWM, or channel 0/1 for hard PWM) and On-Time in milliseconds.
    - **Logic**:
        - **If Soft PWM**: 
            - Formula: `duty = (ms * soft_freq_real * soft_range) / 1000`.
            - Calls `pi.set_PWM_dutycycle(pin_or_channel, duty)`.
        - **If Hard PWM**:
            - Formula: `duty_ns = ms * 1,000,000`.
            - Writes to `/sys/class/pwm/pwmchip0/pwm{pin_or_channel}/duty_cycle`.
    - **Safety**: Clamps `ms` between 1.0 and 2.0

- **`cleanup()`**:
    - Sets all soft pins to 0.
    - Disables hard PWM channels.
    - Stops `pigpio` connection.

## 3. Implementation Details

### Hard PWM Mapping
- **GPIO 12/18** -> Channel 0
- **GPIO 13/19** -> Channel 1
- **Path**: `/sys/class/pwm/pwmchip0/pwm{N}`

### Soft PWM Precision
- Reported frequency from `pigpio` might differ slightly from requested.
- `soft_freq_real = pi.get_PWM_frequency(pin)` ensures accurate duty cycle calculation.
