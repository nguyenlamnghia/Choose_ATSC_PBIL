#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tạo file net-information.json từ SUMO net (.net.xml) và detectors (.add.xml)
- Bám theo cấu trúc net-infomation-example.json (tls → cycle/controller/edges/movements/phases)
- Không phụ thuộc sumolib; chỉ dùng thư viện chuẩn.
"""

import argparse
import json
import xml.etree.ElementTree as ET
from collections import defaultdict, OrderedDict

MIN_GREEN_DEFAULT = 15
MAX_GREEN_DEFAULT = 120
DEFAULT_SAT_FLOW = 1800.0
DEFAULT_SPEED = 13.89  # m/s, ~50 km/h nếu không thấy speed

def parse_edges_from_net(root):
    """
    Trích xuất thuộc tính edge (length, speed) từ .net.xml
    Trả về: dict[edge_id] = {"length": float, "speed": float}
    """
    edge_attr = {}
    for edge in root.findall("edge"):
        edge_id = edge.attrib.get("id")
        # Bỏ qua internal edges dạng id bắt đầu ":"
        if not edge_id or edge_id.startswith(":"):
            continue

        # Lấy lane đầu tiên (thường các lane cùng length/speed)
        lanes = edge.findall("lane")
        if lanes:
            # Dùng lane đầu tiên
            ln = lanes[0]
            length = float(ln.attrib.get("length", "0.0"))
            speed = float(ln.attrib.get("speed", str(DEFAULT_SPEED)))
        else:
            # Phòng hờ nếu không có lane con
            length = 0.0
            speed = DEFAULT_SPEED

        edge_attr[edge_id] = {"length": length, "speed": speed}
    return edge_attr


def parse_tl_connections_and_phases(root):
    """
    Lấy connections và phases cho từng TLS.
    Trả về:
      tls_dict[tls_id] = {
         "connections": [ {link_index, from_edge, to_edge, turn_ratio (optional)} ... ] (đã sort theo link_index)
         "phases": [ {"index": i, "duration": dur, "state": s} ... ] (theo thứ tự trong file)
         "cycle": tổng thời lượng tất cả phase (bao gồm cả yellow/all-red)
      }
    """
    # Gom connections theo tls_id trước
    tls_conns = defaultdict(list)
    for conn in root.findall("connection"):
        tl = conn.attrib.get("tl")
        if not tl:
            continue
        rec = {
            "link_index": int(conn.attrib.get("linkIndex", "-1")),
            "from_edge": conn.attrib.get("from"),
            "to_edge": conn.attrib.get("to"),
        }
        # SUMO có thể không có turnRatio — nếu có thì dùng
        if "turnRatio" in conn.attrib:
            try:
                rec["turn_ratio"] = float(conn.attrib["turnRatio"])
            except Exception:
                pass
        tls_conns[tl].append(rec)

    # Sort theo link_index
    for tlid, lst in tls_conns.items():
        lst.sort(key=lambda x: x["link_index"])

    tls_info = {}
    for tl in root.findall("tlLogic"):
        tls_id = tl.attrib.get("id")
        if not tls_id:
            continue

        phases = []
        cycle = 0.0
        for i, ph in enumerate(tl.findall("phase")):
            dur = float(ph.attrib.get("duration", "0"))
            state = ph.attrib.get("state", "")
            cycle += dur
            phases.append({"index": i, "duration": dur, "state": state})

        tls_info[tls_id] = {
            "connections": tls_conns.get(tls_id, []),
            "phases": phases,
            "cycle": cycle
        }
    return tls_info


def parse_detectors(detector_file):
    """
    Trả về dict: edge_id -> [danh sách id detector] từ file .add.xml
    (map bằng cách lấy phần trước dấu '_' trong thuộc tính lane)
    """
    det_map = defaultdict(list)
    if detector_file is None:
        return det_map

    tree = ET.parse(detector_file)
    root = tree.getroot()

    for e in root.findall(".//laneAreaDetector"):
        det_id = e.attrib.get("id")
        lane = e.attrib.get("lane", "")
        # lane dạng "EDGE_0" hoặc "-3_0" → tách edge_id
        edge_id = lane.split("_")[0] if "_" in lane else lane
        if det_id and edge_id:
            det_map[edge_id].append(det_id)

    return det_map


def build_movements(connections):
    """
    Xây 'movements' theo mẫu: from_edge -> {to_edge: ratio}
    - Nếu connections có 'turn_ratio' cho from_edge thì chuẩn hoá theo tổng.
    - Nếu không, chia đều.
    """
    # Gom theo from_edge
    by_from = defaultdict(list)
    for c in connections:
        by_from[c["from_edge"]].append(c)

    movements = OrderedDict()
    for from_e, lst in sorted(by_from.items()):
        # Ưu tiên turn_ratio nếu có
        ratios = []
        has_ratio = any("turn_ratio" in d for d in lst)
        if has_ratio:
            s = sum(d.get("turn_ratio", 0.0) for d in lst)
            for d in lst:
                val = d.get("turn_ratio", 0.0)
                ratios.append(val / s if s > 0 else 0.0)
        else:
            # Chia đều
            n = len(lst)
            ratios = [1.0 / n] * n if n else []

        movements[from_e] = OrderedDict()
        for d, r in zip(lst, ratios):
            movements[from_e][d["to_edge"]] = round(r, 6)  # giữ gọn số
    return movements


def green_movements_per_phase(connections, phases):
    """
    Trả về map {phase_index_str: {"movements": [[from,to],...], "duration": dur, "min-green":..., "max-green":...}}
    - Chỉ lấy các phase có 'G' hoặc 'g' ở bất kỳ link nào (bỏ yellow/all-red).
    - Ánh xạ ký tự state theo link_index → (from_edge, to_edge)
    """
    # Vect kết nối theo link_index để tra nhanh
    idx_to_conn = {c["link_index"]: c for c in connections}

    result = OrderedDict()
    for ph in phases:
        idx = ph["index"]
        state = ph["state"]
        dur = ph["duration"]

        # Chỉ lấy các phase có duration >= 15
        if dur < 15:
            continue

        # Lấy các link có G/g
        movs = []
        for i, ch in enumerate(state):
            if ch in ("G", "g"):
                conn = idx_to_conn.get(i)
                if conn:
                    movs.append([conn["from_edge"], conn["to_edge"]])
        
        result[str(idx)] = {
            "movements": movs,
            "duration": int(dur) if float(dur).is_integer() else float(dur),
            "min-green": MIN_GREEN_DEFAULT,
            "max-green": MAX_GREEN_DEFAULT,
        }
    return result


def build_edges_block(connections, edge_attr_map, det_map):
    """
    Xây khối 'edges' cho một TLS theo mẫu:
      edge_id: {sat_flow, length, speed, detector: [ids]}
    - Bao gồm tất cả from/to edges xuất hiện trong connections của TLS.
    """
    all_edges = set()
    for c in connections:
        if c.get("from_edge"):
            all_edges.add(c["from_edge"])
        if c.get("to_edge"):
            all_edges.add(c["to_edge"])

    edges_block = OrderedDict()
    for eid in sorted(all_edges, key=lambda x: (x.startswith("-") is False, x)):
        info = edge_attr_map.get(eid, {})
        length = float(info.get("length", 0.0))
        speed = float(info.get("speed", DEFAULT_SPEED))
        detectors = det_map.get(eid, [])
        edges_block[eid] = {
            "sat_flow": int(DEFAULT_SAT_FLOW),
            "length": round(length, 2),
            "speed": round(speed, 2),
            "detector": detectors
        }
    return edges_block


def build_tls_json(net_file, detector_file, controller="max_pressure"):
    """
    Lắp đầy cấu trúc JSON đầu ra theo đúng mẫu.
    """
    tree = ET.parse(net_file)
    root = tree.getroot()

    edge_attr_map = parse_edges_from_net(root)
    tls_raw = parse_tl_connections_and_phases(root)
    det_map = parse_detectors(detector_file)

    out = OrderedDict()
    out["tls"] = OrderedDict()

    for tls_id in sorted(tls_raw.keys(), key=lambda x: (len(x), x)):
        data = tls_raw[tls_id]
        conns = data["connections"]
        phases = data["phases"]

        # 1) edges
        edges_block = build_edges_block(conns, edge_attr_map, det_map)

        # 2) movements (tỉ lệ rẽ)
        movements = build_movements(conns)

        # 3) phases (chỉ lấy phase có xanh)
        phases_block = green_movements_per_phase(conns, phases)

        # 4) cycle: tổng tất cả phase (kể cả vàng/đỏ toàn nút)
        cycle = int(data["cycle"]) if float(data["cycle"]).is_integer() else float(data["cycle"])

        out["tls"][tls_id] = OrderedDict([
            ("cycle", cycle),
            ("controller", controller),
            ("edges", edges_block),
            ("movements", movements),
            ("phases", phases_block),
        ])

    return out


def main():
    ap = argparse.ArgumentParser(description="Build net-information.json từ SUMO .net.xml và .add.xml (detectors)")
    ap.add_argument("--net", required=True, help="Đường dẫn file .net.xml (SUMO network)")
    ap.add_argument("--detectors", required=True, help="Đường dẫn file .add.xml chứa laneAreaDetector")
    ap.add_argument("--out", required=True, help="Đường dẫn file JSON đầu ra")
    ap.add_argument("--controller", default="max_pressure", help="Tên controller muốn ghi vào JSON (mặc định: max_pressure)")
    args = ap.parse_args()

    data = build_tls_json(args.net, args.detectors, controller=args.controller)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Đã tạo: {args.out}")


if __name__ == "__main__":
    main()
