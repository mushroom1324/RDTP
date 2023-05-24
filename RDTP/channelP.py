import socket
import threading
from collections import deque

receiver_ip_addr = "127.0.0.1"
receiver_port_number = 8000

sender_ip_addr = "127.0.0.1"
sender_port_number = 8080

channel_ip_addr = "127.0.0.1"
channel_port_number = 8001
bufferSize = 1024

# Channel P rules
scenario = "N4L1N3L2N23c1N*"  # example scenario

# Set up the socket
UDPChannelSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPChannelSocket.bind((channel_ip_addr, channel_port_number))

# Parse the scenario
rules = deque()
i = 0
while i < len(scenario):
    first = scenario[i]
    second = ""
    i += 1
    while i < len(scenario):
        if scenario[i].isdigit():
            second += scenario[i]
        elif scenario[i] == "*":
            second = 1e11
        else:
            break
        i += 1
    rules.append([first, int(second)])


def apply_rule(packet, address):
    rule = rules[0][0]

    # Apply the rule
    if rule == "L":  # Loss
        print("Packet lost", packet, address)
        pass  # Packet is lost, do nothing
    elif rule == "N":  # Normal
        print("Packet normal", packet, address)
        if address[1] == receiver_port_number:
            UDPChannelSocket.sendto(packet, (sender_ip_addr, sender_port_number))
        else:
            UDPChannelSocket.sendto(packet, (receiver_ip_addr, receiver_port_number))
    elif rule == "c":  # Corrupted
        # TODO: Congeted packet ( time delay )
        pass

    # Update the rule index
    rules[0][1] -= 1
    if rules[0][1] == 0:
        rules.popleft()


while True:
    print("Waiting for message...", rules)
    data, addr = UDPChannelSocket.recvfrom(bufferSize)
    print("From:", addr, "Message:", data.decode())
    threading.Thread(target=apply_rule, args=(data, addr)).start()

