import time
import os

CHIP_PATH = "/sys/class/pwm/pwmchip0"

def write_file(path, value):
    with open(path, 'w') as f:
        f.write(str(value))

def setup_pwm(channel, period_ns, duty_ns):
    pwm_path = f"{CHIP_PATH}/pwm{channel}"
    
    # Export if not exists
    if not os.path.exists(pwm_path):
        write_file(f"{CHIP_PATH}/export", channel)
        time.sleep(0.1) # Wait for udev
    
    # Disable first to be safe
    write_file(f"{pwm_path}/enable", 0)
    
    # Configure
    write_file(f"{pwm_path}/period", period_ns)
    write_file(f"{pwm_path}/duty_cycle", duty_ns)
    
    # Enable
    write_file(f"{pwm_path}/enable", 1)
    print(f"PWM{channel} enabled: Period={period_ns}ns, Duty={duty_ns}ns")

try:
    print("Setting up Hardware PWM...")
    
    # PWM0 (GPIO 12): 50Hz (20ms), 1.5ms pulse (Neutral)
    # Period = 20,000,000 ns
    # Duty = 1,500,000 ns
    setup_pwm(0, 20000000, 1500000)
    
    # PWM1 (GPIO 13): 100Hz (10ms), 2.0ms pulse
    # Period = 10,000,000 ns
    # Duty = 2,000,000 ns
    setup_pwm(1, 10000000, 2000000)
    
    print("PWM running. Press Ctrl+C to stop.")
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping...")
    try:
        # Disable PWM0
        write_file(f"{CHIP_PATH}/pwm0/enable", 0)
        # Unexport PWM0
        write_file(f"{CHIP_PATH}/unexport", 0)
    except:
        pass
        
    try:
        # Disable PWM1
        write_file(f"{CHIP_PATH}/pwm1/enable", 0)
        # Unexport PWM1
        write_file(f"{CHIP_PATH}/unexport", 1)
    except:
        pass
        
    print("Cleaned up.")
