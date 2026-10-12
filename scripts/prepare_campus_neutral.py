"""Stage an isolated neutral-flow case; never compile or launch the solver."""
import json
import shutil
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'vendor/python-deps'))
import numpy as np
import trimesh

source = ROOT/'cases/001'
out = ROOT/'outputs/campus_neutral_setup'
case = out/'001'
if case.exists():
    raise SystemExit('Staging directory already exists; choose/preserve a separate run before restaging.')
mesh = trimesh.load(source/'geom.001.stl', force='mesh')
ground = np.all(np.isclose(mesh.triangles[:,:,2],0.,atol=1e-6),axis=1)
xy = mesh.triangles[ground,:,:2].reshape(-1,2)
np.testing.assert_allclose(xy.min(0),[0,0],atol=1e-5)
np.testing.assert_allclose(xy.max(0),[1090,1350],atol=1e-5)
# Area of exposed ground + projected buried building bases = rectangle.
buildings = trimesh.load(source/'buildings.stl',force='mesh')
base = np.all(np.isclose(buildings.triangles[:,:,2],0.,atol=1e-6),axis=1)
covered_area = mesh.area_faces[ground].sum()+buildings.area_faces[base].sum()
np.testing.assert_allclose(covered_area,1090*1350,rtol=2e-5)
case.mkdir(parents=True)
for name in ['geom.001.stl','prof.inp.001','lscale.inp.001']:
    shutil.copy2(source/name,case/name)
shutil.copy2(source/'namoptions.neutral.001',case/'namoptions.001')
for name in ['preprocess.neutral.slurm','run.neutral.slurm']:
    shutil.copy2(source/name,case/name)
report = {'grid_cells':[218,270,80],'domain_m':[1090,1350,400],
          'ground_bounds_m':[xy.min(0).tolist(),xy.max(0).tolist()],
          'ground_plus_building_base_area_m2':float(covered_area),
          'geometry_max_height_m':float(mesh.bounds[1,2]),
          'mpi_grid':[2,2],'ibm_generated':False,'thermal_enabled':False,
          'runtime_s':0,'planned_smoke_test_s':60,
          'lateral_boundaries':'periodic defaults; no external inflow',
          'notes':['Ground already extends to rectangle; buildings unchanged.',
                   'Outside mapped study boundary is empty flat ground.',
                   'Short transient test; not a steady or validated campus simulation.']}
(out/'setup_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
shutil.make_archive(str(ROOT/'outputs/campus_neutral_inputs'),'gztar',out)
print(json.dumps(report,indent=2))
