
# -*- coding: utf-8 -*-
import json, os, shutil, random, time
import sys

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
PRJ = r"C:\Users\32447\Documents\LCEDA-Pro\projects"
SRC = os.path.join(PRJ, "CQUPT_Card")
DST = os.path.join(PRJ, "UESTC70_Card")
if os.path.exists(DST): shutil.rmtree(DST)
shutil.copytree(SRC, DST)
for f in list(os.listdir(DST)):
    if f.endswith(".eprj3"):
        os.replace(os.path.join(DST,f), os.path.join(DST,"UESTC70_Card.eprj3"))
idx_path = os.path.join(DST,"UESTC70_Card.eprj3")
idx = json.load(open(idx_path, encoding="utf-8"))
idx["name"]="UESTC70_Card"; idx["created_at"]=time.strftime("%Y-%m-%d %H:%M:%S"); idx["updated_at"]=idx["created_at"]
json.dump(idx, open(idx_path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

src_pcb = os.path.join(DST,"pcb","PCB1.epcb2")
lines = [l for l in open(src_pcb,encoding="utf-8").read().split("\n") if l.strip()]
KEEP = {"DOCHEAD","META","PRIMITIVE","LAYER","LAYER_PHYS","RULE","RULE_TEMPLATE","CANVAS","ACTIVE_LAYER","PREFERENCE","SILK_OPTS"}
head=[]; outline=[]
tk=0
for l in lines:
    t = l.split('"type":"')[1].split('"')[0]
    import re
    mm_ = re.search(r'"ticket":(\d+)', l)
    if mm_: tk = max(tk, int(mm_.group(1)))
    if t in KEEP: head.append(l)
    elif t=="POLY" and '"layerId":11' in l: outline.append(l)
print("kept head",len(head),"outline",len(outline),"maxticket",tk)

D = json.load(open(r"E:\homework\开发\嘉立创电路板开发\skill测试\UESTC70\gen\rects.json"))
def mir(rs): return [(-(l+w),y,w,h) for (l,y,w,h) in rs]
def q(v): return round(v,4)
uid = lambda: "%016x"%random.getrandbits(64)
recs=[]
def fill(layer, rs, chunk=1):
    for i in range(0,len(rs),chunk):
        part=rs[i:i+chunk]
        path=[["R",q(a*1/0.0254),q(b/0.0254),q(c/0.0254),q(d/0.0254),0,0] for (a,b,c,d) in part]
        recs.append((layer,path))
BD=D["bd"]; NM=D["nm"]; WV=D["wv"]; MT=D["mt"]
def grow(rs,g=0.10): return [(l-g/2,y+g/2,w+g,h+g) for (l,y,w,h) in rs]
fill(1,BD); fill(5,grow(BD,0.10))
fill(1,NM); fill(5,grow(NM,0.10))
fill(2,mir(WV))
fill(2,mir(MT)); fill(6,grow(mir(MT),0.10))
fill(4,D["sk"])
print("fill groups",len(recs),"paths",sum(len(p) for _,p in recs))
out=list(head)+outline
def R(obj): 
    global tk; tk+=1
    return '{"type":"%s","ticket":%d,"id":"%s"}||%s|'
# frame polylines
for layer,w in ((1,10),(5,12)):
    tk+=1
    path=["R",q(-40.9/0.0254),q(24.9/0.0254),q(81.8/0.0254),q(49.8/0.0254),0,q(2.5/0.0254)]
    out.append('{"type":"POLY","ticket":%d,"id":"%s"}||%s|'%(tk,uid(),json.dumps({"partitionId":"","groupId":0,"netName":"","layerId":layer,"width":w,"path":path,"locked":False,"zIndex":-1,"polyType":"NORMAL"},ensure_ascii=False,separators=(',',':'))))
for layer,path in recs:
    tk+=1
    obj={"partitionId":"","groupId":0,"netName":"","layerId":layer,"width":0.2,"fillStyle":"SOLID","path":path,"locked":False,"zIndex":-1,"isBridgingCopper":False,"networkList":[],"refs":[None]}
    out.append('{"type":"FILL","ticket":%d,"id":"%s"}||%s|'%(tk,uid(),json.dumps(obj,ensure_ascii=False,separators=(',',':'))))
# year text on L1 + L5
for layer,sw in ((1,6.5),(5,9.5)):
    tk+=1
    obj={"partitionId":"","groupId":0,"layerId":layer,"x":-410,"y":-835,"text":"1956 — 2026","fontFamily":"default","fontSize":139,"strokeWidth":sw,"bold":False,"italic":False,"origin":"LEFT_BOTTOM","angle":0,"reverse":False,"expansion":0,"mirror":False,"locked":False,"zIndex":3}
    out.append('{"type":"STRING","ticket":%d,"id":"%s"}||%s|'%(tk,uid(),json.dumps(obj,ensure_ascii=False,separators=(',',':'))))
# back silk strings (mirrored so they read from the back)
for txt,cy,fs in ():
    tk+=1
    obj={"partitionId":"","groupId":0,"layerId":4,"x":0,"y":q(cy/0.0254),"text":txt,"fontFamily":"default","fontSize":fs,"strokeWidth":7.9921,"bold":False,"italic":False,"origin":"LEFT_BOTTOM","angle":0,"reverse":False,"expansion":0,"mirror":True,"locked":False,"zIndex":3}
    out.append('{"type":"STRING","ticket":%d,"id":"%s"}||%s|'%(tk,uid(),json.dumps(obj,ensure_ascii=False,separators=(',',':'))))
# hole pad
tk+=1
pad={"partitionId":"","groupId":0,"netName":"","layerId":12,"num":"1","centerX":q(36.8/0.0254),"centerY":q(21.2/0.0254),"padAngle":0,
     "hole":{"holeType":"ROUND","width":q(3.0/0.0254),"height":q(3.0/0.0254),"cornerRadius":q(0.3/0.0254)},
     "defaultPad":{"padType":"ELLIPSE","width":q(4.2/0.0254),"height":q(4.2/0.0254)},"specialPad":[],"padOffsetX":0,"padOffsetY":0,"relativeAngle":0,
     "plated":True,"padType":"NORMAL","topSolderExpansion":None,"bottomSolderExpansion":None,"topPasteExpansion":None,"bottomPasteExpansion":None,"locked":False}
out.append('{"type":"PAD","ticket":%d,"id":"%s"}||%s|'%(tk,uid(),json.dumps(pad,ensure_ascii=False,separators=(',',':'))))
open(src_pcb,"w",encoding="utf-8").write("\n".join(out)+"\n")
print("wrote", len(out), "records", os.path.getsize(src_pcb)//1024, "KB")
