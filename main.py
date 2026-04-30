from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from datetime import datetime
import aiohttp
import asyncio
import base64
import io
import os
import time
import json

from core import fetch_leaderboard, render_image, get_available_backgrounds

# ================= CONFIG =================

def load_env(path=".env"):
    env = {}
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env[key.strip()] = value.strip()
    return env

env = load_env()

COOKIE         = os.environ.get("COOKIE") or env.get("COOKIE", "")
SUPABASE_URL   = os.environ.get("SUPABASE_URL") or env.get("SUPABASE_URL", "")
SUPABASE_KEY   = os.environ.get("SUPABASE_KEY") or env.get("SUPABASE_KEY", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or env.get("SUPABASE_SERVICE_KEY", "")

headers_garena = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://congdong.ff.garena.vn",
    "Referer": "https://congdong.ff.garena.vn/tinh-diem",
    "Accept": "application/json, text/plain",
    "X-Requested-With": "XMLHttpRequest",
    "Cookie": COOKIE
}

# ================= SUPABASE =================

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ================= APP =================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ================= AUTH HELPER =================

async def get_current_user(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    try:
        user = supabase.auth.get_user(token)
        return user.user
    except:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

async def get_admin_user(request: Request):
    user = await get_current_user(request)
    profile = supabase.table("users").select("role").eq("id", user.id).single().execute()
    if not profile.data or profile.data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền admin")
    return user

# ================= PAGES =================

@app.get("/")
async def index():
    return FileResponse("static/index.html")

@app.get("/login")
async def login_page():
    return FileResponse("static/login.html")

@app.get("/register")
async def register_page():
    return FileResponse("static/register.html")

@app.get("/dashboard")
async def dashboard_page():
    return FileResponse("static/dashboard.html")

@app.get("/backgrounds")
async def backgrounds_page():
    return FileResponse("static/backgrounds.html")

@app.get("/logos")
async def logos_page():
    return FileResponse("static/logos.html")

@app.get("/history")
async def history_page():
    return FileResponse("static/history.html")

@app.get("/admin")
async def admin_page():
    return FileResponse("static/admin.html")

# ================= AUTH API =================

@app.post("/api/register")
async def register(data: dict):
    try:
        res = supabase.auth.sign_up({
            "email": data["email"],
            "password": data["password"]
        })
        # Tạo profile trong bảng users
        supabase_admin.table("users").upsert({
            "id": res.user.id,
            "email": data["email"],
            "role": "user",
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        return {"message": "Đăng ký thành công"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/login")
async def login(data: dict):
    try:
        res = supabase.auth.sign_in_with_password({
            "email": data["email"],
            "password": data["password"]
        })
        # Lấy role
        profile = supabase.table("users").select("role").eq("id", res.user.id).single().execute()
        role = profile.data.get("role", "user") if profile.data else "user"
        return {
            "access_token": res.session.access_token,
            "user": {"id": res.user.id, "email": res.user.email, "role": role}
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail="Email hoặc mật khẩu không đúng")

# ================= NOTIFICATION API =================

@app.get("/api/notification")
async def get_notification():
    try:
        res = supabase.table("notifications").select("*").eq("active", True).order("created_at", desc=True).limit(1).execute()
        if res.data:
            return res.data[0]
        return {"active": False}
    except:
        return {"active": False}

# ================= BACKGROUNDS API =================

@app.get("/api/backgrounds")
async def list_backgrounds():
    bgs = get_available_backgrounds()
    return {"backgrounds": bgs}

@app.get("/api/backgrounds/{bg_name}/preview")
async def background_preview(bg_name: str):
    path = f"backgrounds/{bg_name}.png"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Không tìm thấy background")
    return FileResponse(path, media_type="image/png")

# ================= BXH API =================

@app.post("/api/bxh")
async def create_bxh(
    request: Request,
    user=Depends(get_current_user),
    accountid: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    background: str = Form(...),
    custom_name: str = Form(""),
    remove_match: str = Form(""),
    team_names: str = Form(""),
    champion_rush: int = Form(0),
    logo_custom: UploadFile = File(None),
):
    # Đọc logo_custom nếu có
    logo_bytes = None
    if logo_custom and logo_custom.filename:
        logo_bytes = await logo_custom.read()

    try:
        leaderboard, match_details = await fetch_leaderboard(
            accountid, start_time, end_time, headers_garena,
            remove_match, team_names, {}, champion_rush
        )
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not leaderboard:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu")

    # Render ảnh
    try:
        image_buf = render_image(background, leaderboard, start_time, custom_name, logo_bytes, {})
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    image_bytes = image_buf.read()

    # Lưu lịch sử vào Supabase Storage
    try:
        filename = f"{user.id}/{int(time.time())}.png"
        supabase_admin.storage.from_("history").upload(filename, image_bytes, {"content-type": "image/png"})
        image_url = supabase_admin.storage.from_("history").get_public_url(filename)

        # Lưu vào bảng history
        supabase_admin.table("history").insert({
            "user_id": user.id,
            "image_url": image_url,
            "accountid": accountid,
            "start_time": start_time,
            "end_time": end_time,
            "background": background,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # Giữ 10 bảng gần nhất
        all_history = supabase_admin.table("history").select("id").eq("user_id", user.id).order("created_at", desc=False).execute()
        if all_history.data and len(all_history.data) > 10:
            old_ids = [h["id"] for h in all_history.data[:-10]]
            supabase_admin.table("history").delete().in_("id", old_ids).execute()
    except Exception as e:
        pass  # Không crash nếu lưu lịch sử lỗi

    # Trả ảnh dạng base64
    image_b64 = base64.b64encode(image_bytes).decode()
    return {
        "image": image_b64,
        "match_details": match_details,
        "team_count": len(leaderboard)
    }

# ================= LOGO API =================

@app.get("/api/logos")
async def get_logos(user=Depends(get_current_user)):
    res = supabase.table("logo_sets").select("*").eq("user_id", user.id).execute()
    return {"logo_sets": res.data or []}

@app.post("/api/logos")
async def create_logo_set(
    request: Request,
    user=Depends(get_current_user)
):
    data = await request.json()
    key_logo = data.get("key_logo", "").strip()
    if not key_logo:
        raise HTTPException(status_code=400, detail="Tên bộ logo không được trống")

    # Kiểm tra đã tồn tại chưa
    existing = supabase.table("logo_sets").select("id").eq("user_id", user.id).eq("key_logo", key_logo).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Tên bộ logo đã tồn tại")

    res = supabase.table("logo_sets").insert({
        "user_id": user.id,
        "key_logo": key_logo,
        "created_at": datetime.utcnow().isoformat()
    }).execute()
    return {"message": "Tạo bộ logo thành công", "data": res.data}

@app.post("/api/logos/{logo_set_id}/upload")
async def upload_logo(
    logo_set_id: str,
    file: UploadFile = File(...),
    team_id: str = Form(...),
    user=Depends(get_current_user)
):
    # Kiểm tra bộ logo thuộc user
    logo_set = supabase.table("logo_sets").select("id").eq("id", logo_set_id).eq("user_id", user.id).execute()
    if not logo_set.data:
        raise HTTPException(status_code=404, detail="Không tìm thấy bộ logo")

    # Kiểm tra kích thước
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File quá lớn, tối đa 10MB")

    # Crop circle
    from PIL import Image, ImageDraw
    img = Image.open(io.BytesIO(content)).convert("RGBA")
    size = min(img.size)
    img = img.crop(((img.width - size)//2, (img.height - size)//2,
                    (img.width + size)//2, (img.height + size)//2))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    # Upload lên Supabase Storage
    team_id = team_id.strip()
    id_prefix = team_id[:-2] if len(team_id) >= 3 else team_id
    filename = f"{user.id}/{logo_set_id}/{id_prefix}.png"

    supabase_admin.storage.from_("logos").upload(filename, img_bytes, {"content-type": "image/png", "upsert": "true"})
    url = supabase_admin.storage.from_("logos").get_public_url(filename)

    # Lưu vào database
    existing = supabase.table("logos").select("id").eq("logo_set_id", logo_set_id).eq("team_id_prefix", id_prefix).execute()
    if existing.data:
        supabase_admin.table("logos").update({"url": url}).eq("id", existing.data[0]["id"]).execute()
    else:
        supabase_admin.table("logos").insert({
            "logo_set_id": logo_set_id,
            "user_id": user.id,
            "team_id_prefix": id_prefix,
            "url": url
        }).execute()

    return {"message": "Upload logo thành công", "url": url}

@app.delete("/api/logos/{logo_set_id}")
async def delete_logo_set(logo_set_id: str, user=Depends(get_current_user)):
    logo_set = supabase.table("logo_sets").select("id").eq("id", logo_set_id).eq("user_id", user.id).execute()
    if not logo_set.data:
        raise HTTPException(status_code=404, detail="Không tìm thấy bộ logo")

    supabase_admin.table("logos").delete().eq("logo_set_id", logo_set_id).execute()
    supabase_admin.table("logo_sets").delete().eq("id", logo_set_id).execute()
    return {"message": "Xóa bộ logo thành công"}

# ================= HISTORY API =================

@app.get("/api/history")
async def get_history(user=Depends(get_current_user)):
    res = supabase.table("history").select("*").eq("user_id", user.id).order("created_at", desc=True).limit(10).execute()
    return {"history": res.data or []}

# ================= ADMIN API =================

@app.get("/api/admin/history")
async def admin_all_history(user=Depends(get_admin_user)):
    res = supabase_admin.table("history").select("*, users(email)").order("created_at", desc=True).limit(100).execute()
    history = []
    for h in (res.data or []):
        h["user_email"] = h.get("users", {}).get("email", "N/A") if h.get("users") else "N/A"
        history.append(h)
    return {"history": history}

@app.get("/api/admin/users")
async def admin_get_users(user=Depends(get_admin_user)):
    res = supabase_admin.table("users").select("*").order("created_at", desc=True).execute()
    return {"users": res.data or []}

@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: str, user=Depends(get_admin_user)):
    supabase_admin.auth.admin.delete_user(user_id)
    supabase_admin.table("users").delete().eq("id", user_id).execute()
    return {"message": "Đã xóa tài khoản"}

@app.get("/api/admin/stats")
async def admin_stats(user=Depends(get_admin_user)):
    total_users = supabase_admin.table("users").select("id", count="exact").execute()
    total_history = supabase_admin.table("history").select("id", count="exact").execute()
    bg_stats = supabase_admin.table("history").select("background").execute()

    bg_count = {}
    for h in (bg_stats.data or []):
        bg = h.get("background", "unknown")
        bg_count[bg] = bg_count.get(bg, 0) + 1

    most_used_bg = max(bg_count, key=bg_count.get) if bg_count else "N/A"

    return {
        "total_users": total_users.count or 0,
        "total_bxh": total_history.count or 0,
        "most_used_bg": most_used_bg
    }

@app.get("/api/admin/user/{user_id}/history")
async def admin_user_history(user_id: str, user=Depends(get_admin_user)):
    res = supabase_admin.table("history").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return {"history": res.data or []}

@app.get("/api/admin/backgrounds")
async def admin_list_backgrounds(user=Depends(get_admin_user)):
    return {"backgrounds": get_available_backgrounds()}

@app.delete("/api/admin/backgrounds/{bg_name}")
async def admin_delete_background(bg_name: str, user=Depends(get_admin_user)):
    bg_path = f"backgrounds/{bg_name}.png"
    renderer_path = f"renderers/{bg_name}.py"
    if os.path.exists(bg_path):
        os.remove(bg_path)
    if os.path.exists(renderer_path):
        os.remove(renderer_path)
    return {"message": f"Đã xóa background {bg_name}"}

@app.get("/api/admin/logos")
async def admin_list_logos(user=Depends(get_admin_user)):
    res = supabase_admin.table("logo_sets").select("*, users(email)").execute()
    return {"logo_sets": res.data or []}

@app.delete("/api/admin/logos/{logo_set_id}")
async def admin_delete_logo_set(logo_set_id: str, user=Depends(get_admin_user)):
    supabase_admin.table("logos").delete().eq("logo_set_id", logo_set_id).execute()
    supabase_admin.table("logo_sets").delete().eq("id", logo_set_id).execute()
    return {"message": "Đã xóa bộ logo"}

@app.post("/api/admin/notification")
async def admin_set_notification(request: Request, user=Depends(get_admin_user)):
    data = await request.json()
    supabase_admin.table("notifications").delete().neq("id", 0).execute()
    if data.get("active"):
        supabase_admin.table("notifications").insert({
            "message": data.get("message", ""),
            "duration": data.get("duration", 5),
            "active": True,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
    return {"message": "Cập nhật thông báo thành công"}

@app.post("/api/admin/cookie")
async def admin_update_cookie(request: Request, user=Depends(get_admin_user)):
    data = await request.json()
    new_cookie = data.get("cookie", "").strip()
    if not new_cookie:
        raise HTTPException(status_code=400, detail="Cookie không được trống")
    headers_garena["Cookie"] = new_cookie
    return {"message": "Cập nhật cookie thành công"}

@app.get("/api/admin/backup")
async def admin_backup(user=Depends(get_admin_user)):
    users = supabase_admin.table("users").select("*").execute()
    logo_sets = supabase_admin.table("logo_sets").select("*").execute()
    logos = supabase_admin.table("logos").select("*").execute()
    notifications = supabase_admin.table("notifications").select("*").execute()

    backup_data = {
        "users": users.data or [],
        "logo_sets": logo_sets.data or [],
        "logos": logos.data or [],
        "notifications": notifications.data or [],
        "backup_time": datetime.utcnow().isoformat()
    }

    buf = io.BytesIO(json.dumps(backup_data, ensure_ascii=False, indent=2).encode())
    return StreamingResponse(buf, media_type="application/json",
                             headers={"Content-Disposition": "attachment; filename=backup.json"})

@app.post("/api/admin/import")
async def admin_import(file: UploadFile = File(...), user=Depends(get_admin_user)):
    content = await file.read()
    try:
        data = json.loads(content)
    except:
        raise HTTPException(status_code=400, detail="File không hợp lệ")

    # Import logo_sets và logos (không import users để tránh conflict)
    if "logo_sets" in data:
        for ls in data["logo_sets"]:
            supabase_admin.table("logo_sets").upsert(ls).execute()
    if "logos" in data:
        for logo in data["logos"]:
            supabase_admin.table("logos").upsert(logo).execute()

    return {"message": "Import dữ liệu thành công"}
