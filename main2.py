from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from moviepy.editor import VideoFileClip, concatenate_videoclips
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS設定
origins = [
    "http://localhost:3000",  # ローカルで開発している場合の例
    "https://your-frontend-domain.com",  # 実際のフロントエンドのドメイン
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 許可するオリジンのリスト
    allow_credentials=True,
    allow_methods=["*"],  # 許可するHTTPメソッド（ここではすべてのメソッドを許可）
    allow_headers=["*"],  # 許可するHTTPヘッダー（ここではすべてのヘッダーを許可）
)

# フォルダパスの設定
VIDEOS_DIR = "videos"
OUTPUT_DIR = "output"

# 入力データのためのPydanticモデル
class VideoRequest(BaseModel):
    input_str: str

@app.on_event("startup")
def startup():
    # 必要なディレクトリが存在しない場合は作成
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.post("/merge_videos/")
async def merge_videos(request: VideoRequest):
    input_str = request.input_str

    if not input_str:
        raise HTTPException(status_code=400, detail="Input string cannot be empty.")

    clips = []
    skipped_files = []  # スキップされたファイルを保存するリスト
    invalid_files = []  # 存在しないファイルを保存するリスト
    checked_files = []  # チェックされたファイルを保存するリスト

    print(f"Received input string: {input_str}")  # 入力された文字列を表示

    for i in range(len(input_str) - 1):
        pair = input_str[i:i+2]  # 1文字ずつずらして2文字取り出す
        if len(pair) < 2:
            continue

        video_path = os.path.join(VIDEOS_DIR, f"{pair}.mp4")
        checked_files.append(pair)  # チェックしたファイルを保存

        # ファイルが存在するかチェック
        print(f"Checking for video file: {video_path}")  # チェックしているファイルを表示

        if os.path.exists(video_path):
            try:
                clip = VideoFileClip(video_path)
                clips.append(clip)
            except Exception as e:
                skipped_files.append(pair)
                print(f"Error while loading {pair}: {str(e)}")  # エラー時のログ
                continue
        else:
            invalid_files.append(pair)
            print(f"File not found: {pair}")  # ファイルが見つからない場合のログ

    if not clips:
        raise HTTPException(status_code=404, detail="No valid video files found for the given input.")

    # デバッグ情報の表示
    print("Checked files:", checked_files)
    print("Skipped files:", skipped_files)
    print("Invalid files:", invalid_files)

    if skipped_files or invalid_files:
        return {
            "detail": "Some video files were skipped or not found",
            "skipped_files": skipped_files,
            "invalid_files": invalid_files,
            "checked_files": checked_files
        }

    # 動画を結合
    try:
        final_clip = concatenate_videoclips(clips)
        output_filename = f"merged_video.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
        final_clip.close()
        for clip in clips:
            clip.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during video processing: {str(e)}")

    # Videoをストリーミングして返す
    return StreamingResponse(open(output_path, "rb"), media_type="video/mp4", headers={"Content-Disposition": f"attachment; filename={output_filename}"})