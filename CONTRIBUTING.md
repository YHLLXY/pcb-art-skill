# CONTRIBUTING

## 报问题

用 issue 模板（`板子有问题` / `想做一块板`）。报缺陷时请给：**哪块板、卡在哪一阶段、实际数字、期望数字**。
`看起来不对` 会被要求补数据——这个项目的原则是"量，不要估"。

## 加一块新样例板

`examples/` 目前只放一块（`uestc70`），加新样例要同时带齐六样（见 `examples/README.md`）：
`spec.json`（徽记图相对路径）、`gerber.zip`、`验收单.md`、`preview/` 三张、README、以及 `tests/` 里一条金板断言。

## 改脚本

1. `python -m pip install -r requirements-dev.txt`；
2. 先跑 `python -m pytest tests -q` 存基线；
3. 改完再跑，**红了先修，不许改断言**（金板数字是实测，换字体/换 spec 才允许重定基线，且要写进 CHANGELOG）；
4. 新踩的坑往 `references/04-踩坑清单.md` 末尾加，编号往后，不改旧号。

## 不要提交

| 东西 | 原因 |
|---|---|
| 任何 `.ttf/.otf/.woff` | 商业字体不能进仓库；CI 会 `git ls-files` 拦 |
| `*.epcb2`（除了 `templates/blank` 那份 30 KB 模板） | 一块板 10 MB，仓库会爆 |
| `__pycache__` / `.pytest_cache` | 已在 `.gitignore` |
| 版权在期的商业 IP（Hello Kitty 等） | 只作工艺参考，不上板、不进图 |

## 许可

提交即同意以 MIT 分发你的代码与文档。**不要**往仓库里加别人的图/字体/工程文件，除非许可允许再分发。
