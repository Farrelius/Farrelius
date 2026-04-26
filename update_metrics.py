import requests
import os
import re
from datetime import datetime

USERNAME = "Farrelius"
TOKEN = os.getenv("METRICS_TOKEN")

def get_top_languages():
    url = f"https://api.github.com/users/{USERNAME}/repos"
    headers = {"Authorization": f"token {TOKEN}"}
    repos = requests.get(url, headers=headers).json()
    
    languages = {}
    for repo in repos:
        if repo['language']:
            lang = repo['language']
            languages[lang] = languages.get(lang, 0) + 1
            
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
    top_lang = sorted_langs[0][0] if sorted_langs else "Unknown"
    return top_lang

def update_readme(top_lang):
    now = datetime.now().strftime("%Y-%m-%d %H:%M WIB")
    
    new_metrics = f"""* **Status:** `Active`
* **Top Language:** `{top_lang}`
* **Last Scan:** `{now}`
"""

    with open("README.md", "r") as f:
        content = f.read()

    updated_content = re.sub(r".*?", 
                             new_metrics, content, flags=re.DOTALL)

    with open("README.md", "w") as f:
        f.write(updated_content)

if __name__ == "__main__":
    lang = get_top_languages()
    update_readme(lang)