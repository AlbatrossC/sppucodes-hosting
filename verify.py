import os
import re

def add_download_button(html_content):
    # Regex pattern to match the "View Code" button and extract subject_code and filename
    pattern = re.compile(r'(\s*)<button class="view-code-btn" onclick="loadFile\((.*?)\)">View Code</button>')
    
    def replacement(match):
        indentation = match.group(1)  # Capture leading spaces for indentation
        args = match.group(2).split(', ')
        subject_code = args[0].strip("'")
        filename = args[1].strip("'")
        download_button = f'\n{indentation}<button class="download-code-btn" onclick="downloadCode(\'{subject_code}\', \'{filename}\')">Download Code</button>'
        return match.group(0) + download_button
    
    return pattern.sub(replacement, html_content)

def process_html_files(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".html"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                modified_content = add_download_button(content)
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(modified_content)
                print(f"Updated: {file_path}")

if __name__ == "__main__":
    templates_folder = "templates/subjects"
    process_html_files(templates_folder)
