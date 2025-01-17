from networkx import shortest_path as nx_shortest_path
from osmnx.distance import great_circle_vec
from osmnx.distance import nearest_edges
from osmnx.utils_graph import get_route_edge_attributes
from shapely.geometry import LineString
from shapely.geometry import Point
from shapely.ops import substring


def compute_linestring_length(ls):
    '''
    Computes the length of a partial edge (shapely linesting)
    
    Parameters
    ----------
    ls : shapely.geometry.linestring.LineString

    Returns
    -------
    float : partial edge length distance in meters
    '''

    if type(ls) == LineString:
        x, y = zip(*ls.coords)

        dist = 0
        for i in range(0, len(x) - 1):
            dist += great_circle_vec(y[i], x[i], y[i + 1], x[i + 1])
        return dist
    else:
        return None


def compute_taxi_length(G, nx_route, orig_partial_edge, dest_partial_edge, weight='length', orig_edge_route=[],
                        dest_edge_route=[]):
    '''
    Computes the route complete taxi route length
    '''

    dist = 0
    if nx_route:
        dist += sum(get_route_edge_attributes(G, nx_route, weight))
    if orig_partial_edge:
        print(nx_route)
        if weight == 'length':
            dist += compute_linestring_length(orig_partial_edge)
        else:
            if len(nx_route) > 1:
                dist += get_linestring_weight(G, compute_linestring_length(orig_partial_edge),
                                              [nx_route[0], nx_route[1]], weight)
            else:
                dist += get_linestring_weight(G, compute_linestring_length(orig_partial_edge),
                                              orig_edge_route, weight)
    if dest_partial_edge:
        print(nx_route)
        if weight == 'length':
            dist += compute_linestring_length(dest_partial_edge)
        else:
            if len(nx_route) > 1:
                dist += get_linestring_weight(G, compute_linestring_length(dest_partial_edge),
                                              [nx_route[-1], nx_route[-2]], weight)
            else:
                dist += get_linestring_weight(G, compute_linestring_length(orig_partial_edge),
                                              dest_edge_route, weight)
    return dist


def get_linestring_weight(G, linestring_length, edge_ids, weight):
    '''
    Gets the weight of a fraction of an edge (linestring), by its ration to the edge length
    :param G: networkx.MultiDiGraph
        input graph
    :param linestring_length: float
        length of linestring
    :param edge_ids:
        node ids of the edge
    :param weight:
        weight that should be applied
    :return:
        calculated weight for this linestring
    '''
    weight = get_route_edge_attributes(G, edge_ids, weight)[0]
    edge_length = get_route_edge_attributes(G, edge_ids, 'length')[0]
    return (weight / edge_length) * linestring_length


def get_edge_geometry(G, edge):
    '''
    Retrieve the points that make up a given edge.
    
    Parameters
    ----------
    G : networkx.MultiDiGraph
        input graph
    edge : tuple
        graph edge unique identifier as a tuple: (u, v, key)
    
    Returns
    -------
    list :
        ordered list of (lng, lat) points.
    
    Notes
    -----
    In the event that the 'geometry' key does not exist within the
    OSM graph for the edge in question, it is assumed then that 
    the current edge is just a straight line. This results in an
    automatic assignment of edge end points.
    '''

    if G.edges.get(edge, 0):
        if G.edges[edge].get('geometry', 0):
            return G.edges[edge]['geometry']

    if G.edges.get((edge[1], edge[0], 0), 0):
        if G.edges[(edge[1], edge[0], 0)].get('geometry', 0):
            return G.edges[(edge[1], edge[0], 0)]['geometry']

    return LineString([
        (G.nodes[edge[0]]['x'], G.nodes[edge[0]]['y']),
        (G.nodes[edge[1]]['x'], G.nodes[edge[1]]['y'])])


def shortest_path(G, orig_yx, dest_yx, orig_edge=None, dest_edge=None, weight="length"):
    '''
    Parameters
    ----------
    G : networkx.MultiDiGraph
        input graph
    orig_yx : tuple
        the (lat, lng) or (y, x) point representing the origin of the path
    dest_yx : tuple
        the (lat, lng) or (y, x) point representing the destination of the path
    weight : str
        Name of col in edge that should be used for routing
    
    Returns
    -------
    tuple
        (route_dist, route, orig_edge_p, dest_edge_p, route_weight)
    '''

    # determine nearest edges
    if not orig_edge: orig_edge = nearest_edges(G, orig_yx[1], orig_yx[0])
    if not dest_edge: dest_edge = nearest_edges(G, dest_yx[1], dest_yx[0])

    # routing along same edge
    if orig_edge == dest_edge:
        p_o, p_d = Point(orig_yx[::-1]), Point(dest_yx[::-1])
        edge_geo = G.edges[orig_edge]['geometry']
        orig_clip = edge_geo.project(p_o, normalized=True)
        dest_clip = edge_geo.project(p_d, normalized=True)
        orig_partial_edge = substring(edge_geo, orig_clip, dest_clip, normalized=True)
        dest_partial_edge = []
        nx_route = []

    # routing across multiple edges
    else:
        nx_route = nx_shortest_path(G, orig_edge[0], dest_edge[0], weight)
        p_o, p_d = Point(orig_yx[::-1]), Point(dest_yx[::-1])
        orig_geo = get_edge_geometry(G, orig_edge)
        dest_geo = get_edge_geometry(G, dest_edge)

        orig_clip = orig_geo.project(p_o, normalized=True)
        dest_clip = dest_geo.project(p_d, normalized=True)

        orig_partial_edge_1 = substring(orig_geo, orig_clip, 1, normalized=True)
        orig_partial_edge_2 = substring(orig_geo, 0, orig_clip, normalized=True)
        dest_partial_edge_1 = substring(dest_geo, dest_clip, 1, normalized=True)
        dest_partial_edge_2 = substring(dest_geo, 0, dest_clip, normalized=True)

        # when the nx route is just a single node, this is a bit of an edge case
        if len(nx_route) <= 2:
            nx_route = []
            if orig_partial_edge_1.intersects(dest_partial_edge_1):
                orig_partial_edge = orig_partial_edge_1
                dest_partial_edge = dest_partial_edge_1

            if orig_partial_edge_1.intersects(dest_partial_edge_2):
                orig_partial_edge = orig_partial_edge_1
                dest_partial_edge = dest_partial_edge_2

            if orig_partial_edge_2.intersects(dest_partial_edge_1):
                orig_partial_edge = orig_partial_edge_2
                dest_partial_edge = dest_partial_edge_1

            if orig_partial_edge_2.intersects(dest_partial_edge_2):
                orig_partial_edge = orig_partial_edge_2
                dest_partial_edge = dest_partial_edge_2

        # when routing across two or more edges
        if len(nx_route) >= 3:

            ### resolve origin

            # check overlap with first route edge
            route_orig_edge = get_edge_geometry(G, (nx_route[0], nx_route[1], 0))
            if route_orig_edge.intersects(orig_partial_edge_1) and route_orig_edge.intersects(orig_partial_edge_2):
                nx_route = nx_route[1:]

            # determine which origin partial edge to use
            route_orig_edge = get_edge_geometry(G, (nx_route[0], nx_route[1], 0))
            if route_orig_edge.intersects(orig_partial_edge_1):
                orig_partial_edge = orig_partial_edge_1
            else:
                orig_partial_edge = orig_partial_edge_2

            ### resolve destination

            # check overlap with last route edge
            print(nx_route)
            route_dest_edge = get_edge_geometry(G, (nx_route[-2], nx_route[-1], 0))
            if route_dest_edge.intersects(dest_partial_edge_1) and route_dest_edge.intersects(dest_partial_edge_2):
                nx_route = nx_route[:-1]

            # determine which destination partial edge to use
            if len(nx_route) > 1:
                route_dest_edge = get_edge_geometry(G, (nx_route[-2], nx_route[-1], 0))
                if route_dest_edge.intersects(dest_partial_edge_1):
                    dest_partial_edge = dest_partial_edge_1
                else:
                    dest_partial_edge = dest_partial_edge_2
            else:
                if orig_partial_edge.intersects(dest_partial_edge_1):
                    dest_partial_edge = dest_partial_edge_1
                else:
                    dest_partial_edge = dest_partial_edge_2

    # final check
    if orig_partial_edge:
        if len(orig_partial_edge.coords) <= 1:
            orig_partial_edge = []
    if dest_partial_edge:
        if len(dest_partial_edge.coords) <= 1:
            dest_partial_edge = []

    # compute total path length
    route_dist = compute_taxi_length(G, nx_route, orig_partial_edge, dest_partial_edge)

    # compute total custom weight sum
    if weight == 'length':
        route_weight = route_dist
    else:
        if len(nx_route) > 1:
            route_weight = compute_taxi_length(G, nx_route, orig_partial_edge, dest_partial_edge, weight)
        else:
            route_weight = compute_taxi_length(G, nx_route, orig_partial_edge, dest_partial_edge, weight,
                                               orig_edge_route=[orig_edge[0], orig_edge[1]], dest_edge_route=[dest_edge[0], dest_edge[1]])

    return route_dist, nx_route, orig_partial_edge, dest_partial_edge, route_weight
