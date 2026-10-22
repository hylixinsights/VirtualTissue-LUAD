import h5py, numpy as np, pandas as pd, scipy.sparse as sp, os, json
from scipy.spatial import cKDTree
from scipy.stats import spearmanr
D=os.path.expanduser('~/mnt/Xenium'); OUT=os.path.join(D,'manual_v2_derived')
f=h5py.File(os.path.join(D,'LUAD3_TLS_GO20_UCell.h5ad'),'r'); o=f['obs']; N=133464
def cat(n):
    g=o[n]; c=np.array([x.decode() if isinstance(x,bytes) else x for x in g['categories'][:]])
    return np.where(g['codes'][:]>=0,c[np.clip(g['codes'][:],0,None)],'NA')
ctf=cat('cell_type_fine'); ft=cat('first_type'); stage=cat('TLS_stage_name'); tclass=cat('TLS_class')
gid=o['geodesic_candidate_id'][:]; core=o['is_candidate_core'][:]; sc=o['go20_scored'][:]
xy=f['obsm']['spatial'][:]; d2t=o['dist_to_nearest_tumor_core'][:]
ng=o['n_genes_by_counts'][:]; tx=o['transcript_counts'][:]; area=o['cell_area'][:]
genes=np.array([x.decode() if isinstance(x,bytes) else x for x in f['var']['_index'][:]])
cols=[k for k in o.keys() if k.endswith('_UCell')]
gs=f['uns']['go20_gene_sets']
def s(x): return [v.decode() if isinstance(v,bytes) else v for v in x[:]]
GS=pd.DataFrame({'process':s(gs['process']),'go_id':s(gs['go_id']),'geneset':s(gs['geneset']),
 'n_genes_geneset':gs['n_genes_geneset'][:],'n_genes_available':gs['n_genes_available'][:],
 'coverage_pct':np.round(gs['coverage_pct'][:],3),'genes_available':s(gs['genes_available']),
 'score_column':s(gs['score_column'])})
proc={r.score_column:r.process for r in GS.itertuples()}
X=pd.DataFrame({proc[c]:o[c][:] for c in cols})
types=sorted(pd.unique(ctf))

# 1 composition
def compo(mask,label,ann,arr):
    v=pd.Series(arr[mask]).value_counts()
    return pd.DataFrame({'region':label,'annotation':ann,'cell_type':v.index,'n':v.values,
                         'pct':np.round(100*v.values/mask.sum(),3),'n_region':mask.sum()})
regs={'whole_section':np.ones(N,bool),'inside_candidates':gid>0,'candidate_core':(gid>0)&(core==1),
 'candidate_surroundings':(gid>0)&(core==0),'outside_candidates':gid<0,
 'tumor_core':o['is_tumor_core'][:].astype(bool),
 'stage_mature':stage=='Secondary Follicle (Mature TLS)','stage_primary':stage=='Primary Follicle (Intermediate TLS)',
 'stage_early':stage=='Early Lympoid Aggregate'}
parts=[]
for k,m in regs.items():
    parts.append(compo(m,k,'cell_type_fine',ctf)); parts.append(compo(m,k,'first_type',ft))
pd.concat(parts).to_csv(os.path.join(OUT,'composition_by_region.csv'),index=False)

# 2 annotation concordance
pd.crosstab(pd.Series(ft,name='first_type'),pd.Series(ctf,name='cell_type_fine')).to_csv(os.path.join(OUT,'annotation_crosstab_first_type_vs_cell_type_fine.csv'))

# 3 score reference by cell type
S=X[sc].copy(); S['cell_type_fine']=ctf[sc]; S['first_type']=ft[sc]; S['is_core']=core[sc]
rows=[]
for ann in ['cell_type_fine','first_type']:
    for t,g in S.groupby(ann):
        for p in X.columns:
            v=g[p].values
            rows.append(dict(annotation=ann,cell_type=t,process=p,n=len(v),
              zero_frac=round(float((v==0).mean()),4),q10=round(float(np.percentile(v,10)),4),
              q25=round(float(np.percentile(v,25)),4),median=round(float(np.median(v)),4),
              q75=round(float(np.percentile(v,75)),4),q90=round(float(np.percentile(v,90)),4),
              q99=round(float(np.percentile(v,99)),4),mean=round(float(v.mean()),4),max=round(float(v.max()),4)))
pd.DataFrame(rows).to_csv(os.path.join(OUT,'ucell_reference_by_celltype.csv'),index=False)
# core vs surroundings within cell type
rows=[]
for t,g in S.groupby('cell_type_fine'):
    for p in X.columns:
        a=g.loc[g.is_core==1,p].values; b=g.loc[g.is_core==0,p].values
        rows.append(dict(cell_type=t,process=p,n_core=len(a),n_surr=len(b),
          med_core=round(float(np.median(a)),4) if len(a) else None,
          med_surr=round(float(np.median(b)),4) if len(b) else None,
          delta=round(float(np.median(a)-np.median(b)),4) if len(a) and len(b) else None))
pd.DataFrame(rows).to_csv(os.path.join(OUT,'ucell_core_vs_surroundings_by_celltype.csv'),index=False)

# 4 signature audit + depth confound
aud=[]
for p in X.columns:
    v=X[p][sc].values
    r_all=spearmanr(v,ng[sc]).statistic
    per={}
    for t in ['B_cell','T_CD8_cytotoxic','T_CD4','Tumor','Plasma_cell','Macrophage_SPP1']:
        m=ctf[sc]==t; per[t]=round(float(spearmanr(v[m],ng[sc][m]).statistic),3)
    row=GS[GS.process==p].iloc[0]
    aud.append(dict(process=p,go_id=row.go_id,geneset=row.geneset,n_genes_geneset=int(row.n_genes_geneset),
      n_genes_available=int(row.n_genes_available),coverage_pct=float(row.coverage_pct),
      rho_ngenes_all=round(float(r_all),3),**{f'rho_{k}':v2 for k,v2 in per.items()},
      genes_available=row.genes_available))
pd.DataFrame(aud).to_csv(os.path.join(OUT,'signature_audit.csv'),index=False)

# 5 candidate summary
rows=[]
for g in range(1,29):
    m=gid==g; mc=m&(core==1); s2=pd.Series(stage[mc]).value_counts()
    c=pd.Series(ctf[m]).value_counts(normalize=True)*100
    cc=pd.Series(ctf[mc]).value_counts(normalize=True)*100
    rows.append(dict(candidate=f'B{g}',n_cells=int(m.sum()),n_core=int(mc.sum()),
      stage_core=s2.index[0] if len(s2) else 'NA',
      width_um=round(float(xy[m,0].max()-xy[m,0].min()),1),height_um=round(float(xy[m,1].max()-xy[m,1].min()),1),
      median_dist_tumor_core_um=round(float(np.median(d2t[m])),1),
      pct_first_type_B=round(float((ft[m]=='B_cell').mean()*100),2),
      **{f'pct_{t}':round(float(c.get(t,0)),2) for t in types},
      **{f'core_pct_{t}':round(float(cc.get(t,0)),2) for t in types},
      n_TLS_class_candidate=int((tclass[m]=='TLS_candidate').sum()),
      n_TLS_class_Baggregate=int((tclass[m]=='B_aggregate').sum())))
pd.DataFrame(rows).to_csv(os.path.join(OUT,'candidate_summary.csv'),index=False)

# 6 neighbourhood + contact opportunity
tree=cKDTree(xy); K=len(types); ti={t:i for i,t in enumerate(types)}; code=np.array([ti[t] for t in ctf])
for R in (15.0,30.0):
    M=np.zeros((K,K))
    for i,nb in enumerate(tree.query_ball_point(xy,R)):
        a=code[i]
        for j in nb:
            if j!=i: M[a,code[j]]+=1
    obs_=M/M.sum(axis=1,keepdims=True); glob=np.bincount(code,minlength=K)/N
    pd.DataFrame(np.round(obs_*100,3),index=types,columns=types).to_csv(os.path.join(OUT,f'neighbourhood_composition_{int(R)}um.csv'))
    pd.DataFrame(np.round(obs_/glob[None,:],3),index=types,columns=types).to_csv(os.path.join(OUT,f'neighbourhood_enrichment_{int(R)}um.csv'))
trees={t:cKDTree(xy[ctf==t]) for t in types}
for R in (15.0,30.0):
    out={}
    for a in types:
        A=xy[ctf==a]; r={}
        for b in types:
            d,_=trees[b].query(A,k=2 if a==b else 1); dd=d[:,1] if a==b else d
            r[b]=round(float((dd<=R).mean()),4)
        out[a]=r
    pd.DataFrame(out).T.to_csv(os.path.join(OUT,f'contact_opportunity_{int(R)}um.csv'))
out={}
for a in types:
    A=xy[ctf==a]; r={}
    for b in types:
        d,_=trees[b].query(A,k=2 if a==b else 1); dd=d[:,1] if a==b else d
        r[b]=round(float(np.median(dd)),2)
    out[a]=r
pd.DataFrame(out).T.to_csv(os.path.join(OUT,'median_nn_distance_um.csv'))

# 7 gene detection by cell type (raw and purified)
L=f['layers']['raw_counts']; R_=sp.csr_matrix((L['data'][:],L['indices'][:],L['indptr'][:]),shape=(N,302))
L2=f['layers']['purified_raw']; P_=sp.csc_matrix((L2['data'][:],L2['indices'][:],L2['indptr'][:]),shape=(N,302)).tocsr()
Rb=(R_>0).astype(np.float32); Pb=(P_>0).astype(np.float32)
det={}; detp={}
for t in types:
    m=ctf==t
    det[t]=np.asarray(Rb[m].mean(axis=0)).ravel(); detp[t]=np.asarray(Pb[m].mean(axis=0)).ravel()
Dr=pd.DataFrame(det,index=genes).round(4); Dr['overall']=np.asarray(Rb.mean(axis=0)).ravel().round(4)
Dp=pd.DataFrame(detp,index=genes).round(4); Dp['overall']=np.asarray(Pb.mean(axis=0)).ravel().round(4)
Dr.to_csv(os.path.join(OUT,'gene_detection_by_celltype_raw_counts.csv'))
Dp.to_csv(os.path.join(OUT,'gene_detection_by_celltype_purified_raw.csv'))

# 8 distance bands
bands=pd.cut(d2t,[-0.01,0,25,50,100,250,500,1e9],labels=['core(0)','0-25','25-50','50-100','100-250','250-500','>500'])
tab=pd.crosstab(bands,ctf); tab['n_band']=tab.sum(axis=1)
tab.to_csv(os.path.join(OUT,'composition_by_distance_band_to_tumor_core.csv'))

# 9 QC by cell type
q=pd.DataFrame({'cell_type_fine':ctf,'n_genes':ng,'transcripts':tx,'area':area,'scored':sc})
q.groupby('cell_type_fine').agg(n=('n_genes','size'),med_genes=('n_genes','median'),
  med_tx=('transcripts','median'),med_area=('area','median'),n_scored=('scored','sum')).to_csv(os.path.join(OUT,'qc_by_celltype.csv'))
print('done'); print(sorted(os.listdir(OUT)))
