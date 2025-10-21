import time


def wait():
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print("inside")


while True:
    try:
        input()
        wait()
    except KeyboardInterrupt:
        print("outside")
    except EOFError:
        break
