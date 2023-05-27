# RDTP : Reliable Datagram Transfer Protocol

## Introduction

- UDP를 이용한 신뢰성 있는 데이터 전송 프로토콜을 구현한다.
- Sender X, Receiver Y, Channel P으로 구성된다.
  - Channel P는 가상의 인터넷 환경을 실험하기 위한 채널으로, 트랜스포트 레이어 아래라고 생각하면 된다.


# Sender X
- Sender X가 가지고 있는 Thread는 다음과 같다:
  - update_canvas : Sender X의 window state를 display한다.
  - send_message : 아직 보낸 시도를 하지 않은, window에 저장된 메세지를 보낸다.
  - retransmit : timeout이 발생한 메세지를 재전송한다.
  - message_loop : application layer으로부터 메세지를 받아서 window에 저장한다.
  - receive_ack : Receiver Y로부터 ACK를 받는다.
- sender_scenario.txt에 정의된 시나리오를 따른다.

# Channel P
- Channel P의 기능은 다음과 같다:
  - 전송 과정 중 3계층 이하를 흉내낸다.
  - 메세지 손실, 혼잡 상황을 구현한다.
- channel_scenario.txt에 정의된 시나리오를 따른다.

# Receiver Y
- Receiver Y가 가지고 있는 Thread는 다음과 같다:
    - update_canvas : Receiver Y의 window state를 display한다.
    - read_message : application layer으로 읽지 않은 메세지를 저장한다.
    - receive_message : Sender X로부터 메세지를 받고 ACK를 보낸다.
- receiver_scenario.txt에 정의된 시나리오를 따른다.

## How to run
- channel P >> receiver Y >> sender X 순서대로 실행한다.
  - sender X는 실행하는 즉시 channel P를 통해 receiver Y로 세그멘트를 전송한다. (연결 설정 시작)
  - receiver Y는 세그멘트를 받을 준비가 되어있어야 한다.

# 구현

- 언어 : Python3
- read, send, receive, update_canvas 등의 개별적인 event가 병렬적으로 실행되어야 한다.
  - Threading을 이용하여 구현
- UDP Transfer를 기반으로 한다.
  - Socket을 이용하여 구현
- GUI로 window를 display한다.
  - tkinter를 이용하여 구현
- Console logging의 가시성 추가
  - colorama을 이용해 구현
  
# Description

- RDTP는 신뢰성을 보장하는 Datagram 전송 프로토콜이다.

### 2-way handshake

- Sender X는 Receiver Y에게 initial sequence number를 보낸다.
- Receiver Y는 이에 ACK(y, w)로 응답한다.
<img width="338" alt="image" src="https://github.com/mushroom1324/Algorithm/assets/76674422/d65d0580-d930-41f8-a0d9-8fafc8e229cb">

## Sender X의 기능

#### 연결 설정
- ISN(initial sequence number)를 송신 후, ACK을 수신한다.

#### Application으로부터 메세지 수신
- `sender_scenario.txt` 파일에 정의된 시나리오대로 메세지를 수신한다.
<img width="1145" alt="image" src="https://github.com/mushroom1324/Algorithm/assets/76674422/6dabb13f-3c48-4c35-9a8d-171dc2f5a5a3">
- 메세지를 수신하면 window에 저장한다.
- window에 가용 범위가 부족하면 0.5초 간격으로 읽기를 재시도한다.
- 읽기에 성공하면 send_message를 **최초 시도**한다.

#### Receiver Y에게 메세지 전송
- `SND(next_sequence_number, length)`의 형태로 보낸다.
  - next_sequence_number : 보내는 세그먼트의 시작 번호
  - length(message) : 보내는 세그먼트의 길이
- 보내면서 next_sequence_number를 길이만큼 증가시킨다.

#### Receiver Y로부터 ACK 수신
- `ACK(y, w)`의 형태로 수신한다.
  - y : receiver가 다음으로 받길 기대하는 sequence number
  - w : receiver의 가용 window size
- sendbase보다 y가 작다면 폐기한다. (중복 수신)
- `y - 1 == last_byte_sent` 이 성립한다면 패킷이 순서대로 온 것이다.
  - Timeout timer를 취소한다.
- 그렇지 않다면 아직 수신받지 못한 패킷이 여전히 남아있다는 의미이다.
  - Timeout timer를 **수신받지 못한 마지막 패킷을 보낸 시간**에 따라 재설정한다.

``` text
channel_scenario : N2N1c1N1L3N*
sender_scenario : 50 1 50 1 50 1 50 1 50 1 50 1 50 1 50 1 50 1 50 1 50 1 50 1
```
- 다음의 시나리오로 Timeout timer 조정 예시를 확인 가능하다.


#### Timeout에 따른 재전송
- 마지막으로 보낸, ACK을 받지 못한 메세지를 재전송한다.
```python
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
```
- `fin`은 전송 종료를 확인하기 위한 flag이다.
- `scenarios`의 구조:
  - message : 보내는 세그먼트의 길이
  - delay : 보내는 세그먼트의 전송 시간
  - is_acked : ACK을 받았는지 여부
- `is_acked`가 0인 가장 오래된 패킷을 찾아 재전송한다.

#### 연결 종료
- 모든 메세지를 전송한 후, `last_byte_sent == last_byte_ack`이라면 연결 종료를 시작한다.
- `FIN`을 송신한다.
- `ACK`을 수신하면 연결 종료한다.
- Thread 관리를 위해 `stop_event`를 flag로 둔다.

## Receiver Y의 기능

#### 연결 설정
- ISN을 수신하고, ACK을 송신한다.

#### Application으로 메세지 전달
- `receiver_scenario.txt`에 정의된 시간 간격으로 읽기를 시도한다.
- last_byte_rcvd != last_byte_read 이라면 읽기를 시도한다.

#### Sender X로부터 메세지 수신
- `SND(next_sequence_number, length)`의 형태로 수신한다.
  - next_sequence_number : 보내는 세그먼트의 시작 번호
  - length(message) : 보내는 세그먼트의 길이
- 수신한 세그먼트를 window에 저장한다.
```python
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
```
- 만약 next_sequence_number가 last_byte_rcvd + 1이라면 정상적인 수신을 의미한다.
  - `last_byte_rcvd += length(message)`
  - ACK(`last_byte_rcvd + 1, window_size - window`)을 송신한다.
  - window 조정
- 그렇지 않다면 수신한 세그먼트는 순서가 맞지 않는다.
  - ACK(`last_byte_rcvd + 1, window_size - window`)을 재송신한다.

## Channel P의 기능

<img width="1166" alt="image" src="https://github.com/mushroom1324/Algorithm/assets/76674422/8697c673-595b-456f-8c45-6e26e163869c">

- Channel P는 3계층 이하를 흉내낸다.
- Sender X와 Receiver Y 사이에 위치한다.

# 실행 화면
<img width="1440" alt="image" src="https://github.com/mushroom1324/Algorithm/assets/76674422/6f0ade5b-4888-4e1f-a826-7da88138db24">

## Display : Sender X
- Sender X의 전송 상황을 보여준다.
- canvas update event마다 sendbase, last_byte_acked, last_byte_sent, last_byte_written을 콘솔에 표시한다. (초록색)
- 전송 시 Time, segment size, sequence number를 console에 표시한다. (파란색)
- 가시성을 위해 tkinter를 이용해 GUI를 구현하였다.
  - sendbase 이하: 하얀색
  - sendbase ~ last_byte_acked: 파란색
  - last_byte_acked ~ last_byte_sent: 초록색
  - last_byte_sent ~ last_byte_written: 빨간색
  - last_byte_written ~ window_size: 회색
  - window_size 이상: 하얀색

## Display : Receiver Y
- canvas update event마다 rcvbase, last_byte_rcvd, last_byte_read, window를 콘솔에 표시한다. (초록색)
- Application Read event마다 저장된 메세지 용량을 표시한다. (파란색)
- 가시성을 위해 tkinter를 이용해 GUI를 구현하였다.
  - rcvbase 이하: 하얀색
  - rcvbase ~ last_byte_rcvd: 파란색
  - last_byte_rcvd ~ last_byte_read: 초록색
  - last_byte_read ~ window_size: 회색
  - window_size 이상: 하얀색

# RDTP.conf
- 환경 변수들을 정의한다.
```text
# 주석: RDTP.conf - 2023 컴퓨터네트워크 프로그래밍 과제 configuration file
[DEFAULT]
sender_ip_addr = 127.0.0.1
sender_port_number = 8080
sender_window_size = 256
sender_init_seq_no = 0
sender_timeout_value = 6
sender_scenario_file = sender_scenario

receiver_ip_addr = 127.0.0.1
receiver_port_number = 8000
receiver_window_size = 170
receiver_scenario_file = receiver_scenario

channel_ip_addr = 127.0.0.1
channel_port_number = 8001
channel_scenario_file = channel_scenario
channel_latency = 0.1
channel_small_congestion_delay = 4
channel_big_congestion_delay = 6
```
