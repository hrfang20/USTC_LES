# 结果图与分析文件

本目录索引仓库中已发布的全部可视化结果。原始 NetCDF、求解器日志和重启文件仍保留在本地 `outputs/`，不纳入 Git；图像、PDF、GIF 和绘图摘要复制到 `docs/assets/results/`。

## 官方 201 示例

- 建筑：[PNG](assets/results/201/201_buildings.png) / [PDF](assets/results/201/201_buildings.pdf)
- 风场：[PNG](assets/results/201/201_wind.png) / [PDF](assets/results/201/201_wind.pdf)
- 温湿度与垂直速度：[PNG](assets/results/201/201_scalars.png) / [PDF](assets/results/201/201_scalars.pdf)
- 统计廓线：[PNG](assets/results/201/201_profiles.png) / [PDF](assets/results/201/201_profiles.pdf)
- 表面温度与能量通量：[PNG](assets/results/201/201_surface_energy.png) / [PDF](assets/results/201/201_surface_energy.pdf)
- [分析说明](assets/results/201/README.md) / [数值摘要](assets/results/201/summary.json)

## 校园 001 中性风场

- 风场动画：[GIF](assets/results/campus001/campus_wind_evolution.gif)
- 7.5 m 风场：[PNG](assets/results/campus001/campus_wind_z7p5.png) / [PDF](assets/results/campus001/campus_wind_z7p5.pdf)
- 17.5 m 风场：[PNG](assets/results/campus001/campus_wind_z17p5.png) / [PDF](assets/results/campus001/campus_wind_z17p5.pdf)
- 57.5 m 风场：[PNG](assets/results/campus001/campus_wind_z57p5.png) / [PDF](assets/results/campus001/campus_wind_z57p5.pdf)
- [数值摘要](assets/results/campus001/summary.json)

## 校园 202：200 s 启动段

- 风场动画：[GIF](assets/results/campus202/202_wind_evolution.gif)
- 7.5 m 风场：[PNG](assets/results/campus202/202_wind_z7p5.png) / [PDF](assets/results/campus202/202_wind_z7p5.pdf)
- 17.5 m 风场：[PNG](assets/results/campus202/202_wind_z17p5.png) / [PDF](assets/results/campus202/202_wind_z17p5.pdf)
- 57.5 m 风场：[PNG](assets/results/campus202/202_wind_z57p5.png) / [PDF](assets/results/campus202/202_wind_z57p5.pdf)
- 热力与水汽平面场：[PNG](assets/results/campus202/202_thermal_maps.png) / [PDF](assets/results/campus202/202_thermal_maps.pdf)
- 全高度统计廓线：[PNG](assets/results/campus202/202_profiles.png) / [PDF](assets/results/campus202/202_profiles.pdf)
- 0–100 m 统计廓线：[PNG](assets/results/campus202/202_profiles_low100m.png) / [PDF](assets/results/campus202/202_profiles_low100m.pdf)
- 瞬态诊断：[PNG](assets/results/campus202/202_transient_diagnostics.png) / [PDF](assets/results/campus202/202_transient_diagnostics.pdf)
- [数值摘要](assets/results/campus202/summary.json)

## 校园 202：长时段续算

该段由约 200 s 的重启点继续积分，三维场覆盖约 230–7400 s。名称中的 `7200` 表示续算长度，最终物理时刻约为 7400 s。

- 风场动画：[GIF](assets/results/campus202_7200/202_long_wind_evolution.gif)
- 7.5 m 风场：[PNG](assets/results/campus202_7200/202_long_wind_z7p5.png) / [PDF](assets/results/campus202_7200/202_long_wind_z7p5.pdf)
- 17.5 m 风场：[PNG](assets/results/campus202_7200/202_long_wind_z17p5.png) / [PDF](assets/results/campus202_7200/202_long_wind_z17p5.pdf)
- 57.5 m 风场：[PNG](assets/results/campus202_7200/202_long_wind_z57p5.png) / [PDF](assets/results/campus202_7200/202_long_wind_z57p5.pdf)
- 热力与水汽平面场：[PNG](assets/results/campus202_7200/202_long_thermal_maps.png) / [PDF](assets/results/campus202_7200/202_long_thermal_maps.pdf)
- 最后两个一小时的统计廓线：[PNG](assets/results/campus202_7200/202_long_profiles_hourly_comparison.png) / [PDF](assets/results/campus202_7200/202_long_profiles_hourly_comparison.pdf)
- 时间—高度演化：[PNG](assets/results/campus202_7200/202_long_time_height.png) / [PDF](assets/results/campus202_7200/202_long_time_height.pdf)
- 长时段诊断：[PNG](assets/results/campus202_7200/202_long_diagnostics.png) / [PDF](assets/results/campus202_7200/202_long_diagnostics.pdf)
- [数值摘要](assets/results/campus202_7200/summary.json)

最后两个一小时窗口的 7.5、17.5 和 57.5 m 平均风速分别下降约 21.2%、21.5% 和 17.3%；表面面积加权平均温度最终约为 308.16 K。该时段已有充分发展的热对流湍流，但尚未达到统计稳态。
