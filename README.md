# Vector Space — 代码视频素材

程序化渲染的「向量空间」星系慢转镜头（无解说宣传 / 代码视频素材）。独立目录，不属于任何仓。

## 文件职责

| 文件 | 作用 |
| --- | --- |
| `render_vs.py` | 唯一源码：场景构建（星尘 3800 / 臂星 2200 / 双层雾带 / 主角星）+ 旋转律 + 逐帧合成 |
| `make_space_still.py` | 出定版静帧（锚点 t=3.1s）→ `vs_space_still_anchor.png` |
| `make_space_video.py` | 出 15 s 视频 → `vs_space_video_v2.mp4` |
| `probe_mist_balance.py` | 探针：雾带上下半质量、连续性、尺寸/亮度分布 |
| `probe_motion_pops.py` | 探针：深度阈值换挡统计（前/后雾乘数一帧跳次数） |

## 当前产物

- 定版静帧 `vs_space_still_42g.png`；`vs_space_still_anchor.png` 为逐字节复刻（锚点验证用）
- 视频 `vs_space_video_v2.mp4`（差速自转 + 起转缓入）；`vs_space_video.mp4` 为旧版，留作 A/B
- 自查帧 `vs_v2chk_*`（新片）、`vs_oldchk_*`（旧片首末帧）

## 渲染

```bat
set PYTHONIOENCODING=utf-8
E:\app\python\agent\deer-flow\backend\.venv\Scripts\python.exe make_space_video.py
```

依赖：numpy、Pillow、PATH 上的 ffmpeg。输出名写死在脚本里，重渲到同名文件时注意看图软件锁定（OSError 22）就换名。

## 运动参数（render_vs.py 顶部）

- 锚点 `T_REF=3.1s / A_REF=43.6°`：该时刻渲染逐字节等于定版静帧，改旋转律时别动锚点。
- 差速自转 `SHEAR_K=0.22`：内快外慢，15 s 内内外剪切约 15°（0.4 约翻倍，旋臂会更卷）。
- 起转缓入 `EASE_T=1.25s`：角速度 0→6°/s（60 秒一圈）。

## archive/

历史件 97 个，只存档不删：历史静帧 41、检查帧 `vs_chk_*` 40、旧视频自查帧 `vs_vframe_*` 3，以及早期命中/图标/loop/mp4check 实验件 13。
