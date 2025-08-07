from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import requests
import time

# Your 2Captcha API key (set this in your environment or config securely)
CAPTCHA_API_KEY = "YOUR_2CAPTCHA_API_KEY"  # Replace or inject via env var securely

def solve_recaptcha(site_key, url):
    # Submit CAPTCHA to 2Captcha
    print("Requesting CAPTCHA solution from 2Captcha...")
    payload = {
        'key': CAPTCHA_API_KEY,
        'method': 'userrecaptcha',
        'googlekey': site_key,
        'pageurl': url,
        'json': 1
    }
    response = requests.post('http://2captcha.com/in.php', data=payload).json()

    if response['status'] != 1:
        raise Exception(f"2Captcha error: {response['request']}")

    captcha_id = response['request']
    # Poll for result
    for i in range(20):
        time.sleep(5)
        res = requests.get(f"http://2captcha.com/res.php?key={CAPTCHA_API_KEY}&action=get&id={captcha_id}&json=1").json()
        if res['status'] == 1:
            print("CAPTCHA solved.")
            return res['request']
        elif res['request'] == 'CAPCHA_NOT_READY':
            print("Waiting for CAPTCHA to be solved...")
            continue
        else:
            raise Exception(f"Error solving CAPTCHA: {res['request']}")
    raise Exception("CAPTCHA solving timed out.")

def search_case(case_type, case_number, filing_year):
    """
    Scrape case details from a court website protected by Google reCAPTCHA v2.
    Using Selenium + 2Captcha service to handle CAPTCHA.
    Adjust selectors and URLs for your specific target court.
    """

    # Setup Chrome webdriver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run headless (no GUI)
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    try:
        # Example URL - Replace with the actual URL of the district court search page
        base_url = "https://example-court-website-with-captcha.com/case-search"

        driver.get(base_url)

        # Wait for page load
        wait = WebDriverWait(driver, 15)

        # Fill in form fields - update selectors according to the actual page structure:
        wait.until(EC.presence_of_element_located((By.NAME, 'case_type')))
        driver.find_element(By.NAME, 'case_type').send_keys(case_type)

        driver.find_element(By.NAME, 'case_number').send_keys(case_number)
        driver.find_element(By.NAME, 'filing_year').send_keys(filing_year)

        # Detect if CAPTCHA is on page
        # This sample expects reCAPTCHA div with class 'g-recaptcha'
        recaptcha_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'g-recaptcha')))

        site_key = recaptcha_element.get_attribute('data-sitekey')
        current_url = driver.current_url

        # Solve CAPTCHA via 2Captcha
        captcha_token = solve_recaptcha(site_key, current_url)

        # Inject CAPTCHA response token into textarea (reCAPTCHA response field)
        driver.execute_script(f'document.getElementById("g-recaptcha-response").style.display = "block";')
        driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML = "{captcha_token}";')
        driver.execute_script(f'document.getElementById("g-recaptcha-response").style.display = "none";')

        # Submit the form - update selector for submit button as per actual form
        submit_button = driver.find_element(By.ID, 'submit_button')
        submit_button.click()

        # Wait for results page to load (modify expected element)
        wait.until(EC.presence_of_element_located((By.ID, 'results')))

        page_source = driver.page_source

        # Parse page_source (you can use BeautifulSoup here as before)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')

        data = {}

        try:
            data['parties'] = soup.find('div', {'class': 'caseParty'}).get_text(strip=True)
        except Exception:
            data['parties'] = "Not found"

        try:
            data['filing_date'] = soup.find(text="Filing Date").find_next('td').text.strip()
        except Exception:
            data['filing_date'] = "N/A"

        try:
            data['next_hearing'] = soup.find(text="Next Date").find_next('td').text.strip()
        except Exception:
            data['next_hearing'] = "N/A"

        try:
            orders_section = soup.find('div', {'id': 'orders'})
            if orders_section:
                pdf_links = orders_section.find_all('a', href=True)
                if pdf_links:
                    data['recent_order_link'] = pdf_links[0]['href']
                    data['recent_order_text'] = pdf_links[0].text.strip()
                else:
                    data['recent_order_link'] = None
                    data['recent_order_text'] = "No order/judgment found."
            else:
                data['recent_order_link'] = None
                data['recent_order_text'] = "No order/judgment found."
        except Exception as e:
            data['recent_order_link'] = None
            data['recent_order_text'] = str(e)

        data['raw_html'] = page_source

        return data

    except Exception as e:
        return {"error": str(e), "html": ""}

    finally:
        driver.quit()
