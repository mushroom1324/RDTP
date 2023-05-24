import socket
import configparser

config = configparser.ConfigParser()
config.read('../RDTP.conf')

# get scenario
path = "./scenario/" + config['DEFAULT']['receiver_scenario_file'] + ".txt"
file = open(path, "r").read()

receiver_ip_addr = config['DEFAULT']['receiver_ip_addr']
receiver_port_number = int(config['DEFAULT']['receiver_port_number'])

channel_ip_addr = config['DEFAULT']['channel_ip_addr']
channel_port_number = int(config['DEFAULT']['channel_port_number'])
channel_address = (channel_ip_addr, channel_port_number)

sender_ip_addr = config['DEFAULT']['sender_ip_addr']
sender_port_number = int(config['DEFAULT']['sender_port_number'])

application_storage = 0

window_size = 256
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
after connection is established
"""


while True:
    print("rcvbase:", rcvbase, "last_byte_rcvd:", last_byte_rcvd, "last_byte_read:", last_byte_read, "window:", window)
    # application read data
    if last_byte_rcvd != last_byte_read:
        print("Application read data:", application_storage, rcvbase)
        application_storage += window
        rcvbase += window
        last_byte_read = last_byte_rcvd
        window = 0

    # receive message
    bytesAddressPair = UDPReceiverSocket.recvfrom(window_size)
    print("From Sender:", bytesAddressPair[1], "Message:", bytesAddressPair[0].decode())
    if bytesAddressPair[0].decode() == "FIN":
        # send ACK to sender
        print("To Sender:", "ACK")
        UDPReceiverSocket.sendto("ACK".encode(), bytesAddressPair[1])
        if window:
            print("Application read data:", application_storage, rcvbase)
            application_storage += window
            rcvbase += window
            last_byte_read = last_byte_rcvd
            window = 0
        exit(0)

    receivedMessage = bytesAddressPair[0].decode()[4:-1].split(", ")

    if int(receivedMessage[0]) == last_byte_rcvd:
        # message received in order
        window += int(receivedMessage[1])

        last_byte_rcvd += int(receivedMessage[1])
        sendMessage = "ACK(" + str(last_byte_rcvd + 1) + ", " + str(window_size - window) + ")"
        print("To Sender:", sendMessage)
        UDPReceiverSocket.sendto(sendMessage.encode(), bytesAddressPair[1])
    else:
        # discard segment that is out of order
        # resend ACK
        sendMessage = "ACK(" + str(last_byte_rcvd + 1) + ", " + str(window_size - window) + ")"
        print("To Sender (Retransmit):", sendMessage)
        UDPReceiverSocket.sendto(sendMessage.encode(), bytesAddressPair[1])


