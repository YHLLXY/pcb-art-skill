# 脚本：把 skill 从"文档"变成"能跑"

这 19 个脚本是四轮实战（李欣雨生日板、重庆邮电测试板、电子科大 70 周年）留下来的可复用工具。
**它们不是成品库，是起点**——每个脚本开头都有 1–2 个写死的路径常量，用之前先改成你这次的路径。

---

## 全链路顺序

```
01-layout_mock.py        P2  位图 mock（含 fit_h/fit_v：按目标宽度反解字号）
02-generate_board.py     P3  主生成器：徽记描摹 + 汉字/英文扫描线 + 织纹 → JS 分块
02b-generate_fix.py      P3  同上，专治背面镜像，以及把某个元素搬到别的层
08-apply_chunks.ps1      P4  批量注入（失败自动重开文档 + 重试）
09-open_document.js      P4  每个批次前先激活 PCB 文档（就这一条命令，别省）
04-gerber_raster.py      P5  单层 Gerber → PNG（20 px/mm，G36/D03/G02 都支持）
05-composite.py          P5  正/背合成（暗铜 + 金 + 白丝印）
06-gold_coverage.py      P3  沉金面积占比（对照 12–24%）
07-stroke_width.py       P3  最小线宽实测（判断会不会被工厂吃掉）
03-arc_text.py           P3  环文/弧形文字：逐字旋转贴图 → 扫描线
10-export_gerber.js      P5  导出 Gerber 包
```

## 用之前必须改的常量

| 文件 | 改什么 |
|---|---|
| 01 / 02 / 02b | 开头的 `ROOT`（项目根目录） |
| 03 | 开头 `ROOT` |
| 05 / 06 | 开头 `base`（放 `N_*.png` 的目录） |
| 08 | `$sid`（`session list` 拿）、`$dir`（分块 JS 所在目录）、`order_*.txt` 清单 |
| 09 | 里面的板名（`Board1`） |
| 10 | 输出 zip 的绝对路径 |

## 两个容易忘的

1. **09 要在每个批次前跑**：文档随时会被关掉，报 `reading 'map'` 就是没打开文档。
2. **08 的 `order_*.txt` 要自己生成**：文件名按 `前缀_两位序号.js` 排，前缀顺序 = 注入顺序（先铜后开窗、先底后顶都无所谓，但同一元素的两层要挨着）。

## 02 的四个可调参数

```python
step=0.06      # 扫描步距：≤0.6×最细笔画
hfac=1.25      # 条带高度倍数：>1 才有重叠，1.25 → 重叠 0.016 mm
minw=0.15      # 最小线宽：丝印 0.15 / 铜 0.10
mirror=False   # 底层（2/4/6）必须 True
```

## 别用这些脚本做的事

- **纯 ASCII 不要走扫描线**（用 EDA 文本对象，见 `../02-制造性与矢量.md`）
- **不要把 `minw` 调到工艺下限以下**"骗过"检查：工厂会吃掉它


## 00：徽记解码（换主题第一件事）

`00-decode_badge.py <png> <目标直径mm>` 一次给出四个判断：

- **线稿型还是圆盘型**（环带实色率 ≥60% → 圆盘型）
- 外圆/内圆半径（mm）
- 各颜色面积：透明 / 主色A / 主色B（**任意两主色**：对不透明像素做阈值聚类，不写死蓝/橙）
- 整块填实的金面积与占比（对照 12–24% 的金预算）

实测电子科大：511.5 px → 15.00 mm，内圆 317.3 px → 9.30 mm，环带实色 90.2%，
填实要 434.9 mm² = 板面 9.36% → **可以直接填实**。

**两种原型的画法相反，这是本 skill 最贵的一条（见 04 第 98 条）：**

| 原型 | 画法 |
|---|---|
| 线稿型（本身就是线） | 整枚扫描线；圆用 `["CIRCLE"]` 矢量 |
| 圆盘型（实心色块+挖空白字） | **实心盘整块铜 + 字做阻焊盖住的黑镂空**，字不要描 |

v3 把圆盘型当线稿描，环上六个字全变成 0.1 mm 毛刺；v6 改实心盘后一次就对。

## 11 / 12：直接写 .epcb2（第十一轮新增，推荐）

`11-epcb2_layout.py` 把版式算成矩形表（`rects.json`），`12-epcb2_write.py` 把它写成工程里的
`pcb/PCB1.epcb2`。**不需要会话、不需要分批注入**，1.86 万条填充 3 分钟内落地。

用法：
1. 复制一份现成工程当模板（板框、层定义、规则都带过来）
2. 改两个脚本顶部的 `ROOT` / `D`（版式参数）与 `SRC/DST`（工程路径）
3. 先跑 `11`，看一眼 `preview/mock-*.png`，再跑 `12`
4. `session close --destroy` 后 `open --path`，睡 4 s 再数图元

坑：一条 FILL 只能放一个 path；`mirror:true` 导出无效（背面文字必须镜像几何）。
详见 `references/03-EDA落地.md` 第八节。



## 13：交付前自检（P5 闸门）

`13-check.py` 吃一个 Gerber zip，输出一张判定表，有问题退出码 1。

```
python 13-check.py <gerber.zip> --board 86x54 --ring 15.0:0.5 --ring-cy 7.8
```

参数：`--board 86x54`（必给）、`--gold-min 8 --gold-max 24`、`--silk-pct-min 0.3`、`--black-min 70`、
`--ring 15.0:0.5 --ring-cy 7.8`（有独立圆环时才用）。

查：板尺寸 / 沉金 8–24% / 最小铜宽（p5）/ 最小丝印（p5）/ 白丝印 ≥0.3% / 哑黑 ≥70% / 钻孔数与孔径 / 圆环覆盖率（≥0.95）。
判定分三档：**FAIL**（工艺上会出问题）、**WARN**（配比偏离参考板，只提示不改退出码）、PASS。
最小值用 **p5 分位**不用 min —— 45° 边上每行都会切出 1–2 px 碎片，min 永远是个假数。

实测（UESTC70 v10）：86.25×54.25 / 金 22.46%（正 18.42 / 背 11.73）/ 铜 0.120 / 丝印 0.140 / 白 0.60% / 黑 79.73% / 织纹 100%（9×16 单元）/ 1 孔 φ3.0 → 全绿。

## 14：伪 3D 预览（P4.5 闸门要用）

`14-render3d.py <gerber目录> <输出前缀> [--sc 28]` → `<前缀>_front3d.png` / `<前缀>_back3d.png`

做法：铜/丝印当高度场 → 法线 → 定向光 + 半球光 + 金属高光。哑黑低反射、沉金强高光、白丝印漫反射。
织纹会自动显示成哑黑上的浮雕；板外补投影和板边倒角高光。

不需要 EDA 的 3D 视图，也不需要联网 —— 有 Gerber 就能出，且**改完板直接重出**。

两个调参：`k`（浮雕强度，140 左右）、`GaussianBlur`（法线平滑，2.2）。太平滑会像贴纸，太锐会把 1 px 锯齿放大成虚线。


## 15：编织纹生成器（回放参考板的纹路表）

`15-weave.py` 是织纹的**唯一来源**，别的脚本不要再各写一份。

```
python 15-weave.py --extract <参考板 GTL>      # 从参考板重新提「2 mm 单元朝向表」
python 15-weave.py                            # 用内置表生成，打印条数与铜面积
python 15-weave.py --out wv.json              # 导出矩形表（left, y_center, w, h，mm）
python 15-weave.py --preview 80 -40 26 12 12 out.png    # 12x12 mm 局部图
```

内置表（从参考板提取，8×8 mm 一个周期）：

```
V H H V
H H V V
H V V H
V V H H
```

参数：单元 2.0 mm / 间距 **0.2225** / 线宽 **0.115** / 圆角 R2.2。覆盖率 55–58%（参考板 56–61%）。
⚠️ 间距线宽是官方样板在 400 px/mm 下量出来的；写小一点（0.195/0.103 → 间隙 0.092）**嘉立创做不出来**，
织纹会糊成一块铜（见 04 第 131 条）。`13-check --weave` 会拦住这个。

**三条铁律**：① 板边只沿条纹方向截断，绝不为了补满横着加一条；
② 覆盖率是结果不是目标；③ 改参数前先 `--extract` 重量一遍。

验收：`13-check.py ... --weave` 报「织纹吻合度」，参考板自己 96.5%，低于 90% 判 FAIL。
## 16：一条命令出整块板（spec → .epcb2）

```
python 16-build_board.py <spec.json> <模板工程目录> <输出.epcb2>
```

spec 里只有元素，没有像素（例子：`skill测试\UESTC70\gen\uestc70.spec.json`）：

```json
{
  "frame":  {"w": 86.2, "h": 54.2, "r": 3.5, "cu": 1.0, "mask": 1.1},   // 金线压在板框上
  "weave":  {"clip": [42.55, 25.55], "r": 2.9},
  "badge":  {"png": "...", "d": 30, "cx": 0, "cy": 7.8, "mode": "disc"},
  "texts":  [{"s": "电子科技大学", "font": "xingkai", "width": 40, "cy": -12.8}],
  "strings":[{"layer": 3, "text": "UNIVERSITY ...", "size": 52, "x": -883, "y": -940}],
  "holes":  [{"x": 39.3, "y": 23.4, "d": 3.0, "pad": 4.0},
             {"x": 40.95, "y": 23.4, "d": 0.305}]   // 参考板那圈小孔，见 references/07
}
```

`texts` 支持 `mask_layer: null`（纯丝印，不开窗）与 `mirror: true`（背面）。
拉丁字母用 `strings`（EDA 笔画字体），**导出后要量 bbox 回填 x**（02「文字定位」）。

模板工程目录只是借它的层定义/规则/板框；输出 .epcb2 拷进工程 `pcb/PCB1.epcb2` 后，
**必须 `session close --destroy` 再 `open`**，否则导出的是旧图（04 第 109 条）。

**字体**：`spec.texts[].font` 是**角色名**（`xingkai` / `times` / `consola`），不是字体名。
解析顺序：`spec.fonts` → `GIFT_PCB_FONT_<角色>` → Windows 默认路径；找不到就直接报错并给三条解法。
仓库不含字体文件（华文行楷是商业字体），开源请换 OFL 的霞鹜文楷/思源宋体，见 `../references/02`「字体」。

## 19：下单包清单（MANIFEST + sha256）

```
python 19-pack_order.py <下单包目录>                        # 生成 MANIFEST.txt
python 19-pack_order.py <下单包目录> --verify                # 解压后回验（一致才下单）
python 19-pack_order.py <目录> --require 下单说明,验收单     # 缺件直接退出码 1
```

下单包是最后一道人手环节，最常见的错是**包里放的是上一版**。
清单里每行 `sha256  字节数  相对路径`，回验时逐个重算；不一致、多文件、少文件都会列出来并退出 1。
同时检查单文件是否超过 10 MB（嘉立创上传会卡，04 第 106 条）。

## 所有脚本都会把 stdout 切到 UTF-8

Windows 控制台默认 GBK，中文表打出来是乱码（`��Ŀ` 这种）。每个脚本开头都有：

```python
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
```

新加脚本照抄这三行；否则用户看到的就是一屏问号，比没有输出更糟。


## 20：不开 EDA 先看 spec 长什么样

```
python 20-preview_spec.py <spec.json> <模板工程目录> <out.png> [--sc 24] [--side front|back]
```

spec → `.epcb2` → 按层画成位图：铜（被盖住 = 深褐近黑）、金（铜∧开窗）、白（丝印）、
板框（灰线）、孔（金盘 + 黑洞）。用来判断**元素位置和比例**，不判断材质。

两个已知的表达局限（都写在 templates/layouts/README 里）：

- 拉丁字母是文本对象，真字形在 EDA 里生成；预览只画一条等长细框（按实测 0.617×fontSize）；
- 织纹在 24 px/mm 下会出摩尔纹，看结构请用 `15-weave.py --preview 80 ...`。

## 17 / 18：素材采集与粗筛（P1 前半段）

```
python 17-crawl_assets.py --keywords "panda line art" --out assets/candidates --limit 8
python 17-crawl_assets.py --from-dir D:/pics --out assets/candidates     # 没网走这条
python 18-filter_assets.py assets/candidates --target-mm 40
```

`17` 只从维基共享资源取 **CC/PD** 的图（逐条记许可与作者），或者复制本地目录；
`< 4 KB` 的、`.pdf` 抽页的直接跳过。产出 `meta.json`（来源/许可/sha256）+ `index.md`（图墙）。

`18` 按四条判"能不能上板"：够不够大（≥800 px）、背景干不干净（透明底或白底）、
墨量（3%–55%）、最细笔画（≥0.15 mm @ `--target-mm`）。**它不判断好不好看。**

纪律见 `references/08`：抓到的一张都不许直接上板，用户在图墙里挑、说清取哪一块，才进描摹。
