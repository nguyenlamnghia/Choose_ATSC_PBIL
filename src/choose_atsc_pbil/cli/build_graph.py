import argparse, json, os
from ..sim.extractors import sumo_net_to_nx_graph

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--candidates-out", required=True)
    args = ap.parse_args()

    sumo_net_to_nx_graph(args.net, args.out)

    # For scaffold: make a trivial tls_candidates list; user should replace with actual TLS IDs.
    candidates = {"candidate_tls_ids": ["TLS_0","TLS_1","TLS_2"], "Nmax": 2, "meta": {"picked_by": "scaffold"}}
    os.makedirs(os.path.dirname(args.candidates_out), exist_ok=True)
    with open(args.candidates_out, "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2)
    print(f"Wrote {args.out} and {args.candidates_out}")

if __name__ == "__main__":
    main()
