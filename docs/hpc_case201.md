# 官方 201 算例：HPC 试运行

本地 `cases/201` 来自 uDALES 固定提交 `42e40b6e1efd5529cfba8edd35005123e0ff70e4` 的 `examples/201`。原始模拟输入保留；`config.sh` 的机器路径已替换为占位符，额外提供 `run.slurm`。这是建筑几何、IBM、温湿度输运和表面能量平衡算例；网格 128×128×128，水平尺寸 128×128 m，模拟时间 200 秒，nprocx=2、nprocy=2，共 4 个 MPI 进程。200 秒为官方示例运行长度，不表示已获得稳定统计结果。

## 1. 上传

本机项目目录的 PowerShell：

```powershell
scp outputs/udales_case201.tar.gz <USER>@<LOGIN_HOST>:~/
```

主机名如无法从本机访问，改用平时 SSH 的实际地址。在 HPC 创建新的运行目录并解压：

```bash
RUN201="$HOME/udales-runs/case201-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN201"
tar -xzf "$HOME/udales_case201.tar.gz" -C "$RUN201"
cd "$RUN201"
sha256sum -c SHA256SUMS
```

检查全部显示 OK。归档内文件直接放在当前运行目录，无额外 cases/201 层级。

## 2. 检查输入和程序

```bash
module load <COMPILER_MODULE> <MPI_MODULE> <FFTW_MODULE>
export UDALES_DEPS="$HOME/local/udales-intel"
export PATH="$UDALES_DEPS/bin:$PATH"
export LD_LIBRARY_PATH="$UDALES_DEPS/lib:${LD_LIBRARY_PATH:-}"
test -x "<SOURCE_DIR>/build/intel-release/u-dales"
ldd "<SOURCE_DIR>/build/intel-release/u-dales"
grep -E 'runtime|nprocx|nprocy|lEB|itot|jtot|ktot' namoptions.201
ncdump -h vf.nc.inp.201 | head -40
```

程序路径按实际源码目录修改；ldd 不应出现 not found。该例已附 prof/lscale、solid/fluid_boundary/facet_sections、辐射视角因子及温度等输入，首次复现直接使用，无需重新运行几何或 IBM 前处理。保留原始 namoptions。

config.sh 使用路径占位符；本次 run.slurm 直接调用程序，不读取此文件。不要直接用未经修改的 config.sh 启动官方包装脚本。

## 3. Slurm 提交

先确认 `command -v sbatch` 有输出。若只有 qsub，改用 PBS 脚本。编辑 run.slurm，检查 UDALES_EXE 路径；按集群要求添加 partition/account。默认申请单节点、4 进程、16 GB、1 小时，仅为初次试运行的资源示例，未实测。

```bash
sinfo
sbatch run.slurm
squeue -u "$USER"
```

运行脚本使用 Intel MPI 的 mpirun。如果集群要求使用特定启动器，遵循集群说明调整启动行。

## 4. 检查运行

将 JOBID 换成提交返回的编号：

```bash
tail -f udales-JOBID.log
# Ctrl+C 仅停止查看日志
sacct -j JOBID --format=JobID,State,ExitCode,Elapsed,MaxRSS
ls -lh *.nc
```

应完成 200 秒模拟积分、作业 COMPLETED/0:0、无 Fortran/MPI 错误且生成 NetCDF 输出。OOM 表示需调整内存；TIMEOUT 表示需调整时间。若出现运行错误，保留完整日志及原始输出。输出频率为每 10 秒，字段包括 u0/v0/w0/th/qt，并开启统计与能量平衡输出。

跨进程输出的合并可使用源码 tools/gather_outputs.sh，但需要 NCO。第一次运行先保留分片，确认成功后再合并。

参考：下载源码内 docs/udales-example-simulations.md 的 201 节、examples/201/namoptions.201，以及 src/initfac.f90。
