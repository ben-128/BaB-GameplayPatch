"""
export_coordinates.py
Export coordinate data to JSON and CSV for visualization

Usage: py -3 export_coordinates.py
"""

from pathlib import Path
import struct
import json
import csv

SCRIPT_DIR = Path(__file__).parent
BLAZE_ALL = SCRIPT_DIR / "work" / "BLAZE.ALL"

def extract_coordinates_from_zone(data, start_offset, size, struct_size=16, max_coords=1000):
    """
    Extract 3D coordinates from a specific zone
    Returns list of (x, y, z) tuples with metadata
    """
    coordinates = []

    for i in range(start_offset, start_offset + size - struct_size, struct_size):
        if len(coordinates) >= max_coords:
            break

        chunk = data[i:i+struct_size]

        # Skip padding
        if all(b == 0 for b in chunk) or all(b == 0xCC for b in chunk) or all(b == 0xFF for b in chunk):
            continue

        try:
            # Parse as 3D coordinates (int16)
            x = struct.unpack_from('<h', chunk, 0)[0]
            y = struct.unpack_from('<h', chunk, 2)[0]
            z = struct.unpack_from('<h', chunk, 4)[0]

            # Filter for reasonable coordinate ranges
            if all(-8192 <= coord <= 8192 for coord in [x, y, z]):
                # Parse additional values
                additional = []
                for j in range(6, min(struct_size, 16), 2):
                    try:
                        v = struct.unpack_from('<h', chunk, j)[0]
                        additional.append(v)
                    except:
                        break

                coordinates.append({
                    'offset': hex(i),
                    'x': x,
                    'y': y,
                    'z': z,
                    'additional': additional
                })

        except:
            pass

    return coordinates

def main():
    print("=" * 70)
    print("  COORDINATE DATA EXPORT")
    print("=" * 70)

    print(f"\nReading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"Size: {len(data):,} bytes")

    # Define zones to extract
    zones = [
        (0x100000, 0x10000, "zone_1mb", "Level Geometry Zone 1"),
        (0x200000, 0x10000, "zone_2mb", "Level Geometry Zone 2"),
        (0x300000, 0x10000, "zone_3mb", "Vertex/Polygon Data"),
        (0x500000, 0x10000, "zone_5mb", "Floor/Ceiling Geometry"),
        (0x900000, 0x10000, "zone_9mb", "Camera/Spawn Data"),
    ]

    all_exports = {}

    for start, size, zone_name, description in zones:
        if start + size > len(data):
            continue

        print(f"\n[{zone_name.upper()}] {description}")
        print(f"  Offset: {hex(start)}, Size: {size:,} bytes")

        # Extract coordinates
        coords = extract_coordinates_from_zone(data, start, size, struct_size=16, max_coords=500)

        print(f"  Extracted: {len(coords)} coordinate points")

        if coords:
            # Calculate bounds
            x_values = [c['x'] for c in coords]
            y_values = [c['y'] for c in coords]
            z_values = [c['z'] for c in coords]

            bounds = {
                'x_min': min(x_values), 'x_max': max(x_values),
                'y_min': min(y_values), 'y_max': max(y_values),
                'z_min': min(z_values), 'z_max': max(z_values)
            }

            print(f"  X range: [{bounds['x_min']}, {bounds['x_max']}]")
            print(f"  Y range: [{bounds['y_min']}, {bounds['y_max']}]")
            print(f"  Z range: [{bounds['z_min']}, {bounds['z_max']}]")

            all_exports[zone_name] = {
                'description': description,
                'offset': hex(start),
                'size': size,
                'coordinate_count': len(coords),
                'bounds': bounds,
                'coordinates': coords[:100]  # Limit to first 100 for JSON
            }

            # Export to CSV for easy plotting
            csv_file = SCRIPT_DIR / f"coordinates_{zone_name}.csv"
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['offset', 'x', 'y', 'z', 'additional_values'])
                for coord in coords:
                    writer.writerow([
                        coord['offset'],
                        coord['x'],
                        coord['y'],
                        coord['z'],
                        '|'.join(map(str, coord['additional']))
                    ])

            print(f"  Saved to: {csv_file.name}")

    # Export master JSON
    json_file = SCRIPT_DIR / "coordinates_export.json"
    with open(json_file, 'w') as f:
        json.dump(all_exports, f, indent=2)

    print(f"\n\nMaster JSON saved to: {json_file.name}")

    # Create plotting instructions
    readme_file = SCRIPT_DIR / "COORDINATE_VISUALIZATION.md"
    readme_content = """# Coordinate Visualization Guide

## Extracted Files

The following coordinate data files have been extracted from BLAZE.ALL:

"""

    for zone_name, data in all_exports.items():
        readme_content += f"\n### {zone_name.upper()}\n"
        readme_content += f"- **Description:** {data['description']}\n"
        readme_content += f"- **Offset:** {data['offset']}\n"
        readme_content += f"- **Coordinates:** {data['coordinate_count']}\n"
        readme_content += f"- **File:** `coordinates_{zone_name}.csv`\n"
        readme_content += f"- **X range:** [{data['bounds']['x_min']}, {data['bounds']['x_max']}]\n"
        readme_content += f"- **Y range:** [{data['bounds']['y_min']}, {data['bounds']['y_max']}]\n"
        readme_content += f"- **Z range:** [{data['bounds']['z_min']}, {data['bounds']['z_max']}]\n"

    readme_content += """

## Visualization Methods

### Method 1: Python matplotlib (3D Scatter Plot)

```python
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Load data
df = pd.read_csv('coordinates_zone_5mb.csv')

# Create 3D plot
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')

# Plot points
ax.scatter(df['x'], df['y'], df['z'], c='blue', marker='o', s=1)

ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.set_title('Level Geometry - Zone 5MB')

plt.show()
```

### Method 2: Online 3D Viewer

1. Convert CSV to OBJ format (3D model)
2. Upload to online viewer like:
   - https://3dviewer.net/
   - https://threejs.org/editor/

### Method 3: Blender Import

```python
# Blender Python script
import bpy
import csv

# Read CSV
with open('coordinates_zone_5mb.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        x, y, z = float(row['x']), float(row['y']), float(row['z'])

        # Scale down (PSX units to Blender units)
        x, y, z = x/1000, y/1000, z/1000

        # Create small sphere at each point
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.01, location=(x, y, z))
```

### Method 4: Unity Import

1. Create C# script in Unity:

```csharp
using UnityEngine;
using System.IO;

public class CoordinateLoader : MonoBehaviour {
    void Start() {
        string[] lines = File.ReadAllLines("coordinates_zone_5mb.csv");

        for (int i = 1; i < lines.Length; i++) {
            string[] values = lines[i].Split(',');
            float x = float.Parse(values[1]) / 100f;
            float y = float.Parse(values[2]) / 100f;
            float z = float.Parse(values[3]) / 100f;

            GameObject sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            sphere.transform.position = new Vector3(x, y, z);
            sphere.transform.localScale = Vector3.one * 0.1f;
        }
    }
}
```

## Analysis Recommendations

1. **Start with Zone 5MB** - Most regular patterns, likely floor/ceiling geometry
2. **Compare zones** - Look for overlapping structures
3. **Check symmetry** - Game levels often have symmetrical designs
4. **Identify clusters** - Groups of points may indicate rooms
5. **Check for patterns** - Regular grids suggest structured level design

## Questions to Answer

- Do the points form recognizable level shapes?
- Are there clear room boundaries?
- Do coordinates match known level layouts from gameplay?
- Can we identify doorways, corridors, and chambers?

---

*Generated by export_coordinates.py*
"""

    with open(readme_file, 'w') as f:
        f.write(readme_content)

    print(f"Visualization guide saved to: {readme_file.name}")

    print("\n" + "="*70)
    print("EXPORT COMPLETE")
    print("="*70)
    print(f"\nFiles created:")
    print(f"  - coordinates_export.json (master file)")
    for zone_name, _ in all_exports.items():
        print(f"  - coordinates_{zone_name}.csv")
    print(f"  - COORDINATE_VISUALIZATION.md (guide)")
    print("\nNext step: Visualize the coordinates using the guide!")
    print("="*70)

if __name__ == '__main__':
    main()
