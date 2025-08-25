#!/usr/bin/env python3
"""
Compute turning ratio from a SUMO --vehroute-output XML.

Usage:
  python compute_turn_ratio.py --vehroute <path/to/vehroute.xml> --edge-in <EDGE_IN> --edge-out <EDGE_OUT>

Optional:
  --list-from <EDGE_IN>     List all outgoing ratios from EDGE_IN.
  --delimiter TAB|COMMA     Output delimiter for list (default: TAB)
"""
import argparse
from xml.etree import ElementTree as ET
from collections import Counter

def parse_args():
    ap = argparse.ArgumentParser(description="Compute turning ratio from SUMO vehroute-output")
    ap.add_argument("--vehroute", required=True, help="Path to vehroute-output XML file")
    ap.add_argument("--edge-in", help="Edge ID for incoming edge")
    ap.add_argument("--edge-out", help="Edge ID for outgoing edge")
    ap.add_argument("--list-from", help="If set, list all outgoing ratios from the given incoming edge")
    ap.add_argument("--delimiter", choices=["TAB", "COMMA"], default="TAB")
    return ap.parse_args()

def load_pairs(vehroute_path):
    tree = ET.parse(vehroute_path)
    root = tree.getroot()
    pairs_counter = Counter()
    out_counts_by_in = Counter()
    for v in root.iter("vehicle"):
        route_el = v.find("route")
        if route_el is None:
            continue
        edges_str = route_el.get("edges", "")
        if not edges_str:
            continue
        edges = edges_str.split()
        for i in range(len(edges)-1):
            ein, eout = edges[i], edges[i+1]
            pairs_counter[(ein, eout)] += 1
            out_counts_by_in[ein] += 1
    return pairs_counter, out_counts_by_in

def main():
    args = parse_args()
    pairs_counter, out_counts_by_in = load_pairs(args.vehroute)

    if args.list_from:
        ein = args.list_from
        total = out_counts_by_in.get(ein, 0)
        if total == 0:
            print(f"No transitions starting from edge_in='{ein}' found.")
            return
        # Gather all eout for this ein
        outs = [(eout, cnt, cnt/total) for (ein2, eout), cnt in pairs_counter.items() if ein2 == ein]
        sep = "\t" if args.delimiter == "TAB" else ","
        print(sep.join(["edge_in","edge_out","count","total_from_edge_in","turn_ratio"]))
        for eout, cnt, ratio in sorted(outs, key=lambda x: x[0]):
            print(sep.join([ein, eout, str(cnt), str(total), f"{ratio:.6f}"]))
        return

    if args.edge_in and args.edge_out:
        ein, eout = args.edge_in, args.edge_out
        cnt = pairs_counter.get((ein, eout), 0)
        total = out_counts_by_in.get(ein, 0)
        ratio = (cnt / total) if total else 0.0
        print(f"edge_in={ein} edge_out={eout} -> count={cnt}, total_from_edge_in={total}, turn_ratio={ratio:.6f}")
        return

    print("Nothing to do. Provide --edge-in and --edge-out to get a single ratio, or --list-from to list all outgoing ratios from one edge.")

if __name__ == "__main__":
    main()
