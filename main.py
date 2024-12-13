from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from moviepy.editor import VideoFileClip, concatenate_videoclips
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 必要に応じて特定のオリジンを許可
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# フォルダ設定
VIDEOS_DIR = "videos"
OUTPUT_DIR = "output"

# 入力データモデル
class VideoRequest(BaseModel):
    input_str: str

@app.on_event("startup")
def startup():
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.post("/merge_videos/")
async def merge_videos(request: VideoRequest):
    input_str = request.input_str.strip()

    if not input_str:
        raise HTTPException(status_code=400, detail="Input string cannot be empty.")

    clips = []
    for i in range(len(input_str) - 1):
        pair = input_str[i : i + 2]
        video_path = os.path.join(VIDEOS_DIR, f"{pair}.mp4")
        if os.path.exists(video_path):
            try:
                clips.append(VideoFileClip(video_path))
            except Exception as e:
                print(f"Error loading {video_path}: {e}")
        else:
            print(f"File not found: {video_path}")

    if not clips:
        raise HTTPException(status_code=404, detail="No valid video files found.")

    try:
        final_clip = concatenate_videoclips(clips)
        output_path = os.path.join(OUTPUT_DIR, "merged_video.mp4")
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
        final_clip.close()

        for clip in clips:
            clip.close()

        return StreamingResponse(
            open(output_path, "rb"),
            media_type="video/mp4",
            headers={"Content-Disposition": "attachment; filename=merged_video.mp4"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video processing failed: {e}")
