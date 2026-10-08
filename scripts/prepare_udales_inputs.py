"""Generate draft grid/profiles with official UDPrep, without starting LES.

The namelist is for preprocessing only (runtime=0). Thermal/wall conditions
must be specified before turning it into a stable-boundary-layer simulation.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'vendor/python-deps'), str(ROOT / 'vendor/u-dales/tools/python')]
import numpy as np
from udprep import UDPrep


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ibm', action='store_true', help='Also run compiled IBM preprocessor; no flow solver')
    args = parser.parse_args()
    case = ROOT / 'cases/001'
    config = json.loads((ROOT / 'configs/campus_draft.json').read_text(encoding='utf-8'))
    geometry = json.loads((case / 'geometry_report.json').read_text(encoding='utf-8'))
    if not geometry['ground_geometry_check']['valid']:
        raise RuntimeError('Ground geometry has not passed official QA')
    sizes, spacing = config['domain_m'], config['grid_spacing_m']
    if any(not float(s / d).is_integer() for s, d in zip(sizes, spacing)):
        raise ValueError('Domain must divide exactly by grid spacing')
    counts = [int(s / d) for s, d in zip(sizes, spacing)]
    ug, vg = config['geostrophic_velocity_m_s']
    namelist = f'''! PREPROCESSING DRAFT ONLY: not a calibrated SABL/campus simulation.
! runtime=0 prevents a production time integration; IBM files are still needed.
&RUN
iexpnr = 001
runtime = 0.
dtmax = 0.2
ladaptive = .true.
nprocx = 1
nprocy = 1
libm = .true.
/
&DOMAIN
itot = {counts[0]}
jtot = {counts[1]}
ktot = {counts[2]}
xlen = {sizes[0]}.
ylen = {sizes[1]}.
xlat = {config['latitude_deg']}
/
&PHYSICS
lcoriol = .true.
lbuoyancy = .false.
ltempeq = .false.
lmoist = .false.
/
&NAMSUBGRID
lvreman = .true.
/
&WALLS
iwallmom = 2
iwalltemp = 1
iwallmoist = 1
/
&ENERGYBALANCE
lEB = .false.
/
&INPS
zsize = {sizes[2]}.
u0 = {ug}
v0 = {vg}
thl0 = 288.
qt0 = 0.
tke = 0.1
gen_geom = .true.
stl_file = 'geom.001.stl'
stl_ground = .true.
nompthreads = 4
/
'''
    (case / 'namoptions.001').write_text(namelist, encoding='utf-8')
    prep = UDPrep(case, load_geometry=True, suppress_load_warnings=True)
    prep.grid.run_all()
    prep.forcing.generate_prof()
    prep.forcing.write_prof(force=True)
    prep.forcing.generate_lscale()
    prep.forcing.write_lscale()
    # Read generated files using the same uDALES input reader and verify Ug/Vg.
    profile = prep.sim.load_prof()
    forcing = prep.sim.load_lscale()
    np.testing.assert_allclose(profile[:, 3:5], np.tile([ug, vg], (counts[2], 1)))
    np.testing.assert_allclose(forcing[:, 1:3], np.tile([ug, vg], (counts[2], 1)))
    status = {'status': 'draft_preprocessing_only', 'udales_grid_and_profiles_verified': True,
              'grid_cells': counts, 'total_cells': int(np.prod(counts)),
              'geostrophic_velocity_m_s': [ug, vg], 'ibm_completed': False,
              'simulation_started': False, 'production_platform_decision': 'deferred_until_simulation_launch',
              'thermal_note': 'Temperature transport and buoyancy disabled for input preparation; not SABL yet'}
    if args.ibm:
        try:
            prep.ibm.run_all()
            status['ibm_completed'] = True
        except RuntimeError as exc:
            status['ibm_error'] = str(exc)
            (case / 'input_status.json').write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8')
            raise
    (case / 'input_status.json').write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()
