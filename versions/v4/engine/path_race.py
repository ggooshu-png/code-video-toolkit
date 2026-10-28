"""寻路算法对决代码动画：A* vs Dijkstra —— 复用 sort_race 的字体、缓动和亚像素文字（60fps 整条连续渲染）。

用法: python3 path_race.py --aspect 9:16|16:9 --out out.mp4 [--cols 33 --rows 21] [--seed 5]
      [--wall 0.3] [--eps 40] [--next 下期预告] [--preview]
"""
import argparse, heapq, math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sort_race import (FPS, SR, CJK, MONO, MONO_B, BG, PANEL, BORDER, TXT, DIM, CMP, DONE,
                       ease_out_back, ease_io, ease_out, lerp, Fonts, text_pop)

WALL = (48, 54, 61)
CELL = (28, 34, 42)
START = (63, 220, 160)
GOAL = (255, 92, 92)
PATH = (255, 214, 10)
ACCENT = {"astar": (63, 220, 160), "dijkstra": (120, 170, 255)}
VISIT = {"astar": (35, 120, 100), "dijkstra": (50, 80, 150)}
NAME = {"astar": "A* 搜索", "dijkstra": "Dijkstra"}
SUB = {"astar": "g + h 启发式", "dijkstra": "只看 g 距离"}
CODE = {
    "dijkstra": ["pq = [(0, start)]", "while pq:", "  g, u = pq.pop_min()", "  for v in nbrs(u):", "    pq.push(g+1, v)"],
    "astar":    ["pq = [(h(start), start)]", "while pq:", "  f, u = pq.pop_min()", "  for v in nbrs(u):", "    pq.push(g+1 + h(v), v)"],
}

# ---------- 地图与搜索轨迹 ----------
def make_grid(cols, rows, wall, rng):
    g = [[rng.random() < wall for _ in range(cols)] for _ in range(rows)]
    # 加几道长墙，逼出绕路
    for _ in range(max(2, cols // 8)):
        x = rng.randrange(4, cols - 4)
        y0 = rng.randrange(0, rows // 2); y1 = rng.randrange(rows // 2, rows)
        gap = rng.randrange(y0, y1 + 1)
        for y in range(y0, y1 + 1):
            if y != gap: g[y][x] = True
    s, t = (1, rows // 2), (cols - 2, rows // 2)
    for (x, y) in (s, t):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if 0 <= x + dx < cols and 0 <= y + dy < rows: g[y + dy][x + dx] = False
    return g, s, t

def search(g, s, t, heuristic):
    rows, cols = len(g), len(g[0])
    h = (lambda p: abs(p[0] - t[0]) + abs(p[1] - t[1])) if heuristic else (lambda p: 0)
    dist = {s: 0}; prev = {}; pq = [(h(s), 0, s)]; closed = set(); order = []; cnt = 0
    while pq:
        f, _, u = heapq.heappop(pq)
        if u in closed: continue
        closed.add(u); order.append(u)
        if u == t: break
        x, y = u
        for v in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= v[0] < cols and 0 <= v[1] < rows and not g[v[1]][v[0]]:
                nd = dist[u] + 1
                if nd < dist.get(v, 1e9):
                    dist[v] = nd; prev[v] = u; cnt += 1
                    heapq.heappush(pq, (nd + h(v), cnt, v))
    if t not in closed: return None
    path = [t]
    while path[-1] != s: path.append(prev[path[-1]])
    return order, path[::-1]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aspect", default="9:16")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=33)
    ap.add_argument("--rows", type=int, default=21)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--wall", type=float, default=0.28)
    ap.add_argument("--eps", type=float, default=40.0, help="每秒展开的格子数，两边相同")
    ap.add_argument("--next", default="关注我，下期见")
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()

    vertical = args.aspect == "9:16"
    W, H = (1080, 1920) if vertical else (1920, 1080)
    if args.preview: W, H = W // 2, H // 2
    s = W / (1080 if vertical else 1920)
    F = Fonts(s)

    rng = random.Random(args.seed)
    while True:
        grid, S, T = make_grid(args.cols, args.rows, args.wall, rng)
        rd, ra = search(grid, S, T, False), search(grid, S, T, True)
        if rd and ra: break
    runs = {"astar": ra, "dijkstra": rd}
    LA, RA = "astar", "dijkstra"

    HOOK, EPS = 2.5, args.eps
    PATH_T = 1.0  # 找到终点后画出路径用时
    fin_search = {k: HOOK + len(v[0]) / EPS for k, v in runs.items()}
    finish_t = {k: fin_search[k] + PATH_T for k in runs}
    T_RACE_END = max(finish_t.values()) + 0.6
    T_WIN = T_RACE_END + 2.8
    T_END = T_WIN + 2.4
    nframes = int(T_END * FPS)
    ratio = len(rd[0]) / len(ra[0])
    visit_t = {k: {c: HOOK + i / EPS for i, c in enumerate(v[0])} for k, v in runs.items()}

    if vertical:
        title_box = (0, 0, W, int(270 * s))
        panels = {LA: (int(40*s), int(280*s), W - int(40*s), int(1060*s)),
                  RA: (int(40*s), int(1090*s), W - int(40*s), int(1870*s))}
    else:
        title_box = (0, 0, W, int(190 * s))
        panels = {LA: (int(60*s), int(210*s), int(940*s), int(1000*s)),
                  RA: (int(980*s), int(210*s), W - int(60*s), int(1000*s))}

    # ---------- 音频 ----------
    audio = np.zeros(int(T_END * SR) + SR, dtype=np.float32)
    bl = int(0.04 * SR); tt = np.arange(bl) / SR; env = np.exp(-tt * 70)
    maxd = args.cols + args.rows
    for k, (order, path) in runs.items():
        for i, (x, y) in enumerate(order):
            f = 260 + 700 * (abs(x - S[0]) + abs(y - S[1])) / maxd
            w = np.sin(2*np.pi*f*tt) if k == LA else np.sign(np.sin(2*np.pi*f*tt)) * 0.45
            st = int((HOOK + i / EPS) * SR); audio[st:st + bl] += (w * env * 0.12).astype(np.float32)
        for i in range(len(path)):  # 路径上扬琶音
            st = int((fin_search[k] + PATH_T * i / len(path)) * SR)
            f = 440 * 2 ** (i / len(path) * 1.5)
            audio[st:st + bl] += (np.sin(2*np.pi*f*tt) * env * 0.10).astype(np.float32)
    def chime(t0, freqs, amp=0.25, dur=0.6):
        n = int(dur * SR); x = np.arange(n) / SR; e = np.exp(-x * 5)
        sig = sum(np.sin(2*np.pi*f*x) for f in freqs) / len(freqs)
        st = int(t0 * SR); audio[st:st + n] += (sig * e * amp).astype(np.float32)
    WIN, LOSE = sorted(runs, key=lambda k: finish_t[k])
    chime(0.05, [523, 659], 0.3, 0.4)
    chime(finish_t[WIN], [784, 988, 1175])
    chime(finish_t[LOSE], [392, 494])
    chime(T_RACE_END + 0.1, [523, 659, 784, 1047], 0.35, 1.2)
    fade = int(0.5 * SR); end = int(T_END * SR)
    audio[end - fade:end] *= np.linspace(1, 0, fade, dtype=np.float32); audio[end:] = 0
    audio = np.clip(audio, -1, 1)
    wav_path = args.out + ".wav"
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((audio * 32767).astype(np.int16).tobytes())

    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav_path,
                           "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-maxrate", "20M", "-bufsize", "40M",
                           "-g", str(FPS * 2), "-pix_fmt", "yuv420p", "-fps_mode", "cfr",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", args.out],
                          stdin=subprocess.PIPE)

    # 每个面板的网格几何
    geo = {}
    for k, (x0, y0, x1, y1) in panels.items():
        code_h = 186 * s
        ax0, ax1, ay0, ay1 = x0 + 30*s, x1 - 30*s, y0 + 110*s, y1 - code_h - 36*s
        cs = min((ax1 - ax0) / args.cols, (ay1 - ay0) / args.rows)
        gx = (ax0 + ax1) / 2 - cs * args.cols / 2; gy = (ay0 + ay1) / 2 - cs * args.rows / 2
        geo[k] = (gx, gy, cs)

    def cell_rect(k, c, inset=0.08, off=0):
        gx, gy, cs = geo[k]
        x, y = c
        return (gx + x*cs + cs*inset, gy + y*cs + cs*inset + off, gx + (x+1)*cs - cs*inset, gy + (y+1)*cs - cs*inset + off)

    def draw_panel(d, k, box, t, off):
        x0, y0, x1, y1 = box
        acc = ACCENT[k]
        d.rounded_rectangle(box, radius=int(24*s), fill=PANEL, outline=lerp(BORDER, acc, 0.5), width=max(1, int(3*s)))
        d.text((x0 + 30*s, y0 + 26*s), NAME[k], font=F.get(CJK, 54), fill=acc)
        d.text((x0 + 30*s + F.get(CJK, 54).getlength(NAME[k]) + 20*s, y0 + 44*s), SUB[k], font=F.get(CJK, 30), fill=DIM)
        order, path = runs[k]
        found = t >= fin_search[k]; finished = t >= finish_t[k]
        elapsed = min(max(0, t - HOOK), finish_t[k] - HOOK)
        d.text((x1 - 30*s, y0 + 30*s), f"{elapsed:5.2f}s", font=F.get(MONO_B, 48), fill=DONE if finished else TXT, anchor="ra")
        # 网格：每个格子按自己的访问时间连续淡入（访问瞬间先亮后暗）
        vt = visit_t[k]
        for y in range(args.rows):
            for x in range(args.cols):
                c = (x, y)
                if grid[y][x]: col = WALL
                elif c in vt and t > vt[c]:
                    a = ease_io((t - vt[c]) / 0.35)
                    hot = math.exp(-((t - vt[c]) / 0.25) ** 2)
                    col = lerp(lerp(CELL, VISIT[k], a), (200, 240, 255), hot * 0.7)
                else: col = CELL
                d.rectangle(cell_rect(k, c, off=off), fill=col)
        # 路径：按长度连续生长，末端格子按小数部分淡入
        if found:
            p = ease_io((t - fin_search[k]) / PATH_T) * len(path)
            for i, c in enumerate(path):
                a = min(max(p - i, 0), 1)
                if a <= 0: break
                d.rectangle(cell_rect(k, c, 0.18, off), fill=lerp(VISIT[k], PATH, a))
        for c, col in ((S, START), (T, GOAL)):
            d.rounded_rectangle(cell_rect(k, c, 0.0, off), radius=int(geo[k][2] / 4), fill=col)
        # 代码框
        code_h = 186 * s
        cy0 = y1 - code_h - 20*s
        d.rounded_rectangle((x0 + 20*s, cy0, x1 - 20*s, y1 - 20*s), radius=int(14*s), fill=BG)
        lh = 32 * s
        fidx = max(0, t - HOOK) * EPS; ph = fidx - int(fidx)
        active = -1 if found else (2 if ph < 0.4 else (3 if ph < 0.7 else 4))
        for li, line in enumerate(CODE[k]):
            ly = cy0 + 14*s + li * lh
            if li == active and t >= HOOK:
                d.rectangle((x0 + 22*s, ly - 2*s, x1 - 22*s, ly + lh - 4*s), fill=(56, 48, 20))
                d.rectangle((x0 + 22*s, ly - 2*s, x0 + 28*s, ly + lh - 4*s), fill=CMP)
            d.text((x0 + 44*s, ly), line, font=F.get(MONO, 27), fill=TXT if li == active else DIM)
        n_vis = min(len(order), int(fidx))
        d.text((x1 - 40*s, y1 - 40*s), f"探索 {n_vis} 格", font=F.get(CJK, 26), fill=DIM, anchor="rb")
        if finished:
            q = ease_out_back((t - finish_t[k]) / 0.5)
            gx, gy, cs = geo[k]
            fade = 1 - ease_io((t - finish_t[k] - 1.2) / 0.6)  # 停留后淡出，露出完整路径
            if fade > 0: text_pop(d, (gx + cs * args.cols / 2, gy + cs * args.rows / 2 + off), "到达!", F.get(CJK, 76), DONE, scale=q, alpha=fade, stroke=int(6*s))

    def crossfade(base, draw_a, draw_b, x, dip=False):
        def layer(fn):
            if fn is None: return base
            im = base.copy(); fn(ImageDraw.Draw(im)); return im
        if dip:
            if x < 0.5: return Image.blend(base, layer(draw_a), ease_io(1 - 2 * x)) if draw_a else base
            return Image.blend(base, layer(draw_b), ease_io(2 * x - 1)) if draw_b else base
        if x <= 0: return layer(draw_a)
        if x >= 1: return layer(draw_b)
        return Image.blend(layer(draw_a), layer(draw_b), x)

    bg = Image.new("RGB", (W, H), BG)
    dbg = ImageDraw.Draw(bg); gstep = int(60 * s)
    for x in range(0, W, gstep): dbg.line((x, 0, x, H), fill=(18, 23, 30))
    for y in range(0, H, gstep): dbg.line((0, y, W, y), fill=(18, 23, 30))
    gap = len(rd[0]) - len(ra[0])
    verdict = f"少走 {ratio:.1f} 倍冤枉路" if ratio >= 1.15 else f"险胜 {gap} 格！"

    for fi in range(nframes):
        t = fi / FPS
        img = bg.copy()
        tx, ty = W / 2, title_box[3] / 2
        def hook_title(d):
            p = ease_out_back(t / 0.45)
            text_pop(d, (tx, ty - 50*s), "从绿点走到红点", F.get(CJK, 64), TXT, scale=p * (1 + 0.02 * t))
            p2 = ease_out_back((t - 0.6) / 0.45)
            if p2 > 0: text_pop(d, (tx, ty + 50*s), "谁先找到路？", F.get(CJK, 96), CMP, scale=p2 * (1 + 0.03 * t), stroke=int(4*s))
        def main_title(d):
            text_pop(d, (tx, ty - 30*s), "寻路算法大对决", F.get(CJK, 78), TXT)
            text_pop(d, (tx, ty + 50*s), "A* VS Dijkstra", F.get(CJK, 40), DIM)
        x = (t - (HOOK - 0.5)) / 1.0
        img = crossfade(img, hook_title, main_title, min(max(x, 0), 1), dip=True)
        for k, box in panels.items():
            appear = ease_io((t - 1.0 - (0.25 if k == RA else 0)) / 0.9)
            if appear <= 0: continue
            off = (1 - appear) * 80 * s
            b = (box[0], box[1] + off, box[2], box[3] + off)
            img = crossfade(img, None, lambda dd: draw_panel(dd, k, b, t, off), appear)
        d = ImageDraw.Draw(img)
        px = W * t / T_END; full = int(px)
        if full > 0: d.rectangle((0, H - 10*s, full - 1, H), fill=CMP)
        d.rectangle((full, H - 10*s, full, H), fill=lerp(BG, CMP, px - full))
        if t >= T_RACE_END:
            p = ease_io((t - T_RACE_END) / 0.6)
            img = Image.alpha_composite(img.convert("RGBA"), Image.new("RGBA", (W, H), (0, 0, 0, int(190 * p)))).convert("RGB")
            def result(d):
                push = 1 + 0.03 * (t - T_RACE_END)
                q = ease_out_back((t - T_RACE_END - 0.15) / 0.5)
                if q > 0: text_pop(d, (W/2, H/2 - 120*s), f"{NAME[WIN]} 胜", F.get(CJK, 110), ACCENT[WIN], scale=q * push, stroke=int(6*s))
                q2 = ease_out_back((t - T_RACE_END - 0.55) / 0.5)
                if q2 > 0: text_pop(d, (W/2, H/2 + 40*s), verdict, F.get(CJK, 110), CMP, scale=q2 * push, stroke=int(8*s))
                q3 = ease_out((t - T_RACE_END - 1.1) / 0.4)
                if q3 > 0: text_pop(d, (W/2, H/2 + 190*s), f"探索 {len(ra[0])} 格  vs  {len(rd[0])} 格，路一样长", F.get(CJK, 44), TXT, scale=push, alpha=q3)
            def cta(d):
                q = ease_out((t - T_WIN) / 0.6)
                text_pop(d, (W/2, H/2 - 60*s - (1 - q) * 40*s), "你猜对了吗？", F.get(CJK, 100), TXT, scale=1 + 0.03 * (t - T_WIN), stroke=int(6*s))
                q2 = ease_io((t - T_WIN - 0.3) / 0.6)
                if q2 > 0: text_pop(d, (W/2, H/2 + 90*s), args.next, F.get(CJK, 54), CMP, scale=1 + 0.02 * (t - T_WIN), alpha=q2)
            x = (t - (T_WIN - 0.5)) / 1.0
            img = crossfade(img, result, cta, min(max(x, 0), 1), dip=True)
        fo = ease_io((t - (T_END - 0.5)) / 0.5)
        if fo > 0: img = Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), fo)
        ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait()
    os.remove(wav_path)
    print(f"{args.out}: {W}x{H} {T_END:.1f}s 探索 A*={len(ra[0])} Dijkstra={len(rd[0])} 路长={len(ra[1])} ratio={ratio:.2f}")

if __name__ == "__main__":
    main()
