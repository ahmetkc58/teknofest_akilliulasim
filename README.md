# TEKNOFEST Akıllı Ulaşım - Ambulans İçin Akıllı Kavşak ve GPS Entegrasyon Projesi

Bu proje, **acil durum araçlarının (özellikle ambulansların) trafik ışıklarının neden olduğu yoğunluktan etkilenmeden vakalara ve hastanelere en hızlı şekilde ulaşabilmesi** amacıyla geliştirilmiştir. **Eclipse SUMO (Simulation of Urban MObility)** aracı kullanılarak akıllı kavşak yönetim algoritmaları test edilmekte; ambulanslardan ESP32 modülleri aracılığıyla alınan gerçek zamanlı GPS verileri simülasyon ortamına entegre edilerek trafik ışıklarının ambulansın geçiş üstünlüğüne göre dinamik olarak yönetilmesi sağlanmaktadır. Proje, TEKNOFEST Akıllı Ulaşım yarışmaları kapsamındaki isterler için pratik bir altyapı sunmaktadır.

## 🚀 Özellikler

- **Dinamik Trafik Işığı Kontrolü:** `runner.py` içerisinde indüksiyon döngüleri (induction loops) kullanılarak kavşaktaki araç yoğunluğuna (ve öncelikli ambulans geçişlerine) göre dinamik ışık fazı ayarlanmaktadır.
- **Gerçek Zamanlı Ambulans GPS Entegrasyonu:** Ambulanslardaki ESP32 gibi donanımlardan veya önceden kaydedilmiş test verilerinden (`.csv`) alınan GPS koordinatları SUMO harita koordinat sistemine (x, y) çevrilmekte ve simülasyona aktarılmaktadır.
- **Araç Takibi ve Loglama:** Simülasyon içerisindeki aktif araçların anlık konumları, hızları ve yönleri gerçek zamanlı olarak izlenebilir; analiz için metin belgesine kayıt edilebilir.
- **Modüler Yapı:** Veri kümeleri, simülasyon harita ayarları ve Python yönetici kodları birbirinden ayrılmış temiz bir yapıya sahiptir.

## 📁 Proje Klasör Yapısı

- `runner.py`: SUMO simülasyonunun temel döngüsünü barındırır. Rota dosyasını oluşturur ve trafik ışıklarının algoritmasını (araç gelip gelmeme durumuna göre değişen fazlar) yürütür.
- `gps_sumo.py`: ESP32 veya `csv` formatındaki test dosyalarından GPS verilerini okuyarak SUMO simülasyonuna entegre eder.
- `aktif_arac_konumlari.py`: SUMO üzerinde hareket eden tüm aktif araçların pozisyonlarını, hızlarını ve yollarını ekrana yazdıran veya `arac_konumlari.txt` dosyasına kaydeden bir takip aracıdır.
- `sistem_entegrasyonu.py`: Sistem geneli birleştirme dosyası. (Şu anda geliştirme aşamasındadır.)
- `data/` Klasörü:
  - `cross.sumocfg`: Ana SUMO simülasyon konfigürasyon dosyası.
  - `*.net.xml, *.rou.xml, vb.`: SUMO ağı (.net), yollar, kavşaklar ve rotalara ait ön tanımlı ayarlar.
- `*.csv` Dosyaları: Test amaçlı senaryolar (Tek araçlık veya çoklu araç GPS verileri).

## 🛠️ Gereksinimler ve Kurulum

Öncelikle sisteminizde **Eclipse SUMO**'nun kurulu olması ve işletim sistemi ortam değişkenlerine eklenmiş olması gerekmektedir. 

1. **Python ve Kütüphaneler:**
   Sisteminizde Python 3.x sürümü yüklü olmalıdır. İlgili gereksinimleri yüklemek için terminalde şu komutu çalıştırın:
   ```bash
   pip install requests pandas
   ```
2. **SUMO_HOME Ortam Değişkeni:**
   `traci` kütüphanesinin (Python-SUMO haberleşmesi) çalışabilmesi için `SUMO_HOME` ortam değişkeninin ayarlandığından emin olun.
   - Windows: `C:\Program Files (x86)\Eclipse\Sumo` (kurulum konumuna göre değişiklik gösterebilir) dizinini ortam değişkenleri arasından ayarlayabilirsiniz.

## ⚙️ Kullanım

**1. Temel Simülasyon ve Dinamik Işık Yönetimi:**
Ağı simüle etmek ve rastgele rota oluşturup kavşak simülasyonu başlatmak için:
```bash
python runner.py
```
*(Eğer GUI açılmasını istemiyorsanız `python runner.py --nogui` parametresini kullanabilirsiniz.)*

**2. GPS Verisini Simülasyona Dahil Etme:**
Simülasyon üzerinden araçları koordine etmek ve veri kaynaklarını yönetmek için:
```bash
python gps_sumo.py
```
Bu adımı çalıştırdığınızda size iki seçenek sunar. İsterseniz ağdaki bir ESP32'nin bağlandığı IP üzerinden gerçek veri alabilir, isterseniz `csv` test dosyalarından ("single_vehicle_test", "detailed_test" vb.) veri yürütebilirsiniz.

**3. Araç İstatistiklerini Çekmek ve İzlemek:**
Simülasyondaki araçların X-Y koordinatlarını, hızlarını ve güzergahlarını okumak için:
```bash
python aktif_arac_konumlari.py
```
Program çalıştığında size 3 menü sunar: 
- Tüm araçları ekranda izleme
- Verileri dosyaya (`arac_konumlari.txt`) kaydetme
- ID'si girilen spesifik bir aracı özel takip etme

---

*Bu proje TEKNOFEST gereksinimlerine göre tasarlanmış olup modülerleştirme ve iyileştirme adımları devam etmektedir.*
