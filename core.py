import aiohttp
import importlib
import io
import os
from datetime import datetime, timezone, timedelta


def convert_to_timestamp(date_str):
    VN_TZ = timezone(timedelta(hours=7))
    dt = datetime.strptime(date_str, "%d/%m/%Y %H:%M")
    dt = dt.replace(tzinfo=VN_TZ)
    return int(dt.timestamp())


def get_available_backgrounds():
    if not os.path.exists("backgrounds"):
        return []
    return [
        f.replace(".png", "")
        for f in os.listdir("backgrounds")
        if f.endswith(".png") and os.path.exists(f"renderers/{f.replace('.png', '')}.py")
    ]


def render_image(bg_name, leaderboard, start_str, name_str, logo_bytes, logo_map={}):
    try:
        importlib.invalidate_caches()
        renderer = importlib.import_module(f"renderers.{bg_name}")
        return renderer.create_image(leaderboard, start_str, name_str, logo_bytes, logo_map)
    except ModuleNotFoundError:
        raise FileNotFoundError(f"Không tìm thấy background: {bg_name}")


async def fetch_leaderboard(
    accountid, start_time, end_time, headers,
    remove_match="", team_names="", logo_map={}, champion_rush=0,
    logo_bytes=None
):
    start_ts = convert_to_timestamp(start_time)
    end_ts = convert_to_timestamp(end_time)

    # Parse team_names
    id_to_name = {}
    if team_names:
        for part in team_names.split(","):
            part = part.strip()
            if "=" not in part:
                raise ValueError(f"Sai format team_names: {part}")
            raw_id, raw_name = part.split("=", 1)
            raw_id = raw_id.strip()
            name = raw_name.strip()
            if not name:
                raise ValueError(f"Tên đội trống tại ID: {raw_id}")
            if len(raw_id) < 3:
                raise ValueError(f"ID quá ngắn: {raw_id}")
            id_to_name[raw_id[:-2]] = name

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://congdong.ff.garena.vn/league-score-api/player/find-match",
            json={"accountId": accountid, "startTime": start_ts, "endTime": end_ts},
            headers=headers
        ) as res:
            list_data = await res.json(content_type=None)
            if res.status == 401:
                raise PermissionError("Cookie hết hạn, vui lòng cập nhật cookie.")

    matches = list_data.get("matches", [])

    if remove_match:
        xoa_indexes = set(int(x.strip()) for x in remove_match.split(","))
        matches = [m for i, m in enumerate(matches, 1) if i not in xoa_indexes]

    team_map = {}
    match_details = []
    cr_winner = None

    async with aiohttp.ClientSession() as session:
        for idx, match in enumerate(matches):
            async with session.post(
                "https://congdong.ff.garena.vn/league-score-api/match",
                json={"matchId": match["id"]},
                headers=headers
            ) as detail_res:
                detail_json = await detail_res.json(content_type=None)

            detail_data = detail_json.get("match", {})
            ranks = detail_data.get("ranks", [])

            booyah_team = "Không có"
            for team in ranks:
                if team.get("booyah") == 1:
                    name = (team.get("teamName") or "").strip()
                    if not name:
                        acc_names = team.get("accountNames") or []
                        name = acc_names[0].strip() if acc_names else ""
                    booyah_team = name if name else "Unknown"
                    break

            match_details.append({
                "index": idx + 1,
                "id": match["id"],
                "booyah": booyah_team,
                "success": bool(ranks)
            })

            if not ranks:
                continue

            for team in ranks:
                score = team.get("score", 0)
                kill = team.get("kill", 0)
                booyah = 1 if team.get("booyah") == 1 else 0
                team_name = team.get("teamName")
                current_ids = team.get("playerAccountIds", [])

                custom_display = None
                custom_logo_path = None
                for cid in current_ids:
                    cid_prefix = str(cid)[:-2] if len(str(cid)) >= 3 else str(cid)
                    if custom_display is None and cid_prefix in id_to_name:
                        custom_display = id_to_name[cid_prefix]
                    if custom_logo_path is None and cid_prefix in logo_map:
                        custom_logo_path = logo_map[cid_prefix]

                if team_name and team_name.strip():
                    keyname = "NAME_" + team_name.strip()
                    if keyname not in team_map:
                        team_map[keyname] = {
                            "displayName": custom_display or team_name.strip(),
                            "accountIds": current_ids,
                            "totalScore": 0, "totalKill": 0, "totalBooyah": 0,
                            "logoPath": custom_logo_path
                        }
                    else:
                        if custom_display and not team_map[keyname].get("customized"):
                            team_map[keyname]["displayName"] = custom_display
                            team_map[keyname]["customized"] = True
                        if custom_logo_path and not team_map[keyname].get("logoPath"):
                            team_map[keyname]["logoPath"] = custom_logo_path

                    team_map[keyname]["totalScore"] += score
                    team_map[keyname]["totalKill"] += kill
                    team_map[keyname]["totalBooyah"] += booyah

                    if champion_rush > 0 and cr_winner is None and booyah == 1:
                        if team_map[keyname]["totalScore"] - score >= champion_rush:
                            cr_winner = keyname
                else:
                    found_key = None
                    for k in team_map:
                        if len([i for i in team_map[k].get("accountIds", []) if i in current_ids]) >= 2:
                            found_key = k
                            break

                    if found_key:
                        if custom_display and not team_map[found_key].get("customized"):
                            team_map[found_key]["displayName"] = custom_display
                            team_map[found_key]["customized"] = True
                        if custom_logo_path and not team_map[found_key].get("logoPath"):
                            team_map[found_key]["logoPath"] = custom_logo_path
                        team_map[found_key]["totalScore"] += score
                        team_map[found_key]["totalKill"] += kill
                        team_map[found_key]["totalBooyah"] += booyah

                        if champion_rush > 0 and cr_winner is None and booyah == 1:
                            if team_map[found_key]["totalScore"] - score >= champion_rush:
                                cr_winner = found_key
                    else:
                        new_key = "IDS_" + "-".join(sorted(map(str, current_ids)))
                        account_names = team.get("accountNames") or []
                        team_map[new_key] = {
                            "displayName": custom_display or (account_names[0] if account_names else ""),
                            "accountIds": current_ids,
                            "totalScore": score, "totalKill": kill, "totalBooyah": booyah,
                            "logoPath": custom_logo_path
                        }
                        if custom_display:
                            team_map[new_key]["customized"] = True

    leaderboard = sorted(team_map.values(), key=lambda x: x["totalScore"], reverse=True)

    if champion_rush > 0 and cr_winner and cr_winner in team_map:
        cr_team = team_map[cr_winner]
        leaderboard = [cr_team] + [t for t in leaderboard if t is not cr_team]

    return leaderboard, match_details
