# OSC Server Specification

## 1. Overview
The OSC Server is the primary entry point for the `pi_osc` system. It acts as a network listener that decodes incoming OSC (Open Sound Control) packets and dispatches them to the appropriate hardware or notification modules.

## 2. Technical Stack
- **Library**: `python-osc`
- **Protocol**: UDP
- **Execution Model**: Blocking (Single-threaded) or Threading (if concurrent handling is needed).

## 3. Network Configuration
- **Listen Address**: `0.0.0.0` (Allows connections from any network interface).
- **Listen Port**: `5005` (Standard OSC port for this project).

## 4. Message Dispatcher & State Logic

The server maintains an internal state to handle debouncing and priority logic before updating the PWM Controller.

### Internal State Variables
- `direction` (bool): `True` for backward, `False` for forward.
- `current_speed` (float): Current applied linear speed (0.0 - 1.0).
- `pending_speed` (float): Linear speed waiting for confirmation.
- `last_forward_msg_time` (float): Timestamp of last `/forward` msg.
- `turn_right` (bool): `True` for right, `False` for left.
- `current_angular_velocity` (float): Current applied angular velocity (0.0 - 1.0).
- `pending_angular_velocity` (float): Angular velocity waiting for confirmation.
- `last_right_msg_time` (float): Timestamp of last `/right` msg.
- `update_time` (float): Configurable confirmation delay in seconds (Default: 0.5s).
- `start_enabled` (bool): If `True`, the `/start` command can be triggered.
- `start_active` (bool): Transient state that remains `True` for 0.2s after a `/start` trigger.
- `last_start_trigger_time` (float): Timestamp when `/start` was last triggered.
- `break_active` (bool): Transient state that remains `True` for 0.2s after a `/break` trigger.
- `last_break_trigger_time` (float): Timestamp when `/break` was last triggered.
- `current_pitch` (int): 0 for Up (U), 1 for Neutral (N), 2 for Down (D). Default: 1.
- `last_pitch_change_time` (float): Timestamp of last pitch update to 0 or 2.

### Dispatcher Mapping
| OSC Address | Handler Function | Description |
| :--- | :--- | :--- |
| `/forward` | `forward_handler` | Sets pending speed. |
| `/backward` | `backward_handler` | Sets direction and **immediate** speed reset to 0. |
| `/right` | `right_handler` | Sets pending angular velocity. |
| `/left` | `left_handler` | Sets turn_right state and **immediate** angular velocity reset to 0. |
| `/update_time`| `update_time_handler`| Maps 1.0-5.0 to 0.1s-0.5s for confirmation delay. |
| `/start_enable`| `start_enable_handler`| Updates the `start_enabled` safety state. |
| `/start` | `start_handler` | Triggers `start_active` for 0.2s if enabled. |
| `/break` | `break_handler` | Triggers `break_active` for 0.2s (No enable required). |
| `/pitch` | `pitch_handler` | Sets pitch (0, 1, 2). Auto-restores to 1 after 10s if 0 or 2. |
| `/system/stop`| `system_stop_handler` | Emergency stop all hardware. |

## 5. State Sharing (Shared Memory File)

The server synchronizes its internal state to a JSON file in the Linux shared memory space (`/dev/shm`). This allows external local programs like OpenClaw to read the state with near-zero latency without using OSC queries.

- **File Path**: `/dev/shm/robot_state.json`
- **Update Trigger**: Every time `update_pwm_mock()` is called.
- **Cleanup**: The file is **deleted** upon server shutdown to signal that the system is inactive.
- **Data Format (JSON)**:
```json
{
  "speed": 0.0,
  "direction": false,
  "angular_vel": 0.0,
  "turn_right": false,
  "start_active": false,
  "break_active": false,
  "pitch": 1,
  "update_time": 0.5,
  "timestamp": 1700000000.0
}
```

### JSON Field Descriptions:
- **`speed`**: Current linear velocity (0.0 to 1.0).
- **`direction`**: Linear direction (`false` = Forward, `true` = Backward).
- **`angular_vel`**: Current rotational velocity (0.0 to 1.0).
- **`turn_right`**: Rotational direction (`true` = Right, `false` = Left).
- **`start_active`**: `true` during the 0.2s start pulse.
- **`break_active`**: `true` during the 0.2s break pulse.
- **`pitch`**: Current pitch state (`0`=Up, `1`=Neutral, `2`=Down).
- **`update_time`**: Current confirmation delay used for linear/angular movement (0.1s to 0.5s).
- **`timestamp`**: Unix epoch time when this state was captured.

## 6. Handler & Processing Logic

### Movement Handlers
... (Previous handlers) ...

### `pitch_handler(address, value)`
... (Previous logic) ...

### `query_handler(address, *args)`
- **Logic**: 
    1. Responds to the sender with current state values.
    2. Sent Address: `/status`.
    3. Arguments: `[speed, direction, angular_vel, turn_right, start_active, break_active, pitch]`.

### Main Loop / Background Watcher
... (Rule 1, 2, 3, 4) ...
- **Rule 5 (Pitch Restore)**: If `current_pitch` is 0 or 2 AND `(current_time - last_pitch_change_time) > 10.0s`:
    1. Set `current_pitch` = 1 (Neutral).
    2. Update PWM.

## 6. PWM On-Time Mappings

All states are converted to millisecond (ms) on-time values for the `PWMController`.

### A. Linear Movement (Speed & Direction)
| State | `on_time_ms` |
| :--- | :--- |
| Forward 1.0 | 2.0ms |
| Neutral (Speed 0.0) | 1.5ms |
| Backward 1.0 | 1.0ms |
*Formula: `1.5 + (0.5 * speed * (-1 if direction else 1))`*

### B. Start / Break Pulses
| State | `on_time_ms` |
| :--- | :--- |
| Start Active | 2.0ms |
| Break Active | 1.0ms |
| Inactive (Both False) | 1.5ms |

### C. Pitch
| State | `on_time_ms` |
| :--- | :--- |
| Up (0) | 1.0ms |
| Neutral (1) | 1.5ms |
| Down (2) | 2.0ms |

## 7. Initialization Sequence
1. Load configuration from `config.py`.
2. Initialize `PWMController` and `Notifier`.
3. Create `Dispatcher` and map addresses.
4. Bind the `BlockingOSCUDPServer` to the configured IP/Port.
5. Start `serve_forever()`.

## 7. Operational Requirements
- **Logging**: Every received message should be logged to the console with its timestamp and arguments.
- **Graceful Exit**: Must handle `SIGINT` (Ctrl+C) by stopping the PWM signals before exiting.
