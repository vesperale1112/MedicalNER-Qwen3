#!/usr/bin/env bash
# 提交一个超小 vc job，从 compute 节点视角看 /opt 和 sys.path
# 用法（在调试机 host 上）：bash temp_vc_diag.sh
set -euo pipefail

PROJECT_DIR=/aistor/sjtu/hpc_stor01/home/wangxiran/projects/MedicalNER-Qwen3
mkdir -p "${PROJECT_DIR}/logs"

# 把诊断脚本写到共享存储（vc 任务容器能读到）
cat >"${PROJECT_DIR}/scripts/_compute_node_diag.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
echo "===== hostname / whoami / pwd ====="
hostname
whoami
id
pwd
echo
echo "===== mount | grep -E 'opt|LLaMA' ====="
mount | grep -E "opt|LLaMA" || echo "(no /opt or LLaMA-related mount)"
echo
echo "===== ls /opt ====="
ls -la /opt 2>/dev/null || echo "(no /opt)"
echo
echo "===== ls /opt/LLaMA-Factory ====="
ls -la /opt/LLaMA-Factory 2>/dev/null || echo "(no /opt/LLaMA-Factory)"
echo
echo "===== stat /opt/LLaMA-Factory/src/llamafactory ====="
stat /opt/LLaMA-Factory/src/llamafactory 2>/dev/null || echo "(no)"
echo
echo "===== env (PYTHONPATH / PATH / LD_LIBRARY_PATH) ====="
echo "PYTHONPATH=${PYTHONPATH:-<unset>}"
echo "PATH=${PATH:-<unset>}"
echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-<unset>}"
echo
echo "===== site-packages .pth 里有没有 LLaMA-Factory ====="
grep -l -r "LLaMA-Factory\|llamafactory" \
    /usr/local/python3.10.15/lib/python3.10/site-packages/*.pth 2>/dev/null \
    | while read f; do
        echo "--- $f ---"
        cat "$f"
    done || echo "(none)"
echo
echo "===== python 视角：llamafactory.__file__ + sys.path ====="
python3 - <<'PY'
import sys, importlib, pathlib
print("python:", sys.executable)
print("\n--- sys.path ---")
for p in sys.path:
    print(" ", p)
print("\n--- llamafactory ---")
import llamafactory
print("llamafactory.__file__:", llamafactory.__file__)
print("\n--- /opt/LLaMA-Factory tree (first 2 levels) ---")
root = pathlib.Path("/opt/LLaMA-Factory")
if root.exists():
    for p in sorted(root.rglob("*"))[:30]:
        print(" ", p)
else:
    print("  (/opt/LLaMA-Factory does NOT exist)")
PY
SH
chmod +x "${PROJECT_DIR}/scripts/_compute_node_diag.sh"

# 提交：1 NPU 最小资源、几秒就退、日志落到共享存储
vc submit \
    -p pdgpu-sjtu-ai \
    -i hub.szaic.com/sjtu/sjtu_wumengyue-xiranwang-medicalner-qwen3:v1.0 \
    -g 1 -c 20 -m 120G \
    -e "PROJECT_DIR=${PROJECT_DIR}" \
    JOB=1:1 "${PROJECT_DIR}/logs/compute_diag.JOB.log" \
    --cmd "bash ${PROJECT_DIR}/scripts/_compute_node_diag.sh"

cat <<EOF

已提交。等 ~30 秒后看日志：
  vc list
  tail -n +1 ${PROJECT_DIR}/logs/compute_diag.1.log
EOF
