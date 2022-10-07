import argparse
import sys
import time

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("Not on RPi ??")
    sys.exit(1)


def cleanup():
    print("Cleanup...")
    GPIO.cleanup()
    sys.exit(0)


def event_callback(pin):
    time_formatted = str(time.time()).split(".")
    print(
        ".".join([time_formatted[0][-3:], time_formatted[-1][:6]]),
        "Input detected on pin",
        pin,
    )


def run_receiver_test(
    pin=None,
    bouncetime=100,
):
    print(
        "Setting up GPIO input on pin ",
        pin,
        " with bouncetime ",
        bouncetime,
        " ms.",
    )
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(
        pin, GPIO.FALLING, callback=event_callback, bouncetime=bouncetime
    )

    while True:
        try:
            time.sleep(0.001)
        except KeyboardInterrupt:
            print("Stopping")
            cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser("GPIO receiver test")
    parser.add_argument("-p", "--pin", default=16, type=int)
    kwargs = parser.parse_args().__dict__

    run_receiver_test(**kwargs)
