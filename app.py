# main.py
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, StreamingResponse
import yt_dlp
import os
import tempfile

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Video Downloader API - YouTube, Facebook, TikTok", "status": "active"}

@app.get("/info")
def get_info(url: str = Query(...)):
    """ভিডিও ইনফো নিন (ডাউনলোড ছাড়া)"""
    ydl_opts = {'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "formats": [{"format_id": f.get("format_id"), "ext": f.get("ext"), "quality": f.get("format_note")} 
                           for f in info.get("formats", []) if f.get("vcodec") != "none"]
            }
    except Exception as e:
        return {"error": str(e)}

@app.get("/download")
def download_video(url: str = Query(...), format_id: str = Query("best")):
    """ভিডিও ডাউনলোড করুন"""
    temp_dir = tempfile.mkdtemp()
    file_path = f"{temp_dir}/video.mp4"
    
    ydl_opts = {
        'outtmpl': file_path,
        'format': format_id,
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        def iter_file():
            with open(file_path, 'rb') as f:
                yield from f
            os.remove(file_path)
            os.rmdir(temp_dir)
        
        return StreamingResponse(iter_file(), media_type="video/mp4")
    except Exception as e:
        return {"error": str(e)}
