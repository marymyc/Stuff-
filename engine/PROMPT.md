# The prompt to give any AI agent / البرومبت الذي تعطيه لأي نموذج

Open this folder (or the GitHub repo) in your agent (Claude Code, Codex, Gemini CLI, Cursor...) and paste:

---
Read AGENTS.md and follow it exactly.
Make a new animated short called `<short_name>` from this script:

<paste your script here>

Do the whole pipeline (setup check -> voice -> shot plan -> world -> characters -> look check -> sound -> final
render -> QA) and log progress in projects/<short_name>/STATUS.md after every step. Only stop to ask me for things
you cannot do yourself (API keys, recording a voice, installing software). At the end give me out/<short_name>/final.mp4.
---

## بالعربي
افتح هذا المجلد (أو رابط المستودع على GitHub) داخل النموذج/الوكيل، ثم الصق:

---
Read AGENTS.md and follow it exactly.
Make a new animated short called `اسم_بالإنجليزي` from this script:

[الصق السكريبت هنا - بالإنجليزي أو بالعربي، وسيحوّله النموذج للإنجليزي ويعرضه عليك للموافقة]

Do the whole pipeline and log progress in projects/<name>/STATUS.md after every step.
Only stop to ask me for things you cannot do yourself. At the end give me out/<name>/final.mp4.
---

## To continue an unfinished short / لإكمال فيديو لم يكتمل
```
Read AGENTS.md, then projects/<short_name>/STATUS.md, and continue from the first unchecked step.
```
