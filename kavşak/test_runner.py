#!/usr/bin/env python
# Test script for debugging

import os
import sys

# SUMO_HOME check
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
    print(f"✅ SUMO_HOME found: {os.environ['SUMO_HOME']}")
    print(f"✅ Tools path: {tools}")
else:
    print("❌ SUMO_HOME not found!")
    sys.exit(1)

# Import test
try:
    from sumolib import checkBinary
    print("✅ sumolib imported successfully")
except ImportError as e:
    print(f"❌ sumolib import failed: {e}")
    sys.exit(1)

try:
    import traci
    print("✅ traci imported successfully")
except ImportError as e:
    print(f"❌ traci import failed: {e}")
    sys.exit(1)

# Check files
required_files = [
    "data/cross.sumocfg",
    "data/cross.net.xml",
    "gps-data.gpx"
]

for file in required_files:
    if os.path.exists(file):
        print(f"✅ {file} exists")
    else:
        print(f"❌ {file} missing")

print("\n🚀 All checks passed! Trying to run main script...")

# Try to import main script functions
try:
    import runner
    print("✅ runner.py imported successfully")
    
    # Test GPS parsing
    coords = runner.parse_gps_data("gps-data.gpx")
    if coords:
        print(f"✅ GPS data parsed: {len(coords)} coordinates")
        print(f"   First coord: {coords[0]}")
        print(f"   Last coord: {coords[-1]}")
    else:
        print("❌ GPS data parsing failed")
        
except Exception as e:
    print(f"❌ Error importing runner: {e}")
    import traceback
    traceback.print_exc()
