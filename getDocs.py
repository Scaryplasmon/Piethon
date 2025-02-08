import requests
from bs4 import BeautifulSoup
import re
from pathlib import Path

def download_and_process_html(url, output_dir):
    # Extract filename from URL
    # Remove anchor tags from filename
    filename = url.split('/')[-1].split('#')[0].replace('.html', '.txt')
    output_file = output_dir / filename
    
    try:
        # Add headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error downloading {url}: {e}")
        return False

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Try different common content selectors
    content_selectors = [
        ('div', {'role': 'main'}),
        ('main', {}),
        ('div', {'class': 'body'}),
        ('div', {'class': 'document'}),
        ('div', {'class': 'content'}),
        ('article', {}),
        ('div', {'id': 'content'}),
        ('div', {'class': 'container'}),
    ]
    
    main_content = None
    for tag, attrs in content_selectors:
        main_content = soup.find(tag, attrs)
        if main_content:
            break
    
    if not main_content:
        # Fallback: try to find the largest div with the most text content
        divs = soup.find_all('div')
        if divs:
            main_content = max(divs, key=lambda x: len(x.get_text()))
        else:
            print(f"Could not find main content for {url}")
            return False

    processed_text = []
    
    def process_element(element):
        # Skip navigation and footer sections
        if element.get('role') in ['navigation', 'footer'] or \
           any(c in str(element.get('class', [])) for c in ['nav', 'footer', 'sidebar']):
            return

        if element.name == 'pre':
            code = element.find('code')
            if code and 'class' in code.attrs:
                lang = code['class'][0].replace('language-', '')
                processed_text.append(f"```{lang}")
            else:
                processed_text.append("```")
            processed_text.append(element.get_text().strip())
            processed_text.append("```\n")
            
        elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            text = element.get_text().strip()
            if text:
                processed_text.append(f"\n{'#' * int(element.name[1])} {text}\n")
            
        elif element.name == 'p':
            text = element.get_text().strip()
            if text:
                processed_text.append(f"{text}\n")
                
        elif element.name in ['ul', 'ol']:
            for li in element.find_all('li', recursive=False):
                text = li.get_text().strip()
                if text:
                    processed_text.append(f"* {text}")
            processed_text.append("")
            
        elif element.name == 'table':
            rows = element.find_all('tr')
            if rows:
                processed_text.append("\n| " + " | ".join(cell.get_text().strip() 
                    for cell in rows[0].find_all(['td', 'th'])) + " |")
                processed_text.append("|" + "|".join("---" for _ in 
                    rows[0].find_all(['td', 'th'])) + "|")
                for row in rows[1:]:
                    processed_text.append("| " + " | ".join(cell.get_text().strip() 
                        for cell in row.find_all(['td', 'th'])) + " |")
                processed_text.append("")
            
        else:
            for child in element.children:
                if isinstance(child, str):
                    text = child.strip()
                    if text:
                        processed_text.append(f"{text}\n")
                elif hasattr(child, 'name'):
                    process_element(child)

    process_element(main_content)
    
    # Remove empty lines and clean up the text
    processed_text = [line for line in processed_text if line.strip()]
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(processed_text))
        print(f"Successfully processed and saved to {output_file}")
        return True
    except Exception as e:
        print(f"Error saving {output_file}: {e}")
        return False

def process_links_file(links_file, output_dir):
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Read and process links
    with open(links_file, 'r') as f:
        links = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(links)} links to process")
    
    for i, url in enumerate(links, 1):
        print(f"\nProcessing {i}/{len(links)}: {url}")
        download_and_process_html(url, output_dir)

if __name__ == "__main__":
    links_file = "links.txt"
    output_dir = "pyside6docs2/"
    process_links_file(links_file, output_dir)