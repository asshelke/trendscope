from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

from dotenv import load_dotenv
import os
import re
import time
from datetime import datetime
from utils import write_to_json

driver = None

# Load environment variables
load_dotenv()
TWITTER_EMAIL = os.getenv("TWITTER_EMAIL")
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")
# Headless mode (avoid being detected as a bot)
options = Options()
options.add_argument("--headless=new")
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")  # Avoid /dev/shm issues
options.add_argument("--disable-gpu")  # Disable GPU acceleration
options.add_argument("window-size=1920,1080")
options.add_argument("--start-maximized")

def login_to_twitter(USERNAME, PASSWORD, EMAIL):
    global driver
    
    # Navigate to the Twitter login page
    driver.get("https://x.com/login")
    time.sleep(6)

    # Enter username into text input
    username_input = driver.find_element(By.NAME, "text")
    username_input.send_keys(USERNAME + Keys.ENTER)
    time.sleep(4)

    # Enter email if unusual activity prompted
    try:
        unusual_activity_input = driver.find_element(By.NAME, "text")
        unusual_activity_input.send_keys(EMAIL + Keys.ENTER)
        time.sleep(3)
    except Exception as e:
        pass
        
    # Enter password into password input
    password_input = driver.find_element(By.NAME, "password")
    password_input.send_keys(PASSWORD + Keys.ENTER)
    time.sleep(2)
    
    # Enter email if unusual activity prompted
    try:
        unusual_activity_input = driver.find_element(By.NAME, "text")
        unusual_activity_input.send_keys(EMAIL + Keys.ENTER)
        time.sleep(3)
    except Exception as e:
        pass
    
    print("Twitter login successful.")

def logout_of_twitter():
    global driver
    
    # Navigate to the Twitter logout page
    driver.get("https://x.com/logout")
    time.sleep(2)
    
    # Click the logout button
    driver.find_element(By.CSS_SELECTOR, '[data-testid="confirmationSheetConfirm"]').click()
    time.sleep(5)
    
    print("Twitter logout successful.")

def extract_trend_info(info):
    global driver
    trend_dict = {}
    
    # Extract trend rank
    trend_dict["rank"] = info[0]
    
    # Extract trend title
    for idx, line in enumerate(info):
        if "trending" in line.lower():
            trend_dict["title"] = info[idx + 1]
            break
        
    # Extract post count if it exists
    if "posts" in info[-1]:
        trend_dict["posts"] =re.match(r"[0-9,.]+[A-Z]?", info[-1], re.IGNORECASE).group()
    
    # Extract category if it exists
    if "trending" not in info[1].lower():
        trend_dict["category"] = info[1]
    # Extract location as category instead
    elif "trending in" in info[1].lower():
        trend_dict["category"] = info[1][len("trending in "):]
        
    return trend_dict

def scrape_tweets():
    global driver
    print("Scraping tweets...")
    scraped_tweets = set()
    
    MAX_TWEETS = 50
    MAX_ATTEMPTS = 15
    attempts = MAX_ATTEMPTS

    while len(scraped_tweets) < MAX_TWEETS:
        # Acquire the current batch of tweets
        try:
            tweets = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweetText"]')
            print("Tweets found:", len(tweets))
            links = driver.find_elements(By.CSS_SELECTOR, '[class="css-146c3p1 r-bcqeeo r-1ttztb7 r-qvutc0 r-37j5jr r-a023e6 r-rjixqe r-16dba41 r-xoduu5 r-1q142lx r-1w6e6rj r-9aw3ui r-3s2u2q r-1loqt21"]')
            print("Links found:", len(links))
            prev_count = len(scraped_tweets)
            
            # Update the set of scraped tweets
            for i in range(min(len(tweets), len(links))):
                if tweets[i].text not in scraped_tweets and len(scraped_tweets) < MAX_TWEETS:
                    scraped_tweets.add((tweets[i].text, links[i].get_attribute("href")))
                    
            #     Scroll down to the last scraped tweet
            print("Tweets accumulated", len(scraped_tweets))
            
            if len(scraped_tweets) == prev_count:
                attempts -= 1
                print("Current attempts:", attempts)
                if attempts == 0:
                    break
            else:
                attempts = MAX_ATTEMPTS
            driver.execute_script("arguments[0].scrollIntoView(true);", tweets[-1])
            time.sleep(0.25)
        except Exception as e:
            print(e)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
    scraped_tweets = list(scraped_tweets)
    for i in range(len(scraped_tweets)):
        scraped_tweets[i] = {"text": scraped_tweets[i][0], "url": scraped_tweets[i][1]}
    return scraped_tweets

def scrape_trends(MAX_TRENDS=30):
    global driver
    actions = ActionChains(driver)
    
    # Navigate to the Twitter trends page
    driver.get("https://x.com/explore/tabs/trending")
    time.sleep(6)
    
    scraped_trends = {}
    prev_scroll_height = 0

    while True:
        # Select all trends currently in the DOM
        trends = driver.find_elements(By.CSS_SELECTOR, '[data-testid="cellInnerDiv"]')
        
        # Save trends to dictionary
        for idx in range(len(trends)):
            try:
                ### Skip promoted ads (Check for text)
                if re.findall(r"Promoted by", trends[idx].text, re.IGNORECASE):
                    continue

                info = [i.strip() for i in re.split(r"[\u00b7\n]", trends[idx].text) if i != ""]

                trend_number = info[0]
                if trend_number not in scraped_trends:
                    trend_info = extract_trend_info(info)

                    scraped_trends[trend_number] = trend_info
                    print(f"Info added for trend #{trend_number}")

                    # Open a new tab for every newly scraped trend
                    actions.key_down(Keys.COMMAND).click(trends[idx]).key_up(Keys.COMMAND).perform()
                    
                    driver.implicitly_wait(2)

                    # Switch to the new tab
                    all_tabs = driver.window_handles
                    driver.switch_to.window(all_tabs[-1])
                    
                    driver.implicitly_wait(2)
                    
                    # Scrape the tweets for this trend
                    scraped_trends[trend_number]["tweets"] = scrape_tweets()
                    scraped_trends[trend_number]["tweet_count"] = len(scraped_trends[trend_number]["tweets"])
                    print(f"Tweets scraped for trend #{trend_number}")
                    
                    # Close the tab and switch back to the main tab
                    driver.close()
                    driver.switch_to.window(all_tabs[0])
                    
                    time.sleep(5)
                    
                    trends = driver.find_elements(By.CSS_SELECTOR, '[data-testid="cellInnerDiv"]')
                    
                    if len(scraped_trends) == MAX_TRENDS:
                        print("All tweets successfully scraped.")
                        return scraped_trends
                    
            except Exception as e:
                pass

        # Scroll to the bottom of the trend page
        driver.execute_script("arguments[0].scrollIntoView(true);", trends[-1])
        
        # Update the previous scroll height or stop if the bottom is reached
        scroll_height = driver.execute_script("return document.body.scrollHeight")
        if scroll_height == prev_scroll_height:
            break
        prev_scroll_height = scroll_height
    
    print("All tweets successfully scraped.")

def get_latest_trends_data(TRENDS_TO_FETCH=30):
    global driver

    print("Starting driver...")
    # Start the Chrome driver
    driver = webdriver.Chrome(
        service=(Service(ChromeDriverManager().install())),
        options=options
    )
    driver.maximize_window()
    print("Driver opened...")

    # Login to Twitter
    login_to_twitter(TWITTER_USERNAME, TWITTER_PASSWORD, TWITTER_EMAIL)
    
    # Scrape the trend data
    trend_data = {
        "data": scrape_trends(TRENDS_TO_FETCH), # fetch the trend data
        "timestamp": datetime.now().isoformat()
    }
    
    # Close the driver
    driver.quit()
    return trend_data

if __name__ == "__main__":
    write_to_json(get_latest_trends_data(2), "trends_data.json")