from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from pathlib import Path
from typing import Optional
import os, uuid, shutil, subprocess, re, json, time, asyncio, textwrap
import trafilatura
import edge_tts

BASE = Path(__file__).resolve().parent
DATA = Path(os.getenv("DATA_DIR", str(BASE.parent / "data"))).resolve()
UPLOADS = DATA / "uploads"
JOBS = DATA / "jobs"
for d in (UPLOADS, JOBS):
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="RADAR VIDEO NEWS AI", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

EDITORIAL_RULES = """
Biên tập theo dự án báo chí cách mạng QUẢNG NINH NGÀY MỚI.
Viết lại bằng câu chữ mới nhưng trung thành tuyệt đối với dữ kiện; khách quan, chuẩn mực,
không suy diễn, không thêm dữ kiện chưa kiểm chứng, không kết luận thay cơ quan chức năng.
Tiêu đề IN HOA, tối đa 20 từ, chính xác, không giật gân. Mở bài 2-3 câu; thân bài logic;
đoạn văn 2-4 câu; kết ngắn gọn. Không dùng emoji hoặc câu câu tương tác.
Tránh các cụm: "không chỉ là", "không chỉ", "không những là", "gây sốt", "bão mạng",
"chấn động", "cực kỳ", "siêu", "vô cùng", "nhất từ trước đến nay", "ai cũng biết",
"có lẽ", "dường như", trừ nguyên văn trích dẫn.
Cuối bài phải có "Nguồn: ..." và "#QUẢNG_NINH_NGÀY_MỚI".
"""

class ExtractRequest(BaseModel):
    url: str

class DraftRequest(BaseModel):
    source: str = "Nguồn chưa xác định"
    url: str = ""
    text: str

def safe_name(name: str) -> str:
    name = Path(name or "upload.bin").name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name[:100] or "upload.bin"

def get_ffmpeg():
    try:
        p = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        return p.returncode == 0
    except Exception:
        return False

def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?…])\s+|\n+', text.strip()) if s.strip()]

def headline_from(text):
    sents = split_sentences(text)
    title = sents[0] if sents else "TIN TỨC QUẢNG NINH"
    title = re.sub(r'\s+', ' ', title).strip(' .')
    words = title.split()
    if len(words) > 20:
        title = " ".join(words[:20])
    return title.upper()

def editorial_draft(text, source, url):
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        raise ValueError("Chưa có nội dung nguồn.")
    # A conservative local draft: preserve the supplied content rather than fabricate facts.
    sents = split_sentences(text)
    title = headline_from(text)
    lead = " ".join(sents[:3])
    body = " ".join(sents[3:])
    src = source.strip() or (url.strip() if url.strip() else "Nguồn do người biên tập cung cấp")
    result = f"{title}\n\n{lead}"
    if body:
        result += f"\n\n{body}"
    result += f"\n\nNguồn: {src}\n#QUẢNG_NINH_NGÀY_MỚI"
    return {"headline": title, "brief": lead[:360], "article": result, "script": " ".join(sents), "note": "Bản nháp cục bộ giữ nguyên dữ kiện đầu vào; cần biên tập và kiểm chứng trước khi xuất bản."}

@app.get("/", response_class=HTMLResponse)
def index():
    return (BASE / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/api/health")
def health():
    return {"ok": True, "ffmpeg": get_ffmpeg(), "tts": True, "data_dir": str(DATA)}

@app.post("/api/extract")
def extract(req: ExtractRequest):
    url = req.url.strip()
    if not re.match(r"^https?://", url, re.I):
        raise HTTPException(400, "Chỉ chấp nhận URL http hoặc https.")
    # Basic SSRF guard: block local/private IP targets.
    from urllib.parse import urlparse
    import socket, ipaddress
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            raise ValueError("URL không hợp lệ")
        ips = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        for item in ips:
            ip = ipaddress.ip_address(item[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise HTTPException(400, "Không truy cập địa chỉ mạng nội bộ.")
    except HTTPException:
        raise
    except Exception:
        # DNS may fail; trafilatura will return an error below.
        pass
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise HTTPException(422, "Không tải được trang. Website có thể chặn truy cập; hãy dán nội dung thủ công.")
        content = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
        if not content or len(content) < 80:
            raise HTTPException(422, "Không trích xuất được bài viết đủ nội dung. Hãy dán nội dung thủ công.")
        return {"url": url, "text": content}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(422, f"Không đọc được bài viết: {str(e)[:180]}")

@app.post("/api/editorial-draft")
def draft(req: DraftRequest):
    try:
        return editorial_draft(req.text, req.source, req.url)
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.post("/api/tts")
async def tts(text: str = Form(...), voice: str = Form("vi-VN-NamMinhNeural")):
    if len(text) > 12000:
        raise HTTPException(413, "Lời dẫn quá dài (giới hạn 12.000 ký tự).")
    allowed = {"vi-VN-NamMinhNeural", "vi-VN-HoaiMyNeural"}
    if voice not in allowed:
        voice = "vi-VN-NamMinhNeural"
    job_id = uuid.uuid4().hex[:12]
    outdir = JOBS / job_id
    outdir.mkdir(parents=True)
    outfile = outdir / "voice.mp3"
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(outfile))
    except Exception as e:
        shutil.rmtree(outdir, ignore_errors=True)
        raise HTTPException(502, f"TTS không kết nối được. Kiểm tra Internet hoặc thử lại: {str(e)[:180]}")
    return {"job_id": job_id, "audio_url": f"/api/jobs/{job_id}/voice.mp3"}

@app.get("/api/jobs/{job_id}/voice.mp3")
def voice_file(job_id: str):
    p = JOBS / job_id / "voice.mp3"
    if not p.exists(): raise HTTPException(404, "Không tìm thấy tệp giọng đọc.")
    return FileResponse(p, media_type="audio/mpeg", filename="voice.mp3")

@app.post("/api/render")
async def render(
    headline: str = Form(...),
    brief: str = Form(""),
    source: str = Form("Tin tức Quảng Ninh"),
    url: str = Form(""),
    brand: str = Form("QUẢNG NINH NGÀY MỚI"),
    script: str = Form(...),
    duration: int = Form(60),
    voice: str = Form("vi-VN-NamMinhNeural"),
    style: str = Form("Bản tin thời sự"),
    files: list[UploadFile] = File(default=[]),
    logo: Optional[UploadFile] = File(default=None),
):
    if not get_ffmpeg():
        raise HTTPException(500, "Chưa cài FFmpeg trên máy chủ.")
    if not script.strip():
        raise HTTPException(400, "Lời dẫn không được để trống.")
    duration = max(15, min(int(duration), 180))
    job_id = uuid.uuid4().hex[:12]
    work = JOBS / job_id
    work.mkdir(parents=True)
    assets = []
    try:
        for i, up in enumerate(files[:12]):
            ext = Path(up.filename or "").suffix.lower()
            if ext not in {".jpg",".jpeg",".png",".webp",".mp4",".mov",".m4v",".webm"}:
                continue
            dest = work / f"asset_{i:02d}{ext}"
            with dest.open("wb") as f:
                shutil.copyfileobj(up.file, f)
            if dest.stat().st_size > 250 * 1024 * 1024:
                raise HTTPException(413, "Mỗi tệp tối đa 250 MB.")
            assets.append(dest)
        logo_path = None
        if logo and logo.filename:
            ext = Path(logo.filename).suffix.lower()
            if ext not in {".png",".jpg",".jpeg",".webp"}: raise HTTPException(400, "Logo phải là PNG/JPG/WEBP.")
            logo_path = work / ("logo" + ext)
            with logo_path.open("wb") as f: shutil.copyfileobj(logo.file, f)
        # TTS online voice generation
        voice = voice if voice in {"vi-VN-NamMinhNeural","vi-VN-HoaiMyNeural"} else "vi-VN-NamMinhNeural"
        audio = work / "voice.mp3"
        try:
            await edge_tts.Communicate(script[:12000], voice).save(str(audio))
        except Exception as e:
            raise HTTPException(502, f"Không tạo được giọng đọc: {str(e)[:160]}")
        # Get audio duration
        probe = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(audio)],capture_output=True,text=True)
        audio_dur = float(probe.stdout.strip() or duration) if probe.returncode == 0 else float(duration)
        # Generate approximate SRT from sentence durations weighted by character count
        sents = split_sentences(script)
        if not sents: sents = [script]
        weights = [max(1, len(s)) for s in sents]
        total = sum(weights)
        def stamp(seconds):
            ms = int(max(0, seconds) * 1000)
            h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        srt_lines=[]; cursor=0.0
        for i,(sent,w) in enumerate(zip(sents,weights),1):
            end = audio_dur * sum(weights[:i]) / total
            srt_lines += [str(i), f"{stamp(cursor)} --> {stamp(end)}", sent, ""]
            cursor=end
        (work/"subtitles.srt").write_text("\\n".join(srt_lines),encoding="utf-8")
        vtt = "WEBVTT\\n\\n" + "\\n".join([f"{i}\\n{stamp(float(i))[:-4]}.000 --> {stamp(float(i)+1)[:-4]}.000\\n{s}\\n" for i,s in enumerate(sents,1)])
        (work/"subtitles.vtt").write_text(vtt,encoding="utf-8")
        (work/"script.txt").write_text(
            f"{headline.upper()}\\n\\n{brief}\\n\\n{script}\\n\\nNguồn: {source or url}\\n#QUẢNG_NINH_NGÀY_MỚI\\n",
            encoding="utf-8")
        # Create a background from uploaded media or a branded slate. First image/video is used as the base layer.
        media = assets[0] if assets else None
        W,H=720,1280
        font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        regular="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        # Draw transparent/solid brand overlays with Pillow
        from PIL import Image, ImageDraw, ImageFont
        canvas=Image.new("RGB",(W,H),(7,19,33))
        draw=ImageDraw.Draw(canvas)
        for y in range(H):
            ratio=y/H
            color=(int(18-10*ratio),int(43-27*ratio),int(67-39*ratio))
            draw.line((0,y,W,y),fill=color)
        # logo area
        if logo_path:
            try:
                lg=Image.open(logo_path).convert("RGBA")
                lg.thumbnail((580,145))
                canvas.paste(lg,(30,35),lg)
            except Exception: pass
        else:
            draw.rectangle((25,28,550,112),fill=(5,11,18))
            draw.text((42,40),"QUẢNG NINH NGÀY MỚI",font=ImageFont.truetype(font,30),fill=(255,255,255))
        draw.rectangle((0,0,W,12),fill=(223,38,56))
        draw.rectangle((W-160,35,W-28,78),fill=(223,38,56))
        draw.text((W-148,47),"TIN MỚI",font=ImageFont.truetype(font,19),fill="white")
        draw.text((35,185),source[:48].upper(),font=ImageFont.truetype(font,18),fill=(103,216,232))
        title_font=ImageFont.truetype(font,46)
        y=250
        for line in textwrap.wrap(headline.upper(), width=23)[:4]:
            draw.text((35,y),line,font=title_font,fill=(242,199,106),stroke_width=1,stroke_fill=(0,0,0)); y+=59
        brief_font=ImageFont.truetype(regular,24)
        y=max(y+20,540)
        for line in textwrap.wrap(brief or script[:220], width=42)[:7]:
            draw.text((35,y),line,font=brief_font,fill=(244,248,252)); y+=38
        draw.rectangle((0,1040,W,1100),fill=(223,38,56))
        draw.text((30,1058),"TIN VẮN  ·  TIN TỨC  ·  ĐỜI SỐNG",font=ImageFont.truetype(font,20),fill="white")
        draw.rectangle((0,1180,W,H),fill=(5,13,23))
        draw.text((30,1210),brand[:42].upper(),font=ImageFont.truetype(font,18),fill="white")
        poster=work/"poster.png"; canvas.save(poster)
        # ffmpeg: image loop with audio and hard-burn subtitles, duration follows audio.
        video=work/"video.mp4"
        cmd=["ffmpeg","-y","-loop","1","-i",str(poster),"-i",str(audio),"-vf",f"subtitles={str(work/'subtitles.srt').replace(':','\\\\:')}:force_style='FontName=DejaVu Sans,FontSize=17,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101824,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=95'","-c:v","libx264","-preset","ultrafast","-tune","stillimage","-pix_fmt","yuv420p","-r","25","-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",str(video)]
        proc=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        if proc.returncode != 0:
            # fallback without burned subtitles if FFmpeg build lacks subtitle filter
            cmd2=["ffmpeg","-y","-loop","1","-i",str(poster),"-i",str(audio),"-c:v","libx264","-preset","ultrafast","-tune","stillimage","-pix_fmt","yuv420p","-r","25","-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",str(video)]
            proc2=subprocess.run(cmd2,capture_output=True,text=True,timeout=300)
            if proc2.returncode != 0:
                raise HTTPException(500,"FFmpeg không dựng được video: "+proc.stderr[-500:])
        meta={"job_id":job_id,"headline":headline,"duration_seconds":round(audio_dur,1),"video":f"/api/jobs/{job_id}/video","srt":f"/api/jobs/{job_id}/subtitles.srt","vtt":f"/api/jobs/{job_id}/subtitles.vtt","script":f"/api/jobs/{job_id}/script.txt","note":"Phụ đề được căn thời gian ước tính theo độ dài câu; video hiện dùng một khung đồ họa nền. Hãy xem lại trước khi đăng."}
        (work/"job.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
        return meta
    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(504,"Dựng video vượt quá thời gian cho phép.")
    except Exception as e:
        raise HTTPException(500,f"Lỗi dựng video: {str(e)[:250]}")

@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    p=JOBS/job_id/"job.json"
    if not p.exists(): raise HTTPException(404,"Không tìm thấy dự án.")
    return json.loads(p.read_text(encoding="utf-8"))

@app.get("/api/jobs/{job_id}/{kind}")
def job_file(job_id: str, kind: str):
    allowed={"video.mp4":("video.mp4","video/mp4"),"subtitles.srt":("subtitles.srt","application/x-subrip"),"subtitles.vtt":("subtitles.vtt","text/vtt"),"script.txt":("script.txt","text/plain")}
    if kind not in allowed: raise HTTPException(404,"Tệp không tồn tại.")
    filename,mime=allowed[kind]; p=JOBS/job_id/filename
    if not p.exists(): raise HTTPException(404,"Chưa có tệp.")
    return FileResponse(p,media_type=mime,filename=filename)
