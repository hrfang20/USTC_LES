# 校园 001：关闭热力的初次试算

现有 geom.001.stl 已含 1090×1350 m 矩形地面。道路围合区为不规则研究区域，求解器使用规则长方体。建筑保留原位置，范围外延拓为无建筑平地；尚未补齐周边建筑。默认水平周期边界使该区域周期重复，并非独立校园的开放来流模拟。

配置模板 cases/001/namoptions.neutral.001：218×270×80、5 m 网格，2×2 MPI 分解（4 进程），关闭 ltempeq/lbuoyancy/lmoist/lEB，使用中性壁面 iwallmom=3；保留地转风 (8,0) m/s 与 Coriolis 设置。60 秒只用于启动和性能检查，不能作为统计稳态。原 cases/001 草案不被覆盖。

## 1. 本地准备并上传

```powershell
conda run -n turbpy python scripts/prepare_campus_neutral.py
scp outputs/campus_neutral_inputs.tar.gz <USER>@<LOGIN_HOST>:~/
```

如果已生成 staging 目录，脚本会拒绝覆盖，避免覆盖配置。所有实际账号、集群配置和路径均只在个人运行环境填写。

远程终端：

```bash
ROOT_RUN="$HOME/campus-neutral-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$ROOT_RUN"
tar -xzf "$HOME/campus_neutral_inputs.tar.gz" -C "$ROOT_RUN"
CASE="$ROOT_RUN/001"
```

## 2. 编译 IBM 前处理扩展

201 使用自带 IBM 文件，并未证明前处理扩展已编译。固定源码 f2py 构建含 GNU 参数，需要 GNU C/Fortran 编译器与 Python 开发头文件；它可与已验证的 Intel 求解器分开构建，因为交换的是输入文件。

在集群允许的编译节点：

```bash
module load <GNU_COMPILER_MODULE> <PYTHON_MODULE> <CMAKE_MODULE>
cd "<SOURCE_DIR>"
export CC=gcc
export FC=gfortran
export F77=gfortran
bash tools/python/setup_venv.sh common preprocessing_tools
source tools/python/.venv/bin/activate
python -c "from udprep import ibm_preproc_f2py; print('IBM OK')"
```

setup_venv 需安装 Python 包；无网络时使用集群镜像或准备匹配的离线包。不要把 Windows 的 vendor/python-deps 当作 Linux 环境。模块名需从实际 module avail 选择。若仅需检查已有环境，先运行 import 命令，无需重建。

## 3. 在计算节点生成 IBM 输入

前处理申请单节点 4 CPU；nompthreads=4 与申请一致。初次可申请 32 GB、1 小时，这是未实测的资源起点。以下命令应放进独立的前处理作业或交互计算会话，不在登录节点直接做大规模前处理：

```bash
export PREPROC_NCPU=4
export NUMBA_NUM_THREADS=4
export OMP_NUM_THREADS=4
set -o pipefail
"<SOURCE_DIR>/tools/python/.venv/bin/python" \
  "<SOURCE_DIR>/tools/write_inputs.py" "$CASE" \
  2>&1 | tee "$CASE/preprocess.log"
```

CASE 在新作业中需重新设为实际解压目录下的 001。前处理会生成 solid、fluid_boundary、facet_sections、facets/factypes 等并写回数量参数；此阶段 runtime 保持 0。检查进程退出成功、日志无错误、文件生成、数量参数被写回。关闭 EB 时无需复制 201 的辐射/能量文件。

## 4. 启动 60 秒风场试算

仅在前处理成功后：

```bash
cd "$CASE"
grep -E 'nfcts|nsolpts|nbndpts|nfctsecs|iwallmom' namoptions.001
sed -i 's/^runtime *=.*/runtime = 60./' namoptions.001
```

沿用个人环境中成功运行 201 的脚本副本：任务名改 udales001，运行参数改 namoptions.001，保持 1 节点、4 MPI 进程、OMP_NUM_THREADS=1；初始内存可设 32G。模块和求解器路径沿用已验证的个人配置。求解器作业加载 Intel 环境，不沿用前处理的 GNU 编译环境。

```bash
sbatch --partition=<PARTITION> --qos=<QOS> run.slurm
```

检查 COMPLETED/0:0、积分到约 60 秒、无运行错误及风场输出，使用 sacct 查看 Elapsed/MaxRSS。根据结果再延长预热和采样，评估周期边界、周边建筑和网格分辨率。5 m 网格与假设建筑高度只适合当前试算，尚未做收敛验证。
