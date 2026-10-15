"""Stage campus 202, generating only grid and initial/forcing profiles locally."""
from pathlib import Path
import sys
import json
import shutil
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'vendor/python-deps'), str(ROOT/'vendor/u-dales/tools/python')]
import numpy as np
import f90nml
from udprep import UDPrep

destination = ROOT/'outputs/campus202_setup'
case = destination/'202'
if case.exists():
    raise SystemExit('202 staging already exists; preserve it before preparing a new run.')
case.mkdir(parents=True)
shutil.copy2(ROOT/'cases/001/geom.001.stl',case/'geom.202.stl')
shutil.copy2(ROOT/'cases/202/namoptions.202',case/'namoptions.202')
for job in ['preprocess.slurm','run.slurm']:
    shutil.copy2(ROOT/'cases/202'/job,case/job)
prep = UDPrep(case,load_geometry=True,suppress_load_warnings=True)
prep.grid.run_all()
prep.forcing.run_all()
np.testing.assert_allclose(prep.sim.load_prof()[:,3:5],np.tile([1.5,0.],(80,1)))
np.testing.assert_allclose(prep.sim.load_lscale()[:,1:3],np.tile([1.5,0.],(80,1)))
nml = f90nml.read(case/'namoptions.202')
ref = f90nml.read(ROOT/'vendor/u-dales/examples/201/namoptions.201')
for section,keys in {
 'physics':['lbuoyancy','ltempeq','lmoist','ps','igrw_damp','lcoriol','lnudge','tnudge'],
 'dynamics':['ipoiss','iadv_thl','iadv_qt'],
 'bc':['wtsurf','wqsurf','thl_top','qt_top','qts'],
 'energybalance':['leb','lconstw','lwriteebfiles','dteb','bldt','wsoil','wgrmax','wwilt','wfc','skylw','grlai','rsmin','nfaclyrs'],
 'inps':['u0','thl0','qt0','fact'],
}.items():
    for key in keys:
        assert nml[section][key] == ref[section][key], (section,key)
report = {'case':202,'reference_case':201,'runtime_s':0,'planned_smoke_test_s':200,
          'grid_cells':[218,270,80],'domain_m':[1090,1350,400],
          'initial_wind_m_s':[1.5,0],'thermal_enabled':True,'ibm_and_radiation_completed':False,
          'changes_from_201':['Campus geometry/domain/latitude','Top-half nudging: 40 of 80 levels',
                              'dtmax 0.2 s','No 3D statistical tdump for first test',
                              'Fresh start, not neutral restart'],
          'notes':['Fixed reference solar forcing, not observed campus weather.',
                   'No copied neutral IBM or 201 radiation files.',
                   'Generated default facet materials require verification.']}
(destination/'setup_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
shutil.make_archive(str(ROOT/'outputs/campus202_inputs'),'gztar',destination)
print(json.dumps(report,indent=2))
