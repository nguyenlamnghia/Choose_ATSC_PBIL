import json
import networkx as nx
import sumolib
from xml.etree import ElementTree as ET

# def sumo_net_to_nx_graph():
#     """Minimal extractor scaffold: creates an empty directed graph.
#     In practice, use sumolib to parse edges/nodes and attach TLS metadata.
#     """
#     G = nx.DiGraph()
#     # placeholder: a single node
#     G.add_node("dummy")
#     data = nx.readwrite.json_graph.node_link_data(G)
#     with open(out_json, "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=2)
#     return out_json

def sumo_net_to_nx_graph(net_file: str, out_json: str):
    net = sumolib.net.readNet(net_file)
    G = nx.DiGraph()  # Đồ thị có hướng (directed)

    for edge in net.getEdges():
        edge_id = edge.getID()
        from_node = edge.getFromNode().getID()
        to_node = edge.getToNode().getID()
        length = edge.getLength()
        lanes = [lane.getID() for lane in edge.getLanes()]

    # Thêm cạnh vào đồ thị với các thuộc tính
        G.add_edge(from_node, to_node,
                   id=edge_id,
                   length=length,
                   lanes=lanes)

    # Add traffic lights (TLS) to the graph
    tree = ET.parse(net_file)
    root = tree.getroot()
    
    for tls in root.findall("tlLogic"):
        tls_id = tls.attrib.get("id")
        phases = []
        phase_durations = []

        for i, phase in enumerate(tls.findall("phase")):
            duration = phase.attrib.get("duration")
            state = phase.attrib.get("state")
            phase_durations.append(float(duration))
            phases.append(state)
            
            # print(f"  Phase {i+1}: duration = {duration}, state = {state}")
        
        # Add connection information
        connections = []
        for conn in root.findall("connection"):
            if conn.attrib.get("tl") == tls_id:
                link_index = int(conn.attrib.get("linkIndex"))
                from_edge = conn.attrib.get("from")
                to_edge = conn.attrib.get("to")
                from_lane = conn.attrib.get("fromLane")
                to_lane = conn.attrib.get("toLane")
                turn_ratio = conn.attrib.get("turnRatio", "0.2")  # Default to 0.2 if not specified
                connections.append({
                    "link_index": link_index,
                    "from_edge": from_edge,
                    "to_edge": to_edge,
                    "from_lane": from_lane,
                    "to_lane": to_lane,
                    "turn_ratio": float(turn_ratio)
                })
        # sort connections by link_index
        connections.sort(key=lambda x: x["link_index"])

        # Add turn ratio information
        # Change this part if you have turn ratios in your XML

        G.add_node(tls_id, phases=phases, phase_durations=phase_durations, connections=connections)

    # Convert to JSON format
    data = nx.readwrite.json_graph.node_link_data(G)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Graph saved to {out_json}")

    return G
