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
        scenarios.append([first, scenario[i], 0])
    else:
        first = scenario[i]
    i += 1
scenarios.append([scenario[i], 0, 0])
print(*scenarios)
message_index = 0

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
message = 0

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
message = message.decode()[4:-1].split(", ")
next_sequence_number = int(message[0])
# Set initial AdvWindow
adv_window = int(message[1])

"""
after connection is established, show display
"""

# kill thread event
stop_event = threading.Event()

# Create the main Tkinter window
root = tk.Tk()
root.title('Sender X')

# Create a canvas to draw the rectangles
canvas = tk.Canvas(root, width=1024, height=200)

canvas.pack()


def draw_rectangles(sendbase, last_byte_acked, last_byte_sent, last_byte_written):

    print(Fore.GREEN + "sendbase", sendbase, "LastByteAcked", last_byte_acked, "LastByteSent", last_byte_sent, "LastByteWritten", last_byte_written)

    for i in range(min(0, sendbase - 10), 512):
        color = "white"
        if i <= sendbase:
            color = "white"
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
# Initialize timer
timer = threading.Timer(timeout_value, update_canvas)


def send_message(sequence_number, length, is_timeout=False):
    global adv_window, timer, last_byte_sent, last_byte_written, last_byte_acked, t, timeout_value

    # print(next_sequence_number, last_byte_acked)
    if stop_event.is_set():
        print(Fore.RED + "end process")
        return 0

    print(Fore.BLUE + "Time", int(time.time() - t), "Segment size:", length, "Sequence Number:", sequence_number)

    message = "SND(" + str(sequence_number) + ", " + str(length) + ")"
    print(Fore.RESET + "To Receiver:", message)
    UDPSenderSocket.sendto(message.encode(), channel_address)
    if not is_timeout:
        last_byte_sent += length
        adv_window -= length

    M[last_byte_sent] = [length, time.time()]
    if is_timeout:
        return 0
    else:
        return length


def retransmit(fin=False):
    global timer

    if fin:
        print("Time", int(time.time() - t), "Retransmitting FIN")
        UDPSenderSocket.sendto("FIN".encode(), channel_address)
        timer = threading.Timer(timeout_value, retransmit, (True,))
        timer.start()
        return

    for message, delay, is_acked in scenarios:
        if not is_acked:
            print(Fore.RED + "Time", int(time.time() - t), "Retransmitting", last_byte_acked + 1, "to", last_byte_acked + message)
            send_message(last_byte_acked + 1, message, True)
            break
    timer = threading.Timer(timeout_value, retransmit)
    timer.start()


def message_loop():
    global window, last_byte_written, next_sequence_number, last_byte_acked, adv_window, sendbase, last_byte_sent, timer, timeout_value, message, message_index

    while message_index < len(scenarios) or last_byte_acked != last_byte_sent:

        if message_index < len(scenarios):
            # (1) get input message
            message, delay, is_acked = scenarios[message_index]
            # check buffer size capacity
            if last_byte_written - sendbase + message > window_size:
                print(Fore.BLACK + "Not enough space from sender buffer.. waiting")
                time.sleep(0.5)
                continue

            # save message to window buffer
            window += message
            last_byte_written += message

            while message > adv_window:
                print(Fore.RESET + "Not enough space from receiver buffer..", message, ">", adv_window)
                time.sleep(0.5)

            # (2) send message to receiver
            if next_sequence_number != last_byte_written:  # which is always happens.. so just send message
                next_sequence_number += send_message(next_sequence_number, message)

            # (3) timeout event
            if not timer.is_alive():
                timer = threading.Timer(timeout_value, retransmit)
                timer.start()

            # update canvas
            update_thread = threading.Thread(target=update_canvas, daemon=True, args=(sendbase, last_byte_acked, last_byte_sent, last_byte_written))
            update_thread.start()

        message_index += 1
        time.sleep(delay)

    print(Fore.YELLOW + "Finish sending all messages..")
    stop_event.set()
    # send FIN message to receiver
    UDPSenderSocket.sendto("FIN".encode(), channel_address)
    timer.cancel()
    timer = threading.Timer(timeout_value, retransmit, args=(True,))
    timer.start()


def receive_ack():
    global adv_window, sendbase, last_byte_acked, last_byte_sent, timer, message, root, timeout_value

    while True:
        # (4) receive ACK from receiver
        bytes_address_pair = UDPSenderSocket.recvfrom(window_size)

        # Finish receiving ACK when last ACK received
        if len(bytes_address_pair[0].decode()) == 3:
            print(Fore.RESET + "From Receiver:", receiverAddress, "Message:", bytes_address_pair[0].decode())
            print(Fore.GREEN + "Connection Finished")
            timer.cancel()
            # root.quit()
            exit(0)

        received_message = bytes_address_pair[0].decode()[4:-1].split(", ")

        print(Fore.RESET + "From Receiver:", bytes_address_pair[1], "Message:", bytes_address_pair[0].decode())

        adv_window = int(received_message[1])  # set AdvWindow size

        if int(received_message[0]) > sendbase:
            i = 0
            temp = 0
            while temp != int(received_message[0]) - 1:
                temp += scenarios[i][0]
                scenarios[i][2] = 1
                i += 1

            sendbase = int(received_message[0])
            last_byte_acked = int(received_message[0]) - 1
            if last_byte_acked != last_byte_sent:
                # change timer to new one
                timer.cancel()
                timeout_value -= int(time.time() - M[last_byte_sent][1])
                print(Fore.RESET + "Time", int(time.time() - t), "New timer", timeout_value)
                timer = threading.Timer(timeout_value - int(time.time() - M[last_byte_sent][1]), retransmit)
                timer.start()

            else:
                # ACK received to last_byte_sent
                timer.cancel()


        # update canvas
        update_thread = threading.Thread(target=update_canvas, daemon=True,
                                         args=(sendbase, last_byte_acked, last_byte_sent, last_byte_written))
        update_thread.start()


message_thread = threading.Thread(target=message_loop)
message_thread.start()

ack_thread = threading.Thread(target=receive_ack)
ack_thread.start()

root.mainloop()


