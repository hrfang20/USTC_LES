"""Render scientific figures from the official 201 case and MPI output tiles."""
from pathlib import Path
import sys
import json
import struct
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor/python-deps'))
import numpy as np
import netCDF4 as nc
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

RUN = ROOT / 'outputs/validation/run/201'
OUT = ROOT / 'outputs/validation/figures/201'
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                     'axes.spines.right': False, 'figure.dpi': 150})

def save(fig, name):
    fig.savefig(OUT / (name + '.png'), dpi=180, bbox_inches='tight')
    fig.savefig(OUT / (name + '.pdf'), bbox_inches='tight')
    plt.close(fig)

files = sorted(RUN.glob('fielddump.*.*.201.nc'))
assert len(files) == 4, 'Expected four MPI tiles'
with nc.Dataset(files[0]) as d:
    z = np.asarray(d['zt'][:]); times = np.asarray(d['time'][:])
    zm = np.asarray(d['zm'][:])
shape = (len(z), 128, 128)
fields = {v: np.full(shape, np.nan, dtype=np.float32) for v in ['u','v','w','thl','qt']}
coverage = np.zeros((128,128), dtype=int)
for path in files:
    with nc.Dataset(path) as d:
        assert np.array_equal(times, d['time'][:]), 'Tile times differ'
        ix = np.rint(np.asarray(d['xt'][:]) - .5).astype(int)
        iy = np.rint(np.asarray(d['yt'][:]) - .5).astype(int)
        assert np.allclose(d['xm'][:], ix) and np.allclose(d['ym'][:], iy)
        coverage[np.ix_(iy,ix)] += 1
        for v in fields:
            fields[v][:,iy[:,None],ix] = np.ma.filled(d[v][-1], np.nan)
assert np.all(coverage == 1), 'Missing/overlapping spatial tiles'
assert np.all(np.isfinite(np.stack(list(fields.values())))), 'Nonfinite final fields'
x = y = np.arange(128) + .5
X,Y = np.meshgrid(x,y)
solid = np.zeros(shape, dtype=bool)
ijk = np.loadtxt(RUN/'solid_c.txt', comments='#', dtype=int)
solid[ijk[:,2]-1,ijk[:,1]-1,ijk[:,0]-1] = True
# Native u and v lie at lower cell faces; periodic domain permits wraparound.
u = .5*(fields['u'] + np.roll(fields['u'],-1,axis=2))
v = .5*(fields['v'] + np.roll(fields['v'],-1,axis=1))
speed = np.hypot(u,v)
for arr in [u,v,speed,fields['thl'],fields['qt']]:
    arr[solid] = np.nan

# Binary STL triangles; no modification of official geometry.
raw = (RUN/'geom.201.STL').read_bytes()
ntri = struct.unpack_from('<I', raw, 80)[0]
assert len(raw) == 84 + 50*ntri
dtype = np.dtype([('normal','<f4',(3,)),('verts','<f4',(3,3)),('attr','<u2')])
tri = np.frombuffer(raw, dtype=dtype, count=ntri, offset=84)['verts'].copy()
roof_tri = tri[tri[:,:,2].min(axis=1) > .05]
height = np.max(np.where(solid, z[:,None,None]+.5,0),axis=0)
fig = plt.figure(figsize=(13,5))
ax = fig.add_subplot(121,projection='3d')
mesh = Poly3DCollection(tri,facecolors='#c6d1dc',edgecolors='#576574',linewidths=.12)
ax.add_collection3d(mesh)
ax.set(xlim=(0,128),ylim=(0,128),zlim=(0,max(32,float(tri[:,:,2].max())+3)),
       xlabel='x (m)',ylabel='y (m)',zlabel='z (m)',title='Pre-defined buildings | official 201 STL')
ax.set_box_aspect((128,128,55)); ax.view_init(elev=27,azim=-55)
ax = fig.add_subplot(122)
im = ax.pcolormesh(X,Y,np.ma.masked_where(height==0,height),cmap='cividis',shading='nearest')
ax.set(xlabel='x (m)',ylabel='y (m)',title='Building heights | solid-cell mask',aspect='equal')
ax.set_facecolor('#eef2f4');fig.colorbar(im,ax=ax,label='Height from grid mask (m)')
save(fig,'201_buildings')

ks = [int(np.argmin(abs(z-h))) for h in [2.5,10.5,25.5]]
vmax = float(np.nanpercentile(speed[ks],99.5))
fig,axes = plt.subplots(1,3,figsize=(15,5),constrained_layout=True)
for ax,k in zip(axes,ks):
    im=ax.pcolormesh(X,Y,speed[k],vmin=0,vmax=vmax,cmap='viridis',shading='nearest')
    ax.contourf(X,Y,solid[k],levels=[.5,1.5],colors=['#919ba4'])
    sl = np.s_[::6,::6]
    ax.quiver(X[sl],Y[sl],u[k][sl],v[k][sl],color='white',scale=35,width=.003)
    ax.set(xlabel='x (m)',ylabel='y (m)',aspect='equal',title=f'z = {z[k]:.1f} m')
fig.colorbar(im,ax=axes,label='Horizontal speed (m/s)',shrink=.75)
fig.suptitle(f'201 instantaneous wind | t = {times[-1]:.2f} s | arrows: horizontal velocity')
save(fig,'201_wind')

k=ks[1]
fig,axes=plt.subplots(1,3,figsize=(15,5),constrained_layout=True)
data=[fields['thl'][k],fields['qt'][k]*1000, fields['w'][k]]
titles=['Liquid-water potential temperature (K)','Total water mixing ratio (g/kg)',f'Vertical velocity (m/s), z-face = {zm[k]:.1f} m']
for ax,arr,title in zip(axes,data,titles):
    arr=np.where(solid[k],np.nan,arr)
    lo,hi=np.nanpercentile(arr,[.5,99.5])
    if title.startswith('Vertical'):
        hi=max(abs(lo),abs(hi));lo=-hi
    im=ax.pcolormesh(X,Y,arr,cmap='RdBu_r' if lo<0 else 'magma',vmin=lo,vmax=hi,shading='nearest')
    ax.contourf(X,Y,solid[k],levels=[.5,1.5],colors=['#919ba4'])
    ax.set(xlabel='x (m)',ylabel='y (m)',aspect='equal',title=title)
    fig.colorbar(im,ax=ax,shrink=.7)
fig.suptitle(f'201 thermodynamic fields | t = {times[-1]:.2f} s | scalar height = {z[k]:.1f} m')
save(fig,'201_scalars')

fig,axes=plt.subplots(1,3,figsize=(14,5),constrained_layout=True)
with nc.Dataset(RUN/'xytdump.201.nc') as d:
    tprof=np.asarray(d['time'][:])
    for idx in [0,len(tprof)//2,len(tprof)-1]:
        for ax,name in zip(axes,['uxyt','thlxyt','qtxyt']):
            val=np.asarray(d[name][idx]); val=val*1000 if name=='qtxyt' else val
            ax.plot(val,z,label=f'{tprof[idx]:.1f} s')
    for ax,title in zip(axes,['Mean u (m/s)','Mean liquid-water potential temperature (K)','Mean total water mixing ratio (g/kg)']):
        ax.set(xlabel=title,ylabel='z (m)',ylim=(0,128));ax.grid(alpha=.2);ax.legend()
fig.suptitle('201 horizontal/time-interval statistics | native xytdump output')
save(fig,'201_profiles')

areas=np.loadtxt(RUN/'facetarea.inp.201',comments='#')
fig,axes=plt.subplots(1,2,figsize=(13,4.5),constrained_layout=True)
with nc.Dataset(RUN/'facT.201.nc') as d:
    ft=np.asarray(d['t'][:]);T=np.ma.filled(d['T'][:,0,:],np.nan)
    axes[0].plot(ft,np.average(T,axis=1,weights=areas),label='Area-weighted mean')
    axes[0].fill_between(ft,T.min(axis=1),T.max(axis=1),alpha=.2,label='Facet min-max')
    axes[0].set(xlabel='Simulation time (s)',ylabel='Surface temperature (K)');axes[0].legend()
with nc.Dataset(RUN/'facEB.201.nc') as d:
    for name in ['netsw','LWin','LWout','hf','ef']:
        axes[1].plot(d['t'][:],np.average(d[name][:],axis=1,weights=areas),label=name)
    axes[1].set(xlabel='Simulation time (s)',ylabel='Area-weighted flux (W/m²)');axes[1].legend(ncol=2)
for ax in axes:ax.grid(alpha=.2)
fig.suptitle('201 surface energy balance | stored flux signs retained')
save(fig,'201_surface_energy')

summary={'snapshot_time_s':float(times[-1]),'field_times_s':times.tolist(),
 'grid_shape_zyx':list(shape),'mpi_tiles':len(files),'triangles':ntri,
 'geometry_max_height_m':float(tri[:,:,2].max()),'slice_heights_m':[float(z[k]) for k in ks],
 'fluid_speed_min_max_m_s':[float(np.nanmin(speed)),float(np.nanmax(speed))],
 'notes':['No official numerical reference output used; figures are visualization, not validation.',
 'qt output metadata says 1e-5kg/kg, but raw source writes qt0 without rescaling; used kg/kg -> g/kg.',
 'Wind colormap clips at 99.5 percentile; scalar colormaps clip 0.5-99.5 percentile.',
 'Surface flux signs are those stored by the solver; curves do not prove energy closure.']}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
