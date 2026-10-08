# 自建语料：把图书 PDF 变成可检索文本

本目录是**检索工具**，**不含任何图书正文**。要使用"原文出处"功能，
你需要把**自己合法获得**的摄影书 PDF 抽取成文本。

`out/` 是构建产物（`txt/` 正文、`meta/` 统计、`cards/` 卡片、`done/` 完成标记、
`index.json` 索引），由你自己的书库生成，**不属于本插件的发布内容**。

> 本插件只分发**原创提炼笔记 + 工具脚本**。请只对你依法持有的书籍运行本流程，
> 并遵守当地著作权法律。

---

## 〇、指定你的书库

```bash
export PHOTO_BOOKS_DIR="/path/to/your/photography/books"   # 放 PDF 的目录
# 或者写 corpus/config.json：{"books_dir": "/path/to/your/books"}
```

没有内置默认路径，必须由你指定。`extract_gpu.py` 会在缺失时直接报错退出。

---

## 一、为什么需要这一步

多数摄影书是**扫描件**（每页是图片，文字不是文本层），必须 OCR 才能检索。
少数是**原生文字层** PDF，可以直接抽文本——脚本会自动探测并走不同分支。

---

## 二、关键：必须用 GPU，否则慢到不可用

| 方式 | 单页耗时 | 全库预计 |
|---|---|---|
| CPU（RapidOCR 默认） | **75–167 秒** | **数天** |
| **GPU（RTX 4060 + CUDA）** | **2.5–6 秒** | **数小时** |

差距 30–60 倍。CPU 路径在实践中不可用，务必先让 GPU 生效。

### 让 GPU 真正生效的三个坑（都踩过）

1. **`onnxruntime` 必须是 GPU 版**。普通的 `pip install onnxruntime` 是 **CPU-only**，
   `CUDAExecutionProvider` 根本没编译进去——`get_available_providers()` 里看不到它。
   必须装 `onnxruntime-gpu`。
   注意：`rapidocr-onnxruntime` 依赖会**把它换成 CPU 版**，所以装完 rapidocr 后
   要**最后再重装一次 `onnxruntime-gpu --no-deps --force-reinstall`**。

2. **CUDA/cuDNN 运行时不在 PATH 上**。装 `nvidia-cudnn-cu12` / `nvidia-cublas-cu12` /
   `nvidia-cuda-runtime-cu12` 等 wheel 后，要在**导入 onnxruntime 之前**把它们的
   `bin` 目录注册进 DLL 搜索路径（`extract_gpu.py` 已经内置这段）：
   ```python
   import nvidia, os
   base = os.path.dirname(nvidia.__file__)
   for sub in os.listdir(base):
       for leaf in ("bin", "lib"):
           d = os.path.join(base, sub, leaf)
           if os.path.isdir(d):
               os.add_dll_directory(d)
               os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]
   ```

3. **网络代理会打断 pip**。企业代理或本地代理会破坏 TLS
   （`SSL: WRONG_VERSION_NUMBER`）。**换用镜像源并绕过代理**：
   ```bash
   pip install --proxy "" -i https://pypi.tuna.tsinghua.edu.cn/simple/ onnxruntime-gpu
   ```

### 独立环境

建议把 GPU 依赖装在独立 venv，避免污染系统 Python；同时也能隔离
`onnxruntime` 的 CPU/GPU 版本冲突。

---

## 三、其他踩过的坑（通用工程教训）

- **进程池整批崩溃**：`ProcessPoolExecutor` 一个 worker 异常会连带 `BrokenProcessPool`
  让整批失败。→ 改为**单进程顺序抽取 + 每本完成即落盘**，天然断点续跑。
- **VRAM 争用**：显存被浏览器／壁纸／其他 GPU 应用占满时，OCR 会退化成十几秒每页。
  → 跑之前先释放显存，必要时关闭占用 GPU 的程序。
- **"原生文字层"误判**：有些书前几页有**薄文字层**（只有封面版权页有字），
  会被探测判为 native 而**跳过 OCR**，结果只抽到几千字。
  → 抽完必须**按字符数校验**，低于阈值的一律重新强制 OCR。
- **不要用 `signal.SIGALRM` 做超时**：Windows 没有这个信号，会让每页都抛异常。
- **OCR 慢与分辨率无关**：降 DPI 几乎不提速（字符数不变），瓶颈是**逐行识别**的开销。

---

## 四、重建命令

```bash
cd <photo-craft 技能目录>/corpus

# 1) 抽取（自动跳过已完成的，断点续跑）
python extract_gpu.py

# 2) 重建索引与卡片
python tools.py index
python make_cards.py
python tools.py status
```

抽取脚本就是本目录的 `extract_gpu.py`
（页面标记 `<<<Page n>>>`，`out/done/<slug>` 为完成标记，`chars<200` 不标记完成）。

---

## 五、质量校验

抽完必须自查，**不要相信"跑完了"就等于"抽到了"**：

| 指标 | 怎么看 |
|---|---|
| 完成度 | `python tools.py status`（缺哪些书号会列出来） |
| 字符数 | 明显偏低的书 = 可疑，强制重抽 |
| OCR 置信度 | `meta/*.json` 的 `mean_conf`；图多字少的画册天然偏低，属正常 |
| 目录页 | `index.json` 的 `toc` 字段，用来判断章节定位是否可用 |

**注意**：OCR 有少量错字（尤其繁体与竖排），引用时如遇影响理解的错字，应说明
"原文 OCR 此处为…"，不要当成原文用词。
