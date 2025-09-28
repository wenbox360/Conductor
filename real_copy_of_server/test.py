import serial, time
ser = serial.Serial('/dev/cu.usbmodem101', 9600, timeout=1)
time.sleep(2)  # wait for Arduino to reset
ser.write(b"2,500;\n")  # ask it to beep 500ms
time.sleep(0.2)
print("Read:", ser.readline().decode().strip())
ser.close()
