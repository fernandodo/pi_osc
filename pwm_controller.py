import os
import time
import pigpio

# --- Global State ---
pi = None
soft_freq_real = 71
soft_range_val = 1000
configured_soft_pins = []
configured_hard_channels = []

# Hardware PWM Constants
CHIP_PATH = "/sys/class/pwm/pwmchip0"
hard_period_ns = 15_000_000 # Default for 15.0ms

def clamp(val, min_val=1.0, max_val=2.0):
    """Clamps the value to protect hardware."""
    return max(min_val, min(max_val, val))

# --- Public API ---

def init_pwm(soft_pins=[], period_ms=15.0, pwm_range=1000, init_hard_channels=[0, 1]):
    """Initializes pigpio connection and configures PWM channels."""
    global pi, soft_freq_real, soft_range_val, configured_soft_pins, hard_period_ns, configured_hard_channels
    
    soft_range_val = pwm_range
    configured_soft_pins = soft_pins
    configured_hard_channels = init_hard_channels
    
    # Calculate frequency for software PWM
    frequency = int(1000.0 / period_ms)
    
    # Hardware period is in nanoseconds
    hard_period_ns = int(period_ms * 1_000_000)

    # 1. Initialize Software PWM (pigpio)
    if pi is None or not pi.connected:
        pi = pigpio.pi()
    
    if not pi.connected:
        print("[ERROR] Failed to connect to pigpio daemon!")
    elif soft_pins:
        for pin in soft_pins:
            pi.set_PWM_frequency(pin, frequency)
            pi.set_PWM_range(pin, pwm_range)
        
        # Read back actual frequency for precise calculation
        soft_freq_real = pi.get_PWM_frequency(soft_pins[0])
        print(f"[PWM] SoftPWM Init: Requested={frequency}Hz (from {period_ms}ms), Real={soft_freq_real}Hz, Range={pwm_range}")

    # 2. Initialize Hardware PWM (sysfs)
    for channel in init_hard_channels:
        _init_hard_pwm(channel, hard_period_ns)


def set_pwm(pin_or_channel, ms, is_hardware=False):
    """
    Sets the pulse width.
    :param pin_or_channel: GPIO number (BCM) for soft PWM, or channel (0/1) for hard PWM
    :param ms: On-time in milliseconds
    :param is_hardware: True for sysfs hardware PWM, False for pigpio soft PWM
    """
    ms = clamp(ms)

    if is_hardware:
        channel = pin_or_channel
        duty_ns = int(ms * 1_000_000)
        if duty_ns > hard_period_ns:
            duty_ns = hard_period_ns
            
        _write_sysfs(channel, "duty_cycle", duty_ns)
        
    else:
        if pi is None or not pi.connected:
            return

        duty = int((soft_range_val * ms * soft_freq_real) / 1000.0)
        pi.set_PWM_dutycycle(pin_or_channel, duty)


def enable():
    """Starts all configured PWM channels with an on-time of 1.5ms."""
    for pin in configured_soft_pins:
        set_pwm(pin, 1.5, is_hardware=False)
    for channel in configured_hard_channels:
        set_pwm(channel, 1.5, is_hardware=True)
    print("[PWM] All channels enabled at 1.5ms (Neutral).")


def cleanup():
    """Stops all PWM output and closes connection."""
    global pi
    
    # 1. Cleanup Software PWM
    if pi and pi.connected:
        for pin in configured_soft_pins:
            pi.set_PWM_dutycycle(pin, 0)
        pi.stop()
        pi = None
        print("[PWM] SoftPWM cleaned up.")

    # 2. Cleanup Hardware PWM
    _disable_hard_pwm(0)
    _disable_hard_pwm(1)
    print("[PWM] HardPWM cleaned up.")


# --- Internal Helpers for Hardware PWM ---

def _init_hard_pwm(channel, period_ns):
    pwm_path = f"{CHIP_PATH}/pwm{channel}"
    
    if not os.path.exists(pwm_path):
        try:
            with open(f"{CHIP_PATH}/export", 'w') as f:
                f.write(str(channel))
            time.sleep(0.1) # Wait for udev
        except OSError as e:
            print(f"[PWM] Export warning for channel {channel}: {e}")

    # Disable before configuring
    _write_sysfs(channel, "enable", 0)
    _write_sysfs(channel, "period", period_ns)
    _write_sysfs(channel, "duty_cycle", 0)
    _write_sysfs(channel, "enable", 1)
    print(f"[PWM] HardPWM Channel {channel} Init: Period={period_ns}ns")

def _disable_hard_pwm(channel):
    _write_sysfs(channel, "enable", 0)
    try:
        with open(f"{CHIP_PATH}/unexport", 'w') as f:
            f.write(str(channel))
    except OSError:
        pass

def _write_sysfs(channel, filename, value):
    path = f"{CHIP_PATH}/pwm{channel}/{filename}"
    try:
        with open(path, 'w') as f:
            f.write(str(value))
    except OSError as e:
        pass # Suppress spam during rapid updates if file is busy
