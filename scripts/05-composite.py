
import numpy as np, os
from PIL import Image
import sys

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
base=r'C:\Users\32447\AppData\Local\Temp\dsh'
def L(n): return np.array(Image.open(os.path.join(base,'N_'+n+'.png')).convert('L'))>128
def compose(cu,op,sk,outline):
    img=np.zeros((*cu.shape,3),np.uint8); img[:,:]=[24,27,32]
    img[cu]=[20,22,25]; img[op]=[92,76,40]; img[cu&op]=[214,168,64]; img[sk]=[238,238,238]
    img[outline&~sk&~(cu&op)]=[46,52,58]
    return Image.fromarray(img)
o=L('BoardOutlineLayer')
top=compose(L('TopLayer'),L('TopSolderMaskLayer'),L('TopSilkscreenLayer'),o)
bot=compose(L('BottomLayer'),L('BottomSolderMaskLayer'),L('BottomSilkscreenLayer'),o).transpose(Image.FLIP_LEFT_RIGHT)
w,h=top.size
out=Image.new('RGB',(w,h*2+14),(255,255,255))
out.paste(top,(0,0)); out.paste(bot,(0,h+14))
out.resize((int(w*0.62),int((h*2+14)*0.62)),Image.LANCZOS).save(r'E:\homework\开发\嘉立创电路板开发\skill测试\preview\board-gerber1.png')
print('ok',out.size)
