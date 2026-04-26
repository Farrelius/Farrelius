import requests
import os
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
        return sorted_langs[0][0] if sorted_langs else "Logic/Systems"
    except:
        return "System Active"

def update_readme(top_lang):
    now = datetime.now().strftime("%Y-%m-%d %H:%M WIB")
    # WAJIB ADA ISINYA:
    start_tag = ""
    end_tag = ""
    
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    if start_tag in content and end_tag in content:
        try:
            parts = content.split(start_tag)
            head = parts[0]
            tail = parts[1].split(end_tag)[1]
            
            new_metrics = f"\n* **Status:** `Operational`\n* **Top Language:** `{top_lang}`\n* **Last Scan:** `{now}`\n"
            
            updated_content = head + start_tag + new_metrics + end_tag + tail
            
            with open("README.md", "w", encoding="utf-8") as f:
                f.write(updated_content.strip() + "\n")
            print("System metrics updated successfully.")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Tags missing in README.md")

if __name__ == "__main__":
    lang = get_top_languages()
    update_readme(lang)