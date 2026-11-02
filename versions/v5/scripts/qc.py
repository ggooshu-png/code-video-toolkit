"""出片前自检：帧数/时间戳连续性 + 逐帧差分找硬切与重复帧。

用法: python3 scripts/qc.py video.mp4 [--allow-freeze 起-止,起-止 ...]
"""
import json, subprocess, sys
import numpy as np

def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=r_frame_rate,avg_frame_rate,nb_frames:format=duration",
                          "-of", "json", path], capture_output=True, text=True).stdout
    j = json.loads(out); st = j["streams"][0]
    num, den = map(int, st["r_frame_rate"].split("/"))
    return num / den, st["avg_frame_rate"], int(st.get("nb_frames") or 0), float(j["format"]["duration"])

def frames(path, w=160, h=90):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={w}:{h}", "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(w * h)
        if len(b) < w * h: break
        yield np.frombuffer(b, np.uint8).astype(np.float32)

def main():
    path = sys.argv[1]
    fps, avg, nb, dur = probe(path)
    pts = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.split()
    ts = np.sort(np.array([float(x) for x in pts if x and x != "N/A"]))
    gaps = np.diff(ts)
    bad_ts = int(np.sum(np.abs(gaps - 1 / fps) > 0.5 / fps))
    diffs, prev = [], None
    for f in frames(path):
        if prev is not None: diffs.append(float(np.mean(np.abs(f - prev))))
        prev = f
    d = np.array(diffs)
    med = np.array([np.median(d[max(0, i - 15):i + 16]) for i in range(len(d))])
    cuts = [i + 1 for i in range(len(d)) if d[i] > 5 * max(med[i], 0.3) and d[i] > 3]
    dups = [i + 1 for i in range(len(d)) if d[i] < 0.01]
    print(f"fps={fps:.3f} avg={avg} 帧数={len(d)+1} 期望={round(dur*fps)} 时间戳异常={bad_ts}")
    print(f"疑似硬切/跳变 {len(cuts)} 处: {[round(c/fps,2) for c in cuts[:20]]}")
    print(f"重复帧 {len(dups)} 帧" + (f"，首个在 {dups[0]/fps:.2f}s" if dups else ""))
    ok = bad_ts == 0 and not cuts and abs(len(d) + 1 - round(dur * fps)) <= 1
    print("结论:", "通过" if ok else "需检查（刻意定格的重复帧可忽略）")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
