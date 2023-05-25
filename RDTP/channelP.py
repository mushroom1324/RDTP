import socket
import threading
import time
from collections import deque
import configparser

config = configparser.ConfigParser()
config.read('../RDTP.conf')

# get scenario
path = "./scenario/" + config['DEFAULT']['channel_scenario_file'] + ".txt"
scenario = open(path, "r").read()

receiver_ip_addr = config['DEFAULT']['receiver_ip_addr']
receiver_port_number = int(config['DEFAULT']['receiver_port_number'])

channel_ip_addr = config['DEFAULT']['channel_ip_addr']
channel_port_number = int(config['DEFAULT']['channel_port_number'])
channel_address = (channel_ip_addr, channel_port_number)

sender_ip_addr = config['DEFAULT']['sender_ip_addr']
sender_port_number = int(config['DEFAULT']['sender_port_number'])
buffer_size = 1024

small_congestion_delay = int(config['DEFAULT']['channel_small_congestion_delay'])
big_congestion_delay = int(config['DEFAULT']['channel_big_congestion_delay'])

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
    global rules

    if not rules:
        i = 0
        while i < len(scenario):
            first = scenario[i]
            second = ""
            i += 1
            while i < len(scenario):
                if scenario[i].isdigit():
                    second += scenario[i]
                else:
                    break
                i += 1
            rules.append([first, int(second)])

    rule = rules[0][0]

    # Apply the rule
    if rule == "L":  # Loss
        print("Packet lost", packet, address)
        pass  # Packet is lost, do nothing
    elif rule == "N":  # Normal
        print("Packet normal", packet, address)
        send(address, packet)
    elif rule == "c":  # small congestion
        print("Packet small congestion", packet, address)
        time.sleep(small_congestion_delay)
        threading.Timer(small_congestion_delay, send, args=(address, packet)).start()
    elif rule == "C":  # big congestion
        print("Packet small congestion", packet, address)
        threading.Timer(big_congestion_delay, send, args=(address, packet)).start()

    # Update the rule index
    rules[0][1] -= 1
    if rules[0][1] == 0:
        rules.popleft()


def send(address, packet):
    if address[1] == receiver_port_number:
        UDPChannelSocket.sendto(packet, (sender_ip_addr, sender_port_number))
    else:
        UDPChannelSocket.sendto(packet, (receiver_ip_addr, receiver_port_number))


while True:
    print("Waiting for message...", rules)
    data, addr = UDPChannelSocket.recvfrom(buffer_size)
    print("From:", addr, "Message:", data.decode())
    threading.Thread(target=apply_rule, args=(data, addr)).start()

