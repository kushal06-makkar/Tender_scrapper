from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
from datetime import datetime
import re
from deep_translator import GoogleTranslator

def translate_text(text, source='mk', target='en'):
    """Translate text from source language to target language."""
    if not text or not isinstance(text, str):
        return text
    
    # Skip translation for numeric or very short strings
    if text.isdigit() or len(text) < 2:
        return text
    
    try:
        # Split long text to handle Google Translator's character limit
        if len(text) > 4000:  # Reduced to be safer
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            translated_chunks = []
            for chunk in chunks:
                translated = GoogleTranslator(source=source, target=target).translate(chunk)
                if translated:
                    translated_chunks.append(translated)
                else:
                    translated_chunks.append(chunk)
            return ' '.join(translated_chunks)
        else:
            translated = GoogleTranslator(source=source, target=target).translate(text)
            return translated if translated else text
    except Exception as e:
        print(f"Translation error: {str(e)} for text: '{text[:50]}...'")
        return text  # Return original text if translation fails

def setup_driver():
    
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_page_input(prompt, min_value, max_value=None):
    while True:
        try:
            value = input(prompt)
            if not value.strip() and max_value is not None:
                return max_value
            
            page_num = int(value)
            if page_num < min_value:
                print(f"Page number must be {min_value} or greater")
                continue
            if max_value and page_num > max_value:
                print(f"Page number cannot be greater than {max_value}")
                continue
            return page_num
        except ValueError:
            print("Please enter a valid number")

def change_ads_per_page(driver, items_per_page=25):
    try:
        wait = WebDriverWait(driver, 10)
        
        dropdown = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, 
            "div.MuiTablePagination-input div.MuiSelect-select"
        )))
        dropdown.click()
        time.sleep(1) 
        
        option_25 = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, 
            f'li[data-value="{items_per_page}"]'
        )))
        option_25.click()
        
        time.sleep(3)
        print(f"Changed items per page to {items_per_page}")
        return True
    except Exception as e:
        print(f"Error changing items per page: {str(e)}")
        return False

def get_total_pages(driver):
    try:
        wait = WebDriverWait(driver, 10)
        pagination_text = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.MuiTablePagination-root p.MuiTablePagination-caption:last-of-type")
        )).text
        
        # Extract total number using regex
        match = re.search(r'of (\d+)', pagination_text)
        if match:
            total_items = int(match.group(1))
            return (total_items + 24) // 25
    except Exception as e:
        print(f"Error getting total pages: {str(e)}")
        return None
    return None

def go_to_next_page(driver):
    try:
        wait = WebDriverWait(driver, 10)
        next_button = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR, 
            "div.MuiTablePagination-actions button[title='Next page']"
        )))
        
        if 'Mui-disabled' in next_button.get_attribute('class'):
            print("Next page button is disabled - reached last page")
            return False
            
        wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, 
            "div.MuiTablePagination-actions button[title='Next page']"
        )))
        
        next_button.click()
        time.sleep(3)  
        return True
    except Exception as e:
        print(f"Error navigating to next page: {str(e)}")
        return False

def extract_table_data(driver):
    wait = WebDriverWait(driver, 20)
    
    # Store the main page URL
    main_page_url = driver.current_url
    print(f"Main page URL: {main_page_url}")
    
    table_container = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "div.MuiTableContainer-root")
    ))
    
    # First collect basic tender information
    print("\n--- STEP 1: Collecting basic tender information ---")
    tenders_basic_info = []
    
    try:
        rows = table_container.find_elements(By.CSS_SELECTOR, "tbody tr.MuiTableRow-root")
        print(f"Found {len(rows)} rows")
        
        for row_index, row in enumerate(rows, 1):
            try:
                # Get the tender number and link
                number_cell = row.find_element(By.CSS_SELECTOR, "th.MuiTableCell-body")
                number_link = number_cell.find_element(By.TAG_NAME, "a")
                number = number_cell.text.strip()
                tender_link = number_link.get_attribute('href')
                
                cells = row.find_elements(By.CSS_SELECTOR, "td.MuiTableCell-body")
                
                if len(cells) >= 5:
                    deadline_str = cells[4].text.strip()
                    try:
                        # Check if deadline contains time information
                        if ' ' in deadline_str and len(deadline_str.split(' ')) == 2:
                            date_part, time_part = deadline_str.split(' ')
                            # Try to parse with time
                            try:
                                deadline_datetime = datetime.strptime(deadline_str, '%d.%m.%Y %H:%M:%S')
                                # Compare with current date and time
                                now = datetime.now()
                                if deadline_datetime < now:
                                    print(f"Skipping tender {number} - Deadline passed ({deadline_str})")
                                    continue
                            except ValueError:
                                # If specific time format fails, try other common formats
                                try:
                                    deadline_datetime = datetime.strptime(deadline_str, '%d.%m.%Y %H:%M')
                                    now = datetime.now()
                                    if deadline_datetime < now:
                                        print(f"Skipping tender {number} - Deadline passed ({deadline_str})")
                                        continue
                                except ValueError:
                                    # Fall back to just date comparison
                                    deadline_date = datetime.strptime(date_part, '%d.%m.%Y').date()
                                    today = datetime.now().date()
                                    if deadline_date < today:
                                        print(f"Skipping tender {number} - Deadline passed ({deadline_str})")
                                        continue
                        else:
                            # Just date without time
                            deadline_date = datetime.strptime(deadline_str, '%d.%m.%Y').date()
                            today = datetime.now().date()
                            if deadline_date < today:
                                print(f"Skipping tender {number} - Deadline passed ({deadline_str})")
                                continue
                        
                        # Store basic tender information
                        tender_info = {
                            'Number': number,
                            'Contracting Authority': cells[0].text.strip(),
                            'Subject of Procurement': cells[1].text.strip(),
                            'Type of Procurement': cells[2].text.strip(),
                            'Publication Date': cells[3].text.strip(),
                            'Deadline': deadline_str,
                            'Website Link': "https://e-pazar.gov.mk/activeTenders",
                            'Country': "Macedonia",
                            'Row Index': row_index
                        }
                        
                        tenders_basic_info.append(tender_info)
                        print(f"Collected basic info for tender {number}")
                        
                    except ValueError as e:
                        print(f"Error parsing date for tender {number}: {deadline_str} - {e}")
                        # Try alternate formats if needed
                        try:
                            formats_to_try = ['%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y']
                            for date_format in formats_to_try:
                                try:
                                    deadline_date = datetime.strptime(deadline_str, date_format).date()
                                    today = datetime.now().date()
                                    if deadline_date >= today:
                                        tender_info = {
                                            'Number': number,
                                            'Contracting Authority': cells[0].text.strip(),
                                            'Subject of Procurement': cells[1].text.strip(),
                                            'Type of Procurement': cells[2].text.strip(),
                                            'Publication Date': cells[3].text.strip(),
                                            'Deadline': deadline_str,
                                            'Website Link': "https://e-pazar.gov.mk/activeTenders",
                                            'Country': "Macedonia",
                                            'Row Index': row_index
                                        }
                                        tenders_basic_info.append(tender_info)
                                        print(f"Collected basic info for tender {number} with alternate date format")
                                    break
                                except ValueError:
                                    continue
                        except Exception as e:
                            print(f"Could not process tender with alternate format: {str(e)}")
                else:
                    print(f"Skipping row - insufficient cells: {len(cells)}")
                    
            except Exception as e:
                print(f"Error processing row {row_index}: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error processing table: {str(e)}")
    
    print(f"Collected basic info for {len(tenders_basic_info)} active tenders")
    
    # STEP 2: Get detailed tender URLs by clicking on each tender number
    print("\n--- STEP 2: Getting detailed tender URLs ---")
    
    for index, tender in enumerate(tenders_basic_info):
        try:
            print(f"\nGetting detailed URL for tender {tender['Number']}...")
            
            # Find the tender rows again
            rows = table_container.find_elements(By.CSS_SELECTOR, "tbody tr.MuiTableRow-root")
            
            if tender['Row Index'] <= len(rows):
                # Get the row for this tender
                row = rows[tender['Row Index'] - 1]
                
                # Find the number link in this row
                number_cell = row.find_element(By.CSS_SELECTOR, "th.MuiTableCell-body")
                number_link = number_cell.find_element(By.TAG_NAME, "a")
                
                # Store the current window handle
                main_window = driver.current_window_handle
                
                # Click on the number link
                print(f"Clicking on number link for tender {tender['Number']}...")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", number_link)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", number_link)
                
                # Wait for the page to load
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(2)
                
                # Get the URL of the tender detail page
                detail_url = driver.current_url
                tender['Detail URL'] = detail_url
                print(f"Got detail URL: {detail_url}")
                
                # Go back to the main page
                driver.get(main_page_url)
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(2)
                
                # Re-find the table container
                table_container = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.MuiTableContainer-root")
                ))
                
            else:
                print(f"Row index {tender['Row Index']} out of range. Total rows: {len(rows)}")
                tender['Detail URL'] = "Row not found"
                
        except Exception as e:
            print(f"Error getting detail URL for tender {tender['Number']}: {str(e)}")
            tender['Detail URL'] = f"Error: {str(e)}"
            
            # Try to return to the main page if there was an error
            try:
                driver.get(main_page_url)
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(2)
                table_container = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.MuiTableContainer-root")
                ))
            except:
                print("Error returning to main page")
    
    # STEP 3: Translate tender information
    print("\n--- STEP 3: Translating tender information ---")
    
    tenders_data = []
    for tender in tenders_basic_info:
        try:
            print(f"\nTranslating tender {tender['Number']}...")
            
            # Translate Contracting Authority
            try:
                contracting_authority_en = translate_text(tender['Contracting Authority'])
                print(f"✓ Translated Contracting Authority")
            except Exception as e:
                print(f"✗ Failed to translate Contracting Authority: {str(e)}")
                contracting_authority_en = tender['Contracting Authority']
                
            # Translate Subject of Procurement
            try:
                subject_en = translate_text(tender['Subject of Procurement'])
                print(f"✓ Translated Subject of Procurement")
            except Exception as e:
                print(f"✗ Failed to translate Subject of Procurement: {str(e)}")
                subject_en = tender['Subject of Procurement']
                
            # Translate Type of Procurement
            try:
                procurement_type_en = translate_text(tender['Type of Procurement'])
                print(f"✓ Translated Type of Procurement")
            except Exception as e:
                print(f"✗ Failed to translate Type of Procurement: {str(e)}")
                procurement_type_en = tender['Type of Procurement']
            
            # Create the final tender info with translations
            final_tender = {
                'Number': tender['Number'],
                'Contracting Authority': contracting_authority_en,
                'Subject of Procurement': subject_en,
                'Type of Procurement': procurement_type_en,
                'Publication Date': tender['Publication Date'],
                'Deadline': tender['Deadline'],
                'Website Link': tender['Website Link'],
                'Country': tender['Country'],
                'Detail URL': tender.get('Detail URL', 'N/A')
            }
            
            tenders_data.append(final_tender)
            print(f"✓ Successfully processed tender {tender['Number']}")
            
        except Exception as e:
            print(f"Error processing tender {tender.get('Number', 'unknown')}: {str(e)}")
    
    # Remove the temporary row index field
    for tender in tenders_data:
        if 'Row Index' in tender:
            del tender['Row Index']
    
    print(f"Successfully processed {len(tenders_data)} tenders")
    return tenders_data

def save_to_excel(data, page_number):
    if not data:
        print(f"No data to save for page {page_number}")
        return None
        
    df = pd.DataFrame(data)

    filename = f"Macedonia_tenders_page_{page_number}.xlsx"
    
    df.to_excel(filename, index=False)
    print(f"Data saved to {filename}")
    return filename

def navigate_to_page(driver, target_page):
    try:
        current_page = 1
        while current_page < target_page:
            print(f"Navigating to page {current_page + 1}...")
            if not go_to_next_page(driver):
                print(f"Could not navigate to page {target_page}")
                return False
            current_page += 1
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.MuiTableContainer-root")))
            time.sleep(2)  
        return True
    except Exception as e:
        print(f"Error navigating to page {target_page}: {str(e)}")
        return False

def main():
    driver = None
    try:
        driver = setup_driver()
        
        url = "https://e-pazar.gov.mk/activeTenders"
        print(f"Opening {url}...")
        driver.get(url)
        
        print("Waiting for page to load...")
        time.sleep(5)
        
        if not change_ads_per_page(driver, 25):
            print("Failed to change items per page, exiting...")
            return
            
        total_pages = get_total_pages(driver)
        if not total_pages:
            print("Could not determine total pages")
            return
        print(f"Total pages: {total_pages}")
        
        start_page = get_page_input(
            "Enter the starting page number (1 or greater, press Enter for 1): ",
            min_value=1,
            max_value=total_pages
        )
        
        end_page = get_page_input(
            f"Enter the end page number (press Enter for last page {total_pages}): ",
            min_value=start_page,
            max_value=total_pages
        )
        
        print(f"\nWill process pages {start_page} to {end_page}")
        
        if start_page > 1:
            print(f"Navigating to page {start_page}...")
            if not navigate_to_page(driver, start_page):
                return
        
        current_page = start_page
        while current_page <= end_page:
            print(f"\nProcessing page {current_page} of {end_page}")
            
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.MuiTableContainer-root")))
            time.sleep(2)  
            
            tenders_data = extract_table_data(driver)
            if tenders_data:
                filename = save_to_excel(tenders_data, current_page)
                print(f"Saved page {current_page} to {filename}")
            
            if current_page < end_page:
                if not go_to_next_page(driver):
                    print("Could not go to next page")
                    break
            
            current_page += 1
        
        print("\nFinished processing all pages")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
    finally:
        
        if driver:
            try:
                driver.quit()
                print("Browser closed successfully.")
            except:
                print("Browser already closed.")

if __name__ == "__main__":
    main() 