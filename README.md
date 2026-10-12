# USTC East Campus LES

目标：核对中国科学技术大学东校区建筑布局，参考 JHTDB SABL 方法，使用 **uDALES** 模拟地转风驱动的校园风场。Python 使用已有的 `turbpy` conda 环境。建筑数据先从 OpenStreetMap 读取，Google Maps 布局核对仍待完成。

研究范围为**黄山路—太湖路—金寨路—宿松路围合区域**。已用 OSM 道路矢量生成闭合边界，面积约 0.625 km²，Google Maps 核对仍待完成。允许简化轮廓和附属细节，保留建筑位置、朝向、建筑群布局和主要通道。暂定计算域 `1090 × 1350 × 400 m`，范围外留 150 m 示例缓冲区；缓冲区内周边建筑尚未加入。

已实际读取并导出 **146 条建筑记录**；相接/重叠实体经布尔合并，保留高度台阶。建筑 STL 和含地面的 STL 均通过 uDALES 官方几何检查。**9 条高度来自楼层数 × 3.3 m 的估算，137 条使用 12 m 示例高度**，均有来源和不确定性记录，当前模型不能当作实测建筑高度模型。

官方 `UDPrep` 已生成并回读网格、初始剖面和地转风强迫。IBM 前处理实际尝试后停在缺少已编译的 `ibm_preproc_f2py` 扩展，尚未生成完整浸入边界输入，尚未运行 LES。

## 开始运行

在项目目录的 PowerShell 中执行：

```powershell
conda run -n turbpy python scripts\preflight.py
conda run -n turbpy python scripts\prepare_udales_geometry.py
conda run -n turbpy python scripts\prepare_udales_inputs.py
conda run -n turbpy python -m unittest discover -s tests
```

也可以先 `conda activate turbpy`，再运行相应脚本。打开 `notebooks/02_udales_geometry.ipynb`，选择 **turbpy** 内核，可直接用官方读取器打开已生成的建筑模型。原始 `test.ipynb` 和 `test.py` 保留。

重跑几何脚本需要原始 OSM 文件；首次下载或刷新数据运行 `python scripts/fetch_osm.py --osm-api`，需要网络。源码及依赖放在被 Git 忽略的 `vendor/`，固定版本和重建说明见 `configs/udales_source.json`、`configs/geometry_requirements.txt` 和 `docs/udales_workflow.md`。

预检查生成 `outputs/preflight.json`，列出网格规模、内存下限、平流时间步估计和未完成事项。它不分配三维网格。内存估算不包含临时数组、FFT 和并行通信，不能当作实际硬件需求。

## 项目入口

- `configs/sabl_reference.json`：已核实的参考参数，未核实参数留空。
- `configs/campus_draft.json`：校园计算域规划示例，待复核。
- `data/geometry/buildings.geojson`：原始 WGS84 轮廓和逐栋高度来源。
- `data/geometry/building_inventory.csv`：建筑清单。
- `cases/001/buildings.stl`：闭合建筑实体；`geom.001.stl`：建筑壁面、屋顶和裸露地面。
- `cases/001/geometry_overview.png`：布局与示例高度概览。
- `cases/001/input_status.json`：前处理完成情况与缺失依赖。
- `docs/methodology.md`：方程、方法差异及验证路线。
- `docs/geometry.md`：Google Maps 判读与高度、坐标核验流程。
- `src/ustc_les/physics.py`：地转驱动力和惯性振荡解析解。

下一阶段核对布局及高度，补齐 IBM 编译依赖和稳定分层边界条件。在真正启动模拟前，根据最终网格、编译环境、可用资源及短基准运行耗时评估本机或 HPC；当前不做生产运行平台选择。
