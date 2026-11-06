# CHANGELOG

## v0.1.1 — 2026-11-06（发布前补的口子）

补的是一个陌生人 clone 下来会卡住的地方，不是新功能。

### 新增

- `requirements.txt` / `requirements-dev.txt`：依赖只有 numpy + pillow（测试再要 pytest），之前 README 没写，得靠猜
- `AGENTS.md`：agent 进仓库先读这个 —— 改脚本前先跑测试存基线、红了不许改断言、新坑往前加编号
- `CONTRIBUTING.md`：报问题给数字、加样例要带齐六样、**不许提交字体/大 epcb2/在期商业 IP**
- `tests/test_pack_order.py` 四条：MANIFEST 生成 / 回验一致 / 改一个字节必须红 / 多一个文件必须红 / 缺必需文件必须红 → 测试总数 17 → **21**
- README 加 `Quick start (EN)`（英文读者三行跑通）
- `SKILL.md` 的 description 补英文触发词（decorative PCB, PCB art, silkscreen artwork, matte black + ENIG…），英文语境下才会被调用

### 改

- README 的测试说明、徽章数字同步到 21

## v0.1.0 — 2026-11-06
第一次按「能被别人用起来」的标准收尾。内容来自四轮实战：李欣雨生日板（川农）、重庆邮电测试板、电子科大 70 周年板。

### 新增

- `tests/`：金板复现（37571 条 / 逐层条数 / 织纹 5749 条 2239 mm²）、织纹（间距 0.195、线宽 0.103、单元朝向 100%）、自检脚本本身（金板全绿 + 空板必须红）。`python -m pytest tests -q`
- `examples/uestc70/`：完整一块板（spec + 徽记图 + gerber.zip + 验收单 + 3D/60 px/mm 预览 + 复现说明）
- `templates/blank/`：最小模板工程（147 条：层定义 / 规则 / 板框，没有图形），`16-build_board` 不再依赖别人的工程
- `scripts/19-pack_order.py`：下单包 MANIFEST（sha256 + 字节数），`--verify` 回验，`--require` 查缺件，10 MB 上限警告
- `references/07-从参考板抄什么.md`：十条抄清单（金带贴边 0.49、孔组 8×φ0.305、出血、织纹表、配比、丝印层级、居中靠量…）
- `references/08-素材爬取计划.md`：没有参考板时的找图链路
- `references/05` 新增「差异化」：和 `xxhhwtxx/pcb-art-keychain-skill` 的七项对比 + 值得借的三份
- `assets/`：README 首图（3D 正面/背面 + 织纹 80 px/mm 实拍）
- `templates/问卷.md`（P0.5 八问 + 元素清单 + 三态勾选：待确认 / 已确认（谁·何时）/ 不适用）
- `templates/layouts/`：三个版式（徽记居中 / 左图右字 / 满幅出血）+ 24 px/mm 示意 + 换尺寸的五步
- `scripts/20-preview_spec.py`：spec → 位图预览，不开 EDA 就能看版式和比例（`--sc` / `--side`）
- `tests/test_decode.py`：徽记解码对「蓝橙」和「红金」两种配色都要判对
- `scripts/17-crawl_assets.py`：按关键词从维基共享资源采集 **CC/PD** 素材（记许可/作者/sha256），或 `--from-dir` 走本地目录
- `scripts/18-filter_assets.py`：粗筛成图墙（尺寸 / 底色 / 墨量 / 最细笔画），✅ 可用 / ❌ 剔 + 理由
- `tests/test_assets.py`：素材链路端到端（含「300 px 暗底图必须被剔」）

### 修正

- **金面积统一口径**：正金∪背金 ÷ 板框 = 参考板 **22.00%**；早期文档里的 19.78% 复算不出来，全部改掉并注明废止。「正+背相加」= 28.41% 是错的（板边金带两面压同一片像素）
- 金预算区间 **12–20% → 12–24%**（参考板 22.00%，旧区间把自己的参考板判成"像整板金"）
- `SKILL.md` 的「最贵的 12 条」实际 13 条且有两个 `10.` → 重新编号 1–13
- `README` 里"15% 红线""金 10–15%""白 12–18%"等过期数字全部换成实测值
- **20 个脚本统一把 stdout/stderr 切到 UTF-8**：之前中文自检表在 Windows 上是乱码
- `00-decode_badge` 不再写死"蓝/橙"阈值：改成对不透明像素做 5 bit 直方图聚类，任意两主色都能判
- **输出目录不再要求预先存在**：`16-build_board` / `13-check --md` / `20-preview_spec` 自己建目录（陌生人照 README 第一步就卡在这）
- `20-preview_spec.py` 修正两处 epcb2 约定：`POLY` 的 path 是扁平的 `["R",...]`（`FILL` 才是嵌套），
  `R` 的第二个数是 `top`、`FILL` 的第二个数是 `y_center` —— 写错会画出"横条纹徽记"
- `13-check` 缺层时不再抛 `TypeError`，改报 FAIL（空板必须能被判红）
- `16-build_board` 的 `badge.png` 支持相对 spec 的路径，任意 cwd 可跑
- `references/04` 从 97 条补到 117 条（新增 98–117：原型判错、编辑器不重载、行序镜像、文字靠估、金线内缩、孔漏小孔圈、推断当事实、输出乱码、口径混用、织纹窗口错位）

### 许可

- 代码与文档 MIT © 2026 YHLLXY
- 仓库**不含任何字体文件**；字体名是角色名，用 `spec.fonts` / `GIFT_PCB_FONT_*` 指到你自己的字体

### 已知限制

- EDA 段（写 `.epcb2` → 导出 Gerber）无法自动化，测试只覆盖离线一半
- 徽记图里的商业字体（华文行楷）不进仓库，见 `references/02`「字体」
