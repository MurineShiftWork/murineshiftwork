import os
import xml.etree.ElementTree as ET

root_dir = "/ceph/sjones/projects/sequence_squad/revision_data/lars_recordings/ephys"
target_field = "probe_serial_number"

for dirpath, dirnames, filenames in os.walk(root_dir):
    for filename in filenames:
        if filename.lower().endswith(".xml"):
            file_path = os.path.join(dirpath, filename)
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()

                for elem in root.iter():
                    if elem.tag == target_field and elem.text:
                        print(f"{file_path}: {elem.tag} = {elem.text.strip()}")

                    for attr_name, attr_value in elem.attrib.items():
                        if attr_name == target_field:
                            print(f"{file_path}: {attr_name} = {attr_value}")

            except ET.ParseError:
                print(f"Failed to parse XML: {file_path}")
