from typing import List
from network import Network, Point, Topology
from plotter import Plotter
from math import cos, sin, pi

def generate_ring_points(radius: float, num_points: int = 10) -> List[Point]:

    points = [
        Point(radius * cos(2 * pi * i / num_points), radius * sin(2 * pi * i / num_points))
        for i in range(num_points)
    ]
    return points


def process_network(network: Network, plt: Plotter, title_prefix: str):
    # Build and plot full network
    network.build_graph()
    plt.plot_points(network.nodes, title=f"{title_prefix}_points")
    plt.plot_network_graph(network, title=f"{title_prefix}_graph")
    network.ospf(title=f"{title_prefix}_ospf")

    # Modify network and plot updated state
    network.remove_node(3)
    plt.plot_network_graph(network, title=f"{title_prefix}_modified")
    network.ospf(title=f"{title_prefix}_modified_ospf")


def main():
    plt = Plotter()

    # Line topology
    line_network = Network(
        nodes=[Point(x, x) for x in range(1, 11)],
        connection_radius=1.5,
    )
    process_network(line_network, plt, title_prefix="line")

    # Ring topology
    ring_network = Network(
        nodes=generate_ring_points(radius=3.0),
        connection_radius=3.0,
    )
    process_network(ring_network, plt, title_prefix="ring")

    # Star topology
    star_network = Network.create_network(Topology.kStar)
    process_network(star_network, plt, title_prefix="star")


if __name__ == "__main__":
    main()
