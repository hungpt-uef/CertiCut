"""Solver-agnostic root LP decomposition for B0/C/T/CT."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from time import perf_counter
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
from certicut.graph.interaction import InteractionGraph

@dataclass(frozen=True)
class CoreRootLPResult:
    variant: str; status: str; lower_bound: float | None; z_values: tuple[float,...] | None; x_values: dict[tuple[int,int],float] | None; root_integral: bool; separation_rounds: int; active_triangles: tuple[tuple[int,int,int,int],...]; variable_count: int; constraint_count: int; lp_time_s: float

def _violations(x,n,tol):
    out=[]
    for i,j,k in combinations(range(n),3):
        ij,ik,jk=x[i,j],x[i,k],x[j,k]
        for kind,value in enumerate((ij-ik-jk,ik-ij-jk,jk-ij-ik,ij+ik+jk-2)):
            if value>tol: out.append((value,(i,j,k,kind)))
    return sorted(out,reverse=True)

def solve_core_root_lp(graph: InteractionGraph,*,variant:str,tolerance:float=1e-9,max_rounds:int=100)->CoreRootLPResult:
    n=graph.num_qubits
    if n<1 or n%2: raise ValueError("requires positive even size")
    if variant not in ("b0","cardinality","triangles","b2s"): raise ValueError(variant)
    pairs=tuple(combinations(range(n),2)); pi={p:n+i for i,p in enumerate(pairs)}
    use_c=variant in ("cardinality","b2s"); use_t=variant in ("triangles","b2s"); active=[]; start=perf_counter()
    for rnd in range(max_rounds+1):
        vars=n+len(pairs); rows=1+4*len(pairs)+(1 if use_c else 0)+len(active); A=lil_matrix((rows,vars)); lo=np.full(rows,-np.inf); hi=np.full(rows,np.inf); r=0
        for q in range(n): A[r,q]=1
        lo[r]=hi[r]=n/2; r+=1
        for u,v in pairs:
            x=pi[u,v]
            A[r,x],A[r,u],A[r,v]=1,-1,1;lo[r]=0;r+=1
            A[r,x],A[r,u],A[r,v]=1,1,-1;lo[r]=0;r+=1
            A[r,x],A[r,u],A[r,v]=1,-1,-1;hi[r]=0;r+=1
            A[r,x],A[r,u],A[r,v]=1,1,1;hi[r]=2;r+=1
        if use_c:
            for p in pairs:A[r,pi[p]]=1
            lo[r]=hi[r]=(n//2)**2;r+=1
        for i,j,k,kind in active:
            ij,ik,jk=pi[i,j],pi[i,k],pi[j,k]
            if kind==0:A[r,ij],A[r,ik],A[r,jk]=1,-1,-1;hi[r]=0
            elif kind==1:A[r,ik],A[r,ij],A[r,jk]=1,-1,-1;hi[r]=0
            elif kind==2:A[r,jk],A[r,ij],A[r,ik]=1,-1,-1;hi[r]=0
            else:A[r,ij],A[r,ik],A[r,jk]=1,1,1;hi[r]=2
            r+=1
        eq=[0]+([1+4*len(pairs)] if use_c else []); ge=[q for q in range(rows) if q not in eq and np.isfinite(lo[q])]; le=[q for q in range(rows) if q not in eq and np.isfinite(hi[q])]
        aub=lil_matrix((len(ge)+len(le),vars)); bub=np.empty(len(ge)+len(le))
        for out,src in enumerate(ge): aub[out,:]=-A[src,:];bub[out]=-lo[src]
        for out,src in enumerate(le,start=len(ge)): aub[out,:]=A[src,:];bub[out]=hi[src]
        c=np.zeros(vars)
        for e in graph.edges:c[pi[e.u,e.v]]=e.qpd_log_cost
        bounds=[(0,1)]*vars;bounds[0]=(0,0)
        raw=linprog(c,A_ub=aub.tocsr() if len(bub) else None,b_ub=bub if len(bub) else None,A_eq=A[eq,:].tocsr(),b_eq=lo[eq],bounds=bounds,method="highs")
        if raw.status!=0 or raw.x is None: raise RuntimeError(f"root LP {raw.status}")
        z=tuple(float(raw.x[q]) for q in range(n));x={p:float(raw.x[pi[p]]) for p in pairs}
        if not use_t:return CoreRootLPResult(variant,"optimal",float(raw.fun),z,x,all(abs(v-round(v))<tolerance for v in z),rnd,tuple(active),vars,rows,perf_counter()-start)
        add=[cut for _,cut in _violations(x,n,tolerance) if cut not in set(active)]
        if not add:return CoreRootLPResult(variant,"optimal",float(raw.fun),z,x,all(abs(v-round(v))<tolerance for v in z),rnd,tuple(active),vars,rows,perf_counter()-start)
        active.extend(add)
    raise RuntimeError("separation max rounds")
