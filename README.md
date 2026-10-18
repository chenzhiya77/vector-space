# 代码视频素材

程序化渲染的代码视频素材。每个视频一个独立目录，代码、输出与存档互不引用。

## 视频

| 目录 | 内容 | 成片 |
| --- | --- | --- |
| [`videos/vector_space/`](videos/vector_space/README.md) | 向量空间星系慢转镜头 | [`vs_space_video_v4.mp4`](videos/vector_space/renders/final/vs_space_video_v4.mp4) |

## 运行

从仓库根目录：

```bat
cd videos\vector_space
set PYTHONIOENCODING=utf-8
E:\app\python\agent\deer-flow\backend\.venv\Scripts\python.exe make_space_video.py
```

依赖：numpy、Pillow、PATH 上的 ffmpeg。细节见各视频目录的 README。
