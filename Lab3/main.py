#!/usr/bin/env python3
import pygame
import random
import time
import math
import enum

#####################################
# Параметры конфигурации
#####################################

CONFIG = {
    "routers_number": 50,
    "distance": 0.25,
    "window_size": 16,
    "package": 64,
    "timeout": 0.2,
    "loss_probability": 0.01,
    "fps": 30,
    "prob_remove": 0.1,
    "topology_update_interval": 60
}

WIDTH = 800
HEIGHT = 800


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
PURPLE = (128, 0, 128)
DARK_GRAY = (64, 64, 64)

#####################################
# Классы для сообщений/очередей
#####################################

class MessageStatus(enum.Enum):
    OK = enum.auto()
    LOST = enum.auto()

class Message:
    def __init__(self):
        self.number = -1
        self.real_number = -1
        self.data = ""
        self.status = MessageStatus.OK

    def __str__(self):
        return f"Message(real={self.real_number}, number={self.number}, data={self.data}, status={self.status})"


class MsgQueue:
    def __init__(self, loss_probability=0.0):
        self.msg_queue = []
        self.loss_probability = loss_probability

    def has_msg(self):
        return len(self.msg_queue) > 0

    def get_message(self):
        if self.has_msg():
            return self.msg_queue.pop(0)
        return None

    def send_message(self, msg):
        val = random.random()
        if val < self.loss_probability:
            msg.status = MessageStatus.LOST
        self.msg_queue.append(msg)


#####################################
# Реализация GBN (Go-Back-N)
#####################################
def GBN_sender(window_size, max_number, timeout,
               send_msg_queue, answer_msg_queue, posted_msgs):
    curr_number = 0
    last_ans_number = -1
    start_time = time.time()

    while last_ans_number < max_number:
        expected_number = (last_ans_number + 1) % window_size

        # Смотрим, нет ли ACK
        if answer_msg_queue.has_msg():
            ans = answer_msg_queue.get_message()
            if ans.number == expected_number:
                last_ans_number += 1
                start_time = time.time()
            else:
                curr_number = last_ans_number + 1

        # Проверяем timeout
        if time.time() - start_time > timeout:
            curr_number = last_ans_number + 1
            start_time = time.time()

        if (curr_number < last_ans_number + window_size) and (curr_number <= max_number):
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
    """Пример приёмника GBN."""
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


#####################################
# Реализация SRP (Selective Repeat)
#####################################
class WndMsgStatus(enum.Enum):
    BUSY = enum.auto()
    NEED_REPEAT = enum.auto()
    CAN_BE_USED = enum.auto()

class WndNode:
    def __init__(self, number):
        self.status = WndMsgStatus.NEED_REPEAT
        self.time = 0
        self.number = number

def SRP_sender(window_size, max_number, timeout,
               send_msg_queue, answer_msg_queue, posted_msgs):
    """Пример отправителя SRP."""
    wnd_nodes = [WndNode(i) for i in range(window_size)]
    ans_count = 0

    while ans_count < max_number:
        # Проверяем входящие ACK
        if answer_msg_queue.has_msg():
            ans = answer_msg_queue.get_message()
            ans_count += 1
            wnd_nodes[ans.number].status = WndMsgStatus.CAN_BE_USED

        # Проверяем timeouts
        curr_time = time.time()
        for node in wnd_nodes:
            if node.number > max_number:
                continue
            if curr_time - node.time > timeout:
                node.status = WndMsgStatus.NEED_REPEAT

        # Отправляем новые или повторяем
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

            if node.status == WndMsgStatus.BUSY and node.number <= max_number:
                if node.number + window_size <= max_number:
                    node.number += window_size
                else:
                    node.number = max_number + 1

    msg = Message()
    msg.data = "STOP"
    send_msg_queue.send_message(msg)


def SRP_receiver(window_size, send_msg_queue, answer_msg_queue, received_msgs):
    """Пример приёмника SRP."""
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


#####################################
# Упрощённый алгоритм OSPF (Dijkstra)
#####################################
def dijkstra(nodes_coords, adjacency, start_idx):
    n = len(nodes_coords)
    inf = float('inf')
    dist = [inf] * n
    dist[start_idx] = 0.0
    used = [False] * n
    paths = [[] for _ in range(n)]
    paths[start_idx] = [start_idx]

    while True:
        idx_min = -1
        dist_min = inf
        for i in range(n):
            if (not used[i]) and (dist[i] < dist_min):
                dist_min = dist[i]
                idx_min = i
        if idx_min < 0:
            break
        used[idx_min] = True

        for neigh in adjacency[idx_min]:
            cost = distance(nodes_coords[idx_min], nodes_coords[neigh])
            new_dist = dist_min + cost
            if new_dist < dist[neigh]:
                dist[neigh] = new_dist
                paths[neigh] = paths[idx_min] + [neigh]

    return paths


#####################################
# Вспомогательные функции
#####################################
def distance(p1, p2):
    """Евклидово расстояние между точками"""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def to_screen(coord):
    """Преобразовать координаты [0..1]x[0..1]"""
    x = int(coord[0] * WIDTH)
    y = int((1.0 - coord[1]) * HEIGHT)
    return x, y


#####################################
# Класс для описания узла
#####################################
class Node:
    def __init__(self, x, y, is_special=False):
        """
        is_special = True для A и B, которые не удаляем.
        """
        self.x = x
        self.y = y
        self.is_special = is_special

        self.is_dying = False

        self.color = DARK_GRAY
        if is_special:
            self.color = DARK_GRAY

    def coord(self):
        return (self.x, self.y)


#####################################
# Класс для управления "стримом"
#####################################
class Streaming:
    def __init__(self, protocol_name, max_number, window_size, timeout, loss_probability):
        self.protocol_name = protocol_name
        self.max_number = max_number
        self.done = False

        # Очереди
        self.send_msg_queue = MsgQueue(loss_probability)
        self.ack_msg_queue = MsgQueue(loss_probability)
        # Логи
        self.posted_msgs = []
        self.received_msgs = []

        # Параметры для протоколов
        self.window_size = window_size
        self.timeout = timeout

        # Состояние для GBN:
        self.gbn_sender_state = {
            "curr_number": 0,
            "last_ans_number": -1,
            "start_time": time.time()
        }
        self.gbn_receiver_state = {
            "expected_number": 0
        }

        # Состояние для SRP:
        self.srp_sender_state = {
            "wnd_nodes": [WndNode(i) for i in range(window_size)],
            "ans_count": 0
        }
        self.srp_receiver_state = {}

    def is_done(self):
        return self.done

    def update(self):
        if self.done:
            return

        if self.protocol_name == 'GBN':
            self._gbn_step()
        else:
            self._srp_step()

    def _gbn_step(self):
        st_s = self.gbn_sender_state
        st_r = self.gbn_receiver_state

        # Если уже получили все пакеты
        if st_s["last_ans_number"] >= self.max_number:
            self.done = True
            return

        if self.send_msg_queue.has_msg():
            msg = self.send_msg_queue.get_message()
            if msg.data == "STOP":
                pass
            elif msg.status == MessageStatus.LOST:
                pass
            else:
                if msg.number == st_r["expected_number"]:
                    ans = Message()
                    ans.number = msg.number
                    self.ack_msg_queue.send_message(ans)
                    self.received_msgs.append(f"{msg.real_number}({msg.number})")
                    st_r["expected_number"] = (st_r["expected_number"] + 1) % self.window_size

        if self.ack_msg_queue.has_msg():
            ans = self.ack_msg_queue.get_message()
            expected_number = (st_s["last_ans_number"] + 1) % self.window_size
            if ans.number == expected_number:
                st_s["last_ans_number"] += 1
                st_s["start_time"] = time.time()
            else:
                st_s["curr_number"] = st_s["last_ans_number"] + 1

        # Таймаут
        if time.time() - st_s["start_time"] > self.timeout:
            st_s["curr_number"] = st_s["last_ans_number"] + 1
            st_s["start_time"] = time.time()

        # Отправить пакет
        if (st_s["curr_number"] < st_s["last_ans_number"] + self.window_size) \
           and (st_s["curr_number"] <= self.max_number):
            k = st_s["curr_number"] % self.window_size
            msg = Message()
            msg.number = k
            msg.real_number = st_s["curr_number"]
            self.send_msg_queue.send_message(msg)
            self.posted_msgs.append(f"{msg.real_number}({msg.number})")
            st_s["curr_number"] += 1

        if st_s["last_ans_number"] >= self.max_number:
            stop_msg = Message()
            stop_msg.data = "STOP"
            self.send_msg_queue.send_message(stop_msg)
            self.done = True

    def _srp_step(self):
        st_s = self.srp_sender_state

        # Приёмник
        if self.send_msg_queue.has_msg():
            msg = self.send_msg_queue.get_message()
            if msg.data == "STOP":
                self.done = True
                return
            if msg.status == MessageStatus.LOST:
                pass
            else:
                ans = Message()
                ans.number = msg.number
                self.ack_msg_queue.send_message(ans)
                self.received_msgs.append(f"{msg.real_number}({msg.number})")

        # Отправитель
        if self.ack_msg_queue.has_msg():
            ans = self.ack_msg_queue.get_message()
            st_s["ans_count"] += 1
            idx = ans.number
            if 0 <= idx < len(st_s["wnd_nodes"]):
                st_s["wnd_nodes"][idx].status = WndMsgStatus.CAN_BE_USED

        if st_s["ans_count"] >= self.max_number:
            stop_msg = Message()
            stop_msg.data = "STOP"
            self.send_msg_queue.send_message(stop_msg)
            self.done = True
            return

        curr_time = time.time()
        for node in st_s["wnd_nodes"]:
            if node.number > self.max_number:
                continue
            if curr_time - node.time > self.timeout:
                node.status = WndMsgStatus.NEED_REPEAT

        for node in st_s["wnd_nodes"]:
            if node.number > self.max_number:
                continue
            if node.status in [WndMsgStatus.NEED_REPEAT, WndMsgStatus.CAN_BE_USED]:
                node.status = WndMsgStatus.BUSY
                node.time = time.time()

                msg = Message()
                msg.number = node.number % len(st_s["wnd_nodes"])
                msg.real_number = node.number
                self.send_msg_queue.send_message(msg)
                self.posted_msgs.append(f"{msg.real_number}({msg.number})")

                if node.number + len(st_s["wnd_nodes"]) <= self.max_number:
                    node.number += len(st_s["wnd_nodes"])
                else:
                    node.number = self.max_number + 1


#####################################
# Основной класс
#####################################
class NetworkSim:
    def __init__(self, config, protocol='GBN'):
        self.config = config
        self.protocol = protocol

        # Создаём узлы: A(0,0), B(1,1), + routers_number случайных
        self.nodes = []
        # A
        nodeA = Node(0.0, 0.0, is_special=True)
        self.nodes.append(nodeA)
        # B
        nodeB = Node(1.0, 1.0, is_special=True)
        self.nodes.append(nodeB)

        for _ in range(self.config["routers_number"]):
            x = random.random()
            y = random.random()
            self.nodes.append(Node(x, y, is_special=False))


        self.nodes[0].color = RED
        self.nodes[1].color = PURPLE


        self.stream = None

        self.frame_count = 0

    def step(self):
        self.frame_count += 1


        if self.frame_count % self.config["topology_update_interval"] == 0:
            self._remove_and_add_nodes()

        adjacency = self._build_adjacency()

        coords = [nd.coord() for nd in self.nodes]
        paths = dijkstra(coords, adjacency, 0)
        path = paths[1]

        if len(path) < 2:
            if self.stream:
                self.stream.update()
                got = len(self.stream.received_msgs)
                max_num = self.config["package"]
                progress = got / float(max_num) if max_num else 0.0
            else:
                self.stream = Streaming(
                    protocol_name=self.protocol,
                    max_number=self.config["package"],
                    window_size=self.config["window_size"],
                    timeout=self.config["timeout"],
                    loss_probability=self.config["loss_probability"]
                )
                progress = 0.0

            return adjacency, [], progress
        else:
            if (not self.stream) or self.stream.is_done():
                self.stream = Streaming(
                    protocol_name=self.protocol,
                    max_number=self.config["package"],
                    window_size=self.config["window_size"],
                    timeout=self.config["timeout"],
                    loss_probability=self.config["loss_probability"]
                )
            else:
                pass

            self.stream.update()
            got = len(self.stream.received_msgs)
            max_num = self.config["package"]
            progress = got / float(max_num) if max_num else 0.0

            return adjacency, path, progress

    def _remove_and_add_nodes(self):
        """
        Удаляем узлы (кроме A,B) с вероятностью prob_remove.
        Помеченные на удаление пропадают окончательно в следующем цикле,
        а потом добавляем новые, чтобы общее число промежуточных узлов 
        оставалось постоянным.
        """
        alive = []

        for nd in self.nodes:
            if nd.is_special:
                alive.append(nd)
            else:
                # Если узел уже "is_dying", он пропускается => фактически удаляется
                if not nd.is_dying:
                    alive.append(nd)
        self.nodes = alive

        # Помечаем некоторых узлов на удаление (красим в красный)
        current_routers = self.nodes[2:]  # пропускаем A,B
        for nd in current_routers:
            if random.random() < self.config["prob_remove"]:
                nd.is_dying = True
                nd.color = RED

        # Добавляем недостающие
        normal_count = len([n for n in self.nodes[2:] if not n.is_dying])
        diff = self.config["routers_number"] - normal_count
        for _ in range(diff):
            x = random.random()
            y = random.random()
            new_node = Node(x, y)
            self.nodes.append(new_node)

    def _build_adjacency(self):
        adjacency = []
        coords = [nd.coord() for nd in self.nodes]
        n = len(coords)
        for i in range(n):
            adjacency.append(set())
        dist_thr = self.config["distance"]

        for i in range(n):
            for j in range(i+1, n):
                if distance(coords[i], coords[j]) <= dist_thr:
                    adjacency[i].add(j)
                    adjacency[j].add(i)
        return adjacency


#####################################
# Функции отрисовки
#####################################
def draw_network(screen, net, adjacency, path, progress):
    screen.fill(WHITE)

    coords = [nd.coord() for nd in net.nodes]

    path_set = set(path)
    for i, nd in enumerate(net.nodes):
        if i == 0:
            nd.color = RED
        elif i == 1:
            nd.color = PURPLE
        else:
            if i in path_set:
                nd.color = BLUE
            else:
                nd.color = DARK_GRAY
        if nd.is_dying:
            nd.color = RED

    for i in range(len(adjacency)):
        for j in adjacency[i]:
            if j < i:
                continue
            c1 = coords[i]
            c2 = coords[j]
            pygame.draw.line(screen, BLACK, to_screen(c1), to_screen(c2), 1)

    if len(path) >= 2:
        dists = []
        total_dist = 0.0
        for idx in range(len(path) - 1):
            d = distance(coords[path[idx]], coords[path[idx+1]])
            dists.append(d)
            total_dist += d

        green_dist = total_dist * progress
        cur_dist = 0.0

        for idx in range(len(path) - 1):
            c1 = coords[path[idx]]
            c2 = coords[path[idx + 1]]
            seg_len = dists[idx]

            if cur_dist >= green_dist:
                pygame.draw.line(screen, BLUE, to_screen(c1), to_screen(c2), 4)
            elif cur_dist + seg_len <= green_dist:
                pygame.draw.line(screen, GREEN, to_screen(c1), to_screen(c2), 5)
            else:
                alpha = (green_dist - cur_dist) / seg_len
                mx = c1[0] + alpha*(c2[0] - c1[0])
                my = c1[1] + alpha*(c2[1] - c1[1])
                mid_point = (mx, my)
                pygame.draw.line(screen, GREEN, to_screen(c1), to_screen(mid_point), 5)
                pygame.draw.line(screen, BLUE, to_screen(mid_point), to_screen(c2), 4)

            cur_dist += seg_len

    for nd in net.nodes:
        r = 6
        if nd.is_dying:
            r = 10
        pygame.draw.circle(screen, nd.color, to_screen(nd.coord()), r)


def draw_protocol_label(screen, net):
    font = pygame.font.SysFont(None, 24)
    text = font.render(f"Protocol: {net.protocol}", True, BLACK)
    screen.blit(text, (10, 10))


#####################################
# Основная функция с циклом Pygame
#####################################
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    done = False

    protocol_choice = 'GBN'
    net = NetworkSim(CONFIG, protocol=protocol_choice)

    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    protocol_choice = 'GBN'
                    net = NetworkSim(CONFIG, protocol=protocol_choice)
                elif event.key == pygame.K_s:
                    protocol_choice = 'SRP'
                    net = NetworkSim(CONFIG, protocol=protocol_choice)

        adjacency, path, progress = net.step()

        draw_network(screen, net, adjacency, path, progress)
        draw_protocol_label(screen, net)

        pygame.display.flip()
        clock.tick(CONFIG["fps"])

    pygame.quit()

if __name__ == '__main__':
    main()