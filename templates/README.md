# templates

## blank/ —— 最小模板工程

`blank/pcb/PCB1.epcb2` 只有 147 条记录：层定义（60）、设计规则（16）、层物理（9）、
图元（53）、板框（1），**没有任何图形**，30 KB。

`16-build_board.py` 只需要它三样东西：

1. 层定义 `LAYER` / `LAYER_PHYS` —— 1/2 铜、3/4 丝印、5/6 开窗、11 板框、12 钻孔；
2. 设计规则 `RULE` —— 线宽/间距下限，拷进新工程就不用重设；
3. 板框 `POLY layerId=11` —— 新板的轮廓从这条来。

用法：

```bash
python scripts/16-build_board.py examples/uestc70/spec.json templates/blank out/PCB1.epcb2
```

## 它不是能直接双击打开的工程

仓库里只放 `.epcb2`，因为 `.eprj` 里绑着本机路径和账号信息。要打开它：

1. 在 EDA 里新建一个工程（任意名字）；
2. 把生成的 `PCB1.epcb2` 覆盖进 `<工程>/pcb/PCB1.epcb2`；
3. **`session close --destroy` 再 `open`**（编辑器不会自动重载磁盘改动，04 第 109 条）。

## 换板尺寸

改板框就得改 `POLY layerId=11` 那条（`path:["R",left,top,w,h,rot,r]`，单位 mil），
同时改 spec 里的 `board` / `frame` / `weave.clip`。三处对不上，金带就会跑出板外。
