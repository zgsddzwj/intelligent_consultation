"""打包云端训练所需文件 → finetune/ft_cloud.zip

上传到 AutoDL 实例后解压即得标准目录结构（configs/ + data/ + eval/），
训练 YAML、评测脚本无需任何修改即可运行。

用法：python deploy/pack_for_cloud.py
"""
import sys
import zipfile
from pathlib import Path

FINETUNE_DIR = Path(__file__).resolve().parents[1]
OUT_ZIP = FINETUNE_DIR / "ft_cloud.zip"


def main() -> int:
    data_dir = FINETUNE_DIR / "data"
    train_file = data_dir / "sft_train.jsonl"
    if not train_file.exists():
        print("错误：data/sft_train.jsonl 不存在。")
        print("请先在本地完成全量数据生成与合并：")
        print("  python data_gen/validate_data.py --merge")
        return 1

    files = [
        train_file,
        *sorted((data_dir / "eval").glob("*.json")),
        *sorted((FINETUNE_DIR / "configs").glob("*.yaml")),
        FINETUNE_DIR / "configs" / "dataset_info.json",
        *sorted((FINETUNE_DIR / "data_gen").glob("*.py")),
        FINETUNE_DIR / "eval" / "run_eval.py",
    ]
    files = [f for f in files if f.exists()]

    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, f.relative_to(FINETUNE_DIR))

    size_mb = OUT_ZIP.stat().st_size / 1024 / 1024
    print(f"打包 {len(files)} 个文件（{size_mb:.1f} MB）→ {OUT_ZIP}")
    print("上传到 AutoDL 后：unzip ft_cloud.zip -d /root/autodl-tmp/medical-ft")
    return 0


if __name__ == "__main__":
    sys.exit(main())
