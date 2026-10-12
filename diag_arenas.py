"""Temporary: find the GTHL's arena directory with a real browser. Read-only."""
import time
from selenium.webdriver.common.by import By
import scrape_schedule as s

d = s.setup_driver()
found = {}
try:
    d.get("https://gthlcanada.com/")
    time.sleep(6)
    links = {(a.get_attribute("href") or ""): a.text.strip() for a in d.find_elements(By.TAG_NAME, "a")}
    for href, text in sorted(links.items()):
        if any(k in (href + text).lower() for k in ("arena", "rink", "facilit", "venue", "direction")):
            print("LINK", href, "|", text)
    print("IFRAMES home", [f.get_attribute("src") for f in d.find_elements(By.TAG_NAME, "iframe")])
    d.get(s.SCHEDULE_URL); time.sleep(6)
    print("IFRAMES schedule", [f.get_attribute("src") for f in d.find_elements(By.TAG_NAME, "iframe")])
    for url in ["https://gthlcanada.com/arenas/", "https://gthlcanada.com/arena-directory/", "https://gthlcanada.com/arena-locations/"]:
        d.get(url); time.sleep(5)
        body = d.find_element(By.TAG_NAME, "body").text
        print("PAGE", url, "|", d.title, "|", len(body), "chars")
        if "404" not in d.title and len(body) > 500:
            name = url.rstrip("/").split("/")[-1]
            open(f"fetched/{name}.txt", "w").write(body)
            open(f"fetched/{name}.html", "w").write(d.page_source)
            print("IFRAMES", [f.get_attribute("src") for f in d.find_elements(By.TAG_NAME, "iframe")])
finally:
    d.quit()
