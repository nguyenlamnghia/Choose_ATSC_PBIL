import xml.etree.ElementTree as ET
import argparse
import json

# Function to save traffic light system candidates to a file
# Example: {"candidate_tls_ids": {"24": 0.5, "124": 0.5, "8": 0.5, "18": 0.5, "12": 0.5, "63": 0.5}}
def save_tls_candidates(candidates, output_file):
    with open(output_file, "w") as f:
        dict_candidates = {"candidate_tls_ids": {}}
        for candidate in candidates:
            dict_candidates["candidate_tls_ids"][candidate] = 0.5
        json.dump(dict_candidates, f, ensure_ascii=False, indent=2)

# Function to build traffic light system candidates from an XML file
def build_tls_candidates(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    candidates = []
    for tls in root.findall("tlLogic"):
        tls_id = tls.attrib.get("id")
        if tls_id:
            candidates.append(tls_id)

    return candidates

def main():
    ap = argparse.ArgumentParser(description="Build net-information.json từ SUMO .net.xml và .add.xml (detectors)")
    ap.add_argument("--net", required=True, help="Path to the SUMO .net.xml file")
    ap.add_argument("--output", required=True, help="Path to the output file")
    args = ap.parse_args()

    candidates = build_tls_candidates(args.net)
    save_tls_candidates(candidates, args.output)
