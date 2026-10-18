# Vector Space — 代码视频素材

程序化渲染的「向量空间」星系慢转镜头（无解说宣传 / 代码视频素材）。独立视频目录，代码、输出与存档自包含。

## 文件职责

| 文件 | 作用 |
| --- | --- |
| `render_vs.py` | 唯一源码：v4 场景（星尘 3800 / 臂星 2200 / 核球 / 背景星场 / 雾带 / 尘带）+ 旋转律 + 逐帧合成 |
| `make_space_still.py` | 出 v4 定版静帧（t=3.1s）→ `renders/final/vs_space_still_v4.png` |
| `make_space_video.py` | 出 15 s v4 视频 → `renders/final/vs_space_video_v4.mp4` |
| `probe_mist_balance.py` | 探针：雾带上下半质量、连续性、尺寸/亮度分布 |
| `probe_motion_pops.py` | 探针：深度阈值换挡统计（前/后雾乘数一帧跳次数） |

## 目录

- `renders/final/`：当前交付（v4 静帧、15 s 成片、`vs_v4final_*` 自查帧）
- `renders/compare/`：v3/v4 对照件（静帧、预览、A/B、首末帧）
- `renders/legacy/`：v2 定版与旧检查帧
- `archive/`：历史件与已放弃的 v5 试验（gitignore，不入库）

## 当前产物

- 定版静帧 `renders/final/vs_space_still_v4.png`；视频 `renders/final/vs_space_video_v4.mp4`（差速自转 + 起转缓入）
- v2 定版 `renders/legacy/vs_space_still_42g.png` / `renders/legacy/vs_space_video_v2.mp4` 留作 A/B；`renders/legacy/vs_space_still_anchor.png` 为 v2 锚点，可由已提交的导入版渲染器复现
- 自查帧 `renders/final/vs_v4final_*`

## v4 画面构成

- 核球：核心星 + 暖色辉光 + 薄雾，中心不再空
- 背景：两层视差星场 + 闪烁，画面不再是一块静止底
- 旋臂：星尘与臂星向臂内聚集，盘缘变薄变暗，盘面内暖外冷
- 尘带：臂内缘暗尘 + 盘面中缝薄尘，合成在远/近层之间

## 渲染

从仓库根目录：

```bat
cd videos\vector_space
set PYTHONIOENCODING=utf-8
E:\app\python\agent\deer-flow\backend\.venv\Scripts\python.exe make_space_video.py
```

依赖：numpy、Pillow、PATH 上的 ffmpeg。输出名写死在脚本里，重渲到同名文件时注意看图软件锁定（OSError 22）就换名。

## 运动参数（render_vs.py 顶部）

- 锚点 `T_REF=3.1s / A_REF=43.6°`：该时刻渲染逐字节等于定版静帧，改旋转律时别动锚点。
- 差速自转 `SHEAR_K=0.22`：内快外慢，15 s 内内外剪切约 15°（0.4 约翻倍，旋臂会更卷）。
- 起转缓入 `EASE_T=1.25s`：角速度 0→6°/s（60 秒一圈）。

## archive/

历史件 97 个，只存档不删：历史静帧 41、检查帧 `vs_chk_*` 40、旧视频自查帧 `vs_vframe_*` 3，以及早期命中/图标/loop/mp4check 实验件 13。另有已放弃的 v5 试验件 7 个，存于 `archive/v5/`（gitignore）。
