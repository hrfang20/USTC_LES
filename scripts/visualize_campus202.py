"""Campus 202 transient wind, thermal fields and native statistical profiles."""
from pathlib import Path
import sys, json, io
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor/python-deps'))
import numpy as np
import netCDF4 as nc
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
RUN=ROOT/'outputs/campus202_setup/202'
OUT=ROOT/'outputs/validation/figures/campus202'
OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':10,'figure.dpi':130,'axes.formatter.useoffset':False})
files=sorted(RUN.glob('fielddump.*.*.202.nc'))
assert len(files)==4
with nc.Dataset(files[0]) as d:
    times=np.asarray(d['time'][:]);z=np.asarray(d['zt'][:])
nx,ny=218,270;X,Y=np.meshgrid((np.arange(nx)+.5)*5,(np.arange(ny)+.5)*5)
ks=[int(np.argmin(abs(z-h))) for h in [7.5,17.5,57.5]]
fields={v:np.full((len(times),3,ny,nx),np.nan,np.float32) for v in ['u','v','thl','qt']}
coverage=np.zeros((ny,nx),int)
for f in files:
    with nc.Dataset(f) as d:
        np.testing.assert_array_equal(d['time'][:],times)
        ix=np.rint(np.asarray(d['xt'][:])/5-.5).astype(int)
        iy=np.rint(np.asarray(d['yt'][:])/5-.5).astype(int)
        coverage[np.ix_(iy,ix)]+=1
        for name in fields:
            for h,k in enumerate(ks):
                fields[name][:,h,iy[:,None],ix]=np.ma.filled(d[name][:,k],np.nan)
assert np.all(coverage==1)
assert all(np.isfinite(a).all() for a in fields.values())
fields['u']=.5*(fields['u']+np.roll(fields['u'],-1,axis=3))
fields['v']=.5*(fields['v']+np.roll(fields['v'],-1,axis=2))
mask=np.zeros((len(z),ny,nx),bool)
ijk=np.loadtxt(RUN/'solid_c.txt',comments='#',dtype=int)
mask[ijk[:,2]-1,ijk[:,1]-1,ijk[:,0]-1]=True
for a in fields.values():
    for h,k in enumerate(ks):a[:,h,mask[k]]=np.nan
speed=np.hypot(fields['u'],fields['v']);vmax=np.ceil(np.nanmax(speed)*2)/2
selected=np.linspace(0,len(times)-1,6).round().astype(int)
sl=np.s_[::14,::14]
def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=160,bbox_inches='tight')
    fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
def mapplot(ax,t,h,a,lo,hi,cmap,label,arrows=False):
    im=ax.pcolormesh(X,Y,a,cmap=cmap,vmin=lo,vmax=hi,shading='nearest',rasterized=True)
    if mask[ks[h]].any():ax.contourf(X,Y,mask[ks[h]],levels=[.5,1.5],colors=['#929ca4'])
    if arrows:ax.quiver(X[sl],Y[sl],fields['u'][t,h][sl],fields['v'][t,h][sl],color='white',scale=45,width=.003)
    ax.set(xlim=(0,1090),ylim=(0,1350),aspect='equal',xlabel='x (m)',ylabel='y (m)',title=label)
    return im
for h,k in enumerate(ks):
    fig,axes=plt.subplots(2,3,figsize=(13,11),constrained_layout=True)
    for t,ax in zip(selected,axes.flat):im=mapplot(ax,t,h,speed[t,h],0,vmax,'viridis',f't = {times[t]:.1f} s',True)
    fig.colorbar(im,ax=axes.ravel().tolist(),label='Horizontal speed (m/s)',shrink=.7)
    fig.suptitle(f'Campus 202 | z = {z[k]:.1f} m | common wind-speed scale')
    save(fig,f'202_wind_z{z[k]:g}'.replace('.','p'))
frames=[]
for t in range(len(times)):
    fig,axes=plt.subplots(1,2,figsize=(10,6),constrained_layout=True)
    for h,ax in enumerate(axes):im=mapplot(ax,t,h,speed[t,h],0,vmax,'viridis',f't={times[t]:.1f} s | z={z[ks[h]]:.1f} m',True)
    fig.colorbar(im,ax=axes,label='Horizontal speed (m/s)',shrink=.7)
    buf=io.BytesIO();fig.savefig(buf,format='png',dpi=100);plt.close(fig);buf.seek(0)
    frames.append(Image.open(buf).convert('RGB').copy())
frames[0].save(OUT/'202_wind_evolution.gif',save_all=True,append_images=frames[1:],duration=350,loop=0)
h=0
fig,axes=plt.subplots(2,3,figsize=(13,10),constrained_layout=True)
for row,(name,unit) in enumerate([('thl','K'),('qt','g/kg')]):
    a=fields[name][:,h]*(1000 if name=='qt' else 1)
    lo,hi=np.nanmin(a),np.nanmax(a)
    for ax,t in zip(axes[row],[0,len(times)//2,len(times)-1]):
        im=mapplot(ax,t,h,a[t],lo,hi,'magma',f'{name} | t = {times[t]:.1f} s')
    fig.colorbar(im,ax=axes[row].tolist(),label=unit,shrink=.7)
fig.suptitle(f'Campus 202 | thermal/moisture evolution | z={z[ks[h]]:.1f} m')
save(fig,'202_thermal_maps')
with nc.Dataset(RUN/'xytdump.202.nc') as d:
    tp=np.asarray(d['time'][:]);prof={name:np.ma.filled(d[name][:],np.nan) for name in d.variables if d[name].ndim==2}
assert all(np.isfinite(a).all() for a in prof.values())
fig,axes=plt.subplots(2,3,figsize=(14,9),constrained_layout=True)
for ax,(name,label,coord,factor) in zip(axes.flat,[('uxyt','Mean u (m/s)','zt',1),('thlxyt','Liquid-water potential temperature (K)','zt',1),('qtxyt','Total water mixing ratio (g/kg)','zt',1000),('tketxyc','Resolved TKE (m²/s²)','zt',1),('upwpxyt','Resolved u-w covariance (m²/s²)','zm',1),('wpthlpxyt','Resolved heat covariance (K m/s)','zm',1)]):
    for t in [0,len(tp)//2,len(tp)-1]:ax.plot(prof[name][t]*factor,z if coord=='zt' else z-2.5,label=f'{tp[t]:.1f} s')
    ax.set(xlabel=label,ylabel='z (m)',ylim=(0,400));ax.grid(alpha=.2);ax.legend()
fig.suptitle('Campus 202 | native horizontal/time-interval statistical profiles')
fig.savefig(OUT/'202_profiles.png',dpi=160,bbox_inches='tight')
fig.savefig(OUT/'202_profiles.pdf',bbox_inches='tight')
for ax in axes.flat: ax.set_ylim(0,100)
fig.suptitle('Campus 202 | near-surface statistical profiles (0–100 m)')
save(fig,'202_profiles_low100m')
areas=np.loadtxt(RUN/'facetarea.inp.202',comments='#')
with nc.Dataset(RUN/'facT.202.nc') as d:
    ft=np.asarray(d['t'][:]);T=np.ma.filled(d['T'][:,0,:],np.nan)
    Ts=np.average(T,axis=1,weights=areas)
with nc.Dataset(RUN/'facEB.202.nc') as d:
    et=np.asarray(d['t'][:]);flux={name:np.average(np.ma.filled(d[name][:],np.nan),axis=1,weights=areas) for name in ['netsw','LWin','LWout','hf','ef']}
assert np.isfinite(T).all() and all(np.isfinite(a).all() for a in flux.values())
fig,axes=plt.subplots(1,3,figsize=(15,4.8),constrained_layout=True)
for height in [7.5,17.5,57.5]:
    k=int(np.argmin(abs(z-height)));axes[0].plot(tp,prof['uxyt'][:,k],label=f'z={z[k]:g} m')
axes[0].set(xlabel='Simulation time (s)',ylabel='Mean u (m/s)');axes[0].legend()
axes[1].plot(ft,Ts,label='Area-weighted surface mean');axes[1].fill_between(ft,T.min(1),T.max(1),alpha=.2,label='Facet min-max')
axes[1].set(xlabel='Simulation time (s)',ylabel='Surface temperature (K)');axes[1].legend()
for name,a in flux.items():axes[2].plot(et,a,label=name)
axes[2].set(xlabel='Simulation time (s)',ylabel='Stored area-weighted flux (W/m²)');axes[2].legend(ncol=2)
for ax in axes:ax.grid(alpha=.2)
fig.suptitle('Campus 202 | transient diagnostics; stored flux signs retained')
save(fig,'202_transient_diagnostics')
summary={'last_field_time_s':float(times[-1]),'last_profile_time_s':float(tp[-1]),
         'surface_mean_temperature_K':[float(Ts[0]),float(Ts[-1])],
         'surface_final_min_max_K':[float(T[-1].min()),float(T[-1].max())],
         'selected_height_mean_u_m_s':{str(height):[float(prof['uxyt'][0,np.argmin(abs(z-height))]),float(prof['uxyt'][-1,np.argmin(abs(z-height))])] for height in [7.5,17.5,57.5]},
         'last_flux_area_means_W_m2':{name:float(a[-1]) for name,a in flux.items()},
         'finite_checks':'Selected field slices, all native profiles, surface temperatures and area-mean fluxes checked.',
         'notes':['200 s initial transient, not statistically stationary.',
                  'qt native values treated as kg/kg based on source despite incorrect field metadata.',
                  'No independent reference output comparison or complete energy-closure test.']}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
