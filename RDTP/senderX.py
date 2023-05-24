import socket
import threading
import time
import tkinter as tk
from colorama import Fore, Back, Style

# TODO: Scenario file
file = "50 3 50 3 50 3 50 3 50 3 50 3 50 3 50 3"
scenario = list(map(int, file.split(" ")))
first = 0
scenarios = []

i = 0
while i < len(scenario) - 1:
    if i % 2:
        scenarios.append((first, scenario[i]))
    else:
        first = scenario[i]
    i += 1
scenarios.append((scenario[i], 0))
print(*scenarios)

t = time.time()

receiver_ip_addr = "127.0.0.1"
receiver_port_number = 8000

channel_ip_addr = "127.0.0.1"
channel_port_number = 8001

sender_ip_addr = "127.0.0.1"
sender_port_number = 8080

bufferSize = 512
window = 0
sequenceNumber = 0
NextSeqNum = sequenceNumber
LastByteWritten = 0
LastByteSent = 0

sendbase = NextSeqNum
LastByteAcked = sendbase
PrevByteAcked = LastByteAcked

channel_address = (channel_ip_addr, channel_port_number)

initial_msg = "ISN : " + str(sequenceNumber)

UDPSenderSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPSenderSocket.bind((sender_ip_addr, sender_port_number))


"""
establish connection
    - set AdvWindow
"""

# send message to receiver
print("To Receiver:", initial_msg)
UDPSenderSocket.sendto(initial_msg.encode(), channel_address)

# receive ACK from receiver
message, receiverAddress = UDPSenderSocket.recvfrom(bufferSize)

print("From Receiver:", receiverAddress, "Message:", message.decode())
message = message.decode()[1:-1].split(", ")

# Set initial AdvWindow
AdvWindow = int(message[1])

"""
after connection is established, show display
"""


# Create the main Tkinter window
root = tk.Tk()

# Create a canvas to draw the rectangles
canvas = tk.Canvas(root, width=1024, height=200)
canvas.pack()


def draw_rectangles(sendbase, LastByteAcked, LastByteSent, LastByteWritten):

    print(Fore.GREEN + "sendbase", sendbase, "LastByteAcked", LastByteAcked, "LastByteSent", LastByteSent, "LastByteWritten", LastByteWritten)

    for i in range(min(0, sendbase - 10), 512):
        color = "white"
        if i <= sendbase:
            color = "grey"
        elif i <= LastByteAcked:
            color = "blue"
        elif i <= LastByteSent:
            color = "green"
        elif i <= LastByteWritten:
            color = "red"
        elif i <= sendbase + 256:
            color = "black"
        canvas.create_rectangle(i * 2, 0, (i + 1) * 2, 200, fill=color)


def update_canvas(sendbase, LastByteAcked, LastByteSent, LastByteWritten):
    canvas.delete("all")
    draw_rectangles(sendbase, LastByteAcked, LastByteSent, LastByteWritten)

"""

start receive

"""


def send_message(NextSeqNum, length, Timeout=False):
    if Timeout:
        print(Fore.YELLOW + "Timeout event")
    global AdvWindow, timer, LastByteSent, LastByteWritten, LastByteAcked, PrevByteAcked, t
    print(Fore.BLUE + "Time", int(time.time() - t), "Segment size:", length)

    if length > AdvWindow:
        print(Fore.RESET + "Not enough space from receiver buffer..", abs(NextSeqNum - LastByteWritten), ">", AdvWindow)
        timer = threading.Timer(0.5, send_message, args=(NextSeqNum, length))
        timer.start()
    else:
        message = "SND(" + str(NextSeqNum) + ", " + str(length) + ")"
        print(Fore.RESET + "To Receiver:", message)
        UDPSenderSocket.sendto(message.encode(), channel_address)
        LastByteSent += length
        NextSeqNum += length
        AdvWindow -= length
        # (3) timeout event
        timer = threading.Timer(5, send_message, args=(NextSeqNum, length, True))
        timer.start()




def message_loop():
    global window, LastByteWritten, NextSeqNum, LastByteAcked, AdvWindow, sendbase, LastByteSent, timer

    message_index = 0

    while message_index < len(scenarios):

        # (1) get input message
        message, delay = scenarios[message_index]

        # check buffer size capacity
        if message > bufferSize:
            print(Fore.RESET + "Cannot send message more than 1024 bytes")
            message_index += 1
            continue
        elif window + message > bufferSize:
            print(Fore.RESET + "Not enough space from RDTP buffer.. waiting")
            time.sleep(0.5)
            continue

        # save message to window buffer
        window += message
        LastByteWritten += message

        # (2) send message to receiver
        # if NextSeqNum != LastByteWritten:  # which is always happens.. so just send message
        send_message(NextSeqNum, message)

        # update canvas
        update_thread = threading.Thread(target=update_canvas, daemon=True, args=(sendbase, LastByteAcked, LastByteSent, LastByteWritten))
        update_thread.start()

        # (4) receive ACK from receiver
        bytesAddressPair = UDPSenderSocket.recvfrom(bufferSize)
        receivedMessage = bytesAddressPair[0].decode()[4:-1].split(", ")

        print(Fore.RESET + "From Receiver:", bytesAddressPair[1], "Message:", bytesAddressPair[0].decode())

        AdvWindow = int(receivedMessage[1])  # set AdvWindow size

        if int(receivedMessage[0]) > sendbase:
            sendbase = int(receivedMessage[0])
            LastByteAcked = int(receivedMessage[0]) - 1

            if LastByteAcked != LastByteSent:
                # TODO: regulate timer
                print(Fore.RESET + "timer regulation")
                timer.cancel()
            else:
                timer.cancel()

        message_index += 1
        time.sleep(delay)



message_thread = threading.Thread(target=message_loop)
message_thread.start()

root.mainloop()
