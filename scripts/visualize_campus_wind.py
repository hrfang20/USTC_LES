"""Compare campus neutral wind snapshots with a common color scale."""
from pathlib import Path
import sys
import json
import io
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'vendor/python-deps'))
import numpy as np
import netCDF4 as nc
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

RUN=ROOT/'outputs/campus_neutral_setup/001'
OUT=ROOT/'outputs/validation/figures/campus001'
OUT.mkdir(parents=True,exist_ok=True)
files=sorted(RUN.glob('fielddump.*.*.001.nc'))
assert len(files)==4, 'Four spatial tiles required'
with nc.Dataset(files[0]) as d:
    times=np.asarray(d['time'][:]);z=np.asarray(d['zt'][:])
nx,ny=218,270
x=(np.arange(nx)+.5)*5;y=(np.arange(ny)+.5)*5
X,Y=np.meshgrid(x,y)
ks=[int(np.argmin(abs(z-h))) for h in [7.5,17.5,57.5]]
u=np.full((len(times),len(ks),ny,nx),np.nan,dtype=np.float32)
v=u.copy();seen=np.zeros((ny,nx),int)
for f in files:
    with nc.Dataset(f) as d:
        assert np.array_equal(d['time'][:],times)
        ix=np.rint(np.asarray(d['xt'][:])/5-.5).astype(int)
        iy=np.rint(np.asarray(d['yt'][:])/5-.5).astype(int)
        assert np.allclose(d['xm'][:],ix*5) and np.allclose(d['ym'][:],iy*5)
        seen[np.ix_(iy,ix)]+=1
        for h,k in enumerate(ks):
            u[:,h,iy[:,None],ix]=np.ma.filled(d['u'][:,k,:,:],np.nan)
            v[:,h,iy[:,None],ix]=np.ma.filled(d['v'][:,k,:,:],np.nan)
assert np.all(seen==1),'Missing/overlapping MPI tiles'
assert np.all(np.isfinite(u)) and np.all(np.isfinite(v)), 'Nonfinite wind samples'
# Combine faces across MPI boundaries before interpolation; lateral BC periodic.
u=.5*(u+np.roll(u,-1,axis=3));v=.5*(v+np.roll(v,-1,axis=2))
mask=np.zeros((len(z),ny,nx),bool)
ijk=np.loadtxt(RUN/'solid_c.txt',comments='#',dtype=int)
mask[ijk[:,2]-1,ijk[:,1]-1,ijk[:,0]-1]=True
for h,k in enumerate(ks):
    u[:,h,mask[k]]=np.nan;v[:,h,mask[k]]=np.nan
speed=np.hypot(u,v)
maximum=float(np.nanmax(speed))
# Full data range, shared across every selected time and height (no clipping).
vmax=np.ceil(maximum*2)/2
plt.rcParams.update({'font.size':10,'figure.dpi':130})
sl=np.s_[::14,::14]

def draw(ax,t,h):
    im=ax.pcolormesh(X,Y,speed[t,h],cmap='viridis',vmin=0,vmax=vmax,
                     shading='nearest',rasterized=True)
    if np.any(mask[ks[h]]):
        ax.contourf(X,Y,mask[ks[h]],levels=[.5,1.5],colors=['#929ca4'])
    ax.quiver(X[sl],Y[sl],u[t,h][sl],v[t,h][sl],color='white',
              scale=190,width=.003,headwidth=3)
    ax.set(xlim=(0,1090),ylim=(0,1350),aspect='equal',xlabel='x (m)',ylabel='y (m)',
           title=f't = {times[t]:.1f} s')
    return im

for h,k in enumerate(ks):
    fig,axes=plt.subplots(2,3,figsize=(13,11.5),constrained_layout=True)
    for t,ax in enumerate(axes.flat):
        im=draw(ax,t,h)
    fig.colorbar(im,ax=axes.ravel().tolist(),shrink=.75,label='Horizontal speed (m/s)')
    fig.suptitle(f'Campus 001 | z = {z[k]:.1f} m | neutral flow\n'
                 'Common scale across times and heights; gray = building solids')
    name=f'campus_wind_z{z[k]:g}'.replace('.','p')
    fig.savefig(OUT/(name+'.png'),dpi=170,bbox_inches='tight')
    fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight');plt.close(fig)

frames=[]
for t in range(len(times)):
    fig,axes=plt.subplots(1,2,figsize=(10,6),constrained_layout=True)
    for h,ax in enumerate(axes):
        im=draw(ax,t,h)
        ax.set_title(f't = {times[t]:.1f} s | z = {z[ks[h]]:.1f} m')
    fig.colorbar(im,ax=axes,shrink=.75,label='Horizontal speed (m/s)')
    fig.suptitle('Campus 001 | initial 60 s neutral-flow evolution')
    stream=io.BytesIO();fig.savefig(stream,format='png',dpi=110);plt.close(fig)
    stream.seek(0);frames.append(Image.open(stream).convert('RGB').copy())
frames[0].save(OUT/'campus_wind_evolution.gif',save_all=True,
               append_images=frames[1:],duration=1000,loop=0)
report={'times_s':times.tolist(),'heights_m':[float(z[k]) for k in ks],
        'mpi_tiles':len(files),'grid_xy':[nx,ny],'colormap_max_m_s':float(vmax),
        'sampled_fluid_speed_min_max_m_s':[float(np.nanmin(speed)),maximum],
        'interpretation':'Initial 60-second transient; not a statistically steady result.',
        'processing':'MPI tiles joined by coordinates, u/v interpolated to centers, solid_c masked; periodic interpolation.'}
(OUT/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
