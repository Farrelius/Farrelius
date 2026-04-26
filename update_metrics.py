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
        return sorted_langs[0][0] if sorted_langs else "Logic/Math"
    except:
        return "Unknown"

def update_readme(top_lang):
    now = datetime.now().strftime("%Y-%m-%d %H:%M WIB")
    
    # Template yang akan dimasukkan
    new_metrics = f"\n* **Status:** `Active`\n* **Top Language:** `{top_lang}`\n* **Last Scan:** `{now}`\n"

    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    # Proteksi: Jika tag ditemukan, ganti isinya. 
    # Jika tidak ditemukan, jangan lakukan apa-apa (mencegah duplikasi).
    pattern = r".*?"
    if re.search(pattern, content, flags=re.DOTALL):
        updated_content = re.sub(pattern, new_metrics, content, flags=re.DOTALL)
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(updated_content)
        print("Success: Metrics updated.")
    else:
        print("Error: Tags not found. No changes made to prevent corruption.")

if __name__ == "__main__":
    lang = get_top_languages()
    update_readme(lang)