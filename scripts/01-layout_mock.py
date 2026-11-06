
# -*- coding: utf-8 -*-
import numpy as np, os
from PIL import Image, ImageDraw, ImageFont
import sys

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ROOT=r"E:\homework\开发\嘉立创电路板开发\skill测试"
S=13.0
W=int(92*S); H=int(62*S)
def X(x): return (x+46)*S
def Y(y): return (31-y)*S
GOLD=(206,168,96); SILK=(238,238,242); BG=(12,12,14); CU=(22,22,25); WEAVE=(34,33,35)
# 华文行楷是商业字体，仅本机自带；换 OFL 字体见 references/02「字体可以换」
FX=r"C:\Windows\Fonts\STXINGKA.TTF"; FT=r"C:\Windows\Fonts\times.ttf"
_M=ImageDraw.Draw(Image.new("L",(8,8),0))
def fit_h(s,fp,target_px,sp):
    n=len(s); px=max(6,int(target_px/(n*0.95+sp*(n-1))))
    for _ in range(5):
        f=ImageFont.truetype(fp,px)
        tot=sum(_M.textlength(c,font=f) for c in s)+px*sp*(n-1)
        if tot<=0: break
        px=max(6,int(px*target_px/tot))
    return px
def fit_v(s,fp,target_px,sp):
    n=len(s); px=max(6,int(target_px/(n*0.95+sp*(n-1))))
    for _ in range(5):
        f=ImageFont.truetype(fp,px)
        tot=sum((_M.textbbox((0,0),c,font=f)[3]-_M.textbbox((0,0),c,font=f)[1]) for c in s)+px*sp*(n-1)
        if tot<=0: break
        px=max(6,int(px*target_px/tot))
    return px
def weave_rects(x0,x1,y0,y1,cell=2.0,pitch=0.22,w=0.11):
    out=[]; nx=int(round((x1-x0)/cell)); ny=int(round((y1-y0)/cell))
    for m in range(ny+1):
        for k in range(nx+1):
            r=(k-m)%4; bx=x0+k*cell; by=y0+m*cell
            if r==0:
                yy=by+pitch*0.5
                while yy<by+cell-0.001: out.append((bx,yy,2*cell,w)); yy+=pitch
            elif r==3:
                xx=bx+pitch*0.5
                while xx<bx+cell-0.001: out.append((xx,by+2*cell,w,2*cell)); xx+=pitch
    return out
BADGE=None
def badge_mask():
    global BADGE
    if BADGE is None:
        im=Image.open(os.path.join(ROOT,"assets","cqupt-badge.png")).convert("RGBA")
        a=np.asarray(im); rgb=a[:,:,:3].astype(int); al=a[:,:,3]
        ink=((rgb.mean(axis=2)<190)&(al>128)); ys,xs=np.nonzero(ink)
        BADGE=Image.fromarray((ink[ys.min():ys.max()+1,xs.min():xs.max()+1]*255).astype(np.uint8))
    return BADGE
def base():
    im=Image.new("RGB",(W,H),BG)
    ImageDraw.Draw(im).rounded_rectangle([X(-43),Y(27),X(43),Y(-27)],radius=3.5*S,fill=CU); return im
def border(im):
    ImageDraw.Draw(im).rounded_rectangle([X(-41),Y(25),X(41),Y(-25)],radius=2.5*S,outline=GOLD,width=max(2,round(0.254*S)))
def weave(im):
    d=ImageDraw.Draw(im)
    for (x,y,w,h) in weave_rects(-40.6,40.6,-24.6,24.6):
        if x<-41 or x+w>41.01 or y>25 or y-h<-25: continue
        d.rectangle([X(x),Y(y),X(x+w),Y(y-h)],fill=WEAVE)
def badge(im,cx,cy,wmm,col=GOLD):
    mk=badge_mask(); s=wmm*S/mk.width
    m2=mk.resize((int(mk.width*s),int(mk.height*s)),Image.LANCZOS)
    im.paste(col,(int(X(cx)-m2.width/2),int(Y(cy)-m2.height/2)),m2)
def row(im,s,fp,width_mm,cx,cy,col,sp=0.20):
    px=fit_h(s,fp,width_mm*S,sp); d=ImageDraw.Draw(im); f=ImageFont.truetype(fp,px)
    wid=[d.textlength(c,font=f) for c in s]; gap=px*sp
    tot=sum(wid)+gap*(len(s)-1); x=X(cx)-tot/2
    for c,w in zip(s,wid):
        d.text((x,Y(cy)),c,font=f,fill=col,anchor='lm'); x+=w+gap
    return tot/S
def coln(im,s,fp,height_mm,cx,y_top,col,sp=0.28):
    px=fit_v(s,fp,height_mm*S,sp); d=ImageDraw.Draw(im); f=ImageFont.truetype(fp,px)
    gap=px*sp; y=y_top
    for c in s:
        b=d.textbbox((0,0),c,font=f)
        d.text((X(cx),Y(y-(b[3]-b[1])/2/S)),c,font=f,fill=col,anchor='mm')
        y-=(b[3]-b[1])/S+gap/S
def trow(im,s,fp,width_mm,cx,cy,col):
    px=fit_h(s,fp,width_mm*S,0.0); d=ImageDraw.Draw(im); f=ImageFont.truetype(fp,px)
    d.text((X(cx),Y(cy)),s,font=f,fill=col,anchor='mm')
def hole(im,cx,cy,r=2.1,ri=1.5):
    d=ImageDraw.Draw(im)
    d.ellipse([X(cx-r),Y(cy+r),X(cx+r),Y(cy-r)],fill=GOLD)
    d.ellipse([X(cx-ri),Y(cy+ri),X(cx+ri),Y(cy-ri)],fill=BG)

f=base(); weave(f); border(f)
badge(f,0,8.8,26.5)
coln(f,"修德博学",FX,13.5,-32.8,16.4,GOLD)
coln(f,"求实创新",FX,13.5,32.8,16.4,GOLD)
w1=row(f,"重庆邮电大学",FX,33.0,0,-9.8,GOLD)
w2=row(f,"CHONGQING UNIVERSITY OF POSTS AND TELECOMMUNICATIONS",FT,42.0,0,-16.4,SILK,0.02)
hole(f,37.2,20.6)
print("校名 width",round(w1,1),"英文 width",round(w2,1))

b=base(); weave(b); border(b)
row(b,"修德博学",FX,33.0,0,4.2,GOLD)
row(b,"求实创新",FX,33.0,0,-6.2,GOLD)
trow(b,"1950",FT,12.0,0,-14.2,GOLD)
trow(b,"CQUPT · CHONGQING · CHINA",FT,26.0,0,-19.6,SILK)

sheet=Image.new("RGB",(W*2+36,H+28),(24,24,26))
sheet.paste(f,(10,10)); sheet.paste(b,(W+26,10))
dd=ImageDraw.Draw(sheet); ff=ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc",15)
dd.text((10,H+8),"FRONT",font=ff,fill=(150,150,160)); dd.text((W+26,H+8),"BACK",font=ff,fill=(150,150,160))
sheet.save(os.path.join(ROOT,"preview","layout-v3.png")); print("ok")
