import re
import time
from typing import Tuple

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://spmilabs.ru"
CHECK_URLS = [
    f"{BASE_URL}/new_record/7/90/10_27",
]

def _needs_login(html: str) -> bool:
    return "<form" in html and "action=\"/login\"" in html


def _perform_login(session: requests.Session, username: str, password: str) -> Tuple[bool, str]:
    try:
        session.get(BASE_URL, timeout=20)
    except Exception:
        pass

    payload = {
        "username": username,
        "password": password,
    }
    resp = session.post(f"{BASE_URL}/login", data=payload, timeout=30, allow_redirects=True)
    return resp.ok, resp.text


def _has_available_slot(html: str) -> bool:
    # Quick checks first
    if "timetable_button_active" in html or "Записаться" in html:
        return True

    # Fallback to structured parse
    soup = BeautifulSoup(html, "html.parser")
    # Look for active buttons or explicit text
    if soup.select_one("a.timetable_button_active"):
        return True
    if soup.find(string=re.compile(r"Записаться", re.IGNORECASE)):
        return True
    return False


def check_availability(username: str, password: str, session: requests.Session | None = None) -> bool:
    """
    Returns True if any of CHECK_URLS has available slots, otherwise False.
    Maintains and reuses the provided requests.Session (or creates one).
    """
    sess = session or requests.Session()

    for url in CHECK_URLS:
        time.sleep(10)
        r = sess.get(url, timeout=30, allow_redirects=True)
        html = r.text

        if _needs_login(html):
            ok, _ = _perform_login(sess, username, password)
            if not ok:
                # Failed login => cannot detect availability
                return False
            # Re-try the same URL within the same session
            r = sess.get(url, timeout=30, allow_redirects=True)
            html = r.text

        if _has_available_slot(html):
            print("Availability = True")
            return True
    print("Availability = False")
    return False


__all__ = ["check_availability", "CHECK_URLS", "BASE_URL"]


