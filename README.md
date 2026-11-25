# OptimizeIT

Mevcut bir uygulamayı **işlevini bozmadan** daha hızlı, daha az kaynak tüketen ve daha kararlı hâle getiren yapay zekâ ajan skill'i.

OptimizeIT bir "en iyi pratikler" listesi değildir. Projeyi tanır, gerçek darboğazları bulur, önceliklendirir, temel ölçüm alır, hedefli optimizasyonlar uygular, test/lint/build ile doğrular, aynı koşullarda yeniden ölçer ve ayrıntılı bir rapor üretir.

**Analiz eder → optimize eder → test eder → ölçer → raporlar.**

## Desteklenen Ajanlar

| Ajan | Kullanıcı düzeyi dizin | Proje düzeyi dizin | Alternatif |
|---|---|---|---|
| Claude Code | `~/.claude/skills/optimizeit` | `.claude/skills/optimizeit` | Plugin olarak kurulum |
| Codex | `~/.agents/skills/optimizeit` | `.agents/skills/optimizeit` | Eski sürümler: `~/.codex/skills` |
| Cursor | `~/.cursor/skills/optimizeit` | `.cursor/skills/optimizeit` | Cursor `.claude/skills` dizinini de okur |
| Gemini CLI | `~/.gemini/skills/optimizeit` | `.gemini/skills/optimizeit` | Extension olarak kurulum |

Hepsi aynı açık [Agent Skills](https://agentskills.io/specification) biçimini (`SKILL.md` + destek dosyaları) kullanır; tek bir skill klasörü dört ajanda da çalışır.

## Kurulum

### Kurulum betiğiyle (tüm ajanlar)

```sh
git clone https://github.com/aclxkatirant/OptimizeIT.git
cd OptimizeIT
sh install.sh                    # dört ajana, kullanıcı düzeyinde
sh install.sh --hedef cursor     # yalnızca bir ajana
sh install.sh --proje ../projem  # belirli bir projeye
```

Windows (PowerShell):

```powershell
.\install.ps1
.\install.ps1 -Hedef codex
.\install.ps1 -Proje ..\projem
```

`--hedef` / `-Hedef` değerleri: `claude`, `codex`, `cursor`, `gemini`, `hepsi` (varsayılan).

### Claude Code plugin olarak

```
/plugin marketplace add aclxkatirant/OptimizeIT
/plugin install optimizeit@optimizeit
```

### Gemini CLI extension olarak

```sh
gemini extensions install https://github.com/aclxkatirant/OptimizeIT
```

> Gemini CLI'da Agent Skills deneysel bir özellik olabilir; çalışmıyorsa ayarlardan etkinleştirin ve `/skills reload` ile yeniden yükleyin, `/skills list` ile doğrulayın.

## Kullanım

Skill, performans ile ilgili isteklerde otomatik etkinleşir. Örnekler:

- "Bu projeyi optimize et."
- "`/api/orders` endpoint'i çok yavaş, hızlandır."
- "Uygulamanın açılışı 6 saniye sürüyor, darboğazı bul."
- "Frontend bundle'ı çok büyük."
- "Bellek sürekli artıyor, sızıntı var mı?"

Doğrudan çağırmak için: Claude Code / Cursor'da `/optimizeit`, diğer ajanlarda "OptimizeIT skill'ini kullan".

## İş Akışı

| Faz | Ne yapılır |
|---|---|
| 1. Keşif | Diller, framework'ler, mimari, giriş noktaları, VT, komutlar |
| 2. Analiz | Kontrol listesi + profil; şüpheli desenler bağlamında değerlendirilir |
| 3. Önceliklendirme | CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL, değer/risk sıralaması |
| 4. Temel ölçüm | Tekrarlanabilir komutla "önce" ölçümü |
| 5. Optimizasyon | Tek seferde tek bulgu, davranış korunarak |
| 6. Doğrulama | Test, lint, tip kontrolü, build, davranış karşılaştırması |
| 7. Benchmark | Aynı koşullarda "sonra" ölçümü, gürültü analizi |
| 8. Rapor | 10 bölümlü yapılandırılmış rapor |

## Güvenlik İlkeleri (özet)

- Benchmark sonucu asla uydurulmaz; ölçülmediyse "ölçülmedi" yazılır.
- Çalıştırılmayan test için "geçti" denmez.
- Yıkıcı veritabanı migration'ı asla otomatik uygulanmaz.
- Public API, yapılandırma ve UI davranışı izinsiz değiştirilmez.
- Performans için işlev veya güvenlik kontrolü kaldırılmaz.
- Yeni bağımlılık, şema değişikliği ve davranış değişikliği için onay alınır.

## Depo Yapısı

```
skills/optimizeit/
  SKILL.md                         Skill tanımı ve iş akışı (İngilizce)
  references/                      Faz bazlı ayrıntılı rehberler (Türkçe)
  scripts/kesif.py                 Proje keşif betiği
  scripts/olcum.py                 Benchmark çalıştırma ve karşılaştırma betiği
.claude-plugin/                    Claude Code plugin + marketplace tanımı
gemini-extension.json              Gemini CLI extension tanımı
install.sh / install.ps1           Çoklu ajan kurulum betikleri
```

Betikler yalnızca Python 3.8+ standart kütüphanesini kullanır.

## Lisans

MIT
