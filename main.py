import os
import re
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI()

# Permite que la aplicación del celular se conecte al servidor sin bloqueos de seguridad
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.get("/")
async def read_root():
    return {"status": "MAJOMUSIC Server is Running Online"}

@app.get("/api/search")
async def search_songs(q: str):
    if not q:
        raise HTTPException(status_code=400, detail="Falta consulta")
    
    ydl_opts = {
        'extract_flat': True,
        'skip_download': True,
        'quiet': True,
        'extractor_args': {'youtube': {'player_client': 'android'}},
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(f"ytsearch5:{q}", download=False)
            songs = [{"id": e["id"], "title": e["title"]} for e in res.get('entries', []) if e]
            return {"success": True, "results": songs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/proxy-stream")
async def proxy_stream(id: str):
    if not id:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    video_url = f"https://youtube.com{id}"
    ydl_opts = {
        'format': 'bestaudio/best',
        'skip_download': True,
        'quiet': True,
        'extractor_args': {'youtube': {'player_client': 'android'}},
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info.get('url')
            
        if not stream_url:
            raise HTTPException(status_code=404, detail="No se encontró flujo")
        
        response = requests.get(
            stream_url, 
            stream=True, 
            headers={"User-Agent": "Mozilla/5.0"}
        )
        
        def generate_audio_chunks():
            for chunk in response.iter_content(chunk_size=131072):
                if chunk:
                    yield chunk

        return StreamingResponse(
            generate_audio_chunks(), 
            media_type="audio/mpeg",
            headers={"Accept-Ranges": "bytes"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download")
async def download_song(id: str):
    if not id:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    video_url = f"https://youtube.com{id}"
    final_mp3_path = os.path.join(DOWNLOAD_DIR, f"{id}.mp3")
    
    if os.path.exists(final_mp3_path):
        return FileResponse(path=final_mp3_path, media_type='audio/mpeg', filename=f"{id}.mp3")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, f"{id}.%(ext)s"),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'extractor_args': {'youtube': {'player_client': 'android'}},
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return FileResponse(path=final_mp3_path, media_type='audio/mpeg', filename=f"{id}.mp3")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))