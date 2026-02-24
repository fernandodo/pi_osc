import time
import threading
import json
import os
import pwm_controller
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer

# --- State Management ---
class RobotState:
    def __init__(self):
        self.lock = threading.RLock() # Changed to RLock to allow nested calls
        
        # Linear State
        self.direction = False # False=Forward, True=Backward
        self.current_speed = 0.0
        self.pending_speed = 0.0
        self.last_forward_msg_time = 0.0
        
        # Angular State
        self.turn_right = False # True=Right, False=Left
        self.current_angular_velocity = 0.0
        self.pending_angular_velocity = 0.0
        self.last_right_msg_time = 0.0
        
        self.update_time = 0.1 # Default delay
        self.start_enabled = False
        self.start_active = False
        self.last_start_trigger_time = 0.0
        self.break_active = False
        self.last_break_trigger_time = 0.0
        
        # Pitch State: 0=Up, 1=Neutral, 2=Down
        self.current_pitch = 1
        self.last_pitch_change_time = 0.0
        
        self.running = True

state = RobotState()

def sync_to_shm():
    """Writes current state to /dev/shm for external programs to read"""
    with state.lock:
        data = {
            "speed": state.current_speed,
            "direction": state.direction,
            "angular_vel": state.current_angular_velocity,
            "turn_right": state.turn_right,
            "start_active": state.start_active,
            "break_active": state.break_active,
            "pitch": state.current_pitch,
            "update_time": state.update_time,
            "timestamp": time.time()
        }
    
    # Write to memory disk (/dev/shm is a tmpfs)
    shm_path = "/dev/shm/robot_state.json"
    try:
        # Atomic write: write to temp file then rename (prevents partial reads)
        tmp_path = shm_path + ".tmp"
        with open(tmp_path, 'w') as f:
            json.dump(data, f)
        os.rename(tmp_path, shm_path)
    except Exception as e:
        print(f"[ERROR] Sync to SHM failed: {e}")

def update_pwm():
    """Calculates and updates actual PWM on-times based on current state"""
    sync_to_shm() # Update shared state file
    with state.lock:
        # 1. Linear Mapping: 1.5 + (0.5 * speed * (-1 if direction else 1))
        linear_mod = -1.0 if state.direction else 1.0
        linear_ms = 1.5 + (0.5 * state.current_speed * linear_mod)
        pwm_controller.set_pwm(0, linear_ms, is_hardware=True) # Channel 0 for Linear
        
        # 2. Angular Mapping
        angular_mod = 1.0 if state.turn_right else -1.0
        angular_ms = 1.5 + (0.5 * state.current_angular_velocity * angular_mod)
        pwm_controller.set_pwm(1, angular_ms, is_hardware=True) # Channel 1 for Angular

        # 3. Pulse Mapping (Assume Soft Pin 5)
        pulse_ms = 1.5
        if state.start_active:
            pulse_ms = 2.0
        elif state.break_active:
            pulse_ms = 1.0
        pwm_controller.set_pwm(5, pulse_ms, is_hardware=False)
            
        # 4. Pitch Mapping (Assume Soft Pin 6)
        pitch_map = {0: 1.0, 1: 1.5, 2: 2.0}
        pitch_ms = pitch_map.get(state.current_pitch, 1.5)
        pwm_controller.set_pwm(6, pitch_ms, is_hardware=False)
        
        # Optional: Print for debugging
        # print(f"[PWM] L={linear_ms:.2f}ms, A={angular_ms:.2f}ms, Pulse={pulse_ms:.2f}ms, Pitch={pitch_ms:.2f}ms")

# --- OSC Handlers ---

def forward_handler(address, *args):
    with state.lock:
        state.pending_speed = float(args[0])
        state.last_forward_msg_time = time.time()
    # No immediate PWM update per spec

def backward_handler(address, *args):
    with state.lock:
        is_backward = bool(args[0])
        state.direction = is_backward
        state.current_speed = 0.0
        state.pending_speed = 0.0
        print(f"Backward message received ({is_backward}). Speed reset to 0.")
        update_pwm()

def right_handler(address, *args):
    with state.lock:
        state.pending_angular_velocity = float(args[0])
        state.last_right_msg_time = time.time()
    # No immediate PWM update per spec

def left_handler(address, *args):
    with state.lock:
        is_left = bool(args[0])
        state.turn_right = not is_left
        state.current_angular_velocity = 0.0
        state.pending_angular_velocity = 0.0
        print(f"Left message received ({is_left}). Angular velocity reset to 0.")
        update_pwm()

def update_time_handler(address, *args):
    with state.lock:
        val = float(args[0])
        # Map 1-5 to 0.1s - 0.5s
        new_time = max(1.0, min(5.0, val)) / 10.0
        state.update_time = new_time
        print(f"Update time changed to: {new_time}s")

def start_enable_handler(address, *args):
    with state.lock:
        state.start_enabled = bool(args[0])
        print(f"Start enabled: {state.start_enabled}")

def start_handler(address, *args):
    with state.lock:
        if state.start_enabled:
            state.start_active = True
            state.last_start_trigger_time = time.time()
            print("Start triggered (0.2s pulse)")
            update_pwm()
        else:
            print("Start received but ignored (start_enable is False)")

def break_handler(address, *args):
    with state.lock:
        state.break_active = True
        state.last_break_trigger_time = time.time()
        print("Break triggered (0.2s pulse)")
        update_pwm()

def pitch_handler(address, *args):
    mapping = {
        0: 0, 'U': 0, 'u': 0,
        1: 1, 'N': 1, 'n': 1,
        2: 2, 'D': 2, 'd': 2
    }
    val = args[0]
    new_pitch = mapping.get(val, 1) # Default to Neutral if unknown
    
    with state.lock:
        state.current_pitch = new_pitch
        state.last_pitch_change_time = time.time()
        print(f"Pitch updated to: {new_pitch}")
        update_pwm()

def stop_handler(address, *args):
    print("System stop received.")
    state.running = False

# --- Background Watcher ---

def watcher_loop():
    while state.running:
        now = time.time()
        needs_update = False
        
        with state.lock:
            # Rule 1: Linear speed
            if (now - state.last_forward_msg_time > state.update_time) and (state.current_speed != state.pending_speed):
                state.current_speed = state.pending_speed
                needs_update = True
            
            # Rule 2: Angular velocity
            if (now - state.last_right_msg_time > state.update_time) and (state.current_angular_velocity != state.pending_angular_velocity):
                state.current_angular_velocity = state.pending_angular_velocity
                needs_update = True
            
            # Rule 3: Start Pulse Reset (0.2s)
            if state.start_active and (now - state.last_start_trigger_time > 0.2):
                state.start_active = False
                needs_update = True
            
            # Rule 4: Break Pulse Reset (0.2s)
            if state.break_active and (now - state.last_break_trigger_time > 0.2):
                state.break_active = False
                needs_update = True
            
            # Rule 5: Pitch Restore (10s)
            if state.current_pitch != 1 and (now - state.last_pitch_change_time > 10.0):
                state.current_pitch = 1
                needs_update = True
        
        if needs_update:
            update_pwm()
            
        time.sleep(0.05)

# --- Main Server ---

if __name__ == "__main__":
    ip = "0.0.0.0"
    port = 5005
    
    # Initialize PWM Controller
    # Assuming soft pins: 5, 6 and hard channels: 0, 1
    print("Initializing PWM Controller...")
    pwm_controller.init_pwm(soft_pins=[5, 6], period_ms=15.0, pwm_range=1000, init_hard_channels=[0, 1])
    pwm_controller.enable() # Start in neutral state
    
    dispatcher = Dispatcher()
    dispatcher.map("/forward", forward_handler)
    dispatcher.map("/backward", backward_handler)
    dispatcher.map("/right", right_handler)
    dispatcher.map("/left", left_handler)
    dispatcher.map("/update_time", update_time_handler)
    dispatcher.map("/start_enable", start_enable_handler)
    dispatcher.map("/start", start_handler)
    dispatcher.map("/break", break_handler)
    dispatcher.map("/pitch", pitch_handler)
    dispatcher.map("/system/stop", stop_handler)
    
    # Start background watcher
    watcher_thread = threading.Thread(target=watcher_loop, daemon=True)
    watcher_thread.start()
    
    server = BlockingOSCUDPServer((ip, port), dispatcher)
    print(f"OSC Server started on {ip}:{port}")
    print("Press Ctrl+C to stop manually.")
    
    try:
        while state.running:
            server.handle_request()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        state.running = False
        pwm_controller.cleanup()
        # Remove state file to signal shutdown
        shm_path = "/dev/shm/robot_state.json"
        if os.path.exists(shm_path):
            os.remove(shm_path)
        print("Done.")
