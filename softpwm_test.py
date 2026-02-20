import pigpio
import time

pi = pigpio.pi()
assert pi.connected

gpios = [5,6,16,26]

print("Testing soft PWM on GPIOs: {}".format(gpios))

while True:
    try:
        val = input("Enter new on time in ms (or non-number to exit): ")
        if not val:
            break
        on_time_ms = float(val)
    except ValueError:
        break

    freq = 71
    period_ms = 1000 / freq
    range = 1000
    duty = freq * range * on_time_ms / 1000
    print("Setting on time to {} ms, frequency to {} Hz".format(on_time_ms, freq))
    for g in gpios:
        real_f = pi.set_PWM_frequency(g, freq) # Set frequency
        pi.set_PWM_range(g, range)
        real_d = duty * real_f / freq  # Adjust duty for actual frequency
        pi.set_PWM_dutycycle(g, real_d)

    print("real frequency: {}".format(real_f))
# Stop PWM on all GPIOs
print("Stopping PWM on all GPIOs")
for g in gpios:
    pi.set_PWM_dutycycle(g, 0)

pi.stop()
