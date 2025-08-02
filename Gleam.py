import json
import html
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup


class Gleam:

    def __init__(self, url):
        self.url = url
        self.page = ""
        self.soup = None
        self.giveaway_data = {}
        self.entry_methods = []
        self.actions_required = 0
        self.get_page()
        self.get_giveaway_data()
        self.tasks = self.parse_tasks()
        self.commenttext = self.format_for_reddit()

    def get_page(self):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')

        driver = webdriver.Chrome(options=options)
        driver.get(self.url)
        WebDriverWait(driver, 10).until(
            expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "div[ng-init*='initCampaign']"))
        )
        self.page = driver.page_source
        driver.quit()

    def get_giveaway_data(self):
        self.soup = BeautifulSoup(self.page, "html.parser")
        campaign_div = self.soup.find("div", attrs={"ng-init": lambda v: v and "initCampaign" in v})
        if not campaign_div:
            return None

        # Extract the task data inside ng-init
        raw_json = campaign_div["ng-init"]
        json_str = raw_json.split("initCampaign(", 1)[1].rsplit(")", 1)[0]
        self.giveaway_data = json.loads(html.unescape(json_str))
        self.entry_methods = self.giveaway_data.get("entry_methods", [])
        self.actions_required = self.giveaway_data.get("incentive", {}).get("actions_required", 0)

    def extract_task_links(self, entry):
        task_id = entry.get("id")
        links = set()

        # Look for links in popover content
        elem = self.soup.find(id=f"em{task_id}-popover-content")
        if elem:
            popover_soup = BeautifulSoup(str(elem), "html.parser")
            links.update(a["href"] for a in popover_soup.find_all("a", href=True))

        # Fallback to config3 / config2 HTML fields
        fallback_html = (entry.get("config3", "") or "") + "\n" + (entry.get("config2", "") or "")
        fallback_soup = BeautifulSoup(fallback_html, "html.parser")
        links.update(a["href"] for a in fallback_soup.find_all("a", href=True))

        return list(links)

    def parse_tasks(self):
        tasks = []
        for idx, entry in enumerate(self.entry_methods):
            playtime = None
            if entry.get("entry_type") == "steam_play_game" and entry.get("config3"):
                playtime = float(entry.get("config3"))
                if playtime < 1:
                    playtime = f"{int(playtime * 60)} minutes"
                elif playtime.is_integer():
                    playtime = f"{str(int(playtime))} hours"
                else:
                    playtime = f"{str(playtime)} hours"

            task = {
                "type": entry.get("entry_type"),
                "description": entry.get("action_description").rstrip().rstrip(":"),
                "trigger": entry.get("workflow") or entry.get("template") or entry.get("method_type") or "n/a",
                "requires_auth": bool(entry.get("requires_authentication")),
                "required": idx < self.actions_required,
                "links": self.extract_task_links(entry),
                "playtime": playtime
            }
            tasks.append(task)
        return tasks

    @staticmethod
    def extract_steam_app_ids(links):
        app_ids = []
        for link in links:
            match = re.search(r"store\.steampowered\.com/app/(\d+)", link)
            if match:
                app_ids.append(match.group(1))
        return app_ids

    def format_for_reddit(self):
        required_accounts = {
            t["type"].split("_")[0].capitalize()
            for t in self.tasks if t.get("requires_auth", False)
        }
        commenttext = []
        if required_accounts:
            commenttext.append(f"Required accounts: {', '.join(sorted(required_accounts))}\n")

        commenttext.append("Tasks:\n")
        for idx, task in enumerate(self.tasks, start=1):
            task_type = self.format_task_type(task)
            if task["type"] == "steam_play_game" and task.get("playtime"):
                commenttext.append(f"{idx}. **{task_type.capitalize()}**: {task['description']} ({task['playtime']})")
            else:
                commenttext.append(f"{idx}. **{task_type.capitalize()}**: {task['description']}")

        steam_play_tasks = [t for t in self.tasks if t["type"] == "steam_play_game"]
        if steam_play_tasks:
            commenttext.append("\nPlay task ASF commands:\n")
        app_ids = set()
        playtimes = []
        for task in steam_play_tasks:
            # Extract Steam app IDs for ASF
            app_ids.update(self.extract_steam_app_ids(task["links"]))
            playtimes.append(task["playtime"])

        if app_ids:
            commenttext.append(f"    !addlicense asf {', '.join(f'a/{app_id}' for app_id in app_ids)}")
            commenttext.append(f"    !play asf {', '.join(app_ids)}")
            commenttext.append(f"    wait {max(playtimes, key=self.to_minutes)}")

        return commenttext

    @staticmethod
    def to_minutes(playtimes):
        match = re.search(r'(\d+)\s*(hour|hours|minute|minutes)', playtimes)
        if not match:
            return 0
        value, unit = match.groups()
        value = int(value)
        if "hour" in unit:
            return value * 60
        return value

    @staticmethod
    def format_task_type(task):
        task_type = " ".join(word for word in task["type"].split("_"))
        trigger = task["trigger"].lower()

        # Map task types into logical tasks
        visit_tasks = ["bluesky", "facebook", "instagram", "patreon", "reddit", "telegram", "tiktok", "twitter", "threads", "youtube"]
        if task_type == "promote campaign":
            return "enter giveaway"
        if task["requires_auth"] == False and (task_type == "custom action" or any(keyword in task_type for keyword in visit_tasks)):
            # Visit is seemingly enough for these
            if trigger == "visitdelay":
                return "visit and wait"
            elif trigger == "visitquestion":
                return "visit and answer question"
            else:
                return "visit"
        return task_type
