import xml.etree.ElementTree as ET
import math

tree = ET.parse('gps-data-2.gpx')
root = tree.getroot()
coordinates = []

for trkpt in root.findall('.//trkpt'):
    lat = float(trkpt.get('lat'))
    lon = float(trkpt.get('lon'))
    coordinates.append((lat, lon))

if coordinates:
    lats = [coord[0] for coord in coordinates]
    lons = [coord[1] for coord in coordinates]
    
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    
    print(f'GPS Koordinat Aralığı:')
    print(f'  Latitude:  {lat_min:.8f} - {lat_max:.8f} (Fark: {lat_max-lat_min:.8f})')
    print(f'  Longitude: {lon_min:.8f} - {lon_max:.8f} (Fark: {lon_max-lon_min:.8f})')
    print(f'  Toplam nokta: {len(coordinates)}')
    print(f'  İlk 10 nokta:')
    for i, coord in enumerate(coordinates[:10]):
        print(f'    {i+1}: Lat={coord[0]:.8f}, Lon={coord[1]:.8f}')
        
    # Mesafe hesaplaması (metre cinsinden)
    lat_distance = (lat_max - lat_min) * 111000  # 1 derece ≈ 111km
    lon_distance = (lon_max - lon_min) * 111000 * abs(math.cos(math.radians((lat_min + lat_max)/2)))
    
    print(f'\nGerçek mesafe aralığı:')
    print(f'  Latitude farkı: {lat_distance:.2f} metre')
    print(f'  Longitude farkı: {lon_distance:.2f} metre')
