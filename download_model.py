"""下载 GGUF：Xet 加速 + 稳定断点续传（修 huggingface_hub 随机 incomplete 问题）。"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DEFAULT_REPO = "empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF"
DEFAULT_FILES = (
    "Qwythos-9B-Claude-Mythos-5-1M-Q4_K_M.gguf",
    "mmproj-Qwythos-9B-Claude-Mythos-5-1M-F16.gguf",
)
DEFAULT_LOCAL_DIR = "./models/Qwythos-9B-Claude-Mythos-5-1M-Q4_K_M"
DEFAULT_CONNECTIONS = 32
# 官方默认块缓存为 0，中断后 Xet 无法续；给 50GiB。
DEFAULT_XET_CHUNK_CACHE = 50 * 1024**3

_PATCHED = False


def parse_args() -> argparse.Namespace:
    env_n = os.environ.get("HF_XET_NUM_CONCURRENT_RANGE_GETS")
    p = argparse.ArgumentParser(description="下载 Hugging Face GGUF 模型")
    p.add_argument("--repo", default=DEFAULT_REPO)
    p.add_argument(
        "--filename",
        dest="filenames",
        action="append",
        help="指定文件，可重复；默认主模型 + mmproj",
    )
    p.add_argument("--local-dir", default=DEFAULT_LOCAL_DIR)
    p.add_argument(
        "--connections",
        type=int,
        default=int(env_n) if env_n else DEFAULT_CONNECTIONS,
        help=f"Xet 每文件并发（默认 {DEFAULT_CONNECTIONS}）",
    )
    p.add_argument(
        "--high-performance",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Xet 高性能模式（默认开）",
    )
    p.add_argument(
        "--parallel",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="多文件并行下载（默认开）",
    )
    p.add_argument(
        "--endpoint",
        default=os.environ.get("HF_ENDPOINT"),
        help="Hub 端点，如 https://hf-mirror.com",
    )
    p.add_argument(
        "--http-only",
        action="store_true",
        help="禁用 Xet，用 HTTP Range 字节续传（更稳，通常更慢）",
    )
    p.add_argument("--token", default=os.environ.get("HF_TOKEN"))
    p.add_argument(
        "--max-retries",
        type=int,
        default=0,
        help="失败重试次数；0=一直重试",
    )
    p.add_argument("--retry-delay", type=int, default=5)
    return p.parse_args()


def format_size(n: float | int) -> str:
    x = float(n)
    for u in ("B", "KiB", "MiB", "GiB", "TiB"):
        if x < 1024 or u == "TiB":
            return f"{x:.2f} {u}"
        x /= 1024
    return f"{n} B"


def setup_env(
    *,
    connections: int,
    high_performance: bool,
    http_only: bool,
    endpoint: str | None,
) -> None:
    """须在 import huggingface_hub 之前调用。"""
    if endpoint:
        os.environ["HF_ENDPOINT"] = endpoint.rstrip("/")
    os.environ["HF_XET_NUM_CONCURRENT_RANGE_GETS"] = str(connections)
    os.environ["HF_XET_HIGH_PERFORMANCE"] = (
        "1" if high_performance and not http_only else "0"
    )
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "120")
    if http_only:
        os.environ["HF_HUB_DISABLE_XET"] = "1"
    else:
        os.environ.pop("HF_HUB_DISABLE_XET", None)
        os.environ.setdefault(
            "HF_XET_CHUNK_CACHE_SIZE_BYTES", str(DEFAULT_XET_CHUNK_CACHE)
        )


def install_resume_patch() -> None:
    """固定 incomplete 路径，失败不删；HTTP 支持 Range 续传。"""
    global _PATCHED
    if _PATCHED:
        return

    from huggingface_hub import constants, file_download
    from huggingface_hub.file_download import (
        _check_disk_space,
        _chmod_and_move,
        http_get,
        xet_get,
    )
    from huggingface_hub.utils._runtime import is_xet_available

    log = logging.getLogger("huggingface_hub.file_download")

    def _download_to_tmp_and_move(
        incomplete_path: Path,
        destination_path: Path,
        url_to_download: str,
        headers: dict,
        expected_size: int | None,
        filename: str,
        force_download: bool,
        etag: str | None,
        xet_file_data,
        tqdm_class=None,
    ) -> None:
        if destination_path.exists() and not force_download:
            return

        tmp = incomplete_path
        _promote_uuid_incomplete(tmp)

        resume = 0
        if force_download and tmp.exists():
            tmp.unlink(missing_ok=True)
        elif tmp.exists():
            resume = tmp.stat().st_size
            if expected_size is not None and resume > expected_size:
                tmp.unlink(missing_ok=True)
                resume = 0
            elif expected_size is not None and resume == expected_size:
                _chmod_and_move(tmp, destination_path)
                return
            elif resume > 0:
                print(
                    f"续传 {tmp.name}: {format_size(resume)}"
                    + (f" / {format_size(expected_size)}" if expected_size else ""),
                    flush=True,
                )

        if expected_size is not None:
            _check_disk_space(expected_size, tmp.parent)
            _check_disk_space(expected_size, destination_path.parent)

        use_xet = (
            xet_file_data is not None
            and is_xet_available()
            and not constants.HF_HUB_DISABLE_XET
        )
        # Xet 会重建文件，无法在已有 incomplete 上字节追加；有进度时改 HTTP Range
        if use_xet and resume > 0:
            print(
                f"已有 {format_size(resume)}，用 HTTP Range 续传（避免 Xet 重写）。",
                flush=True,
            )
            use_xet = False

        try:
            if use_xet:
                xet_get(
                    incomplete_path=tmp,
                    xet_file_data=xet_file_data,
                    headers=headers,
                    expected_size=expected_size,
                    displayed_filename=filename,
                    tqdm_class=tqdm_class,
                )
            else:
                mode = "ab" if resume > 0 else "wb"
                with tmp.open(mode) as f:
                    http_get(
                        url_to_download,
                        f,
                        resume_size=resume,
                        headers=headers,
                        expected_size=expected_size,
                        displayed_filename=filename,
                        tqdm_class=tqdm_class,
                    )
            log.debug("Download complete → %s", destination_path)
            _chmod_and_move(tmp, destination_path)
        except BaseException:
            # 关键：不要像上游一样 unlink incomplete
            if tmp.exists():
                print(
                    f"中断，已保留 {tmp.name}（{format_size(tmp.stat().st_size)}），"
                    "重跑同一命令可续传。",
                    flush=True,
                )
            raise

    file_download._download_to_tmp_and_move = _download_to_tmp_and_move
    _PATCHED = True


def _promote_uuid_incomplete(stable: Path) -> None:
    """把旧版 {etag}.{uuid8}.incomplete 提升为稳定名。"""
    if not stable.parent.is_dir():
        return
    stem = stable.name[: -len(".incomplete")]
    best: tuple[int, Path] | None = None
    for path in stable.parent.glob(f"{stem}.*.incomplete"):
        extra = path.name[len(stem) + 1 : -len(".incomplete")]
        if len(extra) != 8 or any(c not in "0123456789abcdef" for c in extra.lower()):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if best is None or size > best[0]:
            best = (size, path)
    if not best or best[0] <= 0:
        return
    size, path = best
    try:
        cur = stable.stat().st_size if stable.exists() else 0
    except OSError:
        cur = 0
    if size <= cur:
        return
    stable.unlink(missing_ok=True)
    path.replace(stable)
    print(f"恢复进度: {path.name} → {stable.name} ({format_size(size)})", flush=True)


def is_permanent(err: BaseException) -> bool:
    msg = f"{type(err).__name__}: {err}"
    return any(
        s in msg
        for s in (
            "EntryNotFoundError",
            "RepositoryNotFoundError",
            "GatedRepoError",
            "RevisionNotFoundError",
            "401 Client Error",
            "403 Client Error",
        )
    )


def download_one(
    repo: str,
    filename: str,
    local_dir: Path,
    token: str | None,
    max_retries: int,
    retry_delay: int,
) -> Path:
    from huggingface_hub import hf_hub_download

    install_resume_patch()
    attempt = 0
    while max_retries == 0 or attempt < max_retries:
        attempt += 1
        print(f"\n[{filename}] 第 {attempt} 次下载…", flush=True)
        try:
            path = Path(
                hf_hub_download(
                    repo_id=repo,
                    filename=filename,
                    repo_type="model",
                    local_dir=str(local_dir),
                    token=token,
                )
            )
            print(
                f"[{filename}] 完成 {path} ({format_size(path.stat().st_size)})",
                flush=True,
            )
            return path
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"[{filename}] 错误: {type(e).__name__}: {e}", flush=True)
            if is_permanent(e):
                raise
            if max_retries and attempt >= max_retries:
                raise
            print(f"[{filename}] {retry_delay}s 后重试…", flush=True)
            time.sleep(retry_delay)
    raise RuntimeError(f"下载失败: {filename}")


def main() -> int:
    args = parse_args()
    if args.connections <= 0 or args.retry_delay < 0 or args.max_retries < 0:
        print("参数错误: connections 须 >0，retry 相关不能为负", file=sys.stderr)
        return 2

    setup_env(
        connections=args.connections,
        high_performance=args.high_performance,
        http_only=args.http_only,
        endpoint=args.endpoint,
    )

    try:
        import huggingface_hub  # noqa: F401
    except ImportError:
        print("请先安装: pip install -U huggingface_hub hf_xet", file=sys.stderr)
        return 1

    local_dir = Path(args.local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)
    files = list(dict.fromkeys(args.filenames or DEFAULT_FILES))  # 去重保序
    endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")

    print("=" * 60)
    print(f"Hub: {endpoint}/{args.repo}")
    print(f"目录: {local_dir}")
    print(f"文件: {', '.join(files)}")
    print(
        f"模式: {'HTTP only' if args.http_only else 'Xet'}"
        f" | 并发={args.connections}"
        f" | 高性能={os.environ.get('HF_XET_HIGH_PERFORMANCE')}"
        f" | {'并行' if args.parallel and len(files) > 1 else '串行'}"
    )
    print("=" * 60)

    paths: list[Path] = []
    try:
        if args.parallel and len(files) > 1:
            with ThreadPoolExecutor(max_workers=len(files)) as pool:
                futs = {
                    pool.submit(
                        download_one,
                        args.repo,
                        name,
                        local_dir,
                        args.token,
                        args.max_retries,
                        args.retry_delay,
                    ): name
                    for name in files
                }
                results: dict[str, Path] = {}
                for fut in as_completed(futs):
                    results[futs[fut]] = fut.result()
            paths = [results[n] for n in files]
        else:
            for name in files:
                paths.append(
                    download_one(
                        args.repo,
                        name,
                        local_dir,
                        args.token,
                        args.max_retries,
                        args.retry_delay,
                    )
                )
    except KeyboardInterrupt:
        print("\n用户中断；进度已保留，重跑同一命令可续传。", flush=True)
        return 130
    except Exception as e:
        print(f"失败: {e}", file=sys.stderr)
        return 1

    print("\ndocker-compose 路径:")
    models_root = Path("./models").resolve()
    for path in paths:
        try:
            rel = path.resolve().relative_to(models_root)
            key = (
                "LLAMA_ARG_MMPROJ"
                if path.name.startswith("mmproj-")
                else "LLAMA_ARG_MODEL"
            )
            print(f"  {key}: /models/{rel.as_posix()}")
        except ValueError:
            print(f"  (不在 ./models 下) {path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
