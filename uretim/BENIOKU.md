# Profil üreticisi

`python3 uretim/uret.py` → `assets/*.svg` + `README.md`

- Ana kaynak: `/root/atasoy-dev/site/ortak/projeler.json` (atasoy.dev portfolyosu). Portfolyo değişince yeniden çalıştır.
- Portfolyoda olmayanlar ve üstüne yazılanlar: `uretim/veri.json`.
- Fontlar `fontlar/indirilen/` altında (git dışı): Bricolage Grotesque ve Source Serif 4 değişken fontları google/fonts deposundan, JetBrains Mono `/root/atasoy-dev/marka/kaynak/`.
- Önizleme: `uretim/araclar/onizle.sh` → `uretim/onizleme/{acik,koyu}.png`
- Ekran görüntüsü almak: `node uretim/araclar/ekran.cjs çıktı.png https://adres`
