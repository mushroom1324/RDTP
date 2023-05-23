import socket

receiver_ip_addr = "127.0.0.1"
receiver_port_number = 8000

channel_ip_addr = "127.0.0.1"
channel_port_number = 8001

sender_ip_addr = "127.0.0.1"
sender_port_number = 8080

applicationStorage = []

maxSequenceNumber = 1000
bufferSize = 512
currentBufferSize = bufferSize
window = ""

prevACK = ""
rcvbase = 0
LastByteRcvd = 0
LastByteRead = 0


UDPReceiverSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPReceiverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, bufferSize)
UDPReceiverSocket.bind((receiver_ip_addr, receiver_port_number))


while True:
    """
    establish connection
        - set senderAddressPort
        - set initialSequenceNumber
    """
    msgFromSender = UDPReceiverSocket.recvfrom(bufferSize)
    senderAddressPort = (msgFromSender[1][0], msgFromSender[1][1])
    print("From Sender:", senderAddressPort, "Message:", msgFromSender[0].decode())

    initialSequenceNumber = int(msgFromSender[0].decode().split(" ")[2])
    ack_msg = "ACK(" + str(initialSequenceNumber + 1) + ", " + str(bufferSize) + ")"

    print("To Sender:", ack_msg)
    UDPReceiverSocket.sendto(ack_msg.encode(), senderAddressPort)
    break

"""
after connection is established
"""


while True:

    # application read data
    if LastByteRcvd != LastByteRead:
        applicationStorage.append(window[LastByteRead:LastByteRcvd])
        rcvbase += len(window[LastByteRead:LastByteRcvd])
        LastByteRead = LastByteRcvd


    # receive message
    bytesAddressPair = UDPReceiverSocket.recvfrom(bufferSize)
    print("From Sender:", bytesAddressPair[1], "Message:", bytesAddressPair[0].decode())
    receivedMessage = bytesAddressPair[0].decode()[4:-1].split(", ")

    if int(receivedMessage[0]) == LastByteRcvd:
        # message reveiced in order
        currentBufferSize -= len(receivedMessage[1])

        LastByteRcvd += len(receivedMessage[1])
        sendMessage = "ACK(" + str(LastByteRcvd + 1) + ", " + str(currentBufferSize) + ")"
        prevACK = sendMessage
        print("To Sender:", sendMessage)
        UDPReceiverSocket.sendto(sendMessage.encode(), bytesAddressPair[1])
    else:
        # discard segment that is out of order
        # resend ACK
        print("To Sender (Retransmit):", prevACK)
        UDPReceiverSocket.sendto(prevACK.encode(), bytesAddressPair[1])


