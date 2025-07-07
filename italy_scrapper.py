from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
from datetime import datetime
import os
from deep_translator import GoogleTranslator

def setup_driver():
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    
    # Set up the Chrome driver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def wait_for_angular(driver):
    """Wait for Angular to finish processing and for page to be fully loaded"""
    try:
        script = """
        return (window.jQuery != null) && (jQuery.active === 0) && 
               (typeof angular === 'undefined' || !angular.element(document).injector() || 
                angular.element(document).injector().get('$http').pendingRequests.length === 0);
        """
        WebDriverWait(driver, 20).until(lambda driver: driver.execute_script(script))
    except:
        WebDriverWait(driver, 20).until(
            lambda driver: driver.execute_script('return document.readyState') == 'complete'
        )

def select_rdo_aperte(driver):
    try:
        print("Waiting for page to be fully loaded...")
        wait_for_angular(driver)
        
        wait = WebDriverWait(driver, 20)
        
        try:
            rdo_checkbox = wait.until(
                EC.presence_of_element_located((By.ID, 'checkbox3'))
            )
            print("Found RDO checkbox by ID")
        except TimeoutException:
            rdo_checkbox = wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    'input#checkbox3[data-ng-click="filtra(\'RDO APERTE\')"]'
                ))
            )
            print("Found RDO checkbox by full selector")

        wait.until(EC.element_to_be_clickable((By.ID, rdo_checkbox.get_attribute('id'))))
        
        try:
            rdo_checkbox.click()
            print("Clicked RDO checkbox normally")
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", rdo_checkbox)
            print("Clicked RDO checkbox using JavaScript")
        
        print("Waiting for page update...")
        time.sleep(10)
        wait_for_angular(driver)
        print("Page update complete")
        
    except Exception as e:
        print(f"Error while selecting RDO option: {str(e)}")
        print("Debug info:")
        print(f"Current URL: {driver.current_url}")
        print(f"Page title: {driver.title}")
        raise e

def get_total_pages(driver):
    """Get the total number of pages"""
    try:
        wait = WebDriverWait(driver, 10)
        pagination = wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "ul.pagination li a.ng-binding")
        ))
        # Get all page numbers and find the maximum
        page_numbers = []
        for page in pagination:
            try:
                num = int(page.text.strip())
                page_numbers.append(num)
            except ValueError:
                continue
        return max(page_numbers) if page_numbers else 1
    except Exception as e:
        print(f"Error getting total pages: {str(e)}")
        return 1

def go_to_page(driver, page_number):
    """Navigate to a specific page"""
    try:
        print(f"\nNavigating to page {page_number}...")
        wait = WebDriverWait(driver, 10)
        
        # Find and click the page number
        page_link = wait.until(EC.presence_of_element_located(
            (By.XPATH, f"//a[contains(@ng-click, 'selectPage') and contains(text(), '{page_number}')]")
        ))
        
        # Scroll the page link into view
        driver.execute_script("arguments[0].scrollIntoView(true);", page_link)
        time.sleep(1)  # Short pause after scrolling
        
        # Click the page link
        try:
            page_link.click()
        except:
            driver.execute_script("arguments[0].click();", page_link)
        
        # Wait for page to load
        time.sleep(5)
        wait_for_angular(driver)
        print(f"Successfully navigated to page {page_number}")
        return True
    except Exception as e:
        print(f"Error navigating to page {page_number}: {str(e)}")
        return False

# Translation function
def translate_text(text, source='it', target='en'):
    """Translate text from Italian to English."""
    if not text or not isinstance(text, str) or text == "N/A":
        return text
    
    # Skip translation for numeric or very short strings
    if text.isdigit() or len(text) < 2:
        return text
    
    try:
        # Split long text to handle Google Translator's character limit
        if len(text) > 4000:  # Google Translator has a limit
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

def extract_tender_details(driver):
    """Extract tender details from the page"""
    print("Extracting tender details...")
    wait = WebDriverWait(driver, 20)
    
    # Store the main page URL
    main_page_url = driver.current_url
    print(f"Main page URL: {main_page_url}")
    
    # Wait for the list container to be present
    list_container = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.listVetrina.col-sm-12.nopadding.ng-scope"))
    )
    print("Found main list container")
    
    # Find all tender rows
    tender_rows = driver.find_elements(By.CSS_SELECTOR, "div.listVetrina.col-sm-12.nopadding.ng-scope")
    print(f"Found {len(tender_rows)} tender rows")
    
    if len(tender_rows) == 0:
        print("No tender rows found.")
        return []
    
    # STEP 1: First collect all basic information from tenders
    print("\n--- STEP 1: Collecting basic tender information ---")
    tenders_basic_info = []
    
    for index, row in enumerate(tender_rows, 1):
        try:
            tender={}
            # N.RDO
            try:
                n_rdo = row.find_element(
                    By.CSS_SELECTOR, 
                    "div.stato.borderElenco.nopadding.col-sm-1 p.regular-14"
                ).text.strip()
                tender['N.RDO'] = n_rdo
                print(f"N.RDO: {n_rdo}")
            except NoSuchElementException as e:
                print(f"Error finding N.RDO: {str(e)}")
                tender['N.RDO'] = "N/A"
            
            # Description
            try:
                # Find the description element based on the HTML structure provided
                description_element = row.find_element(
                    By.CSS_SELECTOR, 
                    "div.borderElenco p.semibold.semibold-16-sm.ellipsis a.ng-binding"
                )
                description = description_element.text.strip()
                tender['DESCRIPTION'] = description
                print(f"Description: {description}")
                
                # Store the description element's href for later use
                try:
                    href = description_element.get_attribute('href')
                    tender['description_href'] = href
                    print(f"Description href: {href}")
                except:
                    tender['description_href'] = None
                    print("Could not get description href")
                
            except NoSuchElementException as e:
                print(f"Error finding description: {str(e)}")
                tender['DESCRIPTION'] = "N/A"
                tender['description_href'] = None
            
            # Product Area
            try:
                product_area = row.find_element(
                    By.CSS_SELECTOR, 
                    "div.listaCatIniz div.regular.responsiveText16 strong"
                ).text.strip()
                tender['PRODUCT AREA'] = product_area
                print(f"Product Area: {product_area}")
            except NoSuchElementException as e:
                print(f"Error finding product area: {str(e)}")
                tender['PRODUCT AREA'] = "N/A"
            
            # Contracting Entity
            try:
                entity = row.find_element(
                    By.CSS_SELECTOR, 
                    "div.stato.borderElenco.nopadding.col-sm-2 div[style*='font-size:12px']"
                ).text.strip()
                tender['CONTRACTING ENTITY'] = entity
                print(f"Contracting Entity: {entity}")
            except NoSuchElementException as e:
                print(f"Error finding contracting entity: {str(e)}")
                tender['CONTRACTING ENTITY'] = "N/A"
            
            # Value
            try:
                value = row.find_element(
                    By.CSS_SELECTOR, 
                    "div.stato.borderElenco.nopadding.col-sm-2.col-md-1 div.regular-14"
                ).text.strip()
                tender['VALUE'] = value if value else "Not specified"
                print(f"Value: {value}")
            except NoSuchElementException as e:
                print(f"Error finding value: {str(e)}")
                tender['VALUE'] = "N/A"
            
            # Published On (using hidden-sm hidden-md version for consistent date format)
            try:
                published = row.find_element(
                    By.CSS_SELECTOR, 
                    "div.stato.borderElenco.nopadding div.hidden-sm.hidden-md"
                ).text.strip()
                tender['PUBLISHED ON'] = published
                print(f"Published On: {published}")
            except NoSuchElementException as e:
                print(f"Error finding published date: {str(e)}")
                tender['PUBLISHED ON'] = "N/A"
            
            # Expires On (using hidden-sm hidden-md version for consistent date format)
            try:
                expires = row.find_element(
                    By.CSS_SELECTOR, 
                    "div.stato.nopadding.noBorderElenco div.hidden-sm.hidden-md"
                ).text.strip()
                tender['EXPIRES ON'] = expires
                print(f"Expires On: {expires}")
            except NoSuchElementException as e:
                print(f"Error finding expiry date: {str(e)}")
                tender['EXPIRES ON'] = "N/A"
            
            # Add website link and country
            tender['Website Link'] = "https://www.acquistinretepa.it/opencms/opencms/vetrina_bandi.html?filter=CO#!#post_call_position"
            tender['Country'] = "Italy"
            
            # Add to the list of tenders with basic info
            tenders_basic_info.append(tender)
            print(f"✓ Successfully collected basic info for tender {index}")
            
        except Exception as e:
            print(f"Error collecting basic info for tender {index}: {str(e)}")
            continue
    
    print(f"\nSuccessfully collected basic info for {len(tenders_basic_info)} tenders")
    
    # STEP 2: Extract document links for each tender
    print("\n--- STEP 2: Extracting document links ---")
    for index, tender in enumerate(tenders_basic_info, 1):
        try:
            print(f"\nExtracting document link for tender {index}: {tender['N.RDO']} - {tender['DESCRIPTION'][:30]}...")
            
            # If we have a direct href, we can use it
            if tender['description_href']:
                print(f"Using stored href: {tender['description_href']}")
                
                # Open the link in a new tab
                driver.execute_script(f"window.open('{tender['description_href']}', '_blank');")
                
                # Switch to the new tab
                driver.switch_to.window(driver.window_handles[-1])
                
                # Wait for page to load
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(2)  # Additional wait to ensure page is fully loaded
                
                # Get the document URL
                document_link = driver.current_url
                tender['Document page Link'] = document_link
                print(f"Document page Link: {document_link}")
                
                # Close the tab and switch back to main window
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                
            else:
                # If we don't have a direct href, we need to find the tender on the page again
                print("No stored href, finding tender on page again...")
                
                # Wait for the tender rows to be loaded
                tender_rows = WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.listVetrina.col-sm-12.nopadding.ng-scope"))
                )
                
                # Find the tender row with matching N.RDO
                found = False
                for row in tender_rows:
                    try:
                        n_rdo_element = row.find_element(By.CSS_SELECTOR, "div.stato.borderElenco.nopadding.col-sm-1 p.regular-14")
                        if n_rdo_element.text.strip() == tender['N.RDO']:
                            print(f"Found tender with N.RDO {tender['N.RDO']} on page")
                            
                            # Find the description link
                            description_element = row.find_element(
                                By.CSS_SELECTOR, 
                                "div.borderElenco p.semibold.semibold-16-sm.ellipsis a.ng-binding"
                            )
                            
                            # Scroll the element into view and click it
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", description_element)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", description_element)
                            
                            # Wait for page to load
                            WebDriverWait(driver, 15).until(
                                lambda d: d.execute_script("return document.readyState") == "complete"
                            )
                            time.sleep(2)  # Additional wait to ensure page is fully loaded
                            
                            # Get the document URL
                            document_link = driver.current_url
                            tender['Document page Link'] = document_link
                            print(f"Document page Link: {document_link}")
                            
                            # Go back to the main page
                            driver.get(main_page_url)
                            WebDriverWait(driver, 15).until(
                                lambda d: d.execute_script("return document.readyState") == "complete"
                            )
                            time.sleep(2)  # Wait for main page to reload
                            
                            found = True
                            break
                    except:
                        continue
                
                if not found:
                    print(f"Could not find tender with N.RDO {tender['N.RDO']} on page")
                    tender['Document page Link'] = "Not found"
        
        except Exception as e:
            print(f"Error extracting document link for tender {index}: {str(e)}")
            tender['Document page Link'] = f"Error: {str(e)}"
            
            # Try to return to the main page if there was an error
            try:
                # Close all tabs except the first one
                current_handle = driver.current_window_handle
                for handle in driver.window_handles:
                    if handle != driver.window_handles[0]:
                        driver.switch_to.window(handle)
                        driver.close()
                
                # Switch back to the main tab
                driver.switch_to.window(driver.window_handles[0])
                
                # Go back to the main page
                driver.get(main_page_url)
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(2)
            except:
                print("Error returning to main page")
    
    # STEP 3: Translate tender information to English
    print("\n--- STEP 3: Translating tender information to English ---")
    
    # Fields to translate
    fields_to_translate = ['DESCRIPTION', 'PRODUCT AREA', 'CONTRACTING ENTITY']
    
    for index, tender in enumerate(tenders_basic_info, 1):
        print(f"\nTranslating tender {index}: {tender['N.RDO']}...")
        
        # Translate each field
        for field in fields_to_translate:
            if field in tender and tender[field] != "N/A":
                try:
                    original_text = tender[field]
                    translated_text = translate_text(original_text)
                    tender[field] = translated_text
                    print(f"✓ Translated {field}")
                except Exception as e:
                    print(f"✗ Failed to translate {field}: {str(e)}")
    
    # Remove the temporary field used for processing
    for tender in tenders_basic_info:
        if 'description_href' in tender:
            del tender['description_href']
    
    print(f"\nSuccessfully processed {len(tenders_basic_info)} tenders")
    return tenders_basic_info

def save_to_excel(tenders, page_number):
    """Save tender details to Excel file"""
    if not tenders:
        print(f"No tender details to save for page {page_number}!")
        return
    
    # Create output directory if it doesn't exist
    output_dir = "tender_details"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"italy_tender_page{page_number}.xlsx")
    
    # Create DataFrame and save to Excel
    df = pd.DataFrame(tenders)
    df.to_excel(filename, index=False)
    print(f"\nTender details for page {page_number} saved to {filename}")
    
    # Display summary
    print(f"\nExtracted Tenders Summary for Page {page_number}:")
    print(f"Total tenders found: {len(tenders)}")
    print("\nFirst few records:")
    print(df.head().to_string())

def main():
    # Get starting page number from user
    while True:
        try:
            start_page = int(input("Enter the starting page number (1 or greater): "))
            if start_page < 1:
                print("Please enter a number greater than or equal to 1")
                continue
            break
        except ValueError:
            print("Please enter a valid number")
    
    url = "https://www.acquistinretepa.it/opencms/opencms/vetrina_bandi.html?filter=CO#!#post_call_position"
    
    try:
        driver = setup_driver()
        
        print("Opening the website...")
        driver.get(url)
        
        # Select RDO APERTE
        select_rdo_aperte(driver)
        
        # Get total number of pages
        total_pages = get_total_pages(driver)
        print(f"\nTotal pages found: {total_pages}")
        
        # Process each page starting from start_page
        for page_num in range(start_page, total_pages + 1):
            if page_num > start_page:
                # Navigate to the next page
                if not go_to_page(driver, page_num):
                    print(f"Failed to navigate to page {page_num}, stopping pagination")
                    break
            
            # Extract and save tender details for current page
            tenders = extract_tender_details(driver)
            save_to_excel(tenders, page_num)
            
            print(f"\nCompleted processing page {page_num} of {total_pages}")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        if 'driver' in locals():
            print(f"Final URL: {driver.current_url}")
    
    finally:
        try:
            if 'driver' in locals():
                driver.quit()
        except:
            pass

if __name__ == "__main__":
    main() 