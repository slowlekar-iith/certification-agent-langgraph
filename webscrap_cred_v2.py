from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import json
import time

def scrape_credly(url):
    """
    Scrape user name and certification details from Credly profile page.
    """
    # Set up Selenium WebDriver
    service = Service(executable_path="/Users/sam/Documents/Langgraph/CertAnalysis/lgcertenv/chromedriver")  # Update with your ChromeDriver path
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # Navigate to the URL
        print(f"  Loading page...")
        driver.get(url)
        
        # Wait for page to load - try multiple possible selectors
        print(f"  Waiting for content to load...")
        wait = WebDriverWait(driver, 20)
        
        # Wait for the page to be interactive
        time.sleep(3)  # Additional wait for dynamic content
        
        # Scroll to load all badges (lazy loading)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Get the page source after JavaScript has rendered
        content = driver.page_source
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")
        
        # Extract user name - try multiple possible selectors
        name = "N/A"
        name_selectors = [
            ("h1", {"class": lambda x: x and "profile" in x.lower()}),
            ("h1", {}),
            ("div", {"class": lambda x: x and "user" in x.lower() and "name" in x.lower()}),
        ]
        
        for tag, attrs in name_selectors:
            element = soup.find(tag, attrs)
            if element and element.text.strip():
                name = element.text.strip()
                print(f"  Found name: {name}")
                break
        
        # Extract certifications - badges are typically in card/grid layouts
        certifications = []
        
        # Try to find badge containers with various possible class names
        badge_containers = []
        
        # Common patterns for Credly badge cards
        possible_selectors = [
            ("div", {"class": lambda x: x and "badge" in " ".join(x).lower()}),
            ("div", {"class": lambda x: x and "card" in " ".join(x).lower()}),
            ("a", {"class": lambda x: x and "badge" in " ".join(x).lower()}),
            ("div", {"data-badge-id": True}),
        ]
        
        for tag, attrs in possible_selectors:
            containers = soup.find_all(tag, attrs)
            if containers:
                badge_containers = containers
                print(f"  Found {len(containers)} badges using {tag} with {attrs}")
                break
        
        if not badge_containers:
            print(f"  No badges found. Saving HTML for debugging...")
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(content)
        
        # Extract details from each badge
        for idx, card in enumerate(badge_containers):
            try:
                # Extract certification name
                cert_name = "N/A"
                name_tags = card.find_all(["h2", "h3", "h4", "div", "span"])
                for tag in name_tags:
                    text = tag.text.strip()
                    if text and len(text) > 5 and len(text) < 150:
                        # Skip common UI elements
                        if text.lower() not in ["view badge", "share", "download", "verify"]:
                            cert_name = text
                            break
                
                # Extract dates - look for date-related text
                cert_date = "N/A"
                cert_expiry = "N/A"
                
                # Search for date patterns in text
                all_text = card.get_text(separator=" | ")
                text_parts = [p.strip() for p in all_text.split("|")]
                
                for part in text_parts:
                    part_lower = part.lower()
                    if "issued" in part_lower or "earned" in part_lower:
                        cert_date = part
                    elif "expires" in part_lower or "expiration" in part_lower:
                        cert_expiry = part
                
                # Look for time elements
                time_elements = card.find_all("time")
                if len(time_elements) >= 1:
                    cert_date = time_elements[0].get("datetime", time_elements[0].text.strip())
                if len(time_elements) >= 2:
                    cert_expiry = time_elements[1].get("datetime", time_elements[1].text.strip())
                
                if cert_name != "N/A":
                    certifications.append({
                        "Certification Name": cert_name,
                        "Certification Date": cert_date,
                        "Certification Expiry Date": cert_expiry
                    })
            
            except Exception as e:
                print(f"  Error parsing badge {idx}: {str(e)}")
                continue
        
        print(f"  Extracted {len(certifications)} certifications")
        return {"Name": name, "Certifications": certifications}
    
    except TimeoutException:
        print(f"  Timeout waiting for page elements")
        return {"Name": "N/A", "Certifications": [], "Error": "Timeout"}
    
    except Exception as e:
        print(f"  Error: {str(e)}")
        return {"Name": "N/A", "Certifications": [], "Error": str(e)}
    
    finally:
        driver.quit()


def scrape_credly_alternative(url):
    """
    Alternative approach using Selenium's direct element finding.
    This method inspects the page structure dynamically.
    """
    service = Service(executable_path="/Users/sam/Documents/Langgraph/CertAnalysis/lgcertenv/chromedriver")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        #print(f"  Loading page...")
        driver.get(url)
        
        # Wait and scroll
        #wait = WebDriverWait(driver, 20)
        wait = WebDriverWait(driver, 5) # Added by Sam
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Find name
        name = "N/A"
        try:
            # Try multiple XPath patterns for name
            name_xpaths = [
                "//h1[contains(@class, 'profile')]",
                "//h1",
                "//*[contains(@class, 'user-name')]",
            ]
            for xpath in name_xpaths:
                try:
                    name_elem = driver.find_element(By.XPATH, xpath)
                    if name_elem.text.strip():
                        name = name_elem.text.strip()
                        #print(f"  Found name: {name}")
                        break
                except:
                    continue
        except Exception as e:
            print(f"  Could not find name: {str(e)}")
        
        # Find badges
        certifications = []
        try:
            # Try to find badge elements
            badge_xpaths = [
                "//*[contains(@class, 'badge') and contains(@class, 'card')]",
                #"//*[contains(@class, 'badges') and contains(@class, 'card')]", # Added by Sam
                "//*[contains(@data-badge-id, '')]",
                "//a[contains(@href, '/badges/')]",
            ]
            
            badge_elements = []
            for xpath in badge_xpaths:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    if elements:
                        badge_elements = elements
                        #print(f"  Found {len(elements)} badge elements")
                        break
                except:
                    continue
            
            for badge in badge_elements[:5]:  # Limit to first 20 badges
                try:
                    cert_user_name = badge.text.split("\n")[1] # Added by Sam later
                    #print("Certification Company : ",cert_user_name) # Added by Sam
                    cert_issue_date = badge.text.split("\n")[2] # Added by Sam later
                    #print("Certification Issue Data : ",cert_issue_date) # Added by Sam
                    cert_expiry_date = badge.text.split("\n")[3] # Added by Sam later
                    #print("Certification Issue Data : ",cert_expiry_date) # Added by Sam
                    cert_date2 = badge.text.split("\n")[4] # Added by Sam later
                    #print("Certification Issue Data : ",cert_date2) # Added by Sam
                    cert_date3 = badge.text.split("\n")[5] # Added by Sam later
                    #print("Certification Issue Data : ",cert_date3) # Added by Sam
                    cert_name = badge.text.split("\n")[6] # Added by Sam later
                    #print("Certification Issue Data : ",cert_name) # Added by Sam
                    #print("Badge Text :", badge.text.split("\n"))
                    #cert_name = badge.get_attribute("title") or badge.text.split("\n")[0] or "N/A"
                    certifications.append({
                        "Certification Name": cert_name.strip(),
                        #"Certification Date": "N/A",
                        "User Name": cert_user_name.split()[5:],
                        "Certification Issue Date": cert_issue_date, # Added by Sam
                        "Certification Expiry Date": cert_expiry_date
                    })
                except:
                    continue
        
        except Exception as e:
            print(f"  Error finding badges: {str(e)}")
        
        #print(f"  Extracted {len(certifications)} certifications")
        return {"Name": name, "Certifications": certifications}
    
    finally:
        driver.quit()


# Main execution
if __name__ == "__main__":
    #import sys
    
    #if len(sys.argv) < 2:
    #    print(json.dumps({"error": "No URL provided"}))
    #    sys.exit(1)
    
    #url = sys.argv[1]  # Get URL from command line argument
    #data = scrape_credly_alternative(url)
    
    # Print as JSON to stdout
    #print(json.dumps(data))
    #urls = [
       # "https://www.credly.com/users/cladius/badges",
       # "https://www.credly.com/users/tushar-ghorpade/badges",
     #   "https://www.credly.com/badges/90ee2ee9-f6cf-4d9b-8a52-f631d8644d58",
    #]
    
    #print("Starting Credly scraping...")
    #print("=" * 60)
    
    #for url in urls:
    #print(f"\nScraping: {url}")
    #print("-" * 60)
        
        # Try primary method
        #data = scrape_credly(url)
    #data = scrape_credly_alternative(url)
    data = scrape_credly_alternative("https://www.credly.com/badges/e192db17-f8c5-46aa-8f99-8a565223f1d6?")
        
        # If no certifications found, try alternative method
        #if not data.get("Certifications"):
        #    print("  Trying alternative scraping method...")
        #    data = scrape_credly_alternative(url)
        
    #print(f"\nResults for {url}:")
    #print(json.dumps(data, indent=2))
    #print("=" * 60)
