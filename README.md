# Stuff- — مصنع فيديوهات تعليمية عمودية (9:16)

تعطي النظام **سكريبتًا إنجليزيًا فقط** (نحو 150–170 كلمة)، فيخرج فيديو عموديًا من 60 إلى 70 ثانية:
عالم 3D مبسّط في Blender + شخصيات 2.5D مرسومة، كاميرا ديناميكية، ترجمة كلمة بكلمة، مؤثرات صوتية، وتعليق صوتي ثابت بـ Chatterbox.

```
script.txt → plan.json → voice (Chatterbox) → timeline → scenes (Blender) → clips → captions + SFX → final.mp4
```

## التشغيل في Google Colab
1. افتح `notebooks/colab_render.ipynb` في Colab (ويُفضَّل GPU).
2. شغّل الخلايا بالترتيب. الخلية الرابعة فيها السكريبت (المدخل الوحيد المطلوب).
3. الخلية السادسة تنتج `work/final/final.mp4`، والسابعة تنزّله.

## التشغيل محليًا
```bash
pip install -e ".[dev]"              # النواة (FFmpeg مطلوب في النظام)
pip install -e ".[tts]"              # Chatterbox + faster-whisper (صوت حقيقي)
pip install bpy==4.2.0               # Blender كمكتبة، ويتطلب Python 3.11؛ أو اضبط BLENDER_BIN على ملف blender
python -m stuff make script.txt --workdir work/demo --name demo
python -m stuff make script.txt --voice silent --renderer pil --scale 0.5   # معاينة سريعة بلا Blender ولا صوت
python -m stuff preflight --mode all                                         # فحص المناطق الحساسة قبل رندر طويل
```
خيارات مفيدة: `--ref-voice clip.wav` و`--align whisper` و`--plan plan.json` و`--engine CYCLES|BLENDER_EEVEE_NEXT` و`--samples N`.

## ربط نموذج ذكاء اصطناعي
اقرأ `AGENTS.md`. باختصار: النموذج **لا يطلب منك إلا السكريبت**، ثم ينفّذ الأوامر أعلاه بنفسه ويصلح المشكلات.

## الصوت الثابت (رجل أمريكي)
- يُحمَّل Chatterbox مرة واحدة، وتُحضَّر شروط الصوت مرة واحدة، ثم يُولَّد كل مشهد بنفس `seed` ونفس معاملات `exaggeration` و`cfg_weight` و`temperature`.
- **لتثبيت هوية رجل أمريكي فعلًا** ضع مقطعًا نظيفًا (10 ثوانٍ فأكثر) من صوت رجل أمريكي لديك حقوقه في `assets/voice/` وشغّل بـ `--ref-voice`. المقاطع الصوتية لا تُرفع إلى GitHub (`.gitignore`).
- بدون مرجع يُستخدم الصوت الافتراضي المدمج في Chatterbox، ولا أضمن أنه صوت رجل أمريكي. فحص `preflight --mode voice` يطبع الطبقة الصوتية (f0) لتتأكد بنفسك.
- بصمة الصوت (`fingerprint`) تُسجَّل في `voice_manifest.json`، وإذا تغيّرت الإعدادات يُعاد توليد كل المشاهد.

## البنية
| المسار | الدور |
|---|---|
| `src/stuff/planner.py` | تقسيم السكريبت إلى لقطات وتحديد الحجم والكاميرا والتعبير والمؤثرات |
| `src/stuff/tts.py`, `align.py` | الصوت الثابت وتوقيت الكلمات والـ timeline |
| `src/stuff/sprites.py` | شخصيات 2.5D إجرائية بسبعة تعابير |
| `src/stuff/blender/kits.py` | مكتبة بيئات معيارية: field وfortress وcanyon وinterior |
| `src/stuff/blender/scene_runner.py` | بناء المشهد والكاميرا والرندر داخل Blender |
| `src/stuff/render_pil.py` | رندر معاينة سريع (للاختبار) |
| `src/stuff/captions.py`, `sfx.py`, `compose.py` | ترجمة ASS ومؤثرات إجرائية وتجميع FFmpeg |
| `docs/` | `STYLE_GUIDE.md` و`PLAN_SCHEMA.md` و`ARCHITECTURE.md` |

لإضافة موضوع جديد (بحر أو مدينة أو مختبر…) اكتب دالة kit جديدة في `kits.py` وسجّلها في `KITS`، وأضف كلماتها المفتاحية في `planner.KIT_WORDS`.

## الاختبار والتحقق
- `ci.yml`: اختبارات الوحدة + مسار كامل بصوت صامت ورندر معاينة.
- `preflight.yml`: Blender الحقيقي (4 بيئات) وChatterbox الحقيقي.
- كل workflow يدفع تقريره إلى فرع **`ci-report`** (مجلد لكل job)، فتقرأ النتائج دون فتح Actions.

## حالة التحقق
*تُحدَّث هذه الفقرة بعد قراءة تقارير `ci-report` فعليًا، ولا تُعتبر أي مرحلة ناجحة قبل ذلك.*
