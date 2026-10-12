# 依赖构建与作业模板

本文仅保留通用操作。账号、登录节点、模块名、安装路径、分区和 QoS 使用占位符，需在个人环境中填写；不要将实际值写入公共仓库。

| 标识符 | 含义 |
| --- | --- |
| `<USER>` / `<LOGIN_HOST>` | 账号 / 登录地址 |
| `<COMPILER_MODULE>` / `<MPI_MODULE>` / `<FFTW_MODULE>` | 匹配的工具链模块 |
| `<SOURCE_DIR>` / `<DEPS_PREFIX>` / `<FFTW_PREFIX>` | 源码 / 依赖安装 / FFTW 路径 |
| `<PARTITION>` / `<QOS>` / `<ACCOUNT>` | 调度配置 |

## 四个依赖

`scripts/hpc-deps/Makefile` 按 zlib 1.3.1 → HDF5 1.12.2 → NetCDF C 4.9.2 → NetCDF Fortran 4.6.1 构建。NetCDF-4 输出需要 HDF5；NetCDF Fortran 应与求解器编译器兼容。默认构建工具为 icc/ifort，允许通过 Make 参数覆盖，不给依赖添加求解器的 real-kind 参数。

上传包 `outputs/udales_deps_buildkit.tar.gz` 包含源码包、LF 换行的 SHA256SUMS 和 Makefile。此上传包位于被忽略的 outputs，不在 Git 中。

```bash
# 将占位符替换为个人环境值
scp outputs/udales_deps_buildkit.tar.gz <USER>@<LOGIN_HOST>:~/
```

远程解压，然后在允许编译的节点执行：

```bash
mkdir -p "$HOME/udales-deps-src"
tar -xzf "$HOME/udales_deps_buildkit.tar.gz" -C "$HOME/udales-deps-src"
cd "$HOME/udales-deps-src"
sha256sum -c SHA256SUMS
module load <COMPILER_MODULE> <MPI_MODULE> <FFTW_MODULE>
make JOBS=4 PREFIX="<DEPS_PREFIX>"
```

JOBS 不超过已分配 CPU。每库依次 configure、make、make check、make install；失败停止，成功安装才写完成标记。默认 WORK 为 `$HOME/udales-deps-build`，日志在其 logs 目录。再次执行跳过成功阶段；不会自动识别之前手工安装的库。更换编译器、参数或 PREFIX 时，指定新的 WORK，避免旧标记和缓存。

分阶段入口为 `make zlib`、`make hdf5`、`make netcdf-c`、`make netcdf-fortran`、`make verify`，均自动补齐前置阶段。Makefile 尚未在远程环境实际自动构建验证。

## 求解器

```bash
module load <COMPILER_MODULE> <MPI_MODULE> <FFTW_MODULE>
export UDALES_DEPS="<DEPS_PREFIX>"
export PATH="$UDALES_DEPS/bin:$PATH"
export LD_LIBRARY_PATH="$UDALES_DEPS/lib:${LD_LIBRARY_PATH:-}"
cd "<SOURCE_DIR>"
set -o pipefail
cmake -S . -B build/intel-release \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_Fortran_COMPILER=mpiifort \
  -DNETCDF_DIR="$UDALES_DEPS" \
  -DNETCDF_FORTRAN_DIR="$UDALES_DEPS" \
  -DCMAKE_PREFIX_PATH="<FFTW_PREFIX>;$UDALES_DEPS" \
  2>&1 | tee configure.log
# 仅在配置成功后执行
cmake --build build/intel-release --parallel 4 2>&1 | tee build.log
ldd build/intel-release/u-dales
```

配置需 FindFFTW：无网络时将已下载的 vendor/findfftw 内容复制到 build/intel-release/findFFTW-src。ldd 不应出现 not found。

## 通用问题

| 问题 | 处理 |
| --- | --- |
| 找不到 nc-config/nf-config | 加载匹配模块或安装用户目录依赖 |
| 校验文件末尾回车 | `sed -i 's/\r$//' SHA256SUMS`，重新校验 |
| Cannot find xml2-config | configure 添加 `--disable-libxml2`；Makefile 已包含 |
| Requested time limit is invalid | 依据实际分区限制调整时间 |
| Invalid qos specification | 依据账号权限选择 `<PARTITION>` / `<QOS>` / `<ACCOUNT>` |

官方 201 网格 128³，MPI 分解 2×2，使用 4 进程，模拟时长 200 秒。使用已有输入；作业模板见 cases/201/run.slurm，填写个人环境值后提交。作业成功需 COMPLETED/0:0、完成积分、无运行错误且生成 NetCDF。资源申请需通过实测调整。

参考：[NetCDF 官方构建说明](https://docs.unidata.ucar.edu/netcdf-c/4.9.3/building_netcdf_fortran.html)。
