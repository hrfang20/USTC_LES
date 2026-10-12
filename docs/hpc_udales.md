# uDALES 上传、编译与试运行

通用编译配置、四个依赖 Makefile、报错处理及 201 作业设置，见 [依赖构建说明](hpc_build.md)。以下为通用平台说明。

本项目源码在 `vendor/u-dales`，固定提交 `42e40b6e1efd5529cfba8edd35005123e0ff70e4`。已补齐 2decomp-fft 和 View3D 子模块。另提供 `vendor/findfftw`，供无法访问 GitHub 的 HPC 配置 CMake 使用。源码尚未在 HPC 编译验证。

## 1. 上传

已生成 `outputs/udales_hpc_source.tar.gz`，包含源码、子模块、FindFFTW 和当前校园算例；不包含 Windows Python 环境或编译产物。

在本机 PowerShell 执行，将 USER 和 LOGIN_HOST 换成账号和登录节点：

```powershell
scp outputs/udales_hpc_source.tar.gz USER@LOGIN_HOST:~/
ssh USER@LOGIN_HOST
```

在 HPC 的 Linux shell 执行：

```bash
mkdir -p "$HOME/USTC_LES"
tar -xzf "$HOME/udales_hpc_source.tar.gz" -C "$HOME/USTC_LES"
cd "$HOME/USTC_LES"
```

若集群要求使用项目盘或 scratch，请将以上目录改到相应路径。传输包不含 Git 历史，保留提交记录见 `configs/udales_hpc_versions.txt`。

## 2. 加载匹配的依赖

需要 Fortran 编译器（GNU >=9、Intel 或 Cray）、MPI、NetCDF C + Fortran、FFTW3、CMake >=3.9。前处理还需要 C 编译器、Python >=3.9 和 Python 开发头文件。

先查看模块：

```bash
module avail
# 使用 Lmod 时也可以 module spider netCDF-Fortran
```

按集群提供的实际名字加载同一工具链的 compiler、MPI、NetCDF、NetCDF-Fortran、FFTW、CMake、Python；不要直接照搬其他集群的模块版本。GNU 编译器应搭配 GNU 构建的 MPI 和 netcdf.mod，Intel 同理。每次编译、运行都加载同一套模块。

```bash
which mpifort
mpifort --version
nf-config --all
nc-config --all
cmake --version
module list
```

Intel MPI 的包装器可能为 `mpiifort` 或 `mpiifx`，Cray 通常是 `ftn`。下文以 GNU + `mpifort` 为例。

## 3. 编译求解器

在集群允许的编译节点上执行；若登录节点禁止编译，先按集群规定申请交互计算节点。先复制已下载的 FindFFTW，使 CMake 不必访问 GitHub：

```bash
cd "$HOME/USTC_LES/vendor/u-dales"
mkdir -p build/release/findFFTW-src
cp -a ../findfftw/. build/release/findFFTW-src/
set -o pipefail
cmake -S . -B build/release \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_Fortran_COMPILER=mpifort \
  -DNETCDF_DIR="$(nc-config --prefix)" \
  -DNETCDF_FORTRAN_DIR="$(nf-config --prefix)" \
  -DNETCDF_USE_DEFAULT_PATHS=ON \
  2>&1 | tee configure.log
cmake --build build/release --parallel 4 2>&1 | tee build.log
test -x build/release/u-dales
ldd build/release/u-dales
```

并行编译数不超过分配的 CPU。FFTW 找不到时，将其安装前缀加入 `-DCMAKE_PREFIX_PATH=/实际/fftw/前缀`。`ldd` 不应出现 `not found`。更换编译器/MPI 后使用新构建目录，避免复用旧缓存。

## 4. 先运行官方示例 001

该示例自带输入，网格 `128×128×128`，模拟时长 21 秒，`nprocx=4`、`nprocy=2`，因此必须启动 8 个 MPI 进程。在计算节点上运行，保留原示例：

```bash
cd "$HOME/USTC_LES"
mkdir -p runs/example001
cp -a vendor/u-dales/examples/001/. runs/example001/
```

### Slurm 作业示例

保存以下内容为 `run_example.slurm`，在标记处填写自己的 module load 行。账号/分区依集群要求补充 `#SBATCH --account=...` 和 `#SBATCH --partition=...`。资源值是初次测试申请示例，并非实测需求。

```bash
#!/bin/bash
#SBATCH --job-name=udales001
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=1
#SBATCH --time=00:20:00
#SBATCH --mem=16G
#SBATCH --output=udales-%j.log
set -euo pipefail
# 在此填写与编译一致的 module load 命令
ROOT="$HOME/USTC_LES"
export OMP_NUM_THREADS=1
cd "$ROOT/runs/example001"
srun "$ROOT/vendor/u-dales/build/release/u-dales" namoptions.001
```

```bash
sbatch run_example.slurm
squeue -u "$USER"
# 完成后检查退出状态与日志
sacct -j JOBID --format=JobID,State,ExitCode,Elapsed,MaxRSS
```

`srun` 需要集群的 MPI/PMI 支持。若集群官方要求 `mpirun`，将运行行替换为 `mpirun -np 8 ...`，不要嵌套两种启动器。

### PBS 作业示例

保存为 `run_example.pbs`；若集群使用旧版 PBS，资源语法须按管理员文档调整：

```bash
#!/bin/bash
#PBS -N udales001
#PBS -l select=1:ncpus=8:mpiprocs=8:mem=16gb
#PBS -l walltime=00:20:00
#PBS -j oe
set -euo pipefail
# 在此填写与编译一致的 module load 命令
ROOT="$HOME/USTC_LES"
export OMP_NUM_THREADS=1
cd "$ROOT/runs/example001"
mpiexec -n 8 "$ROOT/vendor/u-dales/build/release/u-dales" namoptions.001
```

```bash
qsub run_example.pbs
qstat -u "$USER"
```

成功标准：作业退出码为 0、日志无 Fortran/MPI 错误、积分达到设定的 runtime，并生成预期的 NetCDF 输出。需要合并跨进程输出时加载 NCO，再运行官方 `tools/gather_outputs.sh`；保留原始输出用于排查。

## 5. 校园算例的下一步

`cases/001/namoptions.001` 当前 `runtime=0`，仍为前处理草案。先编译前处理扩展，在允许联网且允许编译的节点执行：

```bash
cd "$HOME/USTC_LES/vendor/u-dales"
bash tools/python/setup_venv.sh common preprocessing_tools
source tools/python/.venv/bin/activate
python -c "from udprep import ibm_preproc_f2py; print('IBM extension OK')"
```

该脚本需联网安装 Python 依赖；无网络时需使用集群镜像或预先准备与 HPC Linux/Python 匹配的离线包，Windows 的 `vendor/python-deps` 不能直接复制过去使用。

在交互计算节点或单独的前处理作业中执行（CPU 数应与分配资源及 namoptions 的 nompthreads 相符）：

```bash
export PREPROC_NCPU=8
export NUMBA_NUM_THREADS=8
python tools/write_inputs.py "$HOME/USTC_LES/cases/001"
```

校园网格目前为 `218×270×80`，不要套用官方示例的 4×2 分解：218 不能被 4 整除。应按最终网格及 2DECOMP 的分解要求选择进程布局，再确保作业进程数等于 `nprocx*nprocy`。

完整生成并核查 IBM 输入后，还需核对建筑高度/布局、设置稳定分层与地面冷却、修改 runtime/输出频率，并做短试算测量内存和速度，然后再提交长模拟。前处理成功不代表校园物理设置已验证。

参考：[官方安装文档](https://udales.github.io/u-dales/udales-installation/)、本次固定版本的 `CMakeLists.txt`、`tools/build_preprocessing.sh`、`tools/python/setup_venv.sh`、`tools/write_inputs.py` 和 `examples/001/namoptions.001`。执行命令以本次下载的源码为准。
