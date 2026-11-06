
import numpy as np, re
from PIL import Image, ImageDraw
import sys

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
def parse(txt):
    polys=[]; x=y=0.0; region=False; pts=[]
    for ln in txt.splitlines():
        ln=ln.strip()
        if not ln or ln.startswith("G04") or ln.startswith("%"): continue
        if ln.startswith("G36"): region=True; pts=[]; continue
        if ln.startswith("G37"):
            if len(pts)>=3: polys.append(pts)
            region=False; pts=[]; continue
        if re.match(r"^(?:G54)?D(\d+)\*$",ln): continue
        m=re.match(r"^(?:G0?[123])?(?:X(-?\d+))?(?:Y(-?\d+))?D0?([123])\*$",ln)
        if not m: continue
        nx=int(m.group(1))/100000 if m.group(1) else x
        ny=int(m.group(2))/100000 if m.group(2) else y
        if region:
            if not pts or pts[-1]!=(nx,ny): pts.append((nx,ny))
        x,y=nx,ny
    return polys
def analyze(path,x0,x1,y0,y1,S=100.0,label=""):
    polys=parse(open(path,encoding='utf-8',errors='ignore').read())
    W=int((x1-x0)*S); H=int((y1-y0)*S)
    im=Image.new("L",(W,H),0); d=ImageDraw.Draw(im)
    for p in polys:
        d.polygon([((a-x0)*S,(y1-b)*S) for a,b in p],fill=255)
    a=np.array(im)>127
    runs=[]
    for r in range(a.shape[0]):
        idx=np.nonzero(a[r])[0]
        if len(idx)==0: continue
        splits=1+int(np.sum(np.diff(idx)>1))
        st=idx[0]; pv=idx[0]
        for v in idx[1:]:
            if v==pv+1: pv=v
            else: runs.append(pv-st+1); st=v; pv=v
        runs.append(pv-st+1)
    runs=np.array(runs)/S
    if len(runs)==0: print(label,"empty"); return
    print("%-22s rows %4d  run count %5d  min %.3f  p5 %.3f  p50 %.3f mm"%(label,a.shape[0],len(runs),runs.min(),np.percentile(runs,5),np.percentile(runs,50)))
analyze(r'C:\Users\32447\AppData\Local\Temp\dsh\gcq\Gerber_TopSilkscreenLayer.GTO',-21.5,21.5,-18.8,-14.0,100.0,"front EN (silk)")
analyze(r'C:\Users\32447\AppData\Local\Temp\dsh\gcq\Gerber_BottomSilkscreenLayer.GBO',-14,14,-21,-18,100.0,"back CQUPT line (silk)")
analyze(r'C:\Users\32447\AppData\Local\Temp\dsh\gcq\Gerber_TopLayer.GTL',-14.5,14.5,-5.2,23,60.0,"badge (copper)")
