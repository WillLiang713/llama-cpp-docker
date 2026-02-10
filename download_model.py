"""
Qwen3-Coder-Next-GGUF 模型下载脚本

功能：
- 基于 ModelScope SDK 下载模型
- 支持命令行参数指定模型和量化类型
- 下载失败自动重试
- 下载完成后校验文件完整性
"""

import argparse
import os
import sys
import time
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="从 ModelScope 下载 GGUF 模型")
    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen3-Coder-Next-GGUF",
        help="ModelScope 模型 ID（默认: Qwen/Qwen3-Coder-Next-GGUF）",
    )
    parser.add_argument(
        "--quant",
        type=str,
        default="Q4_K_M",
        help="量化类型，如 Q4_K_M, Q8_0, Q5_K_M 等（默认: Q4_K_M）",
    )
    parser.add_argument(
        "--local-dir",
        type=str,
        default=None,
        help="本地保存目录（默认: ./models/<模型名>-<量化类型>）",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="下载失败最大重试次数（默认: 3）",
    )
    return parser.parse_args()


def download_model(model_id, quant, local_dir, max_retries):
    """下载模型，支持断点续传和失败重试"""
    try:
        from modelscope import snapshot_download
    except ImportError:
        print("错误: 请先安装 modelscope")
        print("  pip install modelscope setuptools")
        sys.exit(1)

    include_pattern = f"{quant}/*"
    print(f"模型: {model_id}")
    print(f"量化: {quant}")
    print(f"匹配: {include_pattern}")
    print(f"保存: {local_dir}")
    print(f"重试: 最多 {max_retries} 次")
    print("-" * 50)

    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n第 {attempt}/{max_retries} 次尝试下载...")
            snapshot_download(
                model_id=model_id,
                allow_patterns=[include_pattern],
                local_dir=local_dir,
                resume_download=True,
            )
            print("\n下载完成!")
            return True
        except KeyboardInterrupt:
            print("\n用户中断下载")
            sys.exit(1)
        except Exception as e:
            print(f"\n下载失败: {e}")
            if attempt < max_retries:
                wait = attempt * 10
                print(f"{wait} 秒后重试...")
                time.sleep(wait)
            else:
                print("已达最大重试次数，下载失败")
                return False


def verify_files(local_dir, quant):
    """校验下载的文件完整性"""
    print("\n" + "=" * 50)
    print("文件校验")
    print("=" * 50)

    quant_dir = Path(local_dir) / quant
    if not quant_dir.exists():
        print(f"错误: 目录不存在 {quant_dir}")
        return False

    gguf_files = sorted(quant_dir.glob("*.gguf"))
    if not gguf_files:
        print(f"错误: 未找到 .gguf 文件")
        return False

    print(f"找到 {len(gguf_files)} 个 .gguf 文件:\n")

    total_size = 0
    for f in gguf_files:
        size = f.stat().st_size
        total_size += size
        size_gb = size / (1024**3)
        print(f"  {f.name:<60} {size_gb:.2f} GB")

    total_gb = total_size / (1024**3)
    print(f"\n总大小: {total_gb:.2f} GB")

    # 检查分片文件命名是否连续
    split_files = [f for f in gguf_files if "-of-" in f.name]
    if split_files:
        last = split_files[-1].name
        total_parts = int(last.split("-of-")[1].split(".")[0])
        if len(split_files) == total_parts:
            print(f"分片校验: 通过 ({len(split_files)}/{total_parts})")
        else:
            print(f"分片校验: 失败 (期望 {total_parts} 个，实际 {len(split_files)} 个)")
            return False

    # 检查是否有空文件
    empty_files = [f for f in gguf_files if f.stat().st_size == 0]
    if empty_files:
        print(f"警告: 发现 {len(empty_files)} 个空文件:")
        for f in empty_files:
            print(f"  {f.name}")
        return False

    print("\n校验结果: 全部通过")
    return True


def main():
    args = parse_args()

    # 构建模型名称用于默认目录
    model_name = args.model.split("/")[-1].replace("-GGUF", "")
    dir_name = f"{model_name}-{args.quant}"

    local_dir = args.local_dir or os.path.join(".", "models", dir_name)

    success = download_model(args.model, args.quant, local_dir, args.max_retries)
    if success:
        verify_files(local_dir, args.quant)


if __name__ == "__main__":
    main()
