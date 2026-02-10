# Qwen3-Coder-Next-GGUF Docker 部署

## 模型信息

- **模型**: Qwen3-Coder-Next-GGUF Q4_K_M
- **来源**: <https://modelscope.cn/models/unsloth/Qwen3-Coder-Next-GGUF>
- **量化**: Q4_K_M（~48.4 GB）

## 下载方式

### 方式一：下载脚本（推荐）

安装依赖：

```bash
pip install modelscope setuptools
```

默认下载 unsloth 版 Q4_K_M：

```bash
python download_model.py
```

自定义模型和量化类型：

```bash
# 下载其他量化版本
python download_model.py --quant Q8_0

# 下载 Qwen 官方版
python download_model.py --model Qwen/Qwen3-Coder-Next-GGUF --quant Q4_K_M

# 指定保存目录
python download_model.py --local-dir ./models/my-model
```

下载完成后脚本会自动校验文件并打印 docker-compose 可用的模型路径。

### 方式二：ModelScope CLI

```bash
pip install modelscope
modelscope download --model unsloth/Qwen3-Coder-Next-GGUF --include "*Q4_K_M*" --local_dir ./models/Qwen3-Coder-Next-Q4_K_M
```

### 方式三：Git LFS

```bash
git lfs install
git clone --depth 1 --filter=blob:none --sparse https://www.modelscope.cn/unsloth/Qwen3-Coder-Next-GGUF.git
cd Qwen3-Coder-Next-GGUF
git sparse-checkout set "Qwen3-Coder-Next-Q4_K_M.gguf"
git lfs pull --include="Qwen3-Coder-Next-Q4_K_M.gguf/*"
```

## 注意事项

下载完成后，根据脚本输出的路径更新 `docker-compose.yml` 中的 `LLAMA_ARG_MODEL`。

不同来源的目录结构可能不同：

```
# unsloth 版
models/Qwen3-Coder-Next-Q4_K_M/
└── Qwen3-Coder-Next-Q4_K_M.gguf/
    ├── Qwen3-Coder-Next-Q4_K_M-00001-of-000XX.gguf
    └── ...

# Qwen 官方版
models/Qwen3-Coder-Next-Q4_K_M/
├── Qwen3-Coder-Next-Q4_K_M-00001-of-000XX.gguf
└── ...
```

## 启动服务

```bash
docker compose up
```

服务启动后访问 `http://localhost:8787` 即可使用。
