import socket
import threading
import configparser
import time
import tkinter as tk
from colorama import Fore


config = configparser.ConfigParser()
config.read('../RDTP.conf')

# get scenario
path = "./scenario/" + config['DEFAULT']['receiver_scenario_file'] + ".txt"
file = open(path, "r").read()

scenarios = list(map(int, file.split(" ")))



receiver_ip_addr = config['DEFAULT']['receiver_ip_addr']
receiver_port_number = int(config['DEFAULT']['receiver_port_number'])

channel_ip_addr = config['DEFAULT']['channel_ip_addr']
channel_port_number = int(config['DEFAULT']['channel_port_number'])
channel_address = (channel_ip_addr, channel_port_number)

sender_ip_addr = config['DEFAULT']['sender_ip_addr']
sender_port_number = int(config['DEFAULT']['sender_port_number'])

application_storage = 0

window_size = 170
window = 0

rcvbase = 0
last_byte_rcvd = 0
last_byte_read = 0


UDPReceiverSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPReceiverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, window_size)
UDPReceiverSocket.bind((receiver_ip_addr, receiver_port_number))


while True:
    """
    establish connection
        - set senderAddressPort
        - set initialSequenceNumber
    """
    msgFromSender = UDPReceiverSocket.recvfrom(window_size)
    senderAddressPort = (msgFromSender[1][0], msgFromSender[1][1])
    print("From Sender:", senderAddressPort, "Message:", msgFromSender[0].decode())

    initialSequenceNumber = int(msgFromSender[0].decode().split(" ")[2])
    ack_msg = "ACK(" + str(initialSequenceNumber + 1) + ", " + str(window_size) + ")"

    print("To Sender:", ack_msg)
    UDPReceiverSocket.sendto(ack_msg.encode(), senderAddressPort)
    break

"""
after connection is established, show display
"""

# kill thread event
stop_event = threading.Event()

# Create the main Tkinter window
root = tk.Tk()

root.title('Receiver Y')

# Create a canvas to draw the rectangles
canvas = tk.Canvas(root, width=1024, height=200)
canvas.pack()


def draw_rectangles(rcvbase, last_byte_rcvd, last_byte_read, window):

    print(Fore.GREEN + "rcvbase", rcvbase, "last_byte_rcvd", last_byte_rcvd, "last_byte_read", last_byte_read, "window", window)

    for i in range(min(0, rcvbase - 10), 512):
        color = "white"
        if i <= rcvbase:
            color = "grey"
        elif i <= last_byte_rcvd:  # which cannot happen..
            color = "blue"
        elif i <= last_byte_read:
            color = "green"
        elif i <= rcvbase + window_size:
            color = "black"
        canvas.create_rectangle(i * 2, 0, (i + 1) * 2, 200, fill=color)


def update_canvas(rcvbase, last_byte_rcvd, last_byte_read, window):
    canvas.delete("all")
    draw_rectangles(rcvbase, last_byte_rcvd, last_byte_read, window)


"""

receive message

"""


def read_message():
    global rcvbase, last_byte_rcvd, last_byte_read, window, application_storage, root

    index = 0
    while not stop_event.is_set():

        # get delay from scenario
        delay = scenarios[index]
        index += 1
        if index == len(scenarios):
            index = 0

        # application read data
        if last_byte_rcvd != last_byte_read:
            application_storage += window
            rcvbase += window
            last_byte_read = last_byte_rcvd
            window = 0
            print(Fore.BLUE + "Application storage:", application_storage)

        time.sleep(delay)


def receive_message():
    global rcvbase, last_byte_rcvd, last_byte_read, window, application_storage, root

    while True:
        # receive message
        bytesAddressPair = UDPReceiverSocket.recvfrom(window_size)
        print(Fore.RESET + "From Sender:", bytesAddressPair[1], "Message:", bytesAddressPair[0].decode())
        if bytesAddressPair[0].decode() == "FIN":
            # send ACK to sender
            print(Fore.RESET + "To Sender:", "ACK")
            UDPReceiverSocket.sendto("ACK".encode(), bytesAddressPair[1])
            time.sleep(2)
            # update canvas
            update_thread = threading.Thread(target=update_canvas, daemon=True,
                                             args=(rcvbase, last_byte_rcvd, last_byte_read, window))
            update_thread.start()
            # root.quit()
            stop_event.set()
            while last_byte_rcvd != last_byte_read:
                time.sleep(1)
            print(Fore.GREEN + "Connection Finished")
            exit(0)

        receivedMessage = bytesAddressPair[0].decode()[4:-1].split(", ")

        if int(receivedMessage[0]) == last_byte_rcvd + 1:
            # message received in order

            last_byte_rcvd += int(receivedMessage[1])
            sendMessage = "ACK(" + str(last_byte_rcvd + 1) + ", " + str(window_size - window) + ")"
            print(Fore.RESET + "To Sender:", sendMessage)
            UDPReceiverSocket.sendto(sendMessage.encode(), bytesAddressPair[1])
            window += int(receivedMessage[1])
        else:
            # discard segment that is out of order
            # resend ACK
            sendMessage = "ACK(" + str(last_byte_rcvd + 1) + ", " + str(window_size - window) + ")"
            print(Fore.YELLOW + "To Sender (Retransmit):", sendMessage)
            UDPReceiverSocket.sendto(sendMessage.encode(), bytesAddressPair[1])

        # update canvas
        update_thread = threading.Thread(target=update_canvas, daemon=True,
                                         args=(rcvbase, last_byte_rcvd, last_byte_read, window))
        update_thread.start()


# read message thread
read_thread = threading.Thread(target=read_message, daemon=True)
read_thread.start()

# start receive message thread
receive_thread = threading.Thread(target=receive_message, daemon=True)
receive_thread.start()

root.mainloop()
