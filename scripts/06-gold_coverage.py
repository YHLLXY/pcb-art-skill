
import numpy as np, os
from PIL import Image, ImageDraw
import sys

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
base=r'C:\Users\32447\AppData\Local\Temp\dsh'
def L(n): return np.array(Image.open(os.path.join(base,'N_'+n+'.png')).convert('L'))>128
ao=L('BoardOutlineLayer'); ys,xs=np.nonzero(ao)
im=Image.new('L',(ao.shape[1],ao.shape[0]),0)
ImageDraw.Draw(im).rounded_rectangle((xs.min(),ys.min(),xs.max(),ys.max()),radius=3.5*20,fill=255)
a=np.asarray(im)>0
gold=(L('TopLayer')&L('TopSolderMaskLayer'))|(L('BottomLayer')&L('BottomSolderMaskLayer'))
print("board mm2", round(int(a.sum())/400.0,1))
print("gold mm2", round(int(gold.sum())/400.0,1), "coverage %", round(100.0*gold.sum()/a.sum(),1))
OUT=r'C:\Users\32447\AppData\Local\Temp\dsh\pkgc'
os.makedirs(OUT,exist_ok=True)
for nm,(cu,op,sk) in {"front":(L('TopLayer'),L('TopSolderMaskLayer'),L('TopSilkscreenLayer')),
                      "back":(L('BottomLayer'),L('BottomSolderMaskLayer'),L('BottomSilkscreenLayer'))}.items():
    img=np.zeros((*cu.shape,3),np.uint8); img[:,:]=[18,20,24]
    img[cu]=[16,18,21]; img[cu&op]=[206,168,96]; img[sk]=[238,238,240]
    c=Image.fromarray(img)
    if nm=="back": c=c.transpose(Image.FLIP_LEFT_RIGHT)
    crop=c.crop((xs.min()-6,ys.min()-6,xs.max()+6,ys.max()+6)); crop.save(os.path.join(OUT,nm+".png"))
print("previews ok")
