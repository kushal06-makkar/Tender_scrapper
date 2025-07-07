from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
import pandas as pd
from deep_translator import GoogleTranslator
import os
import random
from selenium.webdriver.common.action_chains import ActionChains
import traceback
import logging

# Set up logging
logging.basicConfig(
    filename='scraping_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    driver = None
    try:
        logging.info("Starting script execution")
        print("Setting up Chrome driver...")
        chrome_options = Options()
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--ignore-certificate-errors')
        # Add user agent to appear more like a real browser
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        print("Opening https://www.g2b.go.kr/ ...")
        driver.get("https://www.g2b.go.kr/")
        time.sleep(5)
        print("Page loaded. Waiting for 'bid' menu item...")
        wait = WebDriverWait(driver, 40)
        
        # Take screenshot of initial page
        driver.save_screenshot("initial_page.png")
        logging.info("Saved screenshot of initial page")
        
        try:
            bid_menu = None
            try:
                logging.info("Trying to find bid menu by ID")
                bid_menu = wait.until(
                    EC.element_to_be_clickable((By.ID, "mf_wfm_gnb_wfm_gnbMenu_genDepth1_1_btn_menuLvl1"))
                )
                logging.info("Found bid menu by ID")
            except Exception as e:
                logging.warning(f"Could not find bid menu by ID: {e}")
                print(f"Could not find bid menu by ID, trying alternative selectors: {e}")
                try:
                    logging.info("Trying to find bid menu by XPath")
                    bid_menu = wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'bid') or contains(text(), '입찰')]"))
                    )
                    logging.info("Found bid menu by XPath")
                except Exception as e2:
                    logging.warning(f"Could not find bid menu by XPath: {e2}")
                    print(f"Could not find bid menu by XPath either: {e2}")
                    
                    # Try to find all menu items and log them for debugging
                    menu_items = driver.find_elements(By.TAG_NAME, "a")
                    logging.info(f"Found {len(menu_items)} menu items")
                    print(f"Found {len(menu_items)} menu items, first 10 are:")
                    for i, item in enumerate(menu_items[:10]):
                        text = item.text
                        id_attr = item.get_attribute('id')
                        print(f"Menu item {i}: '{text}' - ID: '{id_attr}'")
                        logging.info(f"Menu item {i}: '{text}' - ID: '{id_attr}'")
                        
                    # Try to find by partial text match (case insensitive)
                    logging.info("Trying to find menu items with partial text match")
                    potential_menu_items = []
                    for item in menu_items:
                        text = item.text.lower()
                        if 'bid' in text or '입찰' in text or 'tender' in text:
                            potential_menu_items.append(item)
                    
                    if potential_menu_items:
                        logging.info(f"Found {len(potential_menu_items)} potential menu items")
                        print(f"Found {len(potential_menu_items)} potential menu items")
                        bid_menu = potential_menu_items[0]
            
            if not bid_menu:
                raise Exception("Could not find bid menu element")
            
            print("Clicking 'bid' menu item...")
            bid_menu.click()
            print("Clicked 'bid' menu item.")
            
            # Take screenshot after clicking bid menu
            driver.save_screenshot("after_bid_menu_click.png")
            logging.info("Saved screenshot after clicking bid menu")
            
            submenu_id = "mf_wfm_gnb_wfm_gnbMenu_genDepth1_1_genDepth2_0_genDepth3_0_btn_menuLvl3"
            print("Waiting for 'List of bid announcements' submenu item...")
            submenu = wait.until(
                EC.element_to_be_clickable((By.ID, submenu_id))
            )
            print("Clicking 'List of bid announcements' submenu item...")
            submenu.click()
            print("Clicked 'List of bid announcements' submenu item.")
            
            # Take screenshot after clicking submenu
            driver.save_screenshot("after_submenu_click.png")
            logging.info("Saved screenshot after clicking submenu")
            
            # Check for any modal popups and close them
            try:
                modal_close_buttons = driver.find_elements(By.XPATH, "//div[contains(@class, 'w2modal_popup')]//button[contains(@class, 'close')]")
                if modal_close_buttons:
                    print(f"Found {len(modal_close_buttons)} modal close buttons, attempting to close...")
                    for button in modal_close_buttons:
                        if button.is_displayed():
                            button.click()
                            print("Clicked modal close button")
                            time.sleep(1)
            except Exception as e:
                print(f"Error handling modal popups: {e}")
            
            checkbox_id = "mf_wfm_container_tacBidPbancLst_contents_tab2_body_chkSlprRcptDdlnYn_input_0"
            print("Waiting for 'Excluding bid deadline' checkbox...")
            checkbox = wait.until(
                EC.presence_of_element_located((By.ID, checkbox_id))
            )
            
            # Try to use JavaScript to click the checkbox instead of direct click
            try:
                driver.execute_script("arguments[0].click();", checkbox)
                print("Checked 'Excluding bid deadline' checkbox using JavaScript.")
            except Exception as e:
                print(f"JavaScript click failed: {e}, trying direct click")
                if not checkbox.is_selected():
                    print("Checking 'Excluding bid deadline' checkbox...")
                    checkbox.click()
                    print("Checked 'Excluding bid deadline' checkbox.")
                else:
                    print("'Excluding bid deadline' checkbox is already checked.")
                
            search_btn_id = "mf_wfm_container_tacBidPbancLst_contents_tab2_body_btnS0004"
            print("Waiting for 'Search' button...")
            search_btn = wait.until(
                EC.presence_of_element_located((By.ID, search_btn_id))
            )
            print("Clicking 'Search' button...")
            
            # Try JavaScript click for search button
            try:
                driver.execute_script("arguments[0].click();", search_btn)
                print("Clicked 'Search' button using JavaScript.")
            except Exception as e:
                print(f"JavaScript click failed: {e}, trying direct click")
                search_btn.click()
                print("Clicked 'Search' button.")
            
            # Take screenshot after search
            driver.save_screenshot("after_search.png")
            logging.info("Saved screenshot after search")
            
            dropdown_id = "mf_wfm_container_tacBidPbancLst_contents_tab2_body_sbxRecordCountPerPage1"
            print("Waiting for 'No of tenders visible' dropdown...")
            dropdown = wait.until(
                EC.presence_of_element_located((By.ID, dropdown_id))
            )
            select = Select(dropdown)
            print("Selecting '100' tenders per page...")
            select.select_by_visible_text("100")
            print("Selected '100' tenders per page.")
            
            apply_btn_id = "mf_wfm_container_tacBidPbancLst_contents_tab2_body_btnAplcn1"
            print("Waiting for 'apply' button...")
            apply_btn = wait.until(
                EC.presence_of_element_located((By.ID, apply_btn_id))
            )
            print("Clicking 'apply' button...")
            
            # Try JavaScript click for apply button
            try:
                driver.execute_script("arguments[0].click();", apply_btn)
                print("Clicked 'apply' button using JavaScript.")
            except Exception as e:
                print(f"JavaScript click failed: {e}, trying direct click")
                apply_btn.click()
                print("Clicked 'apply' button.")
                
            print("Waiting for table to load...")
            time.sleep(5)
            
            # Find the scrollable element
            scroll_element_id = "mf_wfm_container_tacBidPbancLst_contents_tab2_body_gridView1_scrollY_div"
            scroll_element = wait.until(
                EC.presence_of_element_located((By.ID, scroll_element_id))
            )
            print("Found scrollable element")
            
            # Find the table
            table_xpath = "//table[contains(@id, 'gridView1_body_table')]"
            table = wait.until(
                EC.presence_of_element_located((By.XPATH, table_xpath))
            )
            
            # Extract data function
            def extract_table_data():
                rows = table.find_elements(By.TAG_NAME, "tr")
                data = []
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    data.append([col.text for col in cols])
                # Remove empty rows
                data = [row for row in data if any(cell.strip() for cell in row)]
                return data

            # Helper to get unique row id (Tender Notice Number or fallback)
            def get_row_id(row):
                return row[5] if len(row) > 5 else str(row)

            # Function to process and save data in batches
            def process_and_save_data(data, start_idx, end_idx, batch_num=None):
                if not data or start_idx >= len(data) or start_idx >= end_idx:
                    return
                rows_to_process = data[start_idx:end_idx]
                valid_rows = [row for row in rows_to_process if len(row) > 9]
                if not valid_rows:
                    return
                no_column = [row[0] for row in valid_rows]
                division_column = [row[1] for row in valid_rows]
                tender_notice_number_column = [row[5] for row in valid_rows]
                announcement_name_column = [row[6] for row in valid_rows]
                announcement_agency_column = [row[7] for row in valid_rows]
                # Split publishing date and bid closing date
                publishing_date_column = []
                bid_closing_date_column = []
                for row in valid_rows:
                    date_text = row[9]
                    if '(' in date_text and ')' in date_text:
                        try:
                            publishing_date = date_text.split('(')[0].strip()
                            bid_closing_date = date_text.split('(')[1].replace(')', '').strip()
                            publishing_date_column.append(publishing_date)
                            bid_closing_date_column.append(bid_closing_date)
                        except:
                            publishing_date_column.append(date_text)
                            bid_closing_date_column.append("")
                    else:
                        publishing_date_column.append(date_text)
                        bid_closing_date_column.append("")
                country_name_column = ['South Korea'] * len(no_column)
                website_link_column = ['https://www.g2b.go.kr/'] * len(no_column)
                # Translate relevant columns to English
                translator = GoogleTranslator(source='auto', target='en')
                def safe_translate(x):
                    try:
                        if x and x != 'nan':
                            return translator.translate(x)
                        return x
                    except Exception as e:
                        print(f"Error translating '{x}': {e}")
                        return x
                batch_size = 50
                for i in range(0, len(division_column), batch_size):
                    end = min(i + batch_size, len(division_column))
                    division_column[i:end] = [safe_translate(x) for x in division_column[i:end]]
                for i in range(0, len(announcement_name_column), batch_size):
                    end = min(i + batch_size, len(announcement_name_column))
                    announcement_name_column[i:end] = [safe_translate(x) for x in announcement_name_column[i:end]]
                for i in range(0, len(announcement_agency_column), batch_size):
                    end = min(i + batch_size, len(announcement_agency_column))
                    announcement_agency_column[i:end] = [safe_translate(x) for x in announcement_agency_column[i:end]]
                df = pd.DataFrame({
                    'No': no_column,
                    'Division': division_column,
                    'Tender Notice Number': tender_notice_number_column,
                    'Announcement Name': announcement_name_column,
                    'Announcement Agency': announcement_agency_column,
                    'Publishing Date': publishing_date_column,
                    'Bid Closing Date': bid_closing_date_column,
                    'Country Name': country_name_column,
                    'Website Link': website_link_column
                })
                os.makedirs('tenders/south.korea', exist_ok=True)
                if batch_num is not None:
                    filename = f"tenders/south.korea/batch_{batch_num}.xlsx"
                    df.to_excel(filename, index=False)
                    print(f"Saved {len(df)} rows to {filename}")
                else:
                    filename = "tenders/south.korea/initial_100.xlsx"
                    df.to_excel(filename, index=False)
                    print(f"Saved initial {len(df)} rows to {filename}")

            # --- Main extraction logic ---
            all_data = []
            processed_ids = set()
            batch_count = 0
            print("Extracting initial data...")
            data = extract_table_data()
            for row in data:
                row_id = get_row_id(row)
                if row_id not in processed_ids:
                    all_data.append(row)
                    processed_ids.add(row_id)
            print(f"Initially found {len(all_data)} unique rows")
            # Save first 100 tenders (or all if less than 100)
            process_and_save_data(all_data, 0, min(100, len(all_data)), batch_num=None)
            previous_data_count = min(100, len(all_data))
            # Scroll and extract more data
            max_attempts = 100
            no_new_data_count = 0
            max_no_new_data = 5
            for attempt in range(max_attempts):
                print(f"Scroll attempt {attempt+1}, current rows: {len(all_data)}")
                current_scroll = driver.execute_script("return arguments[0].scrollTop", scroll_element)
                scroll_amount = 300
                driver.execute_script(f"arguments[0].scrollTop = {current_scroll + scroll_amount}", scroll_element)
                print(f"Scrolled from {current_scroll} to {current_scroll + scroll_amount}")
                time.sleep(10)
                data = extract_table_data()
                new_data = []
                for row in data:
                    row_id = get_row_id(row)
                    if row_id not in processed_ids:
                        new_data.append(row)
                        processed_ids.add(row_id)
                if new_data:
                    print(f"Found {len(new_data)} new unique rows")
                    all_data.extend(new_data)
                    no_new_data_count = 0
                    # Save new data in batches of 10
                    while previous_data_count + 10 <= len(all_data):
                        batch_count += 1
                        process_and_save_data(all_data, previous_data_count, previous_data_count + 10, batch_num=batch_count)
                        previous_data_count += 10
                else:
                    no_new_data_count += 1
                    print(f"No new unique data found ({no_new_data_count}/{max_no_new_data})")
                    if no_new_data_count >= max_no_new_data:
                        print("Reached end of data, stopping scrolling")
                        break
            # Save any remaining data that didn't make a full batch
            if previous_data_count < len(all_data):
                batch_count += 1
                process_and_save_data(all_data, previous_data_count, len(all_data), batch_num=batch_count)
            
        except Exception as e:
            print(f"Could not complete menu navigation, checkbox selection, or search: {e}")
            logging.error(f"Could not complete menu navigation, checkbox selection, or search: {e}")
            logging.error(traceback.format_exc())
            # Save screenshot for debugging
            if driver:
                screenshot_file = "error_screenshot.png"
                driver.save_screenshot(screenshot_file)
                print(f"Saved error screenshot to {screenshot_file}")
                logging.info(f"Saved error screenshot to {screenshot_file}")
        print("Press Enter to close the browser...")
        input()
    except Exception as e:
        print(f"An error occurred: {e}")
        logging.error(f"An error occurred: {e}")
        logging.error(traceback.format_exc())
        if driver:
            screenshot_file = "fatal_error_screenshot.png"
            driver.save_screenshot(screenshot_file)
            print(f"Saved fatal error screenshot to {screenshot_file}")
            logging.info(f"Saved fatal error screenshot to {screenshot_file}")
    finally:
        if driver:
            driver.quit()
        print("Browser closed.")
        logging.info("Browser closed. Script execution complete.")

if __name__ == "__main__":
    main()
