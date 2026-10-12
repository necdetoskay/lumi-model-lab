# Q25 P0/P4 çevrimdışı ilk uygulama

Ücretli çağrı: 0. Hikâye/state değişikliği: 0. Üretim hattı değişikliği: 0.

Q22/Q24 seçili kanıtları kesin Git commit’lerinden byte-exact kopyalandı. Kaynak yolları/hash’leri baseline-lineage.json içinde. Bu kayıt bütün eski engine’i yeniden çalıştırma değildir. Q22 ACCEPT ve Q24 REJECT kararları değiştirilmedi.

Q24 son taslağı için birbirinden ayrı sonuçlar:

- Anlatı: UNVERIFIED — bağımsız insan değerlendirmesi yok; otomatik PASS veya REJECT yok.
- Kontrol: DISPUTED_REVIEW — alıntılar mevcut ve byte olarak doğru, fakat bazıları iddiayı desteklemiyor. Bu semantik karar mevcut Codex taslak incelemesine dayanıyor; bağımsız onay bekliyor.
- State: STATE_MODEL_GAP — son kitap ilk nesne listesinde kimlikli değil. State’in container=null/elde ayraç kaydı terminal metni tam karşılamıyor.
- Kayıt yetkisi: BLOCKED — state commit’i yapılamaz, hikâye de kontrolün tartışmalı hükmüyle otomatik reddedilmez.

Sentetik negatif kontroller yanlış hash, yanlış alıntı, sınır dışı aralık ve eksik kanon referansını INVALID_REVIEW olarak raporlar. Q24’teki geçerli fakat ilgisiz alıntıları kodun kendisinin semantik olarak anladığı iddia edilmiyor. Geçerli bir aralığın varlığından doğruluk türetilmiyor. Boş kontrol raporu da başarı kabul edilmiyor.

Bu yalnız P0 seçili kanıt dondurma ve P4 read-only sonuç ayrımıdır. NarrativeIntent/Memory/Outline, yeni nesne kabulü, tam state extraction, kör insan benchmark’ı ve üretim qualification uygulanmış değildir. P0/P4 görevleri bütünüyle tamamlanmış sayılmaz. Daha önceki 582 test bu farklı base branch için güncel GREEN iddiası değildir.
