import socket
import threading


receiver_ip_addr = "127.0.0.1"
receiver_port_number = 8000

channel_ip_addr = "127.0.0.1"
channel_port_number = 8001

sender_ip_addr = "127.0.0.1"
sender_port_number = 8080

bufferSize = 1024
window = ""
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
after connection is established
"""


def send_message():
    global NextSeqNum, AdvWindow, timer, LastByteSent, LastByteWritten, LastByteAcked, PrevByteAcked

    if LastByteAcked == PrevByteAcked:
        NextSeqNum = LastByteAcked
    PrevByteAcked = LastByteAcked

    if abs(NextSeqNum - LastByteWritten) > AdvWindow:
        print("Not enough space from receiver buffer.. waiting")
        # TODO: should retry
        return
    else:
        print("window:", window)
        message = "SND(" + str(NextSeqNum) + ", " + window[NextSeqNum:LastByteWritten] + ")"
        print("To Receiver:", message)
        UDPSenderSocket.sendto(message.encode(), channel_address)
        LastByteSent += abs(NextSeqNum - LastByteWritten)
        NextSeqNum += abs(NextSeqNum - LastByteWritten) - 1
        AdvWindow -= abs(NextSeqNum - LastByteWritten)
        # (3) timeout event
        timer = threading.Timer(5, send_message)
        timer.start()


while True:
    # (1) get input message
    message = input("Input message: ")

    # check buffer size capacity
    if len(message) > 1024:
        print("Cannot send message more than 1024 bytes")
        message = ""
        continue
    elif len(window) + len(message) > bufferSize:
        print("Not enough space from RDTP buffer.. waiting")
        continue

    # save message to window buffer
    window += message
    LastByteWritten += len(message)

    # (2) send message to receiver
    if NextSeqNum != LastByteWritten:
        send_message()

    # (4) receive ACK from receiver
    bytesAddressPair = UDPSenderSocket.recvfrom(bufferSize)
    receivedMessage = bytesAddressPair[0].decode()[4:-1].split(", ")

    print("From Receiver:", bytesAddressPair[1], "Message:", bytesAddressPair[0].decode())

    AdvWindow = int(receivedMessage[1])  # set AdvWindow size

    if int(receivedMessage[0]) > sendbase:
        sendbase = int(receivedMessage[0])
        LastByteAcked = int(receivedMessage[0]) - 1
        NextSeqNum = int(receivedMessage[0]) - 1
        if LastByteAcked != LastByteSent:
            # TODO: regulate timer
            print("timer regulation")
            timer.cancel()
            pass
        else:
            timer.cancel()




