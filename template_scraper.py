from playwright.sync_api import sync_playwright
import pandas as pd
import time
import json
import os
import re

# I randomly clicked on many templates and recorded the categories I found- this is not ALL the categories, just a random sample
CATEGORIES = [
    "personal-finance", "budgets", "expense-tracker", "personal", "school",
    "student-life", "work", "finance", "engineering", "design", "marketing",
    "hr", "sales", "travel", "social-media", "startup", "freelance",
    "real-estate", "new-years", "personal-goals", "habit-tracking", "seasonal",
    "monthly-planner", "hobbies", "learning", "networking", "creators", "crm",
    "books", "writing", "entertainment", "personal-productivity",
    "life", "friends-family", "pets", "video-games", "weddings", "budget",
    "dating-relationships", "journaling", "blogging", "website-building"
]

OUTPUT_FILE = "notion_templates.csv"
LINKS_FILE = "template_links.json"

# Scroll to load all templates in a category
def scroll_to_load_all(page):
    prev_height = 0
    for _ in range(50):
        page.keyboard.press("End")
        time.sleep(1.5)
        curr_height = page.evaluate("document.body.scrollHeight")
        if curr_height == prev_height:
            break
        prev_height = curr_height

# Collect template links from a category
def collect_template_links(page):
    if os.path.exists(LINKS_FILE):
        print(f"Loading existing links from {LINKS_FILE}...")
        with open(LINKS_FILE) as f:
            return json.load(f)

    all_links = set()
    # Loop through each category in my defined list above and collect template links (URLs)
    for category in CATEGORIES:
        url = f"https://app.notion.com/marketplace/categories/{category}"
        print(f"Collecting links from: {category}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            scroll_to_load_all(page)
            # Get all template links on the page
            links = page.eval_on_selector_all(
                "a[href*='/marketplace/templates/']",
                "els => els.map(el => el.href)"
            )
            # Use a set to avoid duplicates (because one template can be tagged in multiple categories). Scrape 50 templates per category
            clean = set()
            for l in links:
                base = l.split("?")[0]
                if "/marketplace/templates/" in base:
                    clean.add(base)
                if len(clean) >= 50:
                    break
            # Print to check how many templates were found
            print(f"  -> Found {len(clean)} templates")
            all_links.update(clean)
        # If there is an error, print the error and continue to the next category
        except Exception as e:
            print(f"  Error on {category}: {e}")
            continue
    # Convert to list and save to file
    all_links = list(all_links)
    with open(LINKS_FILE, "w") as f:
        json.dump(all_links, f)
    print(f"\nTotal unique templates found: {len(all_links)}")
    return all_links

# Scrape a template page for the following: title, price, downloads, rating, rating count, categories, 
#features, creator name, creator template count, category ranking, last updated, preview image count
def scrape_template_page(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        data = {"url": url}

        # Title
        try:
            title_el = page.query_selector("[style*='font-size: 30px'][style*='font-weight: 600']")
            data["title"] = title_el.inner_text().strip() if title_el else None
        except Exception:
            data["title"] = None

        # Price
        try:
            time.sleep(2)
            page_text = page.inner_text("body")
            price_match = re.search(r'Buy for \$[\d.]+', page_text)
            if price_match:
                data["price"] = price_match.group().replace("Buy for ", "")
                data["is_free"] = False
            else:
                data["price"] = "Free"
                data["is_free"] = True
        except Exception:
            data["price"] = None
            data["is_free"] = None

        # Downloads
        try:
            svg = page.query_selector(".arrowLineDown")
            if svg:
                raw = svg.evaluate("el => el.nextElementSibling.innerText")
                data["downloads"] = raw.strip()
            else:
                data["downloads"] = None
        except Exception:
            data["downloads"] = None

        # Rating
        try:
            rating_els = page.query_selector_all("[style*='font-size: 52px']")
            data["rating"] = rating_els[0].inner_text().strip() if rating_els else None
        except Exception:
            data["rating"] = None

        # Rating count
        try:
            all_small = page.query_selector_all("[style*='font-size: 12px']")
            data["rating_count"] = None
            for el in all_small:
                t = el.inner_text()
                if "ratings" in t:
                    data["rating_count"] = t.strip()
                    break
        except Exception:
            data["rating_count"] = None

        # Categories
        try:
            cat_links = page.query_selector_all("a[href*='/marketplace/categories/']")
            cats = [el.inner_text().strip() for el in cat_links if el.inner_text().strip()]
            data["categories"] = ", ".join(list(dict.fromkeys(cats)))
        except Exception:
            data["categories"] = None

        # Features
        try:
            feature_divs = page.query_selector_all("[style*='bluIcoAccPri'] ~ div")
            features = [el.inner_text().strip() for el in feature_divs if el.inner_text().strip()]
            data["features"] = ", ".join(features) if features else None
        except Exception:
            data["features"] = None

        # Creator name
        try:
            creator_el = page.query_selector("[style*='font-size: 17px'][style*='font-weight: 600']")
            data["creator"] = creator_el.inner_text().strip() if creator_el else None
        except Exception:
            data["creator"] = None

        # Creator template count
        try:
            all_small = page.query_selector_all("[style*='font-size: 12px'][style*='font-weight: 500']")
            data["creator_template_count"] = None
            for el in all_small:
                t = el.inner_text()
                if "template" in t:
                    data["creator_template_count"] = t.strip()
                    break
        except Exception:
            data["creator_template_count"] = None

        # Category ranking
        try:
            rank_els = page.query_selector_all("[style*='font-size: 17px'][style*='font-weight: 600']")
            data["category_rank"] = None
            for el in rank_els:
                t = el.inner_text()
                if "#" in t and "in" in t:
                    data["category_rank"] = t.strip()
                    break
        except Exception:
            data["category_rank"] = None

        # Last updated
        try:
            all_small = page.query_selector_all("[style*='font-size: 12px']")
            data["last_updated"] = None
            for el in all_small:
                t = el.inner_text()
                if "weeks ago" in t or "months ago" in t or "days ago" in t:
                    data["last_updated"] = t.strip()
                    break
        except Exception:
            data["last_updated"] = None

        # Preview image count
        try:
            img_thumbs = page.query_selector_all("[style*='height: 100px']")
            data["preview_image_count"] = len(img_thumbs)
        except Exception:
            data["preview_image_count"] = None

        return data

    except Exception as e:
        print(f"  Fatal error on {url}: {e}")
        return {"url": url, "error": str(e)}


def main():
    existing_urls = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            existing_df = pd.read_csv(OUTPUT_FILE)
            existing_urls = set(existing_df["url"].tolist())
            print(f"Resuming. Already scraped {len(existing_urls)} templates")
        except Exception:
            print("Could not read existing CSV, restarting.")
    # Launch the pop-upbrowser and go to the marketplace page
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://app.notion.com/marketplace", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        input("Log into Notion in the browser, then navigate to the Marketplace, then press Enter...")

        all_links = collect_template_links(page)
        todo = list(set([l for l in all_links if l not in existing_urls]))
        print(f"\nTemplates to scrape: {len(todo)}")

        batch = []
        header_written = os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0
        # Loop through each template link and scrape the data
        for i, url in enumerate(todo):
            print(f"[{i+1}/{len(todo)}] {url.split('/')[-1]}")
            result = scrape_template_page(page, url)
            batch.append(result)

            if len(batch) >= 50:
                df = pd.DataFrame(batch)
                df.to_csv(OUTPUT_FILE, mode="a", header=not header_written, index=False)
                header_written = True
                print(f"  Saved batch of 50")
                batch = []

        if batch:
            df = pd.DataFrame(batch)
            df.to_csv(OUTPUT_FILE, mode="a", header=not header_written, index=False)

        browser.close()

    final_df = pd.read_csv(OUTPUT_FILE)
    print(f"\nDone! Total templates scraped: {len(final_df)}")
    print(final_df.head())


if __name__ == "__main__":
    main()


