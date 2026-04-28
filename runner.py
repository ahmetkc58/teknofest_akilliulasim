from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import optparse
import random

# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa


def generate_routefile():
    random.seed(42)  # make tests reproducible
    N = 5000  # number of time steps                simülasyon süresini belirtir
    # demand per second from different directions
    pWE = 1. / 10  #                                  batı ve ve doğudan gelen araba sayılarını belirliyo her 10 birimde 1 araba üreteecek
    pEW = 1. / 11
    pNS = 1. / 30
    with open("data/cross.rou.xml", "w") as routes: # burada trafik modeli olan xml dosyasını kopyalar
        print("""<routes>
        <vType id="typeWE" accel="0.8" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="16.67" \
guiShape="passenger"/>
        <vType id="typeNS" accel="0.8" decel="4.5" sigma="0.5" length="7" minGap="3" maxSpeed="25" guiShape="emergency"/>

        <route id="right" edges="51o 1i 2o 52i" />
        <route id="left" edges="52o 2i 1o 51i" />
        <route id="down" edges="54o 4i 3o 53i" />""", file=routes)
        vehNr = 0
        for i in range(N):
            if random.uniform(0, 1) < pWE:
                print('    <vehicle id="right_%i" type="typeWE" route="right" depart="%i" />' % ( # burada vehicle kısmı  aracın belli bir rotayı takip eden araçları temsil eder depar kısmıda ne zaman oluşacağını bleirler
                    vehNr, i), file=routes)
                vehNr += 1
            if random.uniform(0, 1) < pEW:
                print('    <vehicle id="left_%i" type="typeWE" route="left" depart="%i" />' % (
                    vehNr, i), file=routes)
                vehNr += 1
            if random.uniform(0, 1) < pNS:
                print('    <vehicle id="down_%i" type="typeNS" route="down" depart="%i" color="1,0,0"/>' % (
                    vehNr, i), file=routes)
                vehNr += 1
        print("</routes>", file=routes)   # xml dosyasının sonunu belirtir

# The program looks like this
#    <tlLogic id="0" type="static" programID="0" offset="0">
# the locations of the tls are      NESW
#        <phase duration="31" state="GrGr"/>
#        <phase duration="6"  state="yryr"/>
#        <phase duration="31" state="rGrG"/>
#        <phase duration="6"  state="ryry"/>
#    </tlLogic>


def run():
    """execute the TraCI control loop"""
    step = 0
    # we start with phase 2 where EW has green
    traci.trafficlight.setPhase("0", 2)                   #trafik ışıklarının başlangıç durumu hazzırlanıyor   2 sayısı yeşil ışık anlamına geliyor
    while traci.simulation.getMinExpectedNumber() > 0:             # beklenen araç sayısı eğer gelecek araba kalmadıysa simülasyon sona erir
        traci.simulationStep()                                  # simülasyon adımı gerçekleştirilir
        if traci.trafficlight.getPhase("0") == 2:
            # we are not already switching
            if traci.inductionloop.getLastStepVehicleNumber("0") > 0:         #burada kuzeyden gelen bir araç var mı diye bakılıyor
                # there is a vehicle from the north, switch
                traci.trafficlight.setPhase("0", 3)                 # tarafik ışığı fazı 3 olarak değiştirilir  doğu ve batı kısımlarında kırmızı yanmaya başlar
            else:                                                # araba gelmiyosa yeşil yakmaya devam eder
                # otherwise try to keep green for EW
                traci.trafficlight.setPhase("0", 2)
        step += 1                                              # adım sayısı bir arttırılır
    traci.close()
    sys.stdout.flush()


def get_options():
    optParser = optparse.OptionParser() # analiz için kullanılan bişeymiş
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="run the commandline version of sumo")
    options, args = optParser.parse_args()
    return options

if __name__ == "__main__":
    options = get_options()
    
    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    # first, generate the route file for this simulation
    generate_routefile() #rota dosyasını oluşturuyor

    # this is the normal way of using traci. sumo is started as a
    # subprocess and then the python script connects and runs
    traci.start([sumoBinary, "-c", "data/cross.sumocfg",
                             "--tripinfo-output", "tripinfo.xml"])
    run()
