# -*- coding: utf-8 -*-
"""下单包清单：给一个目录生成 MANIFEST.txt（sha256 / 大小 / 路径），并能回验。

为什么需要：下单包是最后一道人手环节，最容易犯的错是"包里放的是上一版"。
有了 sha256，解压前后各跑一次，就知道手上这份和当初验收的是不是同一份。

用法:
  python 19-pack_order.py <下单包目录>              # 生成 MANIFEST.txt
  python 19-pack_order.py <下单包目录> --verify      # 回验（解压后跑这个）
  python 19-pack_order.py <目录> --require 下单说明,验收单
  python 19-pack_order.py <目录> --max-mb 10        # 单文件上限（嘉立创上传限制）

退出码 0 = 一致/通过；1 = 有缺失或不一致。
"""
import sys, os, hashlib, time

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ARGV = sys.argv[1:]
def opt(name, default=None):
    if name in ARGV:
        i = ARGV.index(name)
        v = ARGV[i + 1]; del ARGV[i:i + 2]; return v
    return default

VERIFY   = "--verify" in ARGV
if VERIFY: ARGV.remove("--verify")
REQUIRE  = [s for s in opt("--require", "").split(",") if s]
MAX_MB   = float(opt("--max-mb", "10"))
DIR      = ARGV[0] if ARGV else None
if not DIR or not os.path.isdir(DIR):
    print(__doc__); sys.exit(2)
DIR = os.path.abspath(DIR)
MAN = os.path.join(DIR, "MANIFEST.txt")

def sha256(p, buf=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(buf)
            if not b: break
            h.update(b)
    return h.hexdigest()

def walk():
    out = []
    for root, dirs, files in os.walk(DIR):
        dirs.sort()
        for n in sorted(files):
            p = os.path.join(root, n)
            rel = os.path.relpath(p, DIR).replace("\\", "/")
            if rel == "MANIFEST.txt": continue
            out.append((rel, p))
    return sorted(out)

files = walk()
if not files:
    print("目录是空的：", DIR); sys.exit(1)

if VERIFY:
    if not os.path.exists(MAN):
        print("没有 MANIFEST.txt，先跑一次不带 --verify 的"); sys.exit(1)
    want = {}
    for ln in open(MAN, encoding="utf-8"):
        ln = ln.rstrip("\n")
        if not ln or ln.startswith("#"): continue
        parts = ln.split("  ")
        if len(parts) != 3: continue
        want[parts[2]] = (parts[0], int(parts[1]))
    bad, missing, extra = [], [], []
    for rel, p in files:
        if rel not in want: extra.append(rel); continue
        h, sz = want[rel]
        if os.path.getsize(p) != sz or sha256(p) != h:
            bad.append(rel)
    for rel in want:
        if rel not in dict(files): missing.append(rel)
    print("回验 %s：%d 个文件" % (os.path.basename(DIR), len(files)))
    for rel in bad:     print("  内容不一致  ", rel)
    for rel in missing: print("  清单里有、包里没有", rel)
    for rel in extra:   print("  包里有、清单没有  ", rel)
    if bad or missing or extra:
        print("结论：不一致（重打包，别用这一份下单）"); sys.exit(1)
    print("结论：一致")
    sys.exit(0)

rows, total, big = [], 0, []
for rel, p in files:
    sz = os.path.getsize(p); total += sz
    if sz > MAX_MB * 1024 * 1024: big.append((rel, sz))
    rows.append((sha256(p), sz, rel))

lines = ["# 下单包清单（%s）" % os.path.basename(DIR),
         "# 生成时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"),
         "# 共 %d 个文件，合计 %.2f MB" % (len(rows), total / 1048576.0),
         "# 校验方式：python 19-pack_order.py <解压目录> --verify",
         "# sha256                                                              bytes     相对路径"]
for h, sz, rel in rows:
    lines.append("%s  %d  %s" % (h, sz, rel))
open(MAN, "w", encoding="utf-8").write("\n".join(lines) + "\n")

print("清单 ->", MAN)
print("%-56s %10s" % ("文件", "大小"))
for h, sz, rel in rows:
    print("%-56s %10.1f KB" % (rel, sz / 1024.0))
print("合计 %.2f MB（%d 个文件）" % (total / 1048576.0, len(rows)))
miss = [k for k in REQUIRE if not any(k in rel for _, _, rel in rows)]
if miss:
    print("缺少必需文件（--require）：", "、".join(miss)); sys.exit(1)
if big:
    print("警告：以下文件超过 %.0f MB，嘉立创上传会卡：" % MAX_MB)
    for rel, sz in big: print("   %-56s %.1f MB" % (rel, sz / 1048576.0))
