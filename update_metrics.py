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
    start_tag = ""
    end_tag = ""
    
    if not os.path.exists("README.md"):
        print("README.md not found!")
        return

    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    if start_tag in content and end_tag in content:
        # Menggunakan regex agar lebih fleksibel terhadap spasi/line endings
        import re
        pattern = rf"{start_tag}.*?{end_tag}"
        new_content = f"{start_tag}\n* **Status:** `Operational`\n* **Top Language:** `{top_lang}`\n* **Last Scan:** `{now}`\n{end_tag}"
        
        updated_content = re.sub(pattern, new_content, content, flags=re.DOTALL)
        
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(updated_content)
        print("Success: README content updated locally in runner.")
    else:
        print(f"Error: Tags not found. Content length: {len(content)}")

if __name__ == "__main__":
    lang = get_top_languages()
    update_readme(lang)