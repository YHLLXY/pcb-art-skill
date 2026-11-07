# EDA 落地 · Making It Real in EDA（EasyEDA 专业版）

## 环境

```
lceda-pro <cmd> --ext-uuid eda --session <sessionId>
```

- `doctor` → 必须 `connected:true`
- `session list` → 拿 `sessionId`（`status:"alive"`）
- `invoke --code "<js>"` → 在应用里执行

**不带 --session 会报 `NEED_SESSION`。**

## 传代码的三条硬规矩（本轮实测）

1. **JS 里不能有双引号。** 字符串一律单引号，中文用 `String.fromCharCode()`。
   长代码走文件：`$c = Get-Content -Raw -Encoding UTF8 x.js; & $exe invoke ... --code $c`
2. **支持顶层 `await`，`return 值` 就是命令返回的 `value`。**
   `(async()=>{})()` 返回的是 Promise → 拿到 `null`（排查时最容易被这个骗）。
3. **`return` 的字符串会被截断**（约 60 KB）。要导出大块数据就分批查，别指望一次吐 12 万条图元。

## API 使用纪律

1. **先查签名，再调用。** 顺序是：
   ① **官方类型定义**（最权威，每个方法注释里都有可直接抄的示例）：

   ```
   F:\嘉立创\lceda-pro\resources\app\assets\pro-api\<版本>\api-types.d.ts   （约 1.7 MB）
   ```

   直接 grep 方法名，例如 `createPad`、`PrimitivePolyline`，注释里就是完整调用。
   ② 本文件下面那张已验证表 → ③ `Object.getOwnPropertyNames(Object.getPrototypeOf(eda.pcb_XXX))` 列方法
   → ④ 拿一个已有图元回读 `getState_*` 看真实字段。

   **猜一次签名约 90 秒（还常常连错三次），grep 一次 10 秒。**

   **关键：polygon 不是点数组，必须是 `pcb_MathPolygon.createPolygon()` 的返回值。**
   传 `[[x,y],...]` 或扁平数组都会报 `无法创建多边形图元`。
   注意两个 create 里 polygon 的位置**不一样**：`Polyline.create(net, layer, polygon, lw, ?)` 在第 3 位，
   `Fill.create(layer, polygon, '', 0, 0, false)` 在第 2 位。正确写法：

   ```javascript
   const poly = eda.pcb_MathPolygon.createPolygon(['R', x, y, w, h, rot, r]);  // 圆角矩形
   await eda.pcb_PrimitivePolyline.create('', 11, poly, 10, false);            // 板框
   ```

   `['R', x, y, w, h, rot, r]` 中 `x,y` 是左上角，`h` 向 **−y** 方向延伸。
   实测回读：`86×54 mm` 板框 → `["R",-1692.91,1062.99,3385.83,2125.98,0,137.80]`（mil）。
2. **每步 save + 读回。** 画完立刻 `pcb_Document.save()`，再查图元数。
3. 连续两次失败就停下查文档，不要试第三种写法。

## 已验证可用的调用

| 调用 | 说明 |
|---|---|
| `dmt_Board.getAllBoardsInfo()` | 数组，元素含 `name` / `pcb.uuid` |
| `dmt_EditorControl.openDocument(uuid)` | **每轮开工第一件事**，然后 `setTimeout 2500` |
| `pcb_PrimitiveFill.getAll()` | 数组；`.getState_Layer/PrimitiveId/ComplexPolygon/LineWidth` |
| `pcb_PrimitiveFill.create(layer, polygon, '', 0, 0, false)` | polygon 来自 `pcb_MathPolygon.createPolygon([...])` |
| `pcb_PrimitiveFill.delete([ids])` | 批量，300 个 88 ms；一次删 1 万也只要几百 ms |
| `pcb_PrimitiveString.create(layer,x,y,text,font,size,lw,align,rot,rev,exp,mirror)` | **alignMode 1 = 左对齐**（不是居中） |
| `pcb_PrimitiveString.modify(id,{x,y,fontSize,lineWidth,fontFamily})` | 生效 |
| `pcb_PrimitivePolyline.create(net, layer, polygon, lineWidth, ?)` | 板框、金框、丝印框 |
| `pcb_PrimitivePad.create(layer, padNumber, x, y, rotation, ['ELLIPSE',w,h], net, ['ROUND',d], 0, 0, 0, metallization, padType)` | 挂绳孔；层 12，metallization=true |
| `pcb_ManufactureData.getGerberFile('名字')` | 返回 File，还要 `sys_FileSystem.saveFileToFileSystem('C:\\x.zip', file)` |
| `pcb_PrimitivePad.getAll()` | 焊盘数（本板挂绳孔 9 个） |
| `dmt_Project.createProject('Name')` / `openProject(uuid)` | 项目 |
| `dmt_Board.createBoard()` | `"Board2"`（不带参数） |

### 两个「永远不 resolve」的 promise（2026-11 实测，卡死两次）

| 调用 | 现象 | 正确写法 |
|---|---|---|
| `eda.dmt_EditorControl.openDocument(uuid)` | `await` 之后命令 300 s 返回**空**，无 error、无 log | `openDocument(uuid); await new Promise(r=>setTimeout(r,4000));` —— **不 await 它** |
| `eda.pcb_ManufactureData.getGerberFile(name)` | 同上 | `getGerberFile(n).then(f=>saveFileToFileSystem(path,f));` 起火后轮询文件 |

**判据：`invoke` 返回空、又没有 `ok:false`，就是这个 JS 里有 promise 没 resolve。**
不要重试、不要换写法，先找那个 `await`。

**改几何只信 `modify()`**：`setState_*` 全部不落盘（`setState_Layer` / `setState_Polygon` 都"成功"但回读不变）。

**`pcb_PrimitivePolyline` 是半残的**：`modify` 只有 `lineWidth` 生效，`polygon` 改不动；
`setState_Polygon()` + `done()` 抛 `r.getSource is not a function`。
圆环不要用 polyline，改画**分段环形填充**（每环拆 2 段弧、在接缝处重叠 10°，否则接缝留 0.3 mm 缺口）。

## 语法坑

- 错误：`const(r)=await(...)` → `SYNTAX_ERROR: Unexpected token '('`
- 正确：`const r=await(...)`
- `--code` 里带空格要靠包装脚本转义；尽量用无空格写法

## PowerShell 坑

- `.ps1` 里有中文路径 → 必须 **UTF-8 with BOM**，否则中文乱码、找不到文件
- 包装脚本 `lceda.ps1` 会刷一堆 `param : The term ...` 的红色噪音，
  但 JSON 结果仍然正常输出 —— 看 `{"ok":...}` 那一行即可

## 层号

| 层 | 值 |
|---|---|
| 顶层铜 | 1 |
| 底层铜 | 2 |
| 顶层丝印 | 3 |
| 底层丝印 | 4 |
| 顶层阻焊开窗 | 5 |
| 底层阻焊开窗 | 6 |
| 板框 | 11 |
| 机械/孔 | 12 |

PCB 单位是 mil，毫米换算 `/0.0254`。
`['R', left, top, w, h, rot, r]` 里的 `top` 是**上边缘**，高度向 **−y** 方向延伸；
矩形中心是 `(left+w/2, top-h/2)`。

---

## 八、不走 API：直接写 .epcb2（推荐，快 10 倍）

工程是文件夹格式，PCB 就是一个纯文本文件：
`C:\Users\<你>\Documents\LCEDA-Pro\projects\<工程>\pcb\PCB1.epcb2`。
一行一条 JSON 记录，没有分隔符。**毫秒级写出，不需要会话、不需要分批。**

```
{"type":"DOCHEAD","ticket":43851}||{"docType":"PCB","uuid":"<板 uuid>",...}|
{"type":"META","ticket":4,"id":"META"}||{"title":"PCB1","board":"<板 uuid>"}|
{"type":"POLY","ticket":385,"id":"<16 hex>"}||{"layerId":11,"width":10,
   "path":["R",-1692.91,1062.99,3385.83,2125.98,0,137.80],...}|   <- 板框 86x54 R3.5
{"type":"FILL","ticket":403,"id":"<16 hex>"}||{"layerId":1,"width":0.2,
   "fillStyle":"SOLID","path":[["R",-6.7,869.1,5.9,3,0,0]],...}|        <- 一个 path
{"type":"STRING","ticket":3924,"id":"<16 hex>"}||{"layerId":1,"x":0,"y":-835,
   "text":"1956 — 2026","fontFamily":"default","fontSize":139,
   "strokeWidth":6.5,"origin":"LEFT_BOTTOM",...}|
```

### 单位与坐标
- 全部 **mil**（1 mm = 39.3701 mil），**板中心为原点，+y 向上**
- `["R", left, top, w, h, rot, radius]`：`top` 是**上边**，高向下延伸

### 三条硬规则
1. **一条 FILL 只能有一个 path。** 多塞 = 只渲染一部分（实测 400 个只剩几块）。
2. **`mirror:true` 导出无效**，背面文字必须镜像几何（见 04 第 88 条）。
3. 表头记录（DOCHEAD / META / PRIMITIVE / LAYER / RULE / CANVAS / PREFERENCE 等）
   **从现成工程整段照抄**，只把 `ticket` 从最大值往后编号、`id` 换成新的 16 位 hex。

### 标准流程
```
1. shutil.copytree(现成工程, 新工程)          # 板框、层定义、规则全带过来
2. 改名 .eprj3 文件 + 改 name 字段
3. 重写 pcb/PCB1.epcb2：保留表头 + 板框 POLY，其余换成自己的 FILL
4. lceda-pro open --path <新工程>.eprj3       # 拿 sessionId
5. sleep 4s → getAllBoardsInfo → openDocument → sleep 4s
6. pcb_PrimitiveFill.getAll(L) 逐层数图元，与计划数比对
7. pcb_ManufactureData.getGerberFile + saveFileToFileSystem 导出
```
第 4 步之前**先把上一轮会话关掉**（`session close --destroy`），
否则编辑器的旧内存可能盖掉你刚写的文件。

---

## 九、path 的三种写法：R / CIRCLE / 指令序列

`path`（`TPcbSinglePolygon`）是**扁平数组**，三种写法互斥，选一种：

```
矩形      ["R", x, y, w, h, rot, cornerRadius]      // 共 7 个元素，x/y 是左上角
整圆      ["CIRCLE", cx, cy, r]
指令序列   x0 y0  L x1 y1 L x2 y2 ...              // 直线
           x0 y0  ARC angle x1 y1                  // 圆弧：angle 逆时针为正
           x0 y0  CARC angle x1 y1                 // 中心圆弧
```

**实测**：`POLY` + `["CIRCLE"]` + `width:19.685`（0.5 mm）导出为
`G54D11*` + 两段 `G03 ... I1500000J0 D01`，是**精确圆**，不是多边形逼近。
所以徽记的外环、内环、任何圆形边框，一律用这个，不要再扫。

⚠️ 三个坑：
- `angle` 不能写 `0` 或 `±360`，解码会**整条拒收**；
- `R` 的末位是**圆角半径**，不是 2.0 文档里的 `isCCW`；
- `C`（贝塞尔）只有焊盘那条解析路径支持，`POLY/FILL` 走的是 `L/ARC/CARC`，遇到 `C` 直接抛错。

## 十、圆形路径的验收

写完立刻量一次：把该层按 100 px/mm 光栅化，取环带内外 ±5% 的圆环，算覆盖率。
```
coverage >= 0.95   → 环是连续的
coverage <  0.90   → 环被别的东西挖断了，或者写成了多段
```
同时量"环外 0.2 mm 内还有多少金"（毛边），正常应 < 1 mm²。

## 十一、整张手绘稿/签名上板：spec 里的 `board` / `arts` / `dots`

`16-build_board.py` 除了徽记/文字/织纹/孔，还吃三块「非徽记」的 spec 键。
它和徽记的区别是：**输入是一整张位图，输出是任意位置的一整片扫描线**。

```jsonc
{
  "board": {"w": 74, "h": 80, "r": 5},        // 给了就重画板框 POLY（不给则沿用模板的 86×54）
  "step": 0.06,                                // 全局扫描线步距（arts 与 dots 共用）
  "arts": [
    {"png": "assets/doodle_art.png", "w": 71.0, "cx": 0, "cy": 0, "thr": 170,
     "layer": 2, "mask_layer": 6, "mask_expand": 0.05, "mirror": true, "minw": 0.15}
  ],
  "dots": {"ox": -35.5, "oy": 38.539, "pitch": 13.69, "x0": 1.101, "y0": 2.202,
           "r": 1.156, "nx": 6, "ny": 6, "layer": 4, "mirror": true}
}
```

- `arts[*].w` 是**整张图的宽（mm）**，高按图片比例自动算；图以 `(cx,cy)` 为中心放。
- `thr` 是亮度阈值：**墨 = 亮度 < thr**。手绘稿里"轻重笔"的取舍就是这一个数（见 `04` 第 125 条）。
- `mask_expand` 是开窗总扩量。**手绘稿的笔画密，别用 0.10**：实测这块板相邻笔画最窄空隙 0.19 mm，
  开窗 0.05 → 阻焊桥 0.14 mm；开窗 0.10 → 只剩 0.09 mm，阻焊桥会被吃掉。
- `mirror: true` 只对**掩膜**做左右翻（`m[:, ::-1]`），不是翻 rect —— 白点的裁剪要用同一张图。
- `dots` 是"纸面点阵"这类规则点：给网格参数（`ox/oy` 是第一颗的锚点、`pitch` 间距、`r` 半径），
  由程序生成完整圆、再减掉 `dilate(墨, 0.15)` 和孔位，被吃掉 >25% 的整颗丢掉。
- `dots` 出的是**纯丝印**（只写一层），**不开窗**——白点不是金属。

### FILL 与 POLY 的 `R` 是同一口径：`[left, top, w, h, rot, r]`

第二值是**上边**，不是中线。`16` 写文件时把扫描线块的"上边"写进这个字段，`20-preview_spec` 也按上边画。
这条别凭文档猜：用「两种口径各光栅化一次、和真 Gerber 比 IoU」定案（`04` 第 119 条，实测 0.914 vs 0.527）。

### 预览的三个开关

```bash
python scripts/20-preview_spec.py spec.json templates/blank out.png --sc 24 --side back --flip
python scripts/20-preview_spec.py spec.json templates/blank z.png  --sc 60 --side back --flip --crop 26,30,40,40
```
- `--flip`：背面翻过来看（数据是镜像的，不翻就是"从正面透过板子看"，所有字都是反的）。
- `--crop x0,y0,x1,y1`：出局部图（mm）。**验收要求的 ≥60 px/mm 局部图就是这一条**，不用再拿 PIL 手裁。
- 预览的 FILL 会向外扩 0.5 px：扫描线相邻两行在低分辨率下会漏出一条亚像素缝，那是渲染假象，不是板子缺陷。
