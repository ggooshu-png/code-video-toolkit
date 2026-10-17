# 代码动画视频工具包

全平台爆款代码动画视频的渲染器、技能和制作笔记。

- `engine/`：渲染器（Python + PIL + numpy + ffmpeg），一套代码同时输出 9:16 与 16:9。
- `skills/code-animation-video/SKILL.md`：视频制作技能，每周更新一次。
- `notes/`：选题记录、复盘和经验。
- 成片不入库（体积大），存放在项目文件夹 `videos/` 下。

## 快速开始

```bash
pip install pillow numpy   # 另需 ffmpeg 和文泉驿正黑字体
python3 engine/sort_race.py --aspect 9:16 --preview --out preview.mp4
python3 engine/sort_race.py --aspect 16:9 --out sort-race_16x9.mp4
```
