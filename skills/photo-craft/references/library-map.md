# 主题路由：你的问题 → 查哪个知识模块

**用法**：先在本表按主题定位 1-3 个知识模块并读它们，得到**可执行的方法与判断**；
需要**原文出处**时，再到**你自己的摄影书库**里检索（见 §三 与 `corpus/tools.py`）。

本表是"哪类问题归哪个模块"的路由表。**出处引用一律以实际检索结果为准**，
不得凭记忆编造书名或页码。

---

## 一、按主题速查（最常用）

| 你要解决的问题 | 查这些模块 |
|---|---|
| **曝光的原理、测光、对焦、相机操作** | `foundation-basics.md`；速查 `knowledge/20-foundation.md` |
| **人像整体打法、镜头器材、实拍思路** | `portrait-pose.md`；速查 `knowledge/21-portrait-pose.md` |
| **摆姿／美姿** | `portrait-pose.md`（摆姿几何、口令库）；速查 `knowledge/21-portrait-pose.md` |
| **用光原理与光位** | `lighting-flash.md`；速查 `knowledge/22-lighting-flash.md` |
| **热靴闪光灯／离机闪／压光** | `lighting-flash.md`（热靴与压光章节） |
| **构图与视觉设计** | `composition-vision.md`；速查 `knowledge/23-composition-vision.md` |
| **后期修图／磨皮／调色** | `post-color.md`；速查 `knowledge/24-post-color.md` |
| **商品／静物／商业接单** | `commercial-still.md`；速查 `knowledge/25-26-commercial-wedding-children.md` |
| **婚礼跟拍** | `wedding-children.md`；速查 `knowledge/25-26-commercial-wedding-children.md` |
| **儿童摄影** | `wedding-children.md`（儿童章节） |
| **风光摄影／纪实** | `composition-vision.md` + `vision-theory.md` |
| **审美、观念、怎么看照片** | `vision-theory.md`；速查 `knowledge/27-vision-theory.md` |
| **创作方法、个人风格、思路** | `vision-theory.md` + `workflow-sops.md` |
| **拍摄流程、方案、器材清单、应急** | `workflow-sops.md`；速查 `knowledge/28-workflow-sops.md` |

---

## 二、两个层次，两种读法

| 层次 | 位置 | 什么时候用 |
|---|---|---|
| **速查地图** | `knowledge/*.md` | 先读。地图与清单，快速判断"该往哪走" |
| **完整模块** | `references/*.md` | 需要细节、要落地成动作时读 |
| **原文出处** | 你自己的书库 + `corpus/tools.py` | 只有用户明确要"出处／原文"时才走 |

多数真实问题跨 2-3 个模块（例："夜景人像怎么拍" = 用光 + 基础参数 + 后期 + 引导）。
先读主模块，再按需补读。

---

## 三、原文检索与出处（可选层）

**本插件不含任何图书正文。** 检索层需要**用户自己准备的书库**：
把你**合法获得**的摄影书 PDF 放进一个目录，用 `corpus/extract_gpu.py` 抽取成文本，
再用 `corpus/tools.py` 检索。详见 `corpus/BUILD.md`。

```bash
cd <本技能目录>/corpus
python tools.py status                  # 库是否可用
python tools.py list                    # 已抽取的书目状态
python tools.py search "眼神光"          # 全库检索：书名 + p页码 + 原文上下文
python tools.py search "压光" --book <关键词>   # 限定单本
python tools.py read <书号> <起页> <止页>       # 取某本某页原文
```

书号 = 文件名的前导序号，也是 `tools.py` 的检索键，由**你自己的书库目录顺序**决定。

**若没有自建书库**：插件的技法能力（`references/` + `knowledge/`）完全不受影响，
照常给可执行方案；只是**不能给"书名 + 页码"级别的原文出处**——这时要明确说明，
不要编造。

---

## 四、引用格式（回答中给出处时）

```
《书名》 p87：
「……（原文摘录）……」
```

规则：

1. **页码必须是检索／读取得到的真实页码**，不得推测。
   **绝不凭记忆写页码**——记忆里的页码几乎一定是错的。
2. **书名也须来自检索结果**，不要凭印象写"大概是某本书"。
3. 摘录保持原文用词（OCR 可能有少量错字，若影响理解应说明"原文 OCR 此处为…"）。
4. 只给 1-2 条最相关的出处，不做书单堆砌。
5. 若检索不到可靠出处，**明说"库内未检索到"**，再给通用专业建议——
   **不要为了显得有据而编造书名页码**。
6. 用户未自建书库时，直接说明"本插件不含图书正文，无法给出原文出处"，
   给方法论层面的专业建议即可。
