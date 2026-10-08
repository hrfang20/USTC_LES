# uDALES 建筑数据与前处理

## 已执行

使用 `turbpy` Python 下载 OSM 官方地图 API 数据。Overpass 两个服务分别返回 504/500，改用官方 `/api/0.6/map` 后成功。下载窗口只用于搜索，最终边界由四条指定道路的矢量网络构成，不采用搜索矩形代替边界。

提取包含校园定位点的道路闭合面，检查其边界与四条道路均接触。双向道路各有车行道矢量，因此选取内侧围合面，而非拟造道路中心线。原始 WGS84 轮廓转换至 UTM 50N，再平移到局地米制坐标，x 东、y 北、z 上。这里只核实了坐标转换和路网闭合，未独立核验底图配准。

导出 146 条建筑记录；未知高度采用显式的 12 m 情景值，9 条楼层记录乘以假设层高 3.3 m。0.5 m 保拓扑简化若使面积变化超过 2% 则回退原轮廓。省略小于 25 m²、无名称且低于 20 m 的建筑候选；屋顶或架空结构需独立处理，暂不挤出为落地实体。记录所有省略理由。建筑相交处采用实体并集消除内部面，并保留不同高度形成的台阶。

`buildings.stl` 为闭合实体；用官方 `udgeom.add_ground` 加地面前移除埋在 z=0 的建筑底面，避免与地面形成非流形连接。生成的 `geom.001.stl` 是壁面、屋顶和外露地面组成的开放地表，域外围边缘开放是预期结构。两种 STL 已通过官方 `UDGeom.check`；多栋独立建筑允许多连通分量，不要求建筑实体全部连接。

uDALES Python 工具来自固定提交 `42e40b6e1efd5529cfba8edd35005123e0ff70e4`。[官方 Python 工具说明](https://udales.github.io/u-dales/udales-python-package/)和[前处理说明](https://udales.github.io/u-dales/udales-pre-processing/)描述了 `UDGeom`、`UDPrep`、STL、namoptions 及 IBM 输入之间的关系。项目报告中的“可读取”仅指几何读取及检查通过，不代表完整求解器输入已准备完成。

## 本地重建依赖

使用已有 turbpy，不另外创建 Python 环境。下载依赖至项目内，避免改变现有 NumPy/SciPy：

```powershell
git clone https://github.com/uDALES/u-dales.git vendor/u-dales
git -C vendor/u-dales checkout 42e40b6e1efd5529cfba8edd35005123e0ff70e4
& C:\Users\Admin\anaconda3\envs\turbpy\python.exe -m pip install --target vendor/python-deps --no-deps -r configs/geometry_requirements.txt
& C:\Users\Admin\anaconda3\envs\turbpy\python.exe scripts/fetch_osm.py --osm-api
& C:\Users\Admin\anaconda3\envs\turbpy\python.exe scripts/prepare_udales_geometry.py
& C:\Users\Admin\anaconda3\envs\turbpy\python.exe scripts/prepare_udales_inputs.py
```

基础 turbpy 需已有 numpy、scipy、pandas、matplotlib、requests、packaging 和 certifi。原始快照放在 `data/raw/`，Git 默认忽略；重新下载可能随 OSM 编辑而变化。GeoJSON、建筑清单、STL 和报告作为当前派生结果保留。数据来源为 OpenStreetMap contributors，遵循 [ODbL](https://www.openstreetmap.org/copyright)，不是 Google Maps 提取或已核验的 Google Maps 数据。生成物保留来源，不将假设高度当作测量值。

## 当前阶段限制

`namoptions.001` 为前处理草案，`runtime=0`，温度输运/浮力暂关闭；它不是稳定边界层校园模拟的最终配置。官方工具已生成并回读 `prof.inp.001` 和 `lscale.inp.001`，地转风列为 (8, 0) m/s。5 m 网格为 `218 × 270 × 80`，合计 4,708,800 单元，未进行分辨率收敛验证。

执行 `prepare_udales_inputs.py --ibm` 已实际触发官方 IBM 前处理入口，当前错误为缺少 `ibm_preproc_f2py`。需在适当编译环境按官方流程构建扩展，再生成 solid masks、fluid boundaries、facet sections 及壁面属性。尚未进行求解器或前处理编译，不声称官方编译测试已通过。

当前没有可用浏览器自动化连接，Google Maps 核对未完成；OSM 的覆盖完整性和高度需要核验。缓冲区周边建筑也需要按最终来流方向补充。参考 SABL 的地面持续降温、初始稳定分层、SGS 和壁面设置须另行配置；当前 uDALES 草案 Vreman SGS 不等同于 SABL 原始两部分 SFS 模型。

## 模拟启动前再选择计算平台

此阶段只准备和读取数据，不提前提交本地或 HPC 计算。启动前先补齐 IBM 与热力设置，再检查最终网格、MPI 分解、可用内存及 Linux/WSL/HPC 编译环境。用短试算测量每步耗时和峰值内存，推算预热、统计采样及输出需求，然后决定本机或 HPC。Windows 原生 Python 能完成当前读取，不意味着 uDALES Fortran/MPI 求解器已经可运行。
