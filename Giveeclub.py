import requests
from bs4 import BeautifulSoup
import re
import time


class GiveeClub:

    def __init__(self, url):
        url_en = self.remove_locale_from_url(url)
        self.tasks = self.get_tasks(url_en)

    @staticmethod
    def remove_locale_from_url(url):
        # Removes localization between givee.club and /event/ to get english tasks
        return re.sub(r"(https://givee\.club)/[^/]+(/event/\d+)", r"\1\2", url)

    @staticmethod
    def get_tasks(url, retries=3, delay=2):
        tasks = []
        for attempt in range(1, retries + 1):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                task_rows = soup.select('.event-actions table tbody tr')

                # Extract task type and description
                for row in task_rows:
                    description_cell = row.select_one('.event-action-label')
                    description = description_cell.get_text(strip=True) if description_cell else 'No description'
                    tasks.append({'description': description})

                return tasks

            except (requests.RequestException, requests.Timeout) as e:
                print(f"Attempt {attempt} failed: {e}")
                if attempt < retries:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print("All attempts failed, returning empty task list.")
                    return tasks

        return tasks