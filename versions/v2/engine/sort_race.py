"""冒泡排序 vs 快速排序 代码动画对决 —— PIL + numpy + ffmpeg 渲染器。

用法: python3 sort_race.py --aspect 9:16|16:9 --out out.mp4 [--n 32] [--seed 7] [--preview]
"""
import argparse, math, random, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FPS = 60
SR = 44100
CJK = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

BG = (13, 17, 23)
PANEL = (22, 27, 34)
BORDER = (48, 54, 61)
TXT = (230, 237, 243)
DIM = (125, 133, 144)
BAR = (88, 166, 255)
CMP = (255, 196, 0)
SWP = (255, 92, 92)
DONE = (63, 185, 80)
PIVOT = (210, 120, 255)
ACCENT = {"bubble": (255, 140, 66), "quick": (63, 220, 160)}

# ---------- 排序轨迹 ----------
def bubble_trace(a):
    a = a[:]; ev = []; n = len(a); done = set()
    for i in range(n):
        for j in range(n - 1 - i):
            ev.append(dict(t="cmp", i=j, j=j + 1, line=2, arr=a[:], done=set(done)))
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                ev.append(dict(t="swp", i=j, j=j + 1, line=3, arr=a[:], done=set(done)))
        done.add(n - 1 - i)
    ev.append(dict(t="end", i=-1, j=-1, line=-1, arr=a[:], done=set(range(n))))
    return ev

def quick_trace(a):
    a = a[:]; ev = []; done = set()
    def qs(lo, hi):
        if lo > hi: return
        if lo == hi: done.add(lo); return
        p = a[hi]; i = lo
        for j in range(lo, hi):
            ev.append(dict(t="cmp", i=j, j=hi, line=2, arr=a[:], done=set(done), pivot=hi))
            if a[j] < p:
                a[i], a[j] = a[j], a[i]
                ev.append(dict(t="swp", i=i, j=j, line=3, arr=a[:], done=set(done), pivot=hi))
                i += 1
        a[i], a[hi] = a[hi], a[i]
        ev.append(dict(t="swp", i=i, j=hi, line=4, arr=a[:], done=set(done), pivot=i))
        done.add(i)
        qs(lo, i - 1); qs(i + 1, hi)
    qs(0, len(a) - 1)
    ev.append(dict(t="end", i=-1, j=-1, line=-1, arr=a[:], done=set(range(len(a)))))
    return ev

CODE = {
    "bubble": ["for i in range(n):", "  for j in range(n-1-i):", "    if a[j] > a[j+1]:", "      swap(a[j], a[j+1])", ""],
    "quick":  ["def qs(lo, hi):", "  p = a[hi]", "  for j in range(lo, hi):", "    if a[j] < p: swap(i++, j)", "  swap(i, hi); qs(...)"],
}
NAME = {"bubble": "冒泡排序", "quick": "快速排序"}
BIGO = {"bubble": "O(n²)", "quick": "O(n log n)"}

# ---------- 工具 ----------
def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    x = min(max(x, 0), 1)
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

def ease_io(x):
    x = min(max(x, 0), 1); return x * x * (3 - 2 * x)

def ease_out(x):
    x = min(max(x, 0), 1); return 1 - (1 - x) ** 3

def lerp(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

class Fonts:
    def __init__(self, s):
        self.s = s; self.cache = {}
    def get(self, path, size):
        k = (path, int(size * self.s))
        if k not in self.cache: self.cache[k] = ImageFont.truetype(path, max(8, k[1]))
        return self.cache[k]

_PATCH = {}
def text_pop(d, xy, txt, font, fill, scale=1.0, stroke=0, alpha=1.0, stroke_fill=BG):
    """亚像素文字：整字号渲染一次缓存，再用仿射变换做浮点缩放和定位，避免字号取整造成的抖动。"""
    if scale <= 0.01 or alpha <= 0.004: return
    key = (txt, font.path, font.size, fill, stroke, stroke_fill)
    if key not in _PATCH:
        l, t_, r, b = font.getbbox(txt, stroke_width=stroke)
        pad = 4
        im = Image.new("RGBA", (r - l + 2 * pad, b - t_ + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((pad - l, pad - t_), txt, font=font, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
        _PATCH[key] = im
    patch = _PATCH[key]
    w, h = patch.size; tw, th = w * scale, h * scale
    cx, cy = xy
    x0, y0 = math.floor(cx - tw / 2), math.floor(cy - th / 2)
    ox, oy = (x0 - (cx - tw / 2)) / scale, (y0 - (cy - th / 2)) / scale
    region = patch.transform((math.ceil(tw) + 2, math.ceil(th) + 2), Image.AFFINE,
                             (1 / scale, 0, ox, 0, 1 / scale, oy), Image.BICUBIC)
    if alpha < 1:
        a = region.getchannel("A").point(lambda v: int(v * alpha)); region.putalpha(a)
    d._image.paste(region, (x0, y0), region)

def text_center(d, xy, txt, font, fill, stroke=0, stroke_fill=BG):
    d.text(xy, txt, font=font, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=stroke_fill)

# ---------- 主渲染 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aspect", default="9:16")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=32)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--preview", action="store_true", help="半分辨率快速预览")
    args = ap.parse_args()

    vertical = args.aspect == "9:16"
    W, H = (1080, 1920) if vertical else (1920, 1080)
    if args.preview: W, H = W // 2, H // 2
    s = W / (1080 if vertical else 1920)
    F = Fonts(s)

    random.seed(args.seed)
    data = random.sample(range(1, args.n + 1), args.n)
    traces = {"bubble": bubble_trace(data), "quick": quick_trace(data)}

    HOOK = 2.5
    EPS = 52.0  # 每秒执行的操作数，两边相同
    race_len = len(traces["bubble"]) / EPS
    T_RACE_END = HOOK + race_len + 0.6
    T_WIN = T_RACE_END + 2.8
    T_END = T_WIN + 2.4
    nframes = int(T_END * FPS)
    finish_t = {k: HOOK + len(v) / EPS for k, v in traces.items()}
    ratio = len(traces["bubble"]) / len(traces["quick"])

    # 布局
    if vertical:
        title_box = (0, 0, W, int(330 * s))
        panels = {"quick": (int(50*s), int(350*s), W - int(50*s), int(1060*s)),
                  "bubble": (int(50*s), int(1110*s), W - int(50*s), int(1820*s))}
    else:
        title_box = (0, 0, W, int(190 * s))
        panels = {"quick": (int(60*s), int(210*s), int(940*s), int(1000*s)),
                  "bubble": (int(980*s), int(210*s), W - int(60*s), int(1000*s))}

    # ---------- 音频：Sound of Sorting ----------
    total_samples = int(T_END * SR) + SR
    audio = np.zeros(total_samples, dtype=np.float32)
    blip_len = int(0.045 * SR)
    tt = np.arange(blip_len) / SR
    env = np.exp(-tt * 60)
    for k, ev in traces.items():
        for idx, e in enumerate(ev):
            if e["t"] == "end": continue
            t0 = HOOK + idx / EPS
            v = e["arr"][e["i"]]
            f = 220 + 900 * v / args.n
            wavef = np.sin(2*np.pi*f*tt) if k == "quick" else np.sign(np.sin(2*np.pi*f*tt)) * 0.5
            st = int(t0 * SR)
            audio[st:st + blip_len] += (wavef * env * 0.16).astype(np.float32)
    def chime(t0, freqs, amp=0.25, dur=0.6):
        n = int(dur * SR); x = np.arange(n) / SR; e = np.exp(-x * 5)
        sig = sum(np.sin(2*np.pi*f*x) for f in freqs) / len(freqs)
        st = int(t0 * SR); audio[st:st+n] += (sig * e * amp).astype(np.float32)
    chime(0.05, [523, 659], 0.3, 0.4)                 # 开场
    chime(finish_t["quick"], [784, 988, 1175])        # 快排完成
    chime(finish_t["bubble"], [392, 494])             # 冒泡完成
    chime(T_RACE_END + 0.1, [523, 659, 784, 1047], 0.35, 1.2)  # 结果揭晓
    fade = int(0.5 * SR); end = int(T_END * SR)
    audio[end - fade:end] *= np.linspace(1, 0, fade, dtype=np.float32); audio[end:] = 0
    audio = np.clip(audio, -1, 1)
    wav_path = args.out + ".wav"
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())

    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav_path,
                           "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-maxrate", "20M", "-bufsize", "40M",
                           "-g", str(FPS * 2), "-pix_fmt", "yuv420p", "-fps_mode", "cfr",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", args.out],
                          stdin=subprocess.PIPE)

    def draw_panel(d, k, box, t, alpha):
        x0, y0, x1, y1 = box
        pw, ph = x1 - x0, y1 - y0
        acc = ACCENT[k]
        d.rounded_rectangle(box, radius=int(24*s), fill=PANEL, outline=lerp(BORDER, acc, 0.5), width=max(1, int(3*s)))
        # 头部
        d.text((x0 + 30*s, y0 + 26*s), NAME[k], font=F.get(CJK, 54), fill=acc)
        d.text((x0 + 30*s + F.get(CJK, 54).getlength(NAME[k]) + 20*s, y0 + 40*s), BIGO[k], font=F.get(MONO_B, 34), fill=DIM)
        fidx = max(0, t - HOOK) * EPS
        idx = int(fidx); frac = fidx - idx
        ev = traces[k]
        e = ev[min(idx, len(ev) - 1)]
        finished = t >= finish_t[k]
        elapsed = min(max(0, t - HOOK), finish_t[k] - HOOK)
        ops = min(idx, len(ev) - 1)
        timer = f"{elapsed:5.2f}s"
        d.text((x1 - 30*s, y0 + 30*s), timer, font=F.get(MONO_B, 48), fill=DONE if finished else TXT, anchor="ra")
        # 柱子
        code_h = 210 * s
        bx0, bx1 = x0 + 30*s, x1 - 30*s
        by0, by1 = y0 + 120*s, y1 - code_h - 40*s
        n = len(e["arr"]); gap = 4 * s
        bw = (bx1 - bx0 - gap * (n - 1)) / n
        arr = e["arr"]; xpos = {i: float(i) for i in range(n)}
        if not finished and e["t"] == "swp" and e["i"] != e["j"]:
            # 交换动画：两根柱子在本操作时间内平滑滑到对方位置
            a, b = e["i"], e["j"]; m = ease_io(frac / 0.85)
            xpos[a], xpos[b] = b + (a - b) * m, a + (b - a) * m
        fin_mix = ease_io((t - finish_t[k]) / 0.4) if finished else 0.0
        for i, v in enumerate(arr):
            hh = (by1 - by0) * v / n
            c = BAR
            if i in e["done"]: c = DONE
            if finished and fin_mix < 1: c = lerp(BAR, DONE, fin_mix)
            if not finished:
                if e.get("pivot") == i: c = PIVOT
                if i in (e["i"], e["j"]): c = SWP if e["t"] == "swp" else CMP
            else:
                # 完成后从左到右扫一遍绿光（高斯包络，连续变化）
                sweep = (t - finish_t[k] - 0.3) * 50
                c = lerp(c, (200, 255, 210), math.exp(-((i - sweep) / 2.0) ** 2))
            bx = bx0 + xpos[i] * (bw + gap)
            d.rounded_rectangle((bx, by1 - hh, bx + bw, by1), radius=int(min(bw/3, 6*s)), fill=c)
        # 代码框
        cy0 = y1 - code_h - 20*s
        d.rounded_rectangle((x0 + 20*s, cy0, x1 - 20*s, y1 - 20*s), radius=int(14*s), fill=(13, 17, 23))
        lh = 36 * s
        mono = F.get(MONO, 27)
        for li, line in enumerate(CODE[k]):
            ly = cy0 + 14*s + li * lh
            if not finished and li == e["line"]:
                d.rectangle((x0 + 22*s, ly - 2*s, x1 - 22*s, ly + lh - 4*s), fill=(56, 48, 20) if e["t"] == "cmp" else (70, 28, 28))
                d.rectangle((x0 + 22*s, ly - 2*s, x0 + 28*s, ly + lh - 4*s), fill=CMP if e["t"] == "cmp" else SWP)
            d.text((x0 + 44*s, ly), line, font=mono, fill=TXT if (li == e["line"] and not finished) else DIM)
        d.text((x1 - 40*s, y1 - 40*s), f"ops {ops}", font=F.get(MONO, 26), fill=DIM, anchor="rb")
        if finished:
            p = ease_out_back((t - finish_t[k]) / 0.5)
            text_pop(d, ((x0 + x1) / 2, (by0 + by1) / 2), "完成!", F.get(CJK, 76), DONE, scale=p, stroke=int(6*s))

    def crossfade(base, draw_a, draw_b, x, dip=False):
        """叠化：结果 = (base 上画 A) 与 (base 上画 B) 按 x 混合；A 或 B 可为 None。
        dip=True 时 A 先淡出、B 再淡入（同一位置的文字不互相重叠）。"""
        def layer(fn):
            if fn is None: return base
            im = base.copy(); fn(ImageDraw.Draw(im)); return im
        if dip:
            if x < 0.5: return Image.blend(base, layer(draw_a), ease_io(1 - 2 * x)) if draw_a else base
            return Image.blend(base, layer(draw_b), ease_io(2 * x - 1)) if draw_b else base
        if x <= 0: return layer(draw_a)
        if x >= 1: return layer(draw_b)
        return Image.blend(layer(draw_a), layer(draw_b), x)

    for fi in range(nframes):
        t = fi / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        # 背景网格
        g = int(60 * s)
        for x in range(0, W, g): d.line((x, 0, x, H), fill=(18, 23, 30))
        for y in range(0, H, g): d.line((0, y, W, y), fill=(18, 23, 30))
        # 标题：钩子文字与正式标题 0.8 秒叠化
        tx, ty = W / 2, title_box[3] / 2
        def hook_title(d):
            p = ease_out_back(t / 0.45)
            text_pop(d, (tx, ty - 50*s), f"同样 {args.n} 个数", F.get(CJK, 64), TXT, scale=p * (1 + 0.02 * t))
            p2 = ease_out_back((t - 0.6) / 0.45)
            if p2 > 0: text_pop(d, (tx, ty + 50*s), "谁先排完？", F.get(CJK, 96), CMP, scale=p2 * (1 + 0.03 * t), stroke=int(4*s))
        def main_title(d):
            text_center(d, (tx, ty - 30*s), "排序算法大对决", F.get(CJK, 78), TXT)
            text_center(d, (tx, ty + 50*s), "快速排序 VS 冒泡排序", F.get(CJK, 40), DIM)
        x = (t - (HOOK - 0.5)) / 1.0
        img = crossfade(img, hook_title, main_title, min(max(x, 0), 1), dip=True)
        d = ImageDraw.Draw(img)
        # 面板：上滑 + 透明度淡入
        for k, box in panels.items():
            appear = ease_io((t - 1.0 - (0.25 if k == "bubble" else 0)) / 0.9)
            if appear <= 0: continue
            off = int((1 - appear) * 80 * s)
            b = (box[0], box[1] + off, box[2], box[3] + off)
            img = crossfade(img, None, lambda dd: draw_panel(dd, k, b, t, appear), appear)
        d = ImageDraw.Draw(img)
        # 进度条（留存）
        px = W * t / T_END; full = int(px)  # 末端像素按小数部分混色，进度条亚像素平滑
        if full > 0: d.rectangle((0, H - 10*s, full - 1, H), fill=CMP)
        d.rectangle((full, H - 10*s, full, H), fill=lerp(BG, CMP, px - full))
        # 结果揭晓：0.6 秒压暗，结论与结尾 0.8 秒叠化
        if t >= T_RACE_END:
            p = ease_io((t - T_RACE_END) / 0.6)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, int(190 * p)))
            img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
            def result(d):
                q = ease_out_back((t - T_RACE_END - 0.15) / 0.5)
                push = 1 + 0.03 * (t - T_RACE_END)  # 缓慢推近，静止段也保持运动
                if q > 0: text_pop(d, (W/2, H/2 - 120*s), "快速排序", F.get(CJK, 110), ACCENT["quick"], scale=q * push, stroke=int(6*s))
                q2 = ease_out_back((t - T_RACE_END - 0.55) / 0.5)
                if q2 > 0: text_pop(d, (W/2, H/2 + 40*s), f"快了 {ratio:.1f} 倍", F.get(CJK, 140), CMP, scale=q2 * push, stroke=int(8*s))
                q3 = ease_out((t - T_RACE_END - 1.1) / 0.4)
                if q3 > 0: text_pop(d, (W/2, H/2 + 190*s), f"{len(traces['quick'])-1} 步  vs  {len(traces['bubble'])-1} 步", F.get(CJK, 50), TXT, scale=push, alpha=q3)
            def cta(d):
                q = ease_out((t - T_WIN) / 0.6)
                text_pop(d, (W/2, H/2 - 60*s - (1 - q) * 40*s), "你猜对了吗？", F.get(CJK, 100), TXT, scale=1 + 0.03 * (t - T_WIN), stroke=int(6*s))
                q2 = ease_io((t - T_WIN - 0.3) / 0.6)
                if q2 > 0: text_pop(d, (W/2, H/2 + 90*s), "关注我，下期：归并排序登场", F.get(CJK, 54), CMP, scale=1 + 0.02 * (t - T_WIN), alpha=q2)
            x = (t - (T_WIN - 0.5)) / 1.0
            img = crossfade(img, result, cta, min(max(x, 0), 1), dip=True)
        # 结尾 0.5 秒淡出到黑
        fo = ease_io((t - (T_END - 0.5)) / 0.5)
        if fo > 0: img = Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), fo)
        ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait()
    import os; os.remove(wav_path)
    print(f"{args.out}: {W}x{H} {T_END:.1f}s ratio={ratio:.2f}")

if __name__ == "__main__":
    main()
