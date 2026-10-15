# 校园 202：参考官方 201 的热力耦合试验

本实验沿用校园 001 的几何、规则地面及 5 m 网格，参考固定版本官方 201 的动力学、温湿度、壁面与表面能量平衡参数。采用全新初始化，不接续中性 001 的重启文件；不修改已经完成的 001/201。

## 设置与差异

| 项目 | 202 |
| --- | --- |
| 域/网格 | 1090×1350×400 m，218×270×80 |
| MPI | 2×2，4 进程 |
| 初始风/地转风 | (1.5,0) m/s，参考 201；与中性 001 的 8 m/s 不同 |
| 初始空气/壁面 | thl0=295 K，qt0=0.01 kg/kg，facT=295 K |
| 动力学 | FFT Poisson；iadv_thl=iadv_qt=2；Vreman；Coriolis |
| nudging | tnudge=10800 s，顶部 40 层；按 201 顶部半域比例适配 |
| 热力 | lbuoyancy/ltempeq/lmoist/lEB 开启 |
| 壁面 | iwallmom=iwalltemp=iwallmoist=2 |
| 热力边界 | 201 的 thl_top=288 K、qt_top=0 等原样保留 |
| 能量平衡 | dtEB=2 s、bldT=301 K、skyLW=395 W/m²，5 材料层；土壤与植被参数参考 201 |
| 短波 | 固定太阳天顶角 28.4066°、方位角 135°、xazimuth=90°，I=800、Dsky=250 W/m²；采用 201 Python 前处理默认参考情景 |
| 太阳/边界 | isolar=1，无真实日期气象驱动；动力水平周期，辐射 periodic_xy=false 与参考默认一致 |
| 试运行 | 前处理 runtime=0，成功后改为 200 s；dtmax=0.2 s |
| 输出 | 每约 10 s 输出 u/v/w/thl/qt；统计剖面与能量输出；首次关闭大体积 3D tdump |

模板 cases/202/namoptions.202 显式保留参考值，不复制 201 的 nfcts/nsolpts 等几何数量。最高建筑约 52.8 m。5 m 网格尚未收敛、建筑高度仍包含情景假设；默认生成的材料类别也需核验，不能当作实测热物性。此设置不是稳定边界层地面持续冷却实验。201 顶部热力边界会产生明显垂直梯度，应检查其影响。

## 1. 本地准备和上传

```bash
conda activate turbpy
python scripts/prepare_campus202.py
scp outputs/campus202_inputs.tar.gz <USER>@<LOGIN_HOST>:~/
```

脚本复制几何并重生成 202 的网格、prof/lscale；核对主要参数与官方 201 相同，拒绝覆盖已有 staging。不复制 001 的 IBM 文件或 201 的辐射文件。

远程终端：

```bash
RUN202="$HOME/campus202-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN202"
tar -xzf "$HOME/campus202_inputs.tar.gz" -C "$RUN202"
cd "$RUN202/202"
```

## 2. 新生成 IBM、辐射和表面温度

编辑 preprocess.slurm，占位符填写成功编译前处理的个人模块环境、源码路径、分区和 QoS。无需重建已有虚拟环境，但必须有 View3D 和相关扩展。

```bash
"<SOURCE_DIR>/tools/python/.venv/bin/python" -c "from udprep import ibm_preproc_f2py; print('IBM OK')"
ls -l "<SOURCE_DIR>/tools/preprocessing/build/bin/view3d"
sbatch preprocess.slurm
```

与中性 001 相比，需要 c-grid 热量/湿度壁面映射、视角因子、短波、天空可视因子和表面温度。已有 27513 个面片，View3D 计算可能远慢于仅 IBM 的约一分钟。首次 4 CPU/4 小时作业据用户反馈超时，现模板调整为 16 CPU/64 GB/24 小时；nompthreads=16 与资源保持一致。此资源仍待实测，不能保证 16 线程线性加速或必然在 24 小时内完成。求解器仍为 4 MPI 进程，与前处理线程数独立。

模板加入 GNU libgomp 优先加载，避免已遇到的 NVIDIA OpenMP 库符号冲突。路径按实际扩展编译器调整。runtime=0 不会跳过辐射预处理，不应通过提高 runtime 解决前处理超时。稀疏视角因子减少存储但仍有大量配对与遮挡计算。现版本并行 View3D 没有逐面进度、未确认断点恢复支持；超时后不把部分 vfsparse 文件当完整输入。保留失败运行目录，建议创建新目录重跑，以免复用不完整缓存。

先确认作业 COMPLETED/0:0、日志无错误，随后检查：

```bash
grep -Ei 'nfcts|nsolpts|nbndpts|nfctsecs|nnz|iwallmom' namoptions.202
ls -lh facets.inp.202 factypes.inp.202 Tfacinit.inp.202 \
  netsw.inp.202 svf.inp.202 vfsparse.inp.202
ls -lh solid_*.txt fluid_boundary_*.txt facet_sections_*.txt
```

检查 missing-flux 面积和视角因子诊断；非零缺失不等于前处理崩溃，也不能据此宣称映射完全验证。不要把中性 001 的数量参数或辐射输入补到 202。

## 3. 200 秒启动检查

完整前处理成功后：

```bash
cp namoptions.202 namoptions.202.preprocess-backup
sed -i 's/^runtime *=.*/runtime = 200./' namoptions.202
```

编辑 run.slurm，采用已成功运行求解器的个人 Intel/MPI/FFTW 模块与依赖路径。保留 4 MPI 进程、OMP_NUM_THREADS=1。32 GB/2 小时为未实测起点。

```bash
sbatch run.slurm
squeue -j JOBID
tail -f udales-JOBID.log
sacct -j JOBID --format=JobID,State,ExitCode,Elapsed,MaxRSS
```

检查积分到约 200 s、无数值异常，生成风温湿场、facT.202.nc、facEB.202.nc 和统计输出。以 1.5 m/s 穿越1090 m 约需 727 s，200 s 不到一次穿越，不能当作稳态；后续先延长预热并检查速度、温度、水分、通量和能量收支，再开始统计采样。

对比 001/202 时，风速和物理条件同时改变，因此差异不能全部归因于热力作用。如果需要隔离热力影响，应另建保持风速等参数一致的中性对照实验。
