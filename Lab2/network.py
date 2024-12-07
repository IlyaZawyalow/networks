from __future__ import annotations
from enum import Enum
from typing import List
from math import inf


class Topology(Enum):
    kLine = 0
    kRing = 1
    kStar = 2


class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def dist(self, other: Point) -> float:
        return ((self.x - other.x)**2 + (self.y - other.y)**2)**0.5


def print_paths(start_node: int, paths: List[List[int]], file=None):
    for dest, path in enumerate(paths):
        if path:
            line = f"path {start_node} -> {dest}: {path}"
            (file.write(line + "\n") if file else print(line))


class Network:
    @staticmethod
    def create_network(topology: Topology) -> Network:
        if topology == Topology.kStar:
            nodes = [Point(0, 0)] + [
                Point(x, y)
                for x, y in [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
            ]
            network = Network(nodes, connection_radius=0.0)
            center_connections = [i for i in range(1, len(nodes))]
            network.nodes_graph = [[*center_connections]] + [[0] for _ in center_connections]
            return network
        raise ValueError("Unsupported topology")

    def __init__(self, nodes: List[Point], connection_radius: float):
        self.nodes = nodes
        self.connection_radius = connection_radius
        self.nodes_graph: List[List[int]] = []

    def build_graph(self):
        if self.nodes_graph:
            return
        self.nodes_graph = [
            [j for j, neighbor in enumerate(self.nodes) if i != j and node.dist(neighbor) < self.connection_radius]
            for i, node in enumerate(self.nodes)
        ]

    def remove_node(self, idx: int):
        self.nodes[idx] = Point(inf, inf)
        self.build_graph()

    def ospf(self, title: str):
        with open(f"path/{title}.txt", "w") as file:
            for start_node in range(len(self.nodes)):
                file.write(f"Start node {start_node}:\n")
                paths = self.dijkstra(start_node)
                print_paths(start_node, paths, file)
                file.write("-" * 40 + "\n")

    def dijkstra(self, start: int) -> List[List[int]]:
        distances = [inf] * len(self.nodes)
        distances[start] = 0
        used = [False] * len(self.nodes)
        paths = [[] for _ in self.nodes]

        class Node:
            def __init__(self, idx, dist):
                self.idx = idx
                self.dist = dist

        heap = [Node(start, 0)]
        while heap:
            heap.sort(key=lambda n: n.dist)
            current = heap.pop(0)
            if used[current.idx]:
                continue
            used[current.idx] = True

            for neighbor in self.nodes_graph[current.idx]:
                new_dist = distances[current.idx] + self.nodes[current.idx].dist(self.nodes[neighbor])
                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    paths[neighbor] = paths[current.idx] + [current.idx]
                    heap.append(Node(neighbor, new_dist))

        for i, path in enumerate(paths):
            if distances[i] < inf:
                path.append(i)
        return paths
