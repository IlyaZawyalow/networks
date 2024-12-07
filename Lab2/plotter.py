from typing import List
from matplotlib import pyplot as plt
from network import Point, Network


def save_path() -> str:
    return "img/"


class Plotter:
    def plot_points(self, points: List[Point], title: str = "", show: bool = True):
        xs, ys = [p.x for p in points], [p.y for p in points]
        plt.plot(xs, ys, "o")
        for idx, point in enumerate(points):
            plt.text(point.x, point.y + 0.05, f"{idx}")
        if show:
            plt.grid()
            plt.savefig(f"{save_path()}{title}.png", dpi=200)
            plt.clf()

    def plot_network_graph(self, network: Network, title: str = ""):
        for idx, neighbors in enumerate(network.nodes_graph):
            for neighbor_idx in neighbors:
                plt.plot(
                    [network.nodes[idx].x, network.nodes[neighbor_idx].x],
                    [network.nodes[idx].y, network.nodes[neighbor_idx].y],
                    "r-",
                )
        self.plot_points(network.nodes, title, show=False)
        plt.grid()
        plt.savefig(f"{save_path()}{title}.png", dpi=200)
        plt.clf()
