import time
import uuid
from pathlib import Path

from helium import start_chrome, go_to, click, get_driver, write, press, ENTER, start_firefox
from selenium.common import NoSuchElementException
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By

landing_path = Path(__file__).parent / "index.html"
landing_page = """
<!DOCTYPE html>
<html>
    <head>
        <title>Landing page</title>
        <script>
            function redirect() {{
                window.location.href = "{url}"
            }}
            setTimeout(redirect, 2000)
        </script>
    </head>
    <body>
        <p>Please wait 2 seconds...</p>
    </body>
</html>
"""

def start_chrome_driver(user_data: str):
    options = ChromeOptions()
    options.add_argument(f"--user-data-dir={user_data}")
    options.add_argument("--remote-debugging-port=9222")
    start_chrome(options=options)


def start_firefox_driver():
    start_firefox()


def open_landing_page(app_port: int):
    html = landing_page.format(url=f"http://127.0.0.1:{app_port}/")
    with open(landing_path, "w") as f:
        f.write(html)
    go_to(f"file://{landing_path}")


def download_contacts(url: str, file: str, download: str, extension: str):
    driver = get_driver()
    driver.switch_to.new_window("tab")
    go_to(url)
    click(file)
    click(download)
    click(extension)
    time.sleep(1)
    driver.close()


tabs = {}


def open_tab(url: str) -> str:
    driver = get_driver()
    driver.switch_to.new_window("tab")
    go_to(url)
    uid = str(uuid.uuid4())
    tabs[uid] = driver.current_window_handle
    return uid


def focus_tab(uid: str):
    driver = get_driver()
    driver.switch_to.window(tabs[uid])


def send_wa_message(phone: str, text: str) -> bool:
    driver = get_driver()
    click(driver.find_element(By.XPATH, '//button[@title="New chat"]'))
    time.sleep(0.5)
    write(phone, into="Search name or number")
    time.sleep(0.5)
    try:
        element = driver.find_element(By.XPATH, '//div[@role="gridcell"]')
    except NoSuchElementException:
        return False
    click(element)
    time.sleep(0.5)
    write(text, into="Type a message")
    press(ENTER)
    return True
