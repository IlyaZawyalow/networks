import numpy as np
import enum
import time
from threading import Thread
import matplotlib.pyplot as plt

class MessageStatus(enum.Enum):
    OK = enum.auto()
    LOST = enum.auto()

class Message:
    def __init__(self):
        self.number = -1
        self.real_number = -1
        self.data = ""
        self.status = MessageStatus.OK

    def copy(self):
        msg = Message()
        msg.number = self.number
        msg.data = self.data
        msg.status = self.status
        return msg

    def __str__(self):
        return f"({self.real_number}({self.number}), {self.data}, {self.status})"

class MsgQueue:
    def __init__(self, loss_probability=0.3):
        self.msg_queue = []
        self.loss_probability = loss_probability

    def has_msg(self):
        return len(self.msg_queue) > 0

    def get_message(self):
        if self.has_msg():
            return self.msg_queue.pop(0)

    def send_message(self, msg):
        tmp_msg = self.emulating_channel_problems(msg.copy())
        self.msg_queue.append(tmp_msg)

    def emulating_channel_problems(self, msg):
        if np.random.rand() <= self.loss_probability:
            msg.status = MessageStatus.LOST
        return msg

    def __str__(self):
        return "[ " + ", ".join(f"({msg.number}, {msg.status})" for msg in self.msg_queue) + " ]"

def GBN_sender(window_size, max_number, timeout, send_msg_queue, answer_msg_queue, posted_msgs):
    curr_number = 0
    last_ans_number = -1
    start_time = time.time()
    while last_ans_number < max_number:
        expected_number = (last_ans_number + 1) % window_size

        if answer_msg_queue.has_msg():
            ans = answer_msg_queue.get_message()
            if ans.number == expected_number:
                last_ans_number += 1
                start_time = time.time()
            else:
                curr_number = last_ans_number + 1

        if time.time() - start_time > timeout:
            curr_number = last_ans_number + 1
            start_time = time.time()

        if curr_number < last_ans_number + window_size and curr_number <= max_number:
            k = curr_number % window_size
            msg = Message()
            msg.number = k
            msg.real_number = curr_number
            send_msg_queue.send_message(msg)
            posted_msgs.append(f"{curr_number}({k})")

            curr_number += 1

    msg = Message()
    msg.data = "STOP"
    send_msg_queue.send_message(msg)

def GBN_receiver(window_size, send_msg_queue, answer_msg_queue, received_msgs):
    expected_number = 0
    while True:
        if send_msg_queue.has_msg():
            curr_msg = send_msg_queue.get_message()
            if curr_msg.data == "STOP":
                break
            if curr_msg.status == MessageStatus.LOST:
                continue
            if curr_msg.number == expected_number:
                ans = Message()
                ans.number = curr_msg.number
                answer_msg_queue.send_message(ans)
                received_msgs.append(f"{curr_msg.real_number}({curr_msg.number})")
                expected_number = (expected_number + 1) % window_size

def SRP_sender(window_size, max_number, timeout, send_msg_queue, answer_msg_queue, posted_msgs):
    class WndMsgStatus(enum.Enum):
        BUSY = enum.auto()
        NEED_REPEAT = enum.auto()
        CAN_BE_USED = enum.auto()

    class WndNode:
        def __init__(self, number):
            self.status = WndMsgStatus.NEED_REPEAT
            self.time = 0
            self.number = number

        def __str__(self):
            return f"( {self.number}, {self.status}, {self.time})"

    wnd_nodes = [WndNode(i) for i in range(window_size)]
    ans_count = 0

    while ans_count < max_number:
        if answer_msg_queue.has_msg():
            ans = answer_msg_queue.get_message()
            ans_count += 1
            wnd_nodes[ans.number].status = WndMsgStatus.CAN_BE_USED

        curr_time = time.time()
        for node in wnd_nodes:
            if node.number > max_number:
                continue
            if curr_time - node.time > timeout:
                node.status = WndMsgStatus.NEED_REPEAT

        for node in wnd_nodes:
            if node.number > max_number:
                continue
            if node.status in [WndMsgStatus.NEED_REPEAT, WndMsgStatus.CAN_BE_USED]:
                node.status = WndMsgStatus.BUSY
                node.time = time.time()

                msg = Message()
                msg.number = node.number % window_size
                msg.real_number = node.number
                send_msg_queue.send_message(msg)
                posted_msgs.append(f"{msg.real_number}({msg.number})")

                if node.status == WndMsgStatus.CAN_BE_USED:
                    node.number += window_size
                    if node.number > max_number:
                        node.status = WndMsgStatus.BUSY

    msg = Message()
    msg.data = "STOP"
    send_msg_queue.send_message(msg)

def SRP_receiver(window_size, send_msg_queue, answer_msg_queue, received_msgs):
    while True:
        if send_msg_queue.has_msg():
            curr_msg = send_msg_queue.get_message()
            if curr_msg.data == "STOP":
                break
            if curr_msg.status == MessageStatus.LOST:
                continue
            ans = Message()
            ans.number = curr_msg.number
            answer_msg_queue.send_message(ans)
            received_msgs.append(f"{curr_msg.real_number}({curr_msg.number})")

def losing_test():
    window_size = 3
    timeout = 0.2
    max_number = 100
    loss_probability_arr = np.linspace(0, 0.9, 9)
    protocol_arr = ["GBN", "SRP"]

    print("p    | GBN             |SRP")
    print("     | t     |k        |t    |  k")

    gbn_time = []
    srp_time = []
    gbn_k = []
    srp_k = []
    for p in loss_probability_arr:
        table_row = f"{p:.1f}\t"

        send_msg_queue = MsgQueue(p)
        answer_msg_queue = MsgQueue(p)
        posted_msgs = []
        received_msgs = []

        for protocol in protocol_arr:
            if protocol == "GBN":
                sender_th = Thread(target=GBN_sender, args=(window_size, max_number, timeout, send_msg_queue, answer_msg_queue, posted_msgs))
                receiver_th = Thread(target=GBN_receiver, args=(window_size, send_msg_queue, answer_msg_queue, received_msgs))
            elif protocol == "SRP":
                sender_th = Thread(target=SRP_sender, args=(window_size, max_number, timeout, send_msg_queue, answer_msg_queue, posted_msgs))
                receiver_th = Thread(target=SRP_receiver, args=(window_size, send_msg_queue, answer_msg_queue, received_msgs))

            timer_start = time.time()
            sender_th.start()
            receiver_th.start()

            sender_th.join()
            receiver_th.join()
            timer_end = time.time()

            k = len(received_msgs) / len(posted_msgs)
            elapsed = timer_end - timer_start

            table_row += f" | {elapsed:2.2f}  | {k:.2f}   "
            if protocol == "GBN":
                gbn_time.append(elapsed)
                gbn_k.append(k)
            else:
                srp_time.append(elapsed)
                srp_k.append(k)

        print(table_row)

    fig, ax = plt.subplots()
    ax.plot(loss_probability_arr, gbn_k, label="Go-Back-N")
    ax.plot(loss_probability_arr, srp_k, label="Selective repeat")
    ax.set_xlabel('вероятность потери пакета')
    ax.set_ylabel('коэф. эффективности')
    ax.legend()
    ax.grid()
    plt.show()

    fig, ax = plt.subplots()
    ax.plot(loss_probability_arr, gbn_time, label="Go-Back-N")
    ax.plot(loss_probability_arr, srp_time, label="Selective repeat")
    ax.set_xlabel('вероятность потери пакета')
    ax.set_ylabel('время передачи, с')
    ax.legend()
    ax.grid()
    plt.show()

def window_test():
    window_size_arr = range(2, 11)
    timeout = 0.2
    max_number = 100
    loss_probability = 0.2
    protocol_arr = ["GBN", "SRP"]

    print("w    | GBN             |SRP")
    print("     | t     |k        |t    |  k")

    gbn_time = []
    srp_time = []
    gbn_k = []
    srp_k = []
    for window_size in window_size_arr:
        table_row = f"{window_size:}\t"

        send_msg_queue = MsgQueue(loss_probability)
        answer_msg_queue = MsgQueue(loss_probability)
        posted_msgs = []
        received_msgs = []

        for protocol in protocol_arr:
            if protocol == "GBN":
                sender_th = Thread(target=GBN_sender, args=(window_size, max_number, timeout, send_msg_queue, answer_msg_queue, posted_msgs))
                receiver_th = Thread(target=GBN_receiver, args=(window_size, send_msg_queue, answer_msg_queue, received_msgs))
            elif protocol == "SRP":
                sender_th = Thread(target=SRP_sender, args=(window_size, max_number, timeout, send_msg_queue, answer_msg_queue, posted_msgs))
                receiver_th = Thread(target=SRP_receiver, args=(window_size, send_msg_queue, answer_msg_queue, received_msgs))

            timer_start = time.time()
            sender_th.start()
            receiver_th.start()

            sender_th.join()
            receiver_th.join()
            timer_end = time.time()

            k = len(received_msgs) / len(posted_msgs)
            elapsed = timer_end - timer_start

            table_row += f" | {elapsed:2.2f}  | {k:.2f}   "
            if protocol == "GBN":
                gbn_time.append(elapsed)
                gbn_k.append(k)
            else:
                srp_time.append(elapsed)
                srp_k.append(k)

        print(table_row)

    fig, ax = plt.subplots()
    ax.plot(window_size_arr, gbn_k, label="Go-Back-N")
    ax.plot(window_size_arr, srp_k, label="Selective repeat")
    ax.set_xlabel('размер окна')
    ax.set_ylabel('коэф. эффективности')
    ax.legend()
    ax.grid()
    plt.show()

    fig, ax = plt.subplots()
    ax.plot(window_size_arr, gbn_time, label="Go-Back-N")
    ax.plot(window_size_arr, srp_time, label="Selective repeat")
    ax.set_xlabel('размер окна')
    ax.set_ylabel('время передачи, с')
    ax.legend()
    ax.grid()
    plt.show()

if __name__ == "__main__":
    # Conduct the tests
    losing_test()
    window_test()
