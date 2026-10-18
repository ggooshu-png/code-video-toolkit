---
name: code-animation-video
description: Make a viral-style code/algorithm animation video, fully rendered in 9:16 and 16:9 for Douyin, Bilibili, YouTube, Shorts and more.
---

# 代码动画爆款视频制作

## 技术栈（已验证可用）
- Python + PIL 逐帧绘制，numpy 合成音效，ffmpeg 通过 stdin 管道编码。无需 Manim/LaTeX，容器里开箱即用。
- 参考实现：`engine/sort_race.py`（排序对决）。新题材复制它改：数据轨迹函数 + 布局 + 文案。
- 字体：中文 `/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc`；代码 `DejaVuSansMono.ttf`。中文字符绝不能用等宽字体画（会变方框）。
- 所有尺寸乘缩放系数 `s = W / 基准宽`，一套代码同时出 1080x1920 和 1920x1080；竖屏上下堆叠，横屏左右并排。
- 编码：`libx264 -crf 18 -pix_fmt yuv420p -c:a aac -movflags +faststart`，30fps。

## 爆款结构（20 到 30 秒）
1. 0 到 2.5 秒钩子：一个问题或悬念（"谁先排完？"），大字弹出（ease_out_back）。
2. 主体：可视化对比或过程，同屏显示正在执行的代码行高亮、计时器、步数。
3. 揭晓：暗场 + 大号结论数字（"快了 2.9 倍"）。
4. 结尾 CTA：互动问题 + 下期预告，促评论和关注。
- 底部常驻进度条提升完播率；背景深色网格，配色 GitHub Dark 风格，状态色：比较=黄、交换=红、完成=绿、枢轴=紫。

## 声音
- "Sound of Sorting" 式音效：每次操作一个 45ms 短音，音高随数值变化；两条赛道用不同音色（正弦/方波）。关键节点加和弦提示音。平台静音自动播放时画面也要能独立看懂。

## 流程（求快）
1. `--preview` 半分辨率渲染（约 10 秒）。
2. 用 ffmpeg 抽 4 到 5 帧拼成一张图检查：钩子、主体中段、完成瞬间、揭晓、结尾。重点查方框字、文字溢出、遮挡。
3. 两个比例并行全分辨率渲染，输出到 `/mnt/project-files/videos/<题目>/<题目>_9x16.mp4` 与 `_16x9.mp4`。

## 平台要点
- 抖音/快手/视频号/YouTube Shorts/小红书：9:16，前 3 秒决定去留，竖屏安全区：上下各留约 150px 不放关键信息（避开 UI）。
- B站/YouTube 横版：16:9，可延长到 1 到 3 分钟，加讲解节奏。
- 发布永远由用户确认，不代发。

## 选题库
排序对决（归并、堆、基数）、递归可视化、二分查找猜数、寻路算法 A* vs Dijkstra、一行代码黑魔法、Bug 找茬、代码打字特效 + 运行结果。

## 持续改进
每做完一条，把新踩的坑和好用的技巧补进本技能（一两行一条），保持精简。
