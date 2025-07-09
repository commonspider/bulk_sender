from helium import kill_browser

from bulk_sender import load_config, create_app, save_config, start_chrome_driver, start_firefox_driver, open_landing_page

conf = load_config("config.json")
driver_type = conf.get("driver", "chrome")
profile = conf.get("driver_profile", ".profile")
port = conf.get("app_port", "8050")

if driver_type == "chrome":
    start_chrome_driver(profile)
elif driver_type == "firefox":
    start_firefox_driver()
else:
    raise ValueError(driver_type)

open_landing_page(port)

app = create_app()
try:
    print("=== PREMI CTRL-C PER TERMINARE IL PROGRAMMA ===")
    app.run(port=port)
finally:
    save_config()
    kill_browser()
