from PIL import Image, ImageDraw, ImageFont
import json
import os
import io
from datetime import datetime

FONT_PATHS = [
    "Arial-Bold.ttf",
]

def get_font(size):
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()

def create_image(leaderboard, start_str="", name_str="", logo_bytes=None, logo_map={}):
    bg_path = "backgrounds/bg2.png"
    coord_path = "coords/bg2.json"

    if not os.path.exists(bg_path):
        raise FileNotFoundError("Khong tim thay background: bg2")
    if not os.path.exists(coord_path):
        raise FileNotFoundError("Khong tim thay file toa do: coords/bg2.json")

    with open(coord_path, "r") as f:
        coords = json.load(f)

    background = Image.open(bg_path).convert("RGBA")
    draw = ImageDraw.Draw(background)

    font_main = get_font(coords["font_size"])
    font_time = get_font(coords.get("time_font_size", coords["font_size"]))
    font_name = get_font(coords["font_size"])

    LOGO_SIZE = 50
    off = coords.get("offset", 0)

    # Vẽ thời gian
    if start_str:
        try:
            dt = datetime.strptime(start_str, "%d/%m/%Y %H:%M")
            time_text = dt.strftime("%H:%M %d/%m")
        except:
            time_text = start_str
        draw.text((coords["time_x"] - off, coords["time_y"] - off), time_text, font=font_time, fill="white")

    # Vẽ tên host
    if name_str:
        draw.text((coords["name_x"] - off, coords["name_y"] - off), name_str.upper(), font=font_name, fill="white")

    # Chuẩn bị logo
    logo_img = None
    if logo_bytes:
        try:
            logo_img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
            logo_img = logo_img.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
        except:
            logo_img = None

    def draw_text(x, y, text):
        draw.text((x - off, y - off), str(text), font=font_main, fill="white")

    def get_team_logo(team):
        logo_path = team.get("logoPath")
        if logo_path and os.path.exists(logo_path):
            try:
                t_logo = Image.open(logo_path).convert("RGBA")
                return t_logo.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
            except:
                pass
        return logo_img

    def paste_logo(cx, cy, team):
        t_logo = get_team_logo(team)
        if t_logo:
            background.paste(t_logo, (cx - LOGO_SIZE//2, cy - LOGO_SIZE//2), t_logo)

    # Top 1
    if len(leaderboard) >= 1:
        team = leaderboard[0]
        draw_text(coords["top1_team_x"], coords["top1_team_y"], team["displayName"])
        draw_text(coords["top1_elims_x"], coords["top1_stats_y"], team["totalKill"])
        draw_text(coords["top1_booyah_x"], coords["top1_stats_y"], team["totalBooyah"])
        draw_text(coords["top1_total_x"], coords["top1_stats_y"], team["totalScore"])
        paste_logo(coords["top1_logo_x"], coords["top1_logo_y"], team)

    # Cột trái #2-#6
    left_y = coords["left_y"]
    for i, team in enumerate(leaderboard[1:1 + len(left_y)]):
        y = left_y[i]
        draw_text(coords["left_team_x"], y, team["displayName"])
        draw_text(coords["left_elims_x"], y, team["totalKill"])
        draw_text(coords["left_booyah_x"], y, team["totalBooyah"])
        draw_text(coords["left_total_x"], y, team["totalScore"])
        paste_logo(coords["left_logo_x"], y, team)

    # Cột phải #7-#14
    right_y = coords["right_y"]
    right_start = 1 + len(left_y)
    for i, team in enumerate(leaderboard[right_start:right_start + len(right_y)]):
        y = right_y[i]
        draw_text(coords["right_team_x"], y, team["displayName"])
        draw_text(coords["right_elims_x"], y, team["totalKill"])
        draw_text(coords["right_booyah_x"], y, team["totalBooyah"])
        draw_text(coords["right_total_x"], y, team["totalScore"])
        paste_logo(coords["right_logo_x"], y, team)

    buffer = io.BytesIO()
    background.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
