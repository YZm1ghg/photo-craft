---
description: 查自备书库的原文，给出书名 + 页码 + 摘录
argument-hint: "[关键词，例如：蝴蝶光 / 眼神光 / 报价]"
skills: photo-craft
---

在 `photo-craft` 技能的语料库里检索原文，关键词：

$ARGUMENTS

执行步骤（语料目录 = `<photo-craft 技能目录>/corpus`）：

1. 先看 `references/library-map.md` 或 `python tools.py list`，判断哪几本书最可能讲这个
2. 检索：
   ```bash
   python tools.py search "$ARGUMENTS" --top 20
   ```
   必要时限定单本：`python tools.py search "$ARGUMENTS" --book <书名子串或书号>`
3. 对最相关的命中，用 `python tools.py read <书号> <起页> <止页>` 取完整段落
4. 回答里给 **《书名》 p页码** + **原文摘录**（1-2 条最相关的，不堆书单）

**铁律**：
- 页码必须来自实际检索结果，**绝不推测**
- 检索不到就说"库内未检索到"，再给通用专业建议——**宁可说没有，不可编造出处**
- OCR 有少量错字，若影响理解要说明"原文 OCR 此处为…"
