import sqlite3
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time

# Database setup
DATABASE = 'targets.db'

# Regular expression for matching emails
EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'

# Maximum number of internal pages to crawl per website
MAX_PAGES_PER_SITE = 20

def create_emails_table(conn):
    """Create the emails table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            url TEXT,
            email TEXT
        )
    ''')
    conn.commit()
    print("Created 'emails' table in the database.")

def extract_emails_from_page(url, soup):
    """Extract emails from a single page."""
    emails = set(re.findall(EMAIL_REGEX, soup.get_text()))
    print(f"Found {len(emails)} email(s) on {url}")
    return emails

def crawl_site(start_url, conn):
    """Crawl the website starting from the given URL and extract emails."""
    visited = set()
    to_visit = [start_url]
    page_count = 0  # Counter for the number of pages visited

    print(f"\nStarting to crawl website: {start_url}")

    while to_visit and page_count < MAX_PAGES_PER_SITE:
        url = to_visit.pop(0)
        if url in visited:
            print(f"Skipping already visited page: {url}")
            continue

        print(f"\nVisiting page {page_count + 1}: {url}")

        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract emails from the current page
            emails = extract_emails_from_page(url, soup)
            save_emails_to_db(conn, url, emails)

            # Find all links on the page and add them to the to_visit list if they are within the same domain
            for link in soup.find_all('a', href=True):
                full_url = urljoin(url, link['href'])
                if full_url.startswith(start_url) and full_url not in visited:
                    to_visit.append(full_url)
                    print(f"Added new page to crawl: {full_url}")

            visited.add(url)
            page_count += 1

            # Wait for 1 second before making the next request
            print("Waiting 1 second before the next request...")
            time.sleep(5)

        except requests.RequestException as e:
            print(f"Failed to fetch {url}: {e}")

    print(f"\nFinished crawling {start_url}. Visited {page_count} pages.")

def save_emails_to_db(conn, url, emails):
    """Save extracted emails to the database."""
    cursor = conn.cursor()
    for email in emails:
        cursor.execute('INSERT INTO emails (url, email) VALUES (?, ?)', (url, email))
    conn.commit()
    print(f"Saved {len(emails)} email(s) from {url} to the database.")

def main():
    # Connect to the database
    conn = sqlite3.connect(DATABASE)
    create_emails_table(conn)

    # Read URLs from the target_attributes table
    cursor = conn.cursor()
    cursor.execute('SELECT target FROM target_attributes')
    urls = [row[0] for row in cursor.fetchall()]

    print(f"Found {len(urls)} URLs to crawl in the database.")

    # Crawl each URL and extract emails
    for url in urls:
        crawl_site(url, conn)

    # Close the database connection
    conn.close()
    print("\nDatabase connection closed. Crawling completed.")

if __name__ == "__main__":
    main()
