import requests
import os
import re
from datetime import datetime

USERNAME = "Farrelius"
TOKEN = os.getenv("METRICS_TOKEN")

def get_top_languages():
    try:
        url = f"https://api.github.com/users/{USERNAME}/repos"
        headers = {"Authorization": f"token {TOKEN}"}
        response = requests.get(url, headers=headers)
        repos = response.json()
        
        languages = {}
        for repo in repos:
            if isinstance(repo, dict) and repo.get('language'):
                lang = repo['language']
                languages[lang] = languages.get(lang, 0) + 1
        
        sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
        return sorted_langs[0][0] if sorted_langs else "None Detected"
    except Exception as e:
        return f"Error: {str(e)}"

def update_readme(top_lang):
    now = datetime.now().strftime("%Y-%m-%d %H:%M WIB")
    
    # Template baru
    new_metrics = f"\n* **Status:** `Active`\n* **Top Language:** `{top_lang}`\n* **Last Scan:** `{now}`\n"

    if not os.path.exists("README.md"):
        print("README.md not found!")
        return

    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    if "" in content and "" in content:
        updated_content = re.sub(r".*?", 
                                 new_metrics, content, flags=re.DOTALL)
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(updated_content)
        print("README updated successfully!")
    else:
        print("Tags not found! No changes made.")

if __name__ == "__main__":
    lang = get_top_languages()
    update_readme(lang)