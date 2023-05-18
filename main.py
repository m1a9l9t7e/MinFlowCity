import time
import os
import osmnx as ox
import networkx as nx
import random
from manim import *

DOWNLOAD_PATH = './osm_cache'


class MinFlowCity(MovingCameraScene):
    def construct(self):
        # Get graph
        nodes, edges = generate_city_graph()

        # Calculate Solution
        start = time.time()
        state = self.solve(nodes, edges, False)
        end = time.time()
        print(f'Solution found in {end - start:.2f}s')

        # Draw Solution
        print('Drawing Solution...')
        self.adjust_camera_settings(nodes)
        self.draw_graph(nodes, edges, state, scale=0.5)

    def solve(self, nodes, edges, equal_weights=True):
        # Create directed graph
        graph = nx.DiGraph()

        # Add nodes
        num_consumers = 0
        for index, node in nodes.items():
            if node['type'] == 'consumer':
                graph.add_node(index, demand=1)
                num_consumers += 1
            else:
                graph.add_node(index, demand=0)

        graph.add_node('super-supplier', demand=-num_consumers)

        # Add edges
        node_to_position = {index: np.array(node['pos']) for index, node in nodes.items()}
        for u, v in edges:
            distance = 1 if equal_weights else int(np.linalg.norm(node_to_position[u] - node_to_position[v]))
            graph.add_edge(u, v, weight=distance, capacity=num_consumers)
            graph.add_edge(v, u, weight=distance, capacity=num_consumers)

        # Connect super-supplier to the rest of the graph
        for index, node in nodes.items():
            if node['type'] == 'supplier':
                graph.add_edge('super-supplier', index, weight=0, capacity=num_consumers)

        # Compute minimum cost flow
        return nx.min_cost_flow(graph)

    def draw_graph(self, nodes, edges, mapping=None, scale=1.0):
        node_color_map = {
            "supplier": BLUE_C,
            "consumer": GREEN_C,
            "neutral": GRAY,
        }

        node_radius_map = {
            "supplier": 0.6 * scale,
            "consumer": 0.3 * scale,
            "neutral": 0.1 * scale,
        }

        # Draw edges
        for u, v in edges:
            start_node, end_node = nodes[u], nodes[v]
            sx, sy = start_node["pos"]
            ex, ey = end_node["pos"]
            # if edge is part of solution
            if mapping[u][v] > 0 or mapping[v][u] > 0:
                line = Line((sx, sy, 0), (ex, ey, 0), color=GREEN_C, stroke_width=8 * scale)
            else:
                line = Line((sx, sy, 0), (ex, ey, 0), color=GRAY, stroke_width=3 * scale)
            self.add(line)

        # Draw nodes
        for node in nodes.values():
            node_type = node["type"]
            circle = Circle(radius=node_radius_map[node_type], color=node_color_map[node_type], fill_opacity=1)
            x, y = node["pos"]
            circle.shift(np.array([x, y, 0]))
            self.add(circle)

    def adjust_camera_settings(self, nodes):
        positions = [node['pos'] for index, node in nodes.items()]
        # calculate dimensions
        min_x, min_y = np.amin(np.array(list(positions)), axis=0)
        max_x, max_y = np.amax(np.array(list(positions)), axis=0)
        width = max_x - min_x
        height = max_y - min_y
        # move camera
        camera_size = [width, height]
        camera_position = np.array(camera_size) / 2 + np.array([min_x, min_y])
        print("size: {}, camera_pos: {}".format(camera_size, camera_position))
        self.move_camera(camera_size, camera_position, duration=1, border_scale=1.1, shift=[0, 0])

    def move_camera(self, camera_size, camera_position, duration=1, border_scale=1.1, shift=[0.0, 0.0], resolution=[16, 9]):
        camera_position = [camera_position[0] + shift[0], camera_position[1] + shift[1]]
        self.play(
            self.camera.frame.animate.move_to((camera_position[0], camera_position[1], 0)),
            run_time=duration / 2
        )
        if camera_size[0] / resolution[0] > camera_size[1] / resolution[1]:
            self.play(
                self.camera.frame.animate.set_width(camera_size[0] * border_scale),
                run_time=duration / 2
            )
        else:
            self.play(
                self.camera.frame.animate.set_height(camera_size[1] * border_scale),
                run_time=duration / 2
            )


def generate_city_graph(point=(52.5200, 13.4050), distance=4000, num_supplier=15, num_consumer=400):
    # Load raw osm graph
    graph = load_osm_graph(point, distance)
    nodes, edges = ox.graph_to_gdfs(graph)
    print(f'Graph loaded: {len(nodes)} nodes, {len(edges)} edges')

    # assign types to nodes
    node_types = ["supplier"] * num_supplier + ["consumer"] * num_consumer + ["neutral"] * (len(nodes) - num_supplier - num_consumer)
    random.shuffle(node_types)
    nodes_formatted = dict()
    for i, (index, node) in enumerate(nodes.iterrows()):
        nodes_formatted[index] = {
            "pos": (node['x'] * 500, node['y'] * 500),
            "type": node_types[i]
        }

    # only keep unique edges
    unique_edges = set()
    for index, edge in edges.iterrows():
        unique_edges.add(index[:2])

    return nodes_formatted, list(unique_edges)


def load_osm_graph(point, distance):
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    # Check if the data is already cached locally
    path = os.path.join(DOWNLOAD_PATH, f'{point}_{distance}.graphml')
    if os.path.exists(path):
        # Load the graph from a cached file
        graph = ox.load_graphml(path)
    else:
        # Retrieve the OSM street network data for the place
        graph = ox.graph_from_point(point, dist=distance, network_type="drive")
        ox.save_graphml(graph, path)
    return graph


if __name__ == '__main__':
    scene = MinFlowCity()
    scene.render()
