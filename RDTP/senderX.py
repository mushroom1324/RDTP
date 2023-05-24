import socket
import threading
import time
import tkinter as tk
from colorama import Fore
import configparser

config = configparser.ConfigParser()
config.read('../RDTP.conf')

# get scenario
path = "./scenario/" + config['DEFAULT']['sender_scenario_file'] + ".txt"
file = open(path, "r").read()
scenario = list(map(int, file.split(" ")))
scenarios = []
first = 0
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

receiver_ip_addr = config['DEFAULT']['receiver_ip_addr']
receiver_port_number = int(config['DEFAULT']['receiver_port_number'])

channel_ip_addr = config['DEFAULT']['channel_ip_addr']
channel_port_number = int(config['DEFAULT']['channel_port_number'])
channel_address = (channel_ip_addr, channel_port_number)

sender_ip_addr = config['DEFAULT']['sender_ip_addr']
sender_port_number = int(config['DEFAULT']['sender_port_number'])

timeout_value = int(config['DEFAULT']['sender_timeout_value'])

window_size = int(config['DEFAULT']['sender_window_size'])
sequence_number = int(config['DEFAULT']['sender_init_seq_no'])
window = 0
next_sequence_number = 0

sendbase = 0
last_byte_sent = 0
last_byte_acked = 0
last_byte_written = 0

M = [[0, 0] for _ in range(513)]

UDPSenderSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPSenderSocket.bind((sender_ip_addr, sender_port_number))


"""
establish connection
    - set AdvWindow
"""

# send message to receiver
initial_msg = "ISN : " + str(sequence_number)
print("To Receiver:", initial_msg)
UDPSenderSocket.sendto(initial_msg.encode(), channel_address)

# receive ACK from receiver
message, receiverAddress = UDPSenderSocket.recvfrom(window_size)

print("From Receiver:", receiverAddress, "Message:", message.decode())
message = message.decode()[1:-1].split(", ")

# Set initial AdvWindow
AdvWindow = int(message[1])

"""
after connection is established, show display
"""

# kill thread event
stop_event = threading.Event()

# Create the main Tkinter window
root = tk.Tk()

# Create a canvas to draw the rectangles
canvas = tk.Canvas(root, width=1024, height=200)
canvas.pack()


def draw_rectangles(sendbase, last_byte_acked, last_byte_sent, last_byte_written):

    print(Fore.GREEN + "sendbase", sendbase, "LastByteAcked", last_byte_acked, "LastByteSent", last_byte_sent, "LastByteWritten", last_byte_written)

    for i in range(min(0, sendbase - 10), 512):
        color = "white"
        if i <= sendbase:
            color = "grey"
        elif i <= last_byte_acked:  # which cannot happen..
            color = "blue"
        elif i <= last_byte_sent:
            color = "green"
        elif i <= last_byte_written:
            color = "red"
        elif i <= sendbase + 256:
            color = "black"
        canvas.create_rectangle(i * 2, 0, (i + 1) * 2, 200, fill=color)


def update_canvas(sendbase, last_byte_acked, last_byte_sent, last_byte_written):
    canvas.delete("all")
    draw_rectangles(sendbase, last_byte_acked, last_byte_sent, last_byte_written)

"""

start receive

"""


def send_message(next_sequence_number, length, Timeout=False):
    global AdvWindow, timer, last_byte_sent, last_byte_written, last_byte_acked, PrevByteAcked, t

    if stop_event.is_set():
        return

    if Timeout:
        print(Fore.YELLOW + "Timeout event")
    print(Fore.BLUE + "Time", int(time.time() - t), "Segment size:", length)

    if length > AdvWindow:
        print(Fore.RESET + "Not enough space from receiver buffer..", length, ">", AdvWindow)
        timer = threading.Timer(0.5, send_message, args=(next_sequence_number, length))
        timer.start()
    else:
        message = "SND(" + str(next_sequence_number) + ", " + str(length) + ")"
        print(Fore.RESET + "To Receiver:", message)
        UDPSenderSocket.sendto(message.encode(), channel_address)
        if not Timeout:
            last_byte_sent += length
            AdvWindow -= length
        # (3) timeout event
        timer = threading.Timer(timeout_value, send_message, args=(next_sequence_number, length, True))
        timer.start()

    M[next_sequence_number] = [length, time.time()]


def message_loop():
    global window, last_byte_written, next_sequence_number, last_byte_acked, AdvWindow, sendbase, last_byte_sent, timer, timeout_value

    message_index = 0

    while message_index < len(scenarios) or last_byte_acked != last_byte_sent:

        if message_index < len(scenarios):
            # (1) get input message
            message, delay = scenarios[message_index]

            # check buffer size capacity
            if message > window_size:
                print(Fore.BLACK + "Cannot send message more than 1024 bytes")
                message_index += 1
                continue
            elif window + message > window_size:
                print(Fore.BLACK + "Not enough space from sender buffer.. waiting")
                time.sleep(0.5)
                continue

            # save message to window buffer
            window += message
            last_byte_written += message

            # (2) send message to receiver
            # if NextSeqNum != LastByteWritten:  # which is always happens.. so just send message
            send_message(next_sequence_number, message)
            next_sequence_number += message

        # update canvas
        update_thread = threading.Thread(target=update_canvas, daemon=True, args=(sendbase, last_byte_acked, last_byte_sent, last_byte_written))
        update_thread.start()

        # (4) receive ACK from receiver
        bytesAddressPair = UDPSenderSocket.recvfrom(window_size)
        receivedMessage = bytesAddressPair[0].decode()[4:-1].split(", ")

        print(Fore.RESET + "From Receiver:", bytesAddressPair[1], "Message:", bytesAddressPair[0].decode())

        AdvWindow = int(receivedMessage[1])  # set AdvWindow size

        if int(receivedMessage[0]) > sendbase:
            sendbase = int(receivedMessage[0])
            last_byte_acked = int(receivedMessage[0]) - 1
            print(Fore.RED + "last_byte_sent", last_byte_sent, "last_byte_acked:", last_byte_acked)
            if last_byte_acked != last_byte_sent:
                # timeout_value -= int(time.time() - M[last_byte_acked][1])
                print(Fore.CYAN + "Timeout value:", timeout_value)
                # change timer to new timeout value
                timer.cancel()
                # TODO : man.. why..
                timer = threading.Timer(timeout_value, send_message, args=(last_byte_acked + 1, message + last_byte_sent - last_byte_acked))
                timer.start()
        timer.cancel()

        message_index += 1
        time.sleep(delay)
    print("Finish sending all messages..")
    stop_event.set()
    # send FIN message to receiver
    UDPSenderSocket.sendto("FIN".encode(), channel_address)
    # receive ACK from receiver
    while True:
        print("Waiting for ACK..")
        message, receiverAddress = UDPSenderSocket.recvfrom(window_size)
        if message.decode() == "ACK":
            print("From Receiver:", receiverAddress, "Message:", message.decode())
            print("Connection Finished")
            quit(0)


message_thread = threading.Thread(target=message_loop)
message_thread.start()

root.mainloop()


