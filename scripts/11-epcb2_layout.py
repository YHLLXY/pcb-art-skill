
# -*- coding: utf-8 -*-
import numpy as np, os, math, json
from PIL import Image, ImageDraw, ImageFont
import sys

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ROOT=r"E:\homework\开发\嘉立创电路板开发\skill测试\UESTC70"
OUT=os.path.join(ROOT,"gen"); K=0.0254
# 华文行楷是商业字体，仅本机自带；换 OFL 字体见 references/02「字体可以换」
FX=r"C:\Windows\Fonts\STXINGKA.TTF"; FC=r"C:\Windows\Fonts\consola.ttf"
_M=ImageDraw.Draw(Image.new("L",(8,8),0))
def fit_px(s,fp,target_px,sp=0.0):
    n=len(s); px=max(6,int(target_px/(n*0.95+sp*(n-1))))
    for _ in range(6):
        f=ImageFont.truetype(fp,px)
        tot=sum(_M.textlength(c,font=f) for c in s)+px*sp*(n-1)
        if tot<=0: break
        px=max(6,int(px*target_px/tot))
    return px
def text_mask_row(s,fp,width_mm,sp=0.10):
    PX=fit_px(s,fp,width_mm*40,sp); f=ImageFont.truetype(fp,PX); d=_M
    wid=[d.textlength(c,font=f) for c in s]; gap=PX*sp
    tot=sum(wid)+gap*(len(s)-1)
    im=Image.new("L",(int(tot)+40,PX*2+40),0); dr=ImageDraw.Draw(im); x=20
    for c,w in zip(s,wid):
        dr.text((x,20),c,font=f,fill=255); x+=w+gap
    return im.crop(im.getbbox())
def scan(img,w_mm,cx,cy,step=0.06,minw=0.10,hfac=1.25,mirror=False):
    a=np.asarray(img)>127; H,W=a.shape
    s=w_mm/W; TH=H*s; rows=int(round(TH/step)); xl=cx-w_mm/2.0; yt=cy+TH/2.0; out=[]
    for r in range(rows):
        py=int(((r+0.5)*step)/s)
        if py<0 or py>=H: continue
        idx=np.nonzero(a[py])[0]
        if len(idx)==0: continue
        runs=[];st=idx[0];pv=idx[0]
        for v in idx[1:]:
            if v==pv+1: pv=v
            else: runs.append((st,pv)); st=v; pv=v
        runs.append((st,pv)); yc=yt-(r+0.5)*step
        for (s0,s1) in runs:
            x0=xl+s0*s; x1=xl+(s1+1)*s
            if x1-x0<minw: x1=x0+minw
            w=x1-x0; left=x0 if not mirror else -(x0+w)
            out.append((left,yc+step/2.0,w,step*hfac))
    return out
def emits(name,layer,rs,chunk=500):
    n=0
    for i in range(0,len(rs),chunk):
        body=",".join("[%s,%s,%s,%s]"%(round(a/K,1),round(b/K,1),round(c/K,1),round(d/K,1)) for (a,b,c,d) in rs[i:i+chunk])
        js=("const M=eda.pcb_MathPolygon,F=eda.pcb_PrimitiveFill;const D=[%s];"
            "for(const d of D){await(F.create(%d,M.createPolygon(['R',d[0],d[1],d[2],d[3],0,0]),'',0,0,false));}"
            "await(eda.pcb_Document.save());return 'ok '+D.length;"%(body,layer))
        open(os.path.join(OUT,"%s_%02d.js"%(name,i//chunk)),"w",encoding="utf-8").write(js); n+=1
    print("%-6s L%-2d %6d rects %2d files"%(name,layer,len(rs),n))
def grow(rs,g=0.10): return [(l-g/2,y+g/2,w+g,h+g) for (l,y,w,h) in rs]
def mirror(rs): return [(-(l+w),y,w,h) for (l,y,w,h) in rs]

BD_D=30.0; BD_CY=7.8
im=Image.open(os.path.join(ROOT,"assets","uestc-badge.png")).convert("RGBA")
a=np.asarray(im).astype(int)
r_,g_,b_,al=a[:,:,0],a[:,:,1],a[:,:,2],a[:,:,3]
H,W=al.shape; cy,cx=510.5,511.0
Y,X=np.mgrid[0:H,0:W]; R=np.hypot(X-cx,Y-cy)
blue=(al>128)&(b_>110)&(b_>r_+30)
orange=(al>128)&(r_>170)&(g_>70)&(g_<170)&(b_<110)
SC=BD_D/(2*510.7); RO,RI=510.7,318.0
ann=(R<=RO-0.30/SC)&(R>=RI+0.20/SC)
chars=ann&~blue&~orange
motif=(R<=RI)&(blue|orange)
ring=(np.abs(R-RO)<(0.50/SC)/2)|(np.abs(R-RI)<(0.30/SC)/2)
gold_badge=chars|motif|ring
ys,xs=np.nonzero(gold_badge); y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
side=max(y1-y0,x1-x0)+8
mk=Image.new("L",(side,side),0)
mk.paste(Image.fromarray((gold_badge[y0:y1+1,x0:x1+1]*255).astype(np.uint8)), ((side-(x1-x0))//2,(side-(y1-y0))//2))
BDW=side*SC
BD=scan(mk,BDW,0.0,BD_CY,minw=0.13)
emits("bd1",1,BD); emits("bd5",5,grow(BD,0.10))
print("badge side %.2f mm rects %d"%(BDW,len(BD)))

NAME="电子科技大学"; NW=40.0
m=text_mask_row(NAME,FX,NW,0.12); NH=NW*m.height/m.width
NM=scan(m,NW,0.0,-13.3,minw=0.13)
emits("nm1",1,NM); emits("nm5",5,grow(NM,0.10))
print("name w=%.1f h=%.2f rects %d"%(NW,NH,len(NM)))

def weave_rects(clipx=40.85,clipy=24.85,rad=2.2,cell=2.0,pitch=0.22,w=0.11):
    def limx(y):
        ay=abs(y)
        if ay>clipy: return None
        if ay<=clipy-rad: return clipx
        d=clipy-rad; return clipx-rad+math.sqrt(max(0.0,rad*rad-(ay-d)**2))
    def limy(x):
        ax=abs(x)
        if ax>clipx: return None
        if ax<=clipx-rad: return clipy
        d=clipx-rad; return clipy-rad+math.sqrt(max(0.0,rad*rad-(ax-d)**2))
    out=[]
    n=int(math.ceil(clipx*2/cell))+2; m0=-n//2
    for mm in range(m0,m0+n+1):
        for k in range(m0,m0+n+1):
            rr=(k-mm)%4; bx=k*cell; by=mm*cell
            if rr==0:
                yy=by+pitch*0.5
                while yy<by+cell-0.001:
                    L=limx(yy)
                    if L and L>0:
                        a0=max(bx,-L); a1=min(bx+2*cell,L)
                        if a1-a0>0.02: out.append((a0,yy,a1-a0,w))
                    yy+=pitch
            elif rr==3:
                xx=bx+pitch*0.5
                while xx<bx+cell-0.001:
                    L=limy(xx)
                    if L and L>0:
                        a0=max(by,-L); a1=min(by+2*cell,L)
                        if a1-a0>0.02: out.append((xx,a1,w,a1-a0))
                    xx+=pitch
    return out
WV=weave_rects()
emits("wv2",2,mirror(WV)); print("weave",len(WV))

MO1,MO2="求实求真","大气大为"; MW=34.0
m1=text_mask_row(MO1,FX,MW,0.16); m2=text_mask_row(MO2,FX,MW,0.16)
MT=scan(m1,MW,0.0,4.6,minw=0.13)+scan(m2,MW,0.0,-5.8,minw=0.13)
emits("mt2",2,mirror(MT)); emits("mt6",6,grow(mirror(MT),0.10)); print("motto rects",len(MT))
SK1=scan(text_mask_row("UESTC · CHENGDU · CHINA",FC,30.0,0.10),30.0,0.0,-15.6,minw=0.15,mirror=True)
SK2=scan(text_mask_row("70TH ANNIVERSARY",FC,24.0,0.10),24.0,0.0,-19.2,minw=0.15,mirror=True)
SK=SK1+SK2
print("silk rects",len(SK))
json.dump({"bd":BD,"nm":NM,"wv":WV,"mt":MT,"sk":SK,"bdw":BDW,"nh":NH},open(os.path.join(OUT,"rects.json"),"w"))
print("TOTAL", len(BD)+len(NM)+len(WV)+len(MT))
