# Qwen3-Coder-Next-GGUF Q4_K_M 模型下载指南

## 模型信息

- **模型**: Qwen3-Coder-Next-GGUF Q4_K_M
- **来源**: <https://modelscope.cn/models/Qwen/Qwen3-Coder-Next-GGUF/tree/master/Q4_K_M>
- **文件列表**:

| 文件名 | 大小 |
|--------|------|
| Qwen3-Coder-Next-Q4_K_M-00001-of-00004.gguf | 15.5 GB |
| Qwen3-Coder-Next-Q4_K_M-00002-of-00004.gguf | 14.9 GB |
| Qwen3-Coder-Next-Q4_K_M-00003-of-00004.gguf | 14.5 GB |
| Qwen3-Coder-Next-Q4_K_M-00004-of-00004.gguf | 3.5 GB |

- **总大小**: ~48.4 GB

## 下载方式

### 方式一：ModelScope CLI（推荐）

安装 CLI 工具：

```bash
pip install modelscope
```

下载 Q4_K_M 模型到 models 目录：

```bash
modelscope download --model Qwen/Qwen3-Coder-Next-GGUF --include "Q4_K_M/*" --local_dir ./models/Qwen3-Coder-Next-Q4_K_M
```

### 方式二：Git LFS

```bash
git lfs install
git clone --depth 1 --filter=blob:none --sparse https://www.modelscope.cn/Qwen/Qwen3-Coder-Next-GGUF.git
cd Qwen3-Coder-Next-GGUF
git sparse-checkout set Q4_K_M
git lfs pull --include="Q4_K_M/*"
```

### 方式三：HuggingFace CLI

```bash
huggingface-cli download Qwen/Qwen3-Coder-Next-GGUF --include "Q4_K_M/*" --local-dir ./models/Qwen3-Coder-Next-Q4_K_M
```

## 注意事项

下载完成后，确保 4 个 `.gguf` 文件放在 `./models/Qwen3-Coder-Next-Q4_K_M/` 子目录下。

文件结构应为：

```
models/
└── Qwen3-Coder-Next-Q4_K_M/
    ├── Qwen3-Coder-Next-Q4_K_M-00001-of-00004.gguf
    ├── Qwen3-Coder-Next-Q4_K_M-00002-of-00004.gguf
    ├── Qwen3-Coder-Next-Q4_K_M-00003-of-00004.gguf
    └── Qwen3-Coder-Next-Q4_K_M-00004-of-00004.gguf
```

## 启动服务

```bash
docker compose up
```
