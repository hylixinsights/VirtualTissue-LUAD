import pandas as pd, numpy as np, h5py, os, time
from shapely import Polygon, STRtree, distance
from shapely.geometry import MultiPoint
D=os.path.expanduser('~/mnt/Xenium'); t0=time.time()
b=pd.read_csv(os.path.join(D,'cell_boundaries.csv'))
f=h5py.File(os.path.join(D,'LUAD3_TLS_GO20_UCell.h5ad'),'r'); o=f['obs']
cid=o['cell_id'][:]
keep=set(cid.tolist())
b=b[b.cell_id.isin(keep)]
print('vertices kept',len(b), time.time()-t0)
arr=b[['vertex_x','vertex_y']].to_numpy()
ids=b.cell_id.to_numpy()
# group contiguous
starts=np.flatnonzero(np.r_[True, ids[1:]!=ids[:-1]])
ends=np.r_[starts[1:], len(ids)]
uid=ids[starts]
polys=[]
bad=0
for s,e in zip(starts,ends):
    pts=arr[s:e]
    if len(pts)<3: bad+=1; polys.append(None); continue
    p=Polygon(pts)
    if not p.is_valid: p=p.buffer(0)
    polys.append(p)
print('polys',len(polys),'bad',bad, time.time()-t0)
ok=np.array([p is not None and not p.is_empty for p in polys])
uid_ok=uid[ok]; polys_ok=[p for p,k in zip(polys,ok) if k]
areas=np.array([p.area for p in polys_ok])
per=np.array([p.length for p in polys_ok])
print('polygon area um2 pct', np.round(np.percentile(areas,[5,25,50,75,95]),1))
print('perimeter um pct', np.round(np.percentile(per,[5,25,50,75,95]),1))
np.save(os.path.expanduser('~/uid_ok.npy'), uid_ok)
import pickle
with open(os.path.expanduser('~/polys.pkl'),'wb') as fh: pickle.dump(polys_ok,fh)
print('saved', time.time()-t0)
import numpy as np, pickle, os, time, h5py, pandas as pd
from shapely import STRtree, distance
t0=time.time()
uid=np.load(os.path.expanduser('~/uid_ok.npy'))
polys=pickle.load(open(os.path.expanduser('~/polys.pkl'),'rb'))
polys=np.array(polys,dtype=object)
GAP=1.0  # um tolerance between polygon boundaries
buf=np.array([p.buffer(GAP/2, quad_segs=2) for p in polys],dtype=object)
print('buffered',time.time()-t0)
tree=STRtree(buf)
a,bq=tree.query(buf, predicate='intersects')
m=a<bq
a,bq=a[m],bq[m]
print('candidate pairs',len(a),time.time()-t0)
d=distance(polys[a],polys[bq])
print('distances',time.time()-t0, 'pct', np.round(np.percentile(d,[5,50,95]),3))
np.savez_compressed(os.path.expanduser('~/pairs.npz'),i=a.astype(np.int32),j=bq.astype(np.int32),d=d.astype(np.float32),uid=uid)
print('saved',time.time()-t0)
import numpy as np, pickle, os, time
from shapely import STRtree, distance
t0=time.time()
uid=np.load(os.path.expanduser('~/uid_ok.npy'))
polys=np.array(pickle.load(open(os.path.expanduser('~/polys.pkl'),'rb')),dtype=object)
buf=np.array([p.buffer(2.5, quad_segs=2) for p in polys],dtype=object)
tree=STRtree(buf)
a,b=tree.query(buf,predicate='intersects'); m=a<b; a,b=a[m],b[m]
print('pairs within 5um gap:',len(a),time.time()-t0)
d=distance(polys[a],polys[b]).astype(np.float32)
np.savez_compressed(os.path.expanduser('~/pairs5.npz'),i=a.astype(np.int32),j=b.astype(np.int32),d=d,uid=uid)
for th in [0.0,0.25,0.5,1.0,2.0,5.0]:
    print(f'  gap<={th}: {int((d<=th).sum())} pairs')
print('done',time.time()-t0)
import numpy as np, pandas as pd, h5py, os
from scipy.spatial import cKDTree
D=os.path.expanduser('~/mnt/Xenium')
z=np.load(os.path.expanduser('~/pairs5.npz'))
uid=z['uid']; I=z['i']; J=z['j']; dd=z['d']
f=h5py.File(os.path.join(D,'LUAD3_TLS_GO20_UCell.h5ad'),'r'); o=f['obs']
def cat(n):
    g=o[n]; c=np.array([x.decode() if isinstance(x,bytes) else x for x in g['categories'][:]])
    return np.where(g['codes'][:]>=0,c[np.clip(g['codes'][:],0,None)],'NA')
cid=o['cell_id'][:]; ctf=cat('cell_type_fine'); xy=f['obsm']['spatial'][:]
pos={c:k for k,c in enumerate(cid)}
row=np.array([pos[c] for c in uid])          # polygon index -> obs row
t_of_poly=ctf[row]
types=sorted(pd.unique(ctf)); ti={t:k for k,t in enumerate(types)}
for TH in (1.0,0.25):
    m=dd<=TH; i=I[m]; j=J[m]
    ta=np.array([ti[t] for t in t_of_poly[i]]); tb=np.array([ti[t] for t in t_of_poly[j]])
    K=len(types); M=np.zeros((K,K))
    np.add.at(M,(ta,tb),1); np.add.at(M,(tb,ta),1)
    deg=np.zeros(len(uid)); np.add.at(deg,i,1); np.add.at(deg,j,1)
    print(f"\n##### CONTACT gap<= {TH} um  ({m.sum()} pairs)")
    dfdeg=pd.DataFrame({'t':t_of_poly,'deg':deg}).groupby('t')['deg'].agg(['size','mean','median'])
    print("mean contacts per cell:"); print(dfdeg.round(2).to_string())
    comp=pd.DataFrame(M/M.sum(axis=1,keepdims=True)*100,index=types,columns=types).round(1)
    pd.set_option('display.width',300)
    print("\ncontact partner composition (%):"); print(comp.to_string())
    glob=np.bincount([ti[t] for t in ctf],minlength=K)/len(ctf)
    print("\nenrichment:"); print(pd.DataFrame((M/M.sum(axis=1,keepdims=True))/glob[None,:],index=types,columns=types).round(2).to_string())
    # P(>=1 contact with type B)
    has={}
    for t in types:
        tgt=np.zeros(len(uid),bool)
        sel=(tb==ti[t]); np.logical_or.at(tgt,i[sel],True)
        sel2=(ta==ti[t]); np.logical_or.at(tgt,j[sel2],True)
        has[t]=tgt
    P=pd.DataFrame({t:{a: round(float(has[t][t_of_poly==a].mean()),4) for a in types} for t in types})
    print("\nP(>=1 true contact with column type), rows=focal:"); print(P.to_string())
    if TH==1.0: P.to_csv(os.path.join(D,'manual_v2_derived','true_contact_probability_gap1um.csv')); comp.to_csv(os.path.join(D,'manual_v2_derived','true_contact_composition_gap1um.csv')); dfdeg.to_csv(os.path.join(D,'manual_v2_derived','true_contact_degree_gap1um.csv'))
import numpy as np, pandas as pd, h5py, os
from scipy.spatial import cKDTree
D=os.path.expanduser('~/mnt/Xenium')
z=np.load(os.path.expanduser('~/pairs5.npz')); uid=z['uid']; I=z['i']; J=z['j']; dd=z['d']
f=h5py.File(os.path.join(D,'LUAD3_TLS_GO20_UCell.h5ad'),'r'); o=f['obs']
def cat(n):
    g=o[n]; c=np.array([x.decode() if isinstance(x,bytes) else x for x in g['categories'][:]])
    return np.where(g['codes'][:]>=0,c[np.clip(g['codes'][:],0,None)],'NA')
cid=o['cell_id'][:]; ctf=cat('cell_type_fine'); xy=f['obsm']['spatial'][:]
pos={c:k for k,c in enumerate(cid)}; row=np.array([pos[c] for c in uid])
XY=xy[row]; T=ctf[row]; N=len(uid)
true=dd<=1.0
Tset=set(zip(I[true].tolist(),J[true].tolist()))
print("true contact pairs:",len(Tset))
tree=cKDTree(XY)
for TH in (10,12,15,20,25,30):
    prs=tree.query_pairs(TH,output_type='ndarray')
    P=set(zip(prs[:,0].tolist(),prs[:,1].tolist()))
    tp=len(P&Tset); prec=tp/max(len(P),1); rec=tp/len(Tset)
    print(f"  centroid<={TH}um: {len(P)} pairs  precision={prec:.3f} recall={rec:.3f} F1={2*prec*rec/max(prec+rec,1e-9):.3f}")
# centroid distance of true contacts
cd_true=np.linalg.norm(XY[I[true]]-XY[J[true]],axis=1)
print("centroid distance of TRUE contacting pairs (um) pct:",np.round(np.percentile(cd_true,[5,25,50,75,95,99]),1))
# per focal type: P(>=1 tumor contact) true vs centroid15
types=sorted(pd.unique(ctf))
def hasP(pairset,tgt):
    h=np.zeros(N,bool)
    for (i,j) in pairset:
        if T[j]==tgt: h[i]=True
        if T[i]==tgt: h[j]=True
    return h
prs15=tree.query_pairs(15,output_type='ndarray'); P15=set(zip(prs15[:,0].tolist(),prs15[:,1].tolist()))
rows=[]
for a in types:
    for b in ['Tumor','T_CD8_cytotoxic','Macrophage_SPP1','B_cell','CAF']:
        ht=hasP(Tset,b); hc=hasP(P15,b); m=T==a
        rows.append(dict(focal=a,target=b,P_true_contact=round(float(ht[m].mean()),4),
                         P_centroid15=round(float(hc[m].mean()),4),
                         ratio=round(float(ht[m].mean()/max(hc[m].mean(),1e-9)),2)))
r=pd.DataFrame(rows); pd.set_option('display.width',250)
print("\nP(>=1 partner of target type): true polygon contact vs centroid<=15um")
print(r.pivot(index='focal',columns='target',values=['P_true_contact','P_centroid15']).to_string())
r.to_csv(os.path.join(D,'manual_v2_derived','contact_truth_vs_centroid.csv'),index=False)
import numpy as np, pandas as pd, h5py, os, pickle, time
from shapely import STRtree, distance, intersection, buffer
t0=time.time()
D=os.path.expanduser('~/mnt/Xenium')
uid=np.load(os.path.expanduser('~/uid_ok.npy'))
polys=np.array(pickle.load(open(os.path.expanduser('~/polys.pkl'),'rb')),dtype=object)
f=h5py.File(os.path.join(D,'LUAD3_TLS_GO20_UCell.h5ad'),'r'); o=f['obs']
def cat(n):
    g=o[n]; c=np.array([x.decode() if isinstance(x,bytes) else x for x in g['categories'][:]])
    return np.where(g['codes'][:]>=0,c[np.clip(g['codes'][:],0,None)],'NA')
cid=o['cell_id'][:]; ctf=cat('cell_type_fine')
pos={c:k for k,c in enumerate(cid)}; row=np.array([pos[c] for c in uid]); T=ctf[row]
# true polygon distance to nearest Tumor polygon
tum=polys[(T=='Tumor')]
tr=STRtree(tum)
for focal in ['T_CD8_cytotoxic','T_CD4','B_cell','CAF','Macrophage_SPP1','Plasma_cell']:
    src=polys[T==focal]
    nn=tr.nearest(src)
    d=distance(src,tum[nn])
    print(f"{focal}: polygon gap to nearest Tumor (um) median {np.median(d):.1f}  q25 {np.percentile(d,25):.1f} q75 {np.percentile(d,75):.1f}  P(<=1um)={float((d<=1).mean()):.4f} P(<=10um)={float((d<=10).mean()):.4f}")
print('nearest done',time.time()-t0)
# interface length approximation
z=np.load(os.path.expanduser('~/pairs5.npz')); I=z['i']; J=z['j']; dd=z['d']
m=dd<=1.0; i=I[m]; j=J[m]
EPS=0.75
bi=buffer(polys[i],EPS,quad_segs=2); bj=buffer(polys[j],EPS,quad_segs=2)
inter=intersection(bi,bj)
L=np.array([g.area for g in inter])/(2*EPS)
print('interface length um pct',np.round(np.percentile(L,[5,25,50,75,95]),2),'time',time.time()-t0)
types=sorted(pd.unique(ctf)); ti={t:k for k,t in enumerate(types)}; K=len(types)
ta=np.array([ti[t] for t in T[i]]); tb=np.array([ti[t] for t in T[j]])
M=np.zeros((K,K)); np.add.at(M,(ta,tb),L); np.add.at(M,(tb,ta),L)
per=np.zeros(len(uid)); np.add.at(per,i,L); np.add.at(per,j,L)
tot=np.array([p.length for p in polys])
df=pd.DataFrame({'t':T,'contact_len':per,'perimeter':tot})
g=df.groupby('t').apply(lambda d: pd.Series({'median_perimeter_um':d.perimeter.median(),
   'median_contact_len_um':d.contact_len.median(),
   'median_contact_fraction':(d.contact_len/d.perimeter).median()}))
pd.set_option('display.width',300)
print("\ncontacted perimeter by cell type:"); print(g.round(3).to_string())
C=pd.DataFrame(M/M.sum(axis=1,keepdims=True)*100,index=types,columns=types).round(1)
print("\ninterface-length-weighted partner composition (%):"); print(C.to_string())
C.to_csv(os.path.join(D,'manual_v2_derived','contact_interface_composition_gap1um.csv'))
g.to_csv(os.path.join(D,'manual_v2_derived','contact_perimeter_by_celltype.csv'))
print('done',time.time()-t0)
import numpy as np, pandas as pd, h5py, os, time
from shapely import Polygon, STRtree, distance
t0=time.time(); D=os.path.expanduser('~/mnt/Xenium')
b=pd.read_csv(os.path.join(D,'cell_boundaries.csv'))
f=h5py.File(os.path.join(D,'LUAD3_TLS_GO20_UCell.h5ad'),'r'); o=f['obs']
cid=set(o['cell_id'][:].tolist())
arr=b[['vertex_x','vertex_y']].to_numpy(); ids=b.cell_id.to_numpy()
s=np.flatnonzero(np.r_[True, ids[1:]!=ids[:-1]]); e=np.r_[s[1:],len(ids)]
uid=ids[s]
polys=np.array([Polygon(arr[a:z]) if z-a>=3 else None for a,z in zip(s,e)],dtype=object)
ok=np.array([p is not None for p in polys]); polys=polys[ok]; uid=uid[ok]
ann=np.array([u in cid for u in uid])
print('total segmented cells with polygons:',len(uid),' annotated:',int(ann.sum()),' NOT in AnnData:',int((~ann).sum()), time.time()-t0)
print('median area annotated %.1f  unannotated %.1f'%(np.median([p.area for p in polys[ann]]),np.median([p.area for p in polys[~ann]])))
buf=np.array([p.buffer(0.5,quad_segs=2) for p in polys],dtype=object)
tree=STRtree(buf); i,j=tree.query(buf,predicate='intersects'); m=i<j; i,j=i[m],j[m]
d=distance(polys[i],polys[j]); k=d<=1.0; i,j=i[k],j[k]
print('all-cell contact pairs (gap<=1um):',len(i), time.time()-t0)
deg_tot=np.zeros(len(uid)); np.add.at(deg_tot,i,1); np.add.at(deg_tot,j,1)
un=(~ann)
deg_un=np.zeros(len(uid))
np.add.at(deg_un,i,un[j].astype(int)); np.add.at(deg_un,j,un[i].astype(int))
def cat(n):
    g=o[n]; c=np.array([x.decode() if isinstance(x,bytes) else x for x in g['categories'][:]])
    return np.where(g['codes'][:]>=0,c[np.clip(g['codes'][:],0,None)],'NA')
ctf=cat('cell_type_fine'); cida=o['cell_id'][:]; pos={c:k for k,c in enumerate(cida)}
ridx=np.array([pos[u] for u in uid[ann]])
df=pd.DataFrame({'t':ctf[ridx],'deg':deg_tot[ann],'deg_unann':deg_un[ann]})
g=df.groupby('t').agg(mean_contacts=('deg','mean'),mean_unannotated_contacts=('deg_unann','mean'),
                      pct_partners_unannotated=('deg_unann','sum'))
g['pct_partners_unannotated']=(g.mean_unannotated_contacts/g.mean_contacts*100).round(1)
print(g.round(2).to_string())
print('\noverall: annotated cells have mean %.2f contacts, of which %.2f (%.1f%%) are cells absent from the AnnData'%(
  df.deg.mean(),df.deg_unann.mean(),100*df.deg_unann.mean()/df.deg.mean()))
print('cells with >=1 unannotated partner: %.1f%%'%(100*(df.deg_unann>0).mean()))
g.to_csv(os.path.join(D,'manual_v2_derived','contact_unannotated_neighbours.csv'))
print('done',time.time()-t0)
