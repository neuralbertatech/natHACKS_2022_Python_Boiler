import serial
import time

def arduino_run(port):
    ser = serial.Serial('COM3', port)
    while True:
        if time.time() % 2:
            ser.write(b'1')
        else:
            ser.write(b'0')
    
    return
