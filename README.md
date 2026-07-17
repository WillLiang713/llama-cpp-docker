# Qwythos-9B-Claude-Mythos-5-1M-GGUF Docker 部署

## 模型信息

- 模型：`Qwythos-9B-Claude-Mythos-5-1M-Q4_K_M.gguf`
- 视觉投影：`mmproj-Qwythos-9B-Claude-Mythos-5-1M-F16.gguf`
- 来源：<https://huggingface.co/empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF>
- 运行服务：`llama.cpp` CUDA server

## 下载模型

安装 Hugging Face 下载器和 Xet 高性能传输组件：

```bash
python -m pip install -r requirements.txt
```

开始下载：

```bash
python download_model.py
```

下载内容保存到：

```text
models/Qwythos-9B-Claude-Mythos-5-1M-Q4_K_M/
├── Qwythos-9B-Claude-Mythos-5-1M-Q4_K_M.gguf
└── mmproj-Qwythos-9B-Claude-Mythos-5-1M-F16.gguf
```

脚本调用 `hf_hub_download()`，默认 **Xet 高性能 + 32 并发 + 多文件并行**。

**断点续传：** 上游 hub 会用随机 `.incomplete` 且失败即删。本脚本打补丁：固定 etag 临时文件、失败保留；有 partial 时用 HTTP Range 续传，否则走 Xet（并开启块缓存）。`Ctrl+C` 后重跑同一命令即可续。

```bash
# 默认下载
python download_model.py

# 串行 / 关高性能 / 调并发
python download_model.py --no-parallel --no-high-performance --connections 16

# 国内镜像
python download_model.py --endpoint https://hf-mirror.com

# HTTP 字节续传（更稳，通常更慢）
python download_model.py --http-only

# 只下某个文件
python download_model.py --filename mmproj-Qwythos-9B-Claude-Mythos-5-1M-F16.gguf

# Token（提高限额）
set HF_TOKEN=hf_xxx
python download_model.py
```

## 启动服务

确认模型下载完成后运行：

```bash
docker compose up -d
```

服务地址：<http://localhost:8787>

查看运行日志：

```bash
docker compose logs -f
```

> 模型名称中的 `1M` 表示其支持的最大上下文能力，并不代表启动时必须直接分配 1M token。Compose 当前保留 `262144` 上下文设置，避免一开始占用过多显存；可按硬件情况调整 `LLAMA_ARG_CTX_SIZE`。
