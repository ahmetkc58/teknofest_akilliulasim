#!/usr/bin/env python
# Direct run without input prompts

import os
import sys
import optparse

# SUMO_HOME setup
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary
import traci

# Import all functions from runner
from runner import *

def run_simulation_direct():
    """Simülasyonu doğrudan kullanıcı input'u olmadan çalıştır"""
    global use_real_time, current_network_type
    
    print("🚀 Direct simulation start - Cross network")
    use_real_time = False  # Dosyadan okuma modu
    current_network_type = "cross"
    
    # Check for GUI
    try:
        sumoBinary = checkBinary('sumo-gui')  # GUI ile çalıştır
        print("📺 SUMO GUI found, starting with GUI")
    except:
        try:
            sumoBinary = checkBinary('sumo')  # GUI olmadan
            print("💻 Using SUMO without GUI")
        except:
            print("❌ SUMO not found!")
            return
    
    # Generate route file
    print("📁 Generating route file...")
    generate_routefile()
    
    config_file = "data/cross.sumocfg"
    print(f"🚗 Starting SUMO with config: {config_file}")
    
    # Start SUMO
    try:
        traci.start([sumoBinary, "-c", config_file, "--tripinfo-output", "tripinfo.xml"])
        print("✅ SUMO started successfully")
        
        # Run simulation
        run()
        
    except Exception as e:
        print(f"❌ SUMO simulation error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_simulation_direct()
