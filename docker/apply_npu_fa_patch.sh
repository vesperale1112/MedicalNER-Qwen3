#!/usr/bin/env bash
# 把昇腾 FlashAttention patch 安装进当前 Python 环境里 pip 装好的 llamafactory。
#
# 做两件事：
#   1. 把 npu_flash_attn.py 拷到 llamafactory/model/model_utils/ 下
#   2. 在 llamafactory/model/loader.py 的 load_model() 里，patch_config(...) 之后
#      插入 from-import 和 patch_npu_flash_attn() 调用
#
# 幂等：第二次运行不会重复插入。
set -euo pipefail

PATCH_SRC="${PATCH_SRC:-/opt/ascend_patch/npu_flash_attn.py}"

if [[ ! -f "${PATCH_SRC}" ]]; then
    echo "[apply_npu_fa_patch] ERROR: ${PATCH_SRC} not found." >&2
    echo "[apply_npu_fa_patch] Copy /aistor/sjtu/hpc_stor01/public/ascend_patch/npu_flash_attn.py into docker/ before building," >&2
    echo "[apply_npu_fa_patch] or use scripts/build_medicalner_qwen3_npu_image.sh which does it for you." >&2
    exit 1
fi

LF_DIR="$(python3 -c 'import importlib.util, pathlib, sys; s=importlib.util.find_spec("llamafactory"); sys.exit(1) if s is None else print(pathlib.Path(s.origin).parent)')"
if [[ -z "${LF_DIR}" ]]; then
    echo "[apply_npu_fa_patch] ERROR: llamafactory not importable. Install it first." >&2
    exit 1
fi
echo "[apply_npu_fa_patch] llamafactory at: ${LF_DIR}"

MU_DIR="${LF_DIR}/model/model_utils"
LOADER_PY="${LF_DIR}/model/loader.py"
if [[ ! -d "${MU_DIR}" ]]; then
    echo "[apply_npu_fa_patch] ERROR: ${MU_DIR} not found (unexpected llamafactory layout)." >&2
    exit 1
fi
if [[ ! -f "${LOADER_PY}" ]]; then
    echo "[apply_npu_fa_patch] ERROR: ${LOADER_PY} not found." >&2
    exit 1
fi

cp "${PATCH_SRC}" "${MU_DIR}/npu_flash_attn.py"
echo "[apply_npu_fa_patch] copied patch -> ${MU_DIR}/npu_flash_attn.py"

python3 - "${LOADER_PY}" <<'PY'
import io, re, sys
from pathlib import Path

loader = Path(sys.argv[1])
src = loader.read_text(encoding="utf-8")

import_line = "from .model_utils.npu_flash_attn import patch_npu_flash_attn"
call_line = "    patch_npu_flash_attn()"

already_imported = import_line in src
already_called = "patch_npu_flash_attn()" in src

if already_imported and already_called:
    print("[apply_npu_fa_patch] loader.py already patched, skip.")
    sys.exit(0)

if not already_imported:
    # 插入 import：放在第一个 from .model_utils 开头的 import 之后；
    # 如果找不到，就放在所有 from . import 之后。
    m = re.search(r"^from \.model_utils[^\n]*\n", src, flags=re.MULTILINE)
    if m:
        src = src[:m.end()] + import_line + "\n" + src[m.end():]
    else:
        m = re.search(r"(^from \.[^\n]*\n)+", src, flags=re.MULTILINE)
        if not m:
            print("[apply_npu_fa_patch] ERROR: cannot locate import block in loader.py", file=sys.stderr)
            sys.exit(2)
        src = src[:m.end()] + import_line + "\n" + src[m.end():]

if not already_called:
    # 在 load_model 内部找 patch_config(...) 调用并在它后面插入 patch_npu_flash_attn()
    pattern = re.compile(
        r"^([ \t]+)patch_config\([^\n]*\)\n",
        flags=re.MULTILINE,
    )
    m = pattern.search(src)
    if not m:
        print("[apply_npu_fa_patch] ERROR: cannot find patch_config(...) call in loader.py", file=sys.stderr)
        sys.exit(3)
    indent = m.group(1)
    insertion = f"{indent}patch_npu_flash_attn()\n"
    src = src[:m.end()] + insertion + src[m.end():]

loader.write_text(src, encoding="utf-8")
print(f"[apply_npu_fa_patch] patched: {loader}")
PY

python3 -c "from llamafactory.model.model_utils.npu_flash_attn import patch_npu_flash_attn; print('[apply_npu_fa_patch] import OK:', patch_npu_flash_attn)"
echo "[apply_npu_fa_patch] done."
