"""
Download the SocioPatterns Workplace dataset.

The dataset records face-to-face contacts in a workplace (office building
in France, 2015). It has two files:

  1. tij_InVS15.dat  — Contact file
     Format: "t i j" per line
       t = timestamp (seconds since start)
       i, j = anonymous IDs of two people in contact

  2. metadata_InVS15.txt — Department file
     Format: "i Di" per line
       i  = person ID
       Di = department name (e.g., DISQ, DMCT, DSE, etc.)

Source: http://www.sociopatterns.org/datasets/contacts-in-a-workplace/
"""

import os
import urllib.request
import sys

# URLs for the SocioPatterns Workplace 2015 dataset
CONTACT_URL = "http://www.sociopatterns.org/wp-content/uploads/2018/12/tij_InVS15.dat_.gz"
DEPARTMENT_URL = "http://www.sociopatterns.org/wp-content/uploads/2018/12/metadata_InVS15.txt"

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

CONTACT_FILE = os.path.join(DATA_DIR, "tij_InVS15.dat")
DEPARTMENT_FILE = os.path.join(DATA_DIR, "metadata_InVS15.txt")


def download_file(url, dest_path):
    """Download a file from a URL to a local path."""
    print(f"  Downloading: {url}")
    print(f"  Saving to:   {dest_path}")
    urllib.request.urlretrieve(url, dest_path)
    print(f"  ✓ Done ({os.path.getsize(dest_path):,} bytes)")


def generate_synthetic_data():
    """
    Generate synthetic data that mimics the SocioPatterns format.
    Used as a fallback if the real dataset can't be downloaded.
    """
    import random
    random.seed(42)

    print("\n⚠  Generating synthetic dataset (fallback)...")

    # Create 92 people across 5 departments (similar to real data)
    departments = ["DISQ", "DMCT", "DSE", "SFLE", "SRH",
                    "SSI", "SCOM", "SDOC", "DCAR", "DISQ2"]
    dept_sizes = [12, 10, 15, 8, 9, 10, 7, 6, 8, 7]

    node_id = 0
    node_departments = {}
    dept_nodes = {}
    for dept, size in zip(departments, dept_sizes):
        dept_nodes[dept] = []
        for _ in range(size):
            node_departments[node_id] = dept
            dept_nodes[dept].append(node_id)
            node_id += 1

    # Write department file
    with open(DEPARTMENT_FILE, 'w') as f:
        for nid, dept in node_departments.items():
            f.write(f"{nid}\t{dept}\n")
    print(f"  ✓ Department file: {len(node_departments)} people, "
          f"{len(departments)} departments")

    # Generate contacts — people interact more within their department
    contacts = []
    nodes = list(node_departments.keys())
    for t in range(0, 86400, 20):  # One day, 20-second intervals
        # Intra-department contacts (more frequent)
        for dept, members in dept_nodes.items():
            if len(members) < 2:
                continue
            n_contacts = random.randint(0, min(3, len(members) - 1))
            for _ in range(n_contacts):
                i, j = random.sample(members, 2)
                contacts.append((t, min(i, j), max(i, j)))

        # Inter-department contacts (less frequent)
        n_cross = random.randint(0, 2)
        for _ in range(n_cross):
            i, j = random.sample(nodes, 2)
            contacts.append((t, min(i, j), max(i, j)))

    # Write contact file
    with open(CONTACT_FILE, 'w') as f:
        for t, i, j in contacts:
            f.write(f"{t}\t{i}\t{j}\n")
    print(f"  ✓ Contact file: {len(contacts)} contact events")


def main():
    print("=" * 60)
    print("  SocioPatterns Workplace Dataset Downloader")
    print("=" * 60)

    os.makedirs(DATA_DIR, exist_ok=True)

    # Try downloading the real dataset
    try:
        # Download department metadata
        if not os.path.exists(DEPARTMENT_FILE):
            download_file(DEPARTMENT_URL, DEPARTMENT_FILE)
        else:
            print(f"  ✓ Department file already exists: {DEPARTMENT_FILE}")

        # Download contact data (may be gzipped)
        if not os.path.exists(CONTACT_FILE):
            gz_path = CONTACT_FILE + ".gz"
            download_file(CONTACT_URL, gz_path)

            # Decompress
            import gzip
            print("  Decompressing...")
            with gzip.open(gz_path, 'rb') as f_in:
                with open(CONTACT_FILE, 'wb') as f_out:
                    f_out.write(f_in.read())
            os.remove(gz_path)
            print(f"  ✓ Decompressed to {CONTACT_FILE} "
                  f"({os.path.getsize(CONTACT_FILE):,} bytes)")
        else:
            print(f"  ✓ Contact file already exists: {CONTACT_FILE}")

        print("\n✅ Dataset ready!")

    except Exception as e:
        print(f"\n⚠  Download failed: {e}")
        print("  Falling back to synthetic data generation...")
        generate_synthetic_data()
        print("\n✅ Synthetic dataset ready!")


if __name__ == "__main__":
    main()
