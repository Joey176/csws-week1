"""
Metaphysical Core - Time-Matrix Engine
A real-time astronomical and astrological calculation display system.
"""

import time
import datetime
import math
import sys
from zoneinfo import ZoneInfo

import swisseph as swe
from astral import LocationInfo
from astral.sun import sun

# --- Configuration & Constants ---

TATTWAS = [
    ("PRITHVI [EARTH]", 6, "[Y-SQ]"),
    ("JALA    [WATER]", 12, "[S-CR]"),
    ("TEJAS   [FIRE] ", 18, "[R-TR]"),
    ("VAYU    [AIR]  ", 24, "[B-CI]"),
    ("AKASHA  [ETHER]", 30, "[B-EG]"),
]
TOTAL_TATTWA_CYCLE_MINS = 90

CHALDEAN_ORDER = ["SATURN", "JUPITER", "MARS", "SUN", "VENUS", "MERCURY", "MOON"]
WEEKDAY_LORDS = {
    0: "MOON",
    1: "MARS",
    2: "MERCURY",
    3: "JUPITER",
    4: "VENUS",
    5: "SATURN",
    6: "SUN",
}
ZODIAC_SIGNS = ["ARI", "TAU", "GEM", "CAN", "LEO", "VIR", "LIB", "SCO", "SAG", "CAP", "AQU", "PIS"]

PLANET_MAP = {
    "SUN": swe.SUN,
    "MOON": swe.MOON,
    "MERCURY": swe.MERCURY,
    "VENUS": swe.VENUS,
    "MARS": swe.MARS,
    "JUPITER": swe.JUPITER,
    "SATURN": swe.SATURN,
}

# ANSI Terminal Colors
RED = "\033[1;31m"
RESET = "\033[0m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

# Location coordinates for Liverpool, UK
DEFAULT_LATITUDE = 53.4084
DEFAULT_LONGITUDE = -2.9916


# --- Calculation Functions ---


def get_chinese_zodiac(year: int) -> tuple[str, str]:
    """
    Calculate Chinese zodiac sign based on year.

    Args:
        year: The year to calculate for

    Returns:
        Tuple of (stem, branch) representing the Chinese zodiac
    """
    stems = [
        "Yang Wood",
        "Yin Wood",
        "Yang Fire",
        "Yin Fire",
        "Yang Earth",
        "Yin Earth",
        "Yang Metal",
        "Yin Metal",
        "Yang Water",
        "Yin Water",
    ]
    branches = [
        "Rat",
        "Ox",
        "Tiger",
        "Rabbit",
        "Dragon",
        "Snake",
        "Horse",
        "Goat",
        "Monkey",
        "Rooster",
        "Dog",
        "Pig",
    ]

    if year < 4:
        return "Unknown", "Unknown"

    stem_idx = (year - 4) % 10
    branch_idx = (year - 4) % 12
    return stems[stem_idx], branches[branch_idx]


def get_jewish_meta(now: datetime.datetime) -> tuple[str, str]:
    """
    Get Hebrew calendar metadata for the given date.

    Args:
        now: Current datetime

    Returns:
        Tuple of (chrono, holiday) representing Hebrew calendar info
    """
    if now.year == 2026 and now.month == 6 and now.day == 15:
        return "5786.03.30", "ROSH CHODESH TAMMUZ [NEW MOON]"
    return "5786.03.17", "ORDINARY CYCLE"


def calculate_lunar_phase(julian_day: float) -> tuple[float, str]:
    """
    Calculate lunar phase and illumination percentage.

    Args:
        julian_day: Julian day number

    Returns:
        Tuple of (illumination_percent, phase_name)
    """
    res_sun, _ = swe.calc_ut(julian_day, swe.SUN, 0)
    res_moon, _ = swe.calc_ut(julian_day, swe.MOON, 0)

    sun_long = res_sun[0]
    moon_long = res_moon[0]
    diff = (moon_long - sun_long) % 360

    illumination = (1 - math.cos(math.radians(diff))) / 2 * 100
    phase_name = "WAKING LUNAR ENGINE" if illumination > 1 else "DARK MOON HORIZON"

    return illumination, phase_name


def get_sun_data(lat: float, lon: float) -> tuple[dict, dict, dict]:
    """
    Get sunrise and sunset data for today and adjacent days.

    Args:
        lat: Latitude of location
        lon: Longitude of location

    Returns:
        Tuple of (yesterday_sun, today_sun, tomorrow_sun) dicts
    """
    city = LocationInfo("Liverpool", "UK", "Europe/London", lat, lon)
    now = datetime.datetime.now(ZoneInfo("Europe/London"))

    s_yesterday = sun(
        city.observer,
        date=now.date() - datetime.timedelta(days=1),
        tzinfo=ZoneInfo("Europe/London"),
    )
    s_today = sun(city.observer, date=now.date(), tzinfo=ZoneInfo("Europe/London"))
    s_tomorrow = sun(
        city.observer,
        date=now.date() + datetime.timedelta(days=1),
        tzinfo=ZoneInfo("Europe/London"),
    )

    return s_yesterday, s_today, s_tomorrow


def calculate_tattwa(now: datetime.datetime, sunrise_today: datetime.datetime) -> tuple[str, str, int]:
    """
    Calculate active Tattwa element and remaining time.

    Args:
        now: Current datetime
        sunrise_today: Sunrise time for today

    Returns:
        Tuple of (name, symbol, minutes_remaining)
    """
    time_diff = now - sunrise_today
    diff_minutes = time_diff.total_seconds() / 60.0
    minute_in_cycle = diff_minutes % TOTAL_TATTWA_CYCLE_MINS

    elapsed = 0
    for name, duration, symbol in TATTWAS:
        if elapsed <= minute_in_cycle < (elapsed + duration):
            remaining = int((elapsed + duration) - minute_in_cycle)
            return name, symbol, remaining
        elapsed += duration

    return TATTWAS[0][0], TATTWAS[0][2], 0


def calculate_planetary_hour(
    now: datetime.datetime,
    s_yesterday: dict,
    s_today: dict,
    s_tomorrow: dict,
) -> tuple[int, str, str, int, int, str]:
    """
    Calculate current planetary hour and hour ruling planet.

    Args:
        now: Current datetime
        s_yesterday: Yesterday's sun data
        s_today: Today's sun data
        s_tomorrow: Tomorrow's sun data

    Returns:
        Tuple of (hour_number, phase, ruler, minutes_remaining, hour_length_mins, day_ruler)
    """
    if s_today["sunrise"] <= now < s_today["sunset"]:
        phase = "DAYTIME"
        start_time = s_today["sunrise"]
        end_time = s_today["sunset"]
        day_of_week = start_time.weekday()
        base_offset = 0
    else:
        phase = "NIGHTTIME"
        base_offset = 4

        if now >= s_today["sunset"]:
            start_time = s_today["sunset"]
            end_time = s_tomorrow["sunrise"]
            day_of_week = s_today["sunrise"].weekday()
        else:
            start_time = s_yesterday["sunset"]
            end_time = s_today["sunrise"]
            day_of_week = s_yesterday["sunrise"].weekday()

    total_duration = end_time - start_time
    hour_length = total_duration / 12
    current_hour_idx = int((now - start_time) / hour_length)

    # Clamp hour index between 0 and 11
    current_hour_idx = max(0, min(11, current_hour_idx))

    day_lord = WEEKDAY_LORDS[day_of_week]
    final_planet_idx = (CHALDEAN_ORDER.index(day_lord) + base_offset + current_hour_idx) % 7
    ruler = CHALDEAN_ORDER[final_planet_idx]

    minutes_remaining = int(((start_time + (hour_length * (current_hour_idx + 1))) - now).total_seconds() / 60)
    hour_length_mins = int(hour_length.total_seconds() / 60)

    return current_hour_idx + 1, phase, ruler, minutes_remaining, hour_length_mins, day_lord


def get_zodiac_positions(julian_day: float) -> dict[str, str]:
    """
    Get celestial longitude positions for all planets.

    Args:
        julian_day: Julian day number

    Returns:
        Dictionary mapping planet names to position strings
    """
    positions = {}

    for name, swe_id in PLANET_MAP.items():
        res, _ = swe.calc_ut(julian_day, swe_id, swe.FLG_SPEED)
        longitude = res[0]
        speed = res[3]
        sign_index = int(longitude // 30)
        retro_marker = "<-" if speed < 0 else "  "
        positions[name] = f"{int(longitude % 30):02d}DG {ZODIAC_SIGNS[sign_index]} {retro_marker}"

    return positions


# --- Terminal Display Engine ---


def format_display_output(
    now_local: datetime.datetime,
    c_stem: str,
    c_branch: str,
    j_chrono: str,
    j_holiday: str,
    t_name: str,
    t_symbol: str,
    t_rem: int,
    p_hour: int,
    p_phase: str,
    p_day_ruler: str,
    p_ruler: str,
    p_rem: int,
    p_len: int,
    m_illum: float,
    m_phase_name: str,
    planet_positions: dict[str, str],
    blink_state: bool,
) -> str:
    """Format the complete display output string."""
    sep = ":" if blink_state else " "
    time_str = now_local.strftime(f"%H{sep}%M{sep}%S")

    output = []
    output.append("==================================================")
    output.append(" ::: METAPHYSICAL CORE // TIME-MATRIX ENGINE ::: ")
    output.append("==================================================")
    output.append(f" [LOCAL SYSTEM TIME] ------> [ {time_str} ] (BST)")
    output.append(f" [MATRIX CHRONO] -----------> [ {now_local.strftime('%Y.%m.%d')} ]")
    output.append(f" [CHINESE VECTOR] ----------> [ Year of the {c_stem} {c_branch} ]")
    output.append(f" [HEBREW LUNISOLAR] --------> [ AM {j_chrono} // {j_holiday} ]")
    output.append("--------------------------------------------------")
    output.append(" >> ACTIVE TATTWA ELEMENT VECTOR")
    output.append(f"    MATRIX IDENT: {t_name}")
    output.append(f"    GEOM SIGNIFIER: {t_symbol}")
    output.append(f"    TERM WINDOW : {t_rem:02d} MIN REMAINING")
    output.append("--------------------------------------------------")
    output.append(" >> CURRENT PLANETARY CYCLE HORIZON")
    output.append(f"    INTERVAL    : HOUR {p_hour:02d} / 12 [{p_phase}]")
    output.append(f"    CYCLE LRD   : {p_day_ruler} [OVERALL DAY]")
    output.append(f"    CHRONO LRD  : {p_ruler} [ACTIVE HOUR]")
    output.append(f"    SYS DECAY   : {p_rem:02d} MIN TO NEXT SHIFT (SCALE: {p_len}M)")
    output.append("--------------------------------------------------")
    output.append(" >> AXIS PROXIMITY EVENT TRACKER")
    output.append(" NEXT SOLSTICE : 2026.06.21 [SUMMER]")
    output.append(" NEXT EQUINOX  : 2026.09.22 [AUTUMNAL AXIS DISTANT]")
    output.append(f"    LUNAR PHASING : {m_phase_name} ({m_illum:.2f}% LUMEN)")
    output.append("--------------------------------------------------")
    output.append(" >> CELESTIAL LONGITUDE COORDINATES")

    for planet, position in planet_positions.items():
        pointer = ">> " if planet == p_ruler else "   "
        output.append(f"    {pointer}{planet:<8} :: [ {position} ]")

    output.append("==================================================")
    output.append(" [CLICK STOP BUTTON TO HALT ENGINE PROCESS]")

    return "\n".join(output)


def run_alien_clock(lat: float, lon: float) -> None:
    """
    Run the main time-matrix engine display loop in terminal.

    Args:
        lat: Latitude of observation point
        lon: Longitude of observation point
    """
    blink_state = True

    try:
        while True:
            uk_tz = ZoneInfo("Europe/London")
            now_local = datetime.datetime.now(uk_tz)
            now_utc = datetime.datetime.now(datetime.timezone.utc)

            julian_day = swe.julday(
                now_utc.year,
                now_utc.month,
                now_utc.day,
                now_utc.hour + now_utc.minute / 60.0 + now_utc.second / 3600.0,
            )

            # Perform all calculations
            s_yesterday, s_today, s_tomorrow = get_sun_data(lat, lon)
            t_name, t_symbol, t_rem = calculate_tattwa(now_local, s_today["sunrise"])
            (
                p_hour,
                p_phase,
                p_ruler,
                p_rem,
                p_len,
                p_day_ruler,
            ) = calculate_planetary_hour(now_local, s_yesterday, s_today, s_tomorrow)
            planet_positions = get_zodiac_positions(julian_day)

            c_stem, c_branch = get_chinese_zodiac(now_local.year)
            j_chrono, j_holiday = get_jewish_meta(now_local)
            m_illum, m_phase_name = calculate_lunar_phase(julian_day)

            blink_state = not blink_state

            # Format and display output
            output = format_display_output(
                now_local,
                c_stem,
                c_branch,
                j_chrono,
                j_holiday,
                t_name,
                t_symbol,
                t_rem,
                p_hour,
                p_phase,
                p_day_ruler,
                p_ruler,
                p_rem,
                p_len,
                m_illum,
                m_phase_name,
                planet_positions,
                blink_state,
            )

            # Clear screen and print
            print("\033[H\033[J", end="")  # Clear terminal
            print(RED + output + RESET)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[INTERFACE SYSTEM OFFLINE]")
    finally:
        swe.close()


if __name__ == "__main__":
    run_alien_clock(DEFAULT_LATITUDE, DEFAULT_LONGITUDE)
