# AGENTS.md

这个仓库是一个 **agent skill**：`SKILL.md` 是给 agent 读的入口，`references/` 是按需加载的细节，`scripts/` 是能跑的脚本。

## 如果你是被派来改这个仓库的 agent

1. 先读 `SKILL.md`（八阶段 + 三条铁律 + 最贵的 13 条），再读你要改的那一段对应的 `references/`；
2. **改脚本前先跑 `python -m pytest tests -q`** 存个基线（25 条，约 13 秒）；
3. 改完必须再跑一遍，**红了先修，不许改断言让测试变绿**（金板数字是量出来的，见 CHANGELOG）；
4. 涉及新踩的坑 → 往 `references/04-踩坑清单.md` 末尾加一条（编号往后、不改旧号）；
5. 提交前自查三条：无字体二进制、`STXINGKA` 只出现在“用户自备”的说明里、测试全绿。

## 命令

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests -q                     # 25 条离线测试
python scripts/13-check.py <gerber.zip> --weave --md out/验收单.md
python scripts/16-build_board.py examples/uestc70/spec.json templates/blank out/PCB1.epcb2
python scripts/20-preview_spec.py examples/uestc70/spec.json templates/blank out/mock.png --sc 24
```

## 不要做的事

- **不要提交任何字体文件**（CI 会拦）；`STXINGKA.TTF` 是商业字体，只作本机默认路径；
- **不要改 `examples/uestc70/badge.png` 的许可声明**：校徽不在 MIT 内，见 `examples/uestc70/LOGO-COPYRIGHT.md`；
- **不要为了"看起来更好"改 `13-check` 的阈值**：那些区间是从参考板量出来的，改了要同步改 `references/02` 并说明依据。
