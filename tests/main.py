import os
import unittest
import taxicab as tc
import osmnx as ox


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
NETWORK_PATH = os.path.join(THIS_DIR, 'data/test_graph.osm')

# load graph
G = ox.load_graphml(NETWORK_PATH)


class test_main(unittest.TestCase):
    def test_same_edge(self):
        orig = (39.0884, -84.3232)
        dest = (39.08843038088047, -84.32261113356783)
        route = tc.distance.shortest_path(G, orig, dest)
        self.assertEqual(route[0], 108.98249858377586)

    def test_short_route(self):
        orig = (39.08734, -84.32400)
        dest = (39.08840, -84.32307)
        route = tc.distance.shortest_path(G, orig, dest)
        self.assertEqual(route[0], 25.752097710314846)

    def test_far_away_nodes(self):
        orig = (39.08710, -84.31050)
        dest = (39.08800, -84.32000)
        route = tc.distance.shortest_path(G, orig, dest)
        self.assertEqual(route[0], 669.0529395595279)

if __name__ == '__main__':
    unittest.main()
