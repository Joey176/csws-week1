#!/usr/bin/env python3
"""
AstroCal.py
Colab-ready script for AstroCal with dynamic coloring, precise planet positions,
and aspects. Automatically installs pyswisseph and astral in Colab if missing.

Run in Colab by pasting into a code cell and executing, or upload and run:
!python AstroCal.py

Stop the live loop by interrupting the cell (Stop button) or Ctrl+C.
"""

import sys
import subprocess
import time
import datetime
import math

# Improved package installer for Colab: installs pyswisseph (provides swisseph)
# and astral, then imports them. Returns the imported modules.

def ensure_packages():
    import subprocess, sys
    try:
        import swisseph as swe
        import astral
        return swe, astral
    except Exception:
        pass

    print("Installing required packages: pyswisseph (swisseph), astral ...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyswisseph", "astral"])
    except subprocess.CalledProcessError:
        print("Automatic pip install failed. Please run in a notebook cell:")
        print("  !pip install pyswisseph astral")
        raise

    # Try importing again
    try:
        import swisseph as swe
        import astral
        return swe, astral
    except Exception:
        print("Import still failed after installation. Try restarting the Colab runtime (Runtime -> Restart runtime), then re-run the cell.")
        raise

# Ensure required packages and import the needed symbols
swe, astral = ensure_packages()
from zoneinfo import ZoneInfo
from IPython.display import display, HTML, clear_output
from astral import LocationInfo
from astral.sun import sun

# --- Config & Structures ---
TATTWAS = [
    ("PRITHVI [EARTH]", 6, "[Y-SQ]"),
    ("JALA    [WATER]", 12, "[S-CR]"),
    ("TEJAS   [FIRE] ", 18, "[R-TR]"),
    ("VAYU    [AIR]  ", 24, "[B-CI]"),
    ("AKASHA  [ETHER]", 30, "[B-EG]")
]
TOTAL_TATTWA_CYCLE_MINS = 90

CHALDEAN_ORDER = ["SATURN", "JUPITER", "MARS", "SUN", "VENUS", "MERCURY", "MOON"]
WEEKDAY_LORDS = {0: "MOON", 1: "MARS", 2: "MERCURY", 3: "JUPITER", 4: "VENUS", 5: "SATURN", 6: "SUN"}
ZODIAC_SIGNS = ["ARI", "TAU", "GEM", "CAN", "LEO", "VIR", "LIB", "SCO", "SAG", "CAP", "AQU", "PIS"]

PLANET_MAP = {
    "SUN": swe.SUN, "MOON": swe.MOON, "MERCURY": swe.MERCURY, "VENUS": swe.VENUS,
    "MARS": swe.MARS, "JUPITER": swe.JUPITER, "SATURN": swe.SATURN
}

ASPECTS = {
    0: "Conjunction",
    60: "Sextile",
    90: "Square",
    120: "Trine",
    150: "Quincunx",
    180: "Opposition"
}

# Map planets to hex colors (used for text and border)
PLANET_COLORS = {
    "SUN": "#FFD700",        # Gold
    "MOON": "#C0C0C0",       # Silver
    "MERCURY": "#FF8C00",    # Orange
    "VENUS": "#50C878",      # Emerald Green
    "MARS": "#FF0000",       # Red
    "JUPITER": "#0000FF",    # Blue
    "SATURN": "#000000"      # Black
}

# --- Utility / Calculation Modules ---

def get_chinese_zodiac(year):
    stems = ["Yang Wood", "Yin Wood", "Yang Fire", "Yin Fire", "Yang Earth", "Yin Earth", "Yang Metal", "Yin Metal", "Yang Water", "Yin Water"]
    branches = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig"]
    if year < 4:
        return "Unknown", "Unknown"
    stem_idx = (year - 4) % 10
    branch_idx = (year - 4) % 12
    return stems[stem_idx], branches[branch_idx]


def get_jewish_meta(now):
    if now.year == 2026 and now.month == 6:
        if now.day == 15:
            return "5786.03.30", "ROSH CHODESH TAMMUZ [NEW MOON]"
    return "5786.03.17", "ORDINARY CYCLE"


def calculate_lunar_phase(julian_day):
    res_sun, _ = swe.calc_ut(julian_day, swe.SUN, 0)
    res_moon, _ = swe.calc_ut(julian_day, swe.MOON, 0)
    sun_long = res_sun[0]
    moon_long = res_moon[0]
    diff = (moon_long - sun_long) % 360
    illumination = (1 - math.cos(math.radians(diff))) / 2 * 100
    return illumination, "WAKING LUNAR ENGINE" if illumination > 1 else "DARK MOON HORIZON"


def get_sun_data(lat, lon, tz_name="Europe/London"):
    city = LocationInfo("Liverpool", "UK", tz_name, lat, lon)
    now = datetime.datetime.now(ZoneInfo(tz_name))
    s_today = sun(city.observer, date=now.date(), tzinfo=ZoneInfo(tz_name))
    s_tomorrow = sun(city.observer, date=now.date() + datetime.timedelta(days=1), tzinfo=ZoneInfo(tz_name))
    s_yesterday = sun(city.observer, date=now.date() - datetime.timedelta(days=1), tzinfo=ZoneInfo(tz_name))
    return s_yesterday, s_today, s_tomorrow


def calculate_tattwa(now, sunrise_today):
    time_diff = now - sunrise_today
    diff_minutes = time_diff.total_seconds() / 60.0
    minute_in_cycle = diff_minutes % TOTAL_TATTWA_CYCLE_MINS

    elapsed = 0
    for name, duration, symbol in TATTWAS:
        if elapsed <= minute_in_cycle < (elapsed + duration):
            return name, symbol, int((elapsed + duration) - minute_in_cycle)
        elapsed += duration
    return TATTWAS[0][0], TATTWAS[0][1], 0


def calculate_planetary_hour(now, s_yesterday, s_today, s_tomorrow):
    if s_today['sunrise'] <= now < s_today['sunset']:
        phase = "DAYTIME"
        start_time = s_today['sunrise']
        end_time = s_today['sunset']
        day_of_week = start_time.weekday()
        base_offset = 0
    else:
        phase = "NIGHTTIME"
        base_offset = 4
        if now >= s_today['sunset']:
            start_time = s_today['sunset']
            end_time = s_tomorrow['sunrise']
            day_of_week = s_today['sunrise'].weekday()
        else:
            start_time = s_yesterday['sunset']
            end_time = s_today['sunrise']
            day_of_week = s_yesterday['sunrise'].weekday()

    total_duration = end_time - start_time
    hour_length = total_duration / 12
    try:
        current_hour_idx = int((now - start_time) / hour_length)
    except Exception:
        current_hour_idx = 0

    if current_hour_idx > 11:
        current_hour_idx = 11
    if current_hour_idx < 0:
        current_hour_idx = 0

    day_lord = WEEKDAY_LORDS[day_of_week]
    final_planet_idx = (CHALDEAN_ORDER.index(day_lord) + base_offset + current_hour_idx) % 7
    p_ruler = CHALDEAN_ORDER[final_planet_idx]

    next_boundary = start_time + (hour_length * (current_hour_idx + 1))
    p_rem = int(max(0, (next_boundary - now).total_seconds()) / 60)
    p_len = int(hour_length.total_seconds() / 60)

    return current_hour_idx + 1, phase, p_ruler, p_rem, p_len, day_lord


def format_deg_dms(longitude):
    lon = longitude % 360.0
    sign_index = int(lon // 30) % 12
    deg_in_sign = lon - (sign_index * 30)
    deg = int(math.floor(deg_in_sign))
    rem = (deg_in_sign - deg) * 60.0
    minutes = int(math.floor(rem))
    seconds = int(round((rem - minutes) * 60.0))
    if seconds == 60:
        seconds = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        deg += 1
    if deg >= 30:
        deg = 29
        minutes = 59
        seconds = 59
    return f"{deg:02d}°{minutes:02d}'{seconds:02d}\" {ZODIAC_SIGNS[sign_index]}", sign_index, deg_in_sign


def get_zodiac_positions(julian_day):
    positions_fmt = {}
    positions_long = {}
    for name, swe_id in PLANET_MAP.items():
        res, _ = swe.calc_ut(julian_day, swe_id, swe.FLG_SPEED)
        longitude = res[0]
        speed = res[3] if len(res) > 3 else 0.0
        retro_marker = "<-" if speed < 0 else "  "
        dms, sign_idx, _ = format_deg_dms(longitude)
        positions_fmt[name] = f"{dms} {retro_marker}"
        positions_long[name] = longitude % 360.0
    return positions_fmt, positions_long


def deg_to_dms_tuple(angle_deg):
    lon = angle_deg % 360.0
    sign_index = int(lon // 30) % 12
    deg_in_sign = lon - (sign_index * 30)
    deg = int(math.floor(deg_in_sign))
    rem = (deg_in_sign - deg) * 60.0
    minutes = int(math.floor(rem))
    seconds = int(round((rem - minutes) * 60.0))
    if seconds == 60:
        seconds = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        deg += 1
    if deg >= 30:
        deg = 29
        minutes = 59
        seconds = 59
    return deg, minutes, seconds, sign_index


def angle_to_dms_string(angle_deg):
    deg, minutes, seconds, sign_index = deg_to_dms_tuple(angle_deg)
    return f"{deg:02d}°{minutes:02d}'{seconds:02d}\" {ZODIAC_SIGNS[sign_index]}"


def get_aspect(p_long, other_long):
    diff = (other_long - p_long) % 360.0
    sep = diff if diff <= 180.0 else 360.0 - diff
    nearest_aspect_angle = min(ASPECTS.keys(), key=lambda a: abs(sep - a))
    orb = abs(sep - nearest_aspect_angle)
    sep_dms = angle_to_dms_string(sep if diff <= 180.0 else 360.0 - diff)
    return sep, sep_dms, ASPECTS[nearest_aspect_angle], nearest_aspect_angle, orb

# --- Notebook / Colab Display Engine ---

def run_notebook_clock(lat, lon, tz_name="Europe/London"):
    blink_state = True

    try:
        while True:
            uk_tz = ZoneInfo(tz_name)
            now_local = datetime.datetime.now(uk_tz)
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            julian_day = swe.julday(now_utc.year, now_utc.month, now_utc.day,
                                     now_utc.hour + now_utc.minute / 60.0 + now_utc.second / 3600.0 +
                                     now_utc.microsecond / 3600.0 / 1e6)

            s_yesterday, s_today, s_tomorrow = get_sun_data(lat, lon, tz_name=tz_name)
            t_name, t_symbol, t_rem = calculate_tattwa(now_local, s_today['sunrise'])
            p_hour, p_phase, p_ruler, p_rem, p_len, p_day_ruler = calculate_planetary_hour(now_local, s_yesterday, s_today, s_tomorrow)
            planet_fmt, planet_long = get_zodiac_positions(julian_day)

            c_stem, c_branch = get_chinese_zodiac(now_local.year)
            j_chrono, j_holiday = get_jewish_meta(now_local)
            m_illum, m_phase_name = calculate_lunar_phase(julian_day)

            # determine colors dynamically - chrono lord gets its own planetary color
            border_color = PLANET_COLORS.get(p_day_ruler, "#ff1111")
            text_color = PLANET_COLORS.get(p_ruler, "#ff3333")
            # add a semitransparent shadow color from border_color
            shadow_color = border_color + "66" if len(border_color) == 7 else border_color

            sep = ":" if blink_state else " "
            blink_state = not blink_state
            time_str = now_local.strftime(f"%H{sep}%M{sep}%S")

            # build dynamic container style using the chosen colors
            container_style = f"""
            <div style="background-color: #050505; color: {text_color}; font-family: 'Courier New', monospace;
                        padding: 20px; border: 3px solid {border_color}; border-radius: 8px; width: 700px;
                        box-shadow: 0px 0px 15px {shadow_color}; line-height: 1.4;">
            <pre style="color: {text_color}; background: transparent; border: none; margin: 0; white-space: pre-wrap;">
            """

            # Build HTML layout content
            output_text = "==================================================\n"
            output_text += " ::: METAPHYSICAL CORE // TIME-MATRIX ENGINE ::: \n"
            output_text += "==================================================\n"
            output_text += f" [LOCAL SYSTEM TIME] ------> [ {time_str} ] ({now_local.tzname()})\n"
            output_text += f" [MATRIX CHRONO] -----------> [ {now_local.strftime('%Y.%m.%d')} ]\n"
            output_text += f" [CHINESE VECTOR] ----------> [ Year of the {c_stem} {c_branch} ]\n"
            output_text += f" [HEBREW LUNISOLAR] --------> [ AM {j_chrono} // {j_holiday} ]\n"
            output_text += "--------------------------------------------------\n"
            output_text += f" >> ACTIVE TATTWA ELEMENT VECTOR\n"
            output_text += f"    MATRIX IDENT: {t_name}\n"
            output_text += f"    GEOM SIGNIFIER: {t_symbol}\n"
            output_text += f"    TERM WINDOW : {t_rem:02d} MIN REMAINING\n"
            output_text += "--------------------------------------------------\n"
            output_text += f" >> CURRENT PLANETARY CYCLE HORIZON\n"
            output_text += f"    INTERVAL    : HOUR {p_hour:02d} / 12 [{p_phase}]\n"
            output_text += f"    CYCLE LRD   : {p_day_ruler} [OVERALL DAY]\n"
            output_text += f"    CHRONO LRD  : {p_ruler} [ACTIVE HOUR]\n"
            output_text += f"    SYS DECAY   : {p_rem:02d} MIN TO NEXT SHIFT (SCALE: {p_len}M)\n"
            output_text += "--------------------------------------------------\n"
            output_text += f" >> AXIS PROXIMITY EVENT TRACKER\n"
            output_text += f"    NEXT SOLSTICE : 2026.06.21 [SUMMER]\n"
            output_text += f"    NEXT EQUINOX  : 2026.09.22 [AUTUMNAL AXIS DISTANT]\n"
            output_text += f"    LUNAR PHASING : {m_phase_name} ({m_illum:.2f}% LUMEN)\n"
            output_text += "--------------------------------------------------\n"

            # Celestial longitudes (to the very second)
            output_text += " >> CELESTIAL LONGITUDE COORDINATES (to the second)\n"
            for planet, fmt in planet_fmt.items():
                pointer = ">> " if planet == p_ruler else "   "
                output_text += f"    {pointer}{planet:<8} :: [ {fmt} ]\n"
            output_text += "--------------------------------------------------\n"

            # Aspects from chrono-lord to the other planets
            output_text += f" >> ASPECTS FROM {p_ruler}\n"
            p_long = planet_long[p_ruler]
            chrono_pos_dms = angle_to_dms_string(p_long)
            output_text += f"    {p_ruler} POSITION: {chrono_pos_dms} (decimal {p_long:.6f}°)\n"
            for other in PLANET_MAP.keys():
                if other == p_ruler:
                    continue
                other_long = planet_long[other]
                sep_deg, sep_dms, aspect_name, aspect_angle, orb = get_aspect(p_long, other_long)
                orb_str = f"{abs(orb):.3f}°"
                sep_decimal = sep_deg
                output_text += (f"    -> {other:<8} : {angle_to_dms_string(other_long)} "
                                f"(sep {sep_decimal:.6f}° / {sep_dms}) -> {aspect_name}({aspect_angle}°) orb {orb_str}\n")
            output_text += "==================================================\n"
            output_text += " [CLICK THE STOP BUTTON ON THE CELL TO HALT ENGINE]"

            # Render UI in notebook (dynamic colors applied)
            clear_output(wait=True)
            display(HTML(f"{container_style}{output_text}</pre></div>"))

            time.sleep(1)

    except KeyboardInterrupt:
        clear_output(wait=True)
        print("METAPHYSICAL CORE ENGINE SHUT DOWN SAFELY.")
    finally:
        try:
            swe.close()
        except Exception:
            pass

if __name__ == "__main__":
    LATITUDE = 53.4084
    LONGITUDE = -2.9916
    run_notebook_clock(LATITUDE, LONGITUDE)
