from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
import os
from datetime import datetime
import re

def standardize_datetime(date_string):
    """Convert various date/time formats to dd-mm-yyyy and hh-mm-ss format"""
    # Remove any leading/trailing whitespace and commas
    date_string = date_string.strip().strip(',')
    
    # Initialize variables
    date_part = ""
    time_part = ""
    
    # First try to separate time if it exists (looking for patterns like "17:00" or "17 : 00")
    time_match = re.search(r'(\d{1,2}\s*:\s*\d{2})', date_string)
    if time_match:
        time_str = time_match.group(1)
        # Remove the time from the date string
        date_string = date_string.replace(time_str, '').strip().strip(',').strip()
        # Standardize time format
        time_parts = re.findall(r'\d+', time_str)
        if len(time_parts) >= 2:
            hours = time_parts[0].zfill(2)
            minutes = time_parts[1].zfill(2)
            time_part = f"{hours}-{minutes}-00"  # Adding 00 for seconds
    
    # Try different date formats
    try:
        # Remove any extra spaces between components and standardize separators
        date_string = re.sub(r'\s+', ' ', date_string)
        date_string = re.sub(r'[.,]', '', date_string)  # Remove periods and commas
        
        # Common Japanese date format: Reiwa X Year Month Day
        reiwa_match = re.search(r'(?:Reiwa|令和)\s*(\d+)\s*(?:Year|年)\s*(\d+)\s*(?:Month|月)\s*(\d+)\s*(?:Day|日)', date_string)
        if reiwa_match:
            reiwa_year = int(reiwa_match.group(1))
            month = int(reiwa_match.group(2))
            day = int(reiwa_match.group(3))
            # Convert Reiwa year to Gregorian (Reiwa 1 = 2019)
            gregorian_year = 2018 + reiwa_year
            return f"{str(day).zfill(2)}-{str(month).zfill(2)}-{str(gregorian_year)}"
        
        # Try different date formats
        date_formats = [
            '%d %B %Y',
            '%d %b %Y',
            '%B %d %Y',
            '%b %d %Y',
            '%Y/%m/%d',
            '%d/%m/%Y',
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%Y年%m月%d日',  # Japanese format
            '%Y.%m.%d',
            '%d.%m.%Y',
            '%m/%d/%Y',
            '%d %m %Y',
            '%Y %m %d'
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_string, fmt)
                date_part = parsed_date.strftime('%d-%m-%Y')
                break
            except ValueError:
                continue
        
        if not date_part:
            # Try to extract components for more flexible parsing
            # Look for patterns like "2 July, 2025" or "July 2, 2025"
            components = re.findall(r'(\d{1,4}|[A-Za-z]+)', date_string)
            if len(components) >= 3:
                year = None
                month = None
                day = None
                
                # Process each component
                for comp in components:
                    # Check for year (4 digits)
                    if comp.isdigit() and len(comp) == 4:
                        year = int(comp)
                    # Check for month name
                    elif comp.isalpha() and len(comp) >= 3:
                        try:
                            month = datetime.strptime(comp[:3], '%b').month
                        except ValueError:
                            try:
                                month = datetime.strptime(comp, '%B').month
                            except ValueError:
                                continue
                    # Check for day (1-2 digits)
                    elif comp.isdigit() and len(comp) <= 2:
                        day = int(comp)
                
                # If we found all components, format the date
                if year and month and day:
                    date_part = f"{str(day).zfill(2)}-{str(month).zfill(2)}-{str(year)}"
    
    except Exception as e:
        print(f"Error parsing date: {e}")
    
    # Return formatted date and time
    if date_part and time_part:
        return f"{date_part} {time_part}"
    elif date_part:
        return f"{date_part}"
    elif time_part:
        return f"{time_part}"
    return date_string  # Return original string if parsing failed

def extract_time_limit(text):
    """Extract time limit information from the summary text using regex"""
    time_limits = []
    
    # Clean the text by removing unnecessary HTML tags and normalizing spaces
    text = re.sub(r'<(?!br|/br)[^>]+>', ' ', text)  # Keep <br> tags for splitting
    text = re.sub(r'\s+', ' ', text)
    
    # Split text by <br> tags to process line by line
    lines = re.split(r'<br\s*/?>', text)
    
    # First look for comment submission deadline in the specific format
    comment_patterns = [
        (r'[⑴-⑽]\s*Time\s*limit\s*for\s*(?:the\s*)?submission\s*of\s*comments\s*:\s*([^<>\n]+)', 'Comment Submission'),
        (r'[⑴-⑽]\s*Comment\s*deadline\s*:\s*([^<>\n]+)', 'Comment Deadline'),
        (r'[⑴-⑽]\s*Comments\s*due\s*by\s*:\s*([^<>\n]+)', 'Comments Due'),
        (r'[⑴-⑽]\s*Comment\s*period\s*(?:ends|closes)\s*:\s*([^<>\n]+)', 'Comment Period End')
    ]
    
    for line in lines:
        for pattern, label in comment_patterns:
            comment_match = re.search(pattern, line, re.IGNORECASE)
            if comment_match:
                comment_deadline = comment_match.group(1).strip()
                if comment_deadline and comment_deadline.lower() != 'none':
                    # Standardize the date/time format
                    formatted_deadline = standardize_datetime(comment_deadline)
                    time_limits.append(f"{label}: {formatted_deadline}")
    
    # Pattern to match time-limit for the tender entries
    tender_patterns = [
        # Electronic bidding patterns
        (r'[⑴-⑽]\s*Term\s*for\s*(?:the\s*)?submission\s*of\s*tenders?\s*by\s*electronic\s*bidding\s*system[^:]*:\s*([^<>\n]+)', 'Electronic Bidding'),
        (r'[⑴-⑽]\s*Electronic\s*bidding\s*(?:period|term|deadline)[^:]*:\s*([^<>\n]+)', 'Electronic Bidding'),
        (r'[⑴-⑽]\s*E-bidding\s*(?:period|term|deadline)[^:]*:\s*([^<>\n]+)', 'Electronic Bidding'),
        (r'[⑴-⑽]\s*Online\s*submission\s*(?:period|term|deadline)[^:]*:\s*([^<>\n]+)', 'Electronic Bidding'),
        
        # Specific tender submission patterns
        (r'[⑴-⑽]\s*Time-limit\s*for\s*the\s*tender\s*\(Mailing\)[^:]*:\s*([^<>\n]+)', 'Tender (Mailing)'),
        (r'[⑴-⑽]\s*Time-limit\s*for\s*the\s*tender\s*\(Bringing\)[^:]*:\s*([^<>\n]+)', 'Tender (Bringing)'),
        (r'[⑴-⑽]\s*Time-limit\s*for\s*(?:tender|submission|application)[^:]*:\s*([^<>\n]+)', 'Tender'),
        (r'[⑴-⑽]\s*Time-limit\s*for\s*receipt\s*of\s*tenders[^:]*:\s*([^<>\n]+)', 'Tender Receipt'),
        (r'[⑴-⑽]\s*Time-limit\s*for\s*submission[^:]*:\s*([^<>\n]+)', 'Submission'),
        (r'[⑴-⑽]\s*Due\s*date[^:]*:\s*([^<>\n]+)', 'Due Date'),
        
        # Specific date patterns
        (r'[⑴-⑽]\s*Submission\s*deadline[^:]*:\s*([^<>\n]+)', 'Submission Deadline'),
        (r'[⑴-⑽]\s*Application\s*deadline[^:]*:\s*([^<>\n]+)', 'Application Deadline'),
        (r'[⑴-⑽]\s*Closing\s*date[^:]*:\s*([^<>\n]+)', 'Closing Date'),
        (r'[⑴-⑽]\s*Expiration\s*date[^:]*:\s*([^<>\n]+)', 'Expiration Date'),
        (r'[⑴-⑽]\s*Tender\s*closing\s*date[^:]*:\s*([^<>\n]+)', 'Tender Closing Date'),
        (r'[⑴-⑽]\s*Bid\s*closing\s*date[^:]*:\s*([^<>\n]+)', 'Bid Closing Date'),
        
        # Specific time patterns
        (r'[⑴-⑽]\s*Time\s*of\s*tender[^:]*:\s*([^<>\n]+)', 'Tender Time'),
        (r'[⑴-⑽]\s*Time\s*of\s*submission[^:]*:\s*([^<>\n]+)', 'Submission Time'),
        (r'[⑴-⑽]\s*Time\s*of\s*closing[^:]*:\s*([^<>\n]+)', 'Closing Time'),
        (r'[⑴-⑽]\s*Tender\s*closing\s*time[^:]*:\s*([^<>\n]+)', 'Tender Closing Time'),
        (r'[⑴-⑽]\s*Bid\s*closing\s*time[^:]*:\s*([^<>\n]+)', 'Bid Closing Time'),
        
        # Combined date and time patterns
        (r'[⑴-⑽]\s*Deadline\s*for\s*(?:tender|submission)[^:]*:\s*([^<>\n]+)', 'Tender Deadline'),
        (r'[⑴-⑽]\s*Final\s*(?:date|time)[^:]*:\s*([^<>\n]+)', 'Final Date/Time'),
        (r'[⑴-⑽]\s*Last\s*(?:date|time)[^:]*:\s*([^<>\n]+)', 'Last Date/Time'),
        (r'[⑴-⑽]\s*Tender\s*(?:date|time)[^:]*:\s*([^<>\n]+)', 'Tender Date/Time'),
        (r'[⑴-⑽]\s*Bid\s*(?:date|time)[^:]*:\s*([^<>\n]+)', 'Bid Date/Time')
    ]
    
    # Look for tender time limits
    for line in lines:
        for pattern, label in tender_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                time_limit = match.group(1).strip()
                if time_limit and time_limit.lower() != 'none':
                    # Standardize the date/time format
                    formatted_time_limit = standardize_datetime(time_limit)
                    time_limits.append(f"{label}: {formatted_time_limit}")
    
    # If no specific time limits found, try broader patterns
    if not time_limits:
        broader_patterns = [
            # Electronic bidding patterns
            (r'Term\s*for\s*(?:the\s*)?submission\s*(?:of\s*tenders?)?\s*by\s*electronic\s*bidding[^:]*:\s*([^<>\n]+)', 'Electronic bidding'),
            (r'Electronic\s*bidding\s*(?:period|term|deadline)[^:]*:\s*([^<>\n]+)', 'Electronic bidding'),
            (r'E-bidding\s*(?:period|term|deadline)[^:]*:\s*([^<>\n]+)', 'Electronic bidding'),
            (r'Online\s*submission\s*(?:period|term|deadline)[^:]*:\s*([^<>\n]+)', 'Online submission'),
            
            # General time limit patterns
            (r'Time-limit[^:]*:\s*([^<>\n]+)', 'Time-limit'),
            (r'Deadline[^:]*:\s*([^<>\n]+)', 'Deadline'),
            (r'Due\s*date[^:]*:\s*([^<>\n]+)', 'Due date'),
            (r'Submission\s*date[^:]*:\s*([^<>\n]+)', 'Submission date'),
            
            # Additional date patterns
            (r'Closing\s*date[^:]*:\s*([^<>\n]+)', 'Closing date'),
            (r'End\s*date[^:]*:\s*([^<>\n]+)', 'End date'),
            (r'Expiry\s*date[^:]*:\s*([^<>\n]+)', 'Expiry date'),
            (r'Tender\s*date[^:]*:\s*([^<>\n]+)', 'Tender date'),
            (r'Bid\s*date[^:]*:\s*([^<>\n]+)', 'Bid date'),
            
            # Additional time patterns
            (r'Closing\s*time[^:]*:\s*([^<>\n]+)', 'Closing time'),
            (r'End\s*time[^:]*:\s*([^<>\n]+)', 'End time'),
            (r'Final\s*time[^:]*:\s*([^<>\n]+)', 'Final time'),
            (r'Tender\s*time[^:]*:\s*([^<>\n]+)', 'Tender time'),
            (r'Bid\s*time[^:]*:\s*([^<>\n]+)', 'Bid time'),
            
            # Date/time combinations
            (r'(?:Date|Time)\s*of\s*submission[^:]*:\s*([^<>\n]+)', 'Submission date/time'),
            (r'(?:Date|Time)\s*of\s*closing[^:]*:\s*([^<>\n]+)', 'Closing date/time'),
            (r'(?:Date|Time)\s*of\s*tender[^:]*:\s*([^<>\n]+)', 'Tender date/time'),
            (r'(?:Date|Time)\s*of\s*bid[^:]*:\s*([^<>\n]+)', 'Bid date/time'),
            
            # Additional combinations
            (r'Tender\s*(?:closing|end)\s*(?:date|time)[^:]*:\s*([^<>\n]+)', 'Tender closing'),
            (r'Bid\s*(?:closing|end)\s*(?:date|time)[^:]*:\s*([^<>\n]+)', 'Bid closing'),
            (r'Submission\s*(?:closing|end)\s*(?:date|time)[^:]*:\s*([^<>\n]+)', 'Submission closing')
        ]
        
        for line in lines:
            for pattern, label in broader_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    time_limit = match.group(1).strip()
                    if time_limit and time_limit.lower() != 'none':
                        # Standardize the date/time format
                        formatted_time_limit = standardize_datetime(time_limit)
                        time_limits.append(f"{label}: {formatted_time_limit}")
    
    if time_limits:
        # Remove duplicates while preserving order
        unique_limits = []
        for limit in time_limits:
            if limit not in unique_limits:
                unique_limits.append(limit)
        return " | ".join(unique_limits)
    
    return "Not specified"

def extract_detail_info(driver, title_element):
    """Extract detailed information by clicking on the tender title"""
    print(f"Clicking on title: {title_element.text[:50]}...")
    
    # Store the current window handle
    main_window = driver.current_window_handle
    
    try:
        # Click on the title to open the detail page
        title_element.click()
        time.sleep(3)
        
        # Switch to the new window if one opened
        all_windows = driver.window_handles
        detail_window = None
        for window in all_windows:
            if window != main_window:
                detail_window = window
                break
        
        if detail_window:
            driver.switch_to.window(detail_window)
            time.sleep(3)
        
        # Get the current URL after clicking
        detail_url = driver.current_url
        print(f"Detail page URL: {detail_url}")
        
        detail_info = {
            'Detail URL': detail_url,
            'Time Limit': "Not specified"
        }
        
        try:
            print("Searching for time limit information...")
            
            # Look for the summary cell that contains time limit information
            # Try different CSS selectors to find the relevant content
            selectors = [
                "table.elem_table_basic td",
                "table.search-detail td",
                "div.search-detail td",
                "table td"
            ]
            
            found_time_limit = False
            for selector in selectors:
                if found_time_limit:
                    break
                    
                summary_cells = driver.find_elements(By.CSS_SELECTOR, selector)
                for cell in summary_cells:
                    cell_text = cell.get_attribute('innerHTML')
                    if not cell_text:
                        continue
                    
                    # Extract time limits from the cell text
                    time_limit = extract_time_limit(cell_text)
                    if time_limit != "Not specified":
                        if detail_info['Time Limit'] == "Not specified":
                            detail_info['Time Limit'] = time_limit
                        else:
                            detail_info['Time Limit'] += f" | {time_limit}"
                        found_time_limit = True
                        break
            
        except Exception as e:
            print(f"Error extracting time limit: {e}")
        
        # Try to find any documents or attachments
        document_links = []
        try:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='pdf'], a[href*='doc'], a[href*='xls']")
            for link in links:
                doc_url = link.get_attribute("href")
                doc_text = link.text.strip()
                if doc_url and doc_text:
                    document_links.append({"text": doc_text, "url": doc_url})
        except:
            pass
        
        if document_links:
            detail_info["Document Links"] = document_links
        
        # Close the detail window and switch back to the main window
        if detail_window:
            driver.close()
            driver.switch_to.window(main_window)
        
    except Exception as e:
        print(f"Error extracting detail information: {e}")
        # Make sure we're back on the main window
        for window in driver.window_handles:
            if window == main_window:
                driver.switch_to.window(main_window)
                break
    
    return detail_info

def scrape_japan_tenders(start_page=1, end_page=1):
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    # Uncomment the line below if you want to run Chrome in headless mode
    # chrome_options.add_argument("--headless")
    
    # Initialize the Chrome driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # Base URL without pagination
    base_url = "https://www.jetro.go.jp/en/database/procurement/national/list.html?type=&from=&to=&entity=&area=&keyword=&classification1=&classification2=&classification3=&deadline="
    
    # Navigate to the JETRO government procurement website with starting page
    initial_url = f"{base_url}&_page={start_page}"
    print(f"Opening URL: {initial_url}")
    
    try:
        driver.get(initial_url)
        print("Successfully loaded the page")
        
        # Wait for the page to load completely
        time.sleep(5)
        
        # Get the page title to verify we're on the right page
        page_title = driver.title
        print(f"Page title: {page_title}")
        
        # Process each page from start_page to end_page
        current_page = start_page
        
        while current_page <= end_page:
            print(f"Processing page {current_page} of {end_page}")
            current_url = f"{base_url}&_page={current_page}"
            
            # Initialize page-specific tender data list
            page_tender_data = []
            
            try:
                # If not on the first page iteration, navigate to the current page
                if current_page != start_page or current_page > start_page:
                    driver.get(current_url)
                    time.sleep(3)
                
                # Wait for the table to be present using the correct CSS selector
                table = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.elem_table_basic.spv table.var_base_color"))
                )
                
                # Find all rows in the table (excluding the hidden template row)
                rows = table.find_elements(By.CSS_SELECTOR, "tbody tr:not([style*='display:none'])")
                
                print(f"Found {len(rows)} rows in the table on page {current_page}")
                
                # Process each row to get basic and detailed information
                tenders_per_page = len(rows)
                tenders_with_time_limit = 0
                
                for i in range(tenders_per_page):
                    # Refresh the page to avoid stale element references
                    if i > 0:
                        driver.get(current_url)
                        time.sleep(3)
                        
                        # Re-locate the table and rows
                        table = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.elem_table_basic.spv table.var_base_color"))
                        )
                        rows = table.find_elements(By.CSS_SELECTOR, "tbody tr:not([style*='display:none'])")
                    
                    # Get the current row
                    row = rows[i]
                    
                    # Skip if this is the template row
                    if "local_results_template" in row.get_attribute("id") and "display: none" in row.get_attribute("style"):
                        continue
                    
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 4:
                        # Extract data from each cell using the data-role attributes
                        raw_publishing_date = cells[0].find_element(By.CSS_SELECTOR, "span[data-role='date']").text.strip()
                        # Standardize the publishing date format
                        publishing_date = standardize_datetime(raw_publishing_date)
                        procurement_entity = cells[1].find_element(By.CSS_SELECTOR, "span[data-role='info']").text.strip()
                        notice_type = cells[2].find_element(By.CSS_SELECTOR, "span[data-role='cate']").text.strip()
                        
                        # For the title, we need to get the element to click on it
                        title_cell = cells[3]
                        title = title_cell.text.strip()
                        
                        # Get the title link element
                        detail_link_element = None
                        try:
                            detail_link_element = title_cell.find_element(By.TAG_NAME, "a")
                        except:
                            print(f"No link found for tender: {title[:50]}...")
                            continue
                        
                        # Store the basic data
                        tender_info = {
                            'Publishing Date': publishing_date,
                            'Procurement Entity': procurement_entity,
                            'Type of Notice': notice_type,
                            'Title': title,
                            'Country': 'Japan',
                            'Website Link': current_url
                        }
                        
                        print(f"Processing tender {i+1}/{tenders_per_page} on page {current_page}")
                        
                        # Click on the title and extract detailed information
                        if detail_link_element:
                            detail_info = extract_detail_info(driver, detail_link_element)
                            
                            # Only add tenders with specified time limits
                            if detail_info.get('Time Limit') != "Not specified":
                                # Merge basic and detailed information
                                tender_info = {**tender_info, **detail_info}
                                page_tender_data.append(tender_info)
                                tenders_with_time_limit += 1
                
                # Save the data for this page to Excel
                if page_tender_data:
                    df = pd.DataFrame(page_tender_data)
                    
                    # Handle document links column which contains lists
                    if 'Document Links' in df.columns:
                        df['Document Links'] = df['Document Links'].apply(lambda x: str(x) if isinstance(x, list) else x)
                    
                    # Create timestamp for the filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_file = f"japan_tenders_page_{current_page}_{timestamp}.xlsx"
                    df.to_excel(output_file, index=False)
                    print(f"Data for page {current_page} saved to {os.path.abspath(output_file)}")
                    print(f"Found {tenders_with_time_limit} tenders with specified time limits on page {current_page}")
                else:
                    print(f"No tenders with specified time limits found on page {current_page}")
                
                # Move to the next page
                current_page += 1
                
            except Exception as e:
                print(f"Error processing page {current_page}: {e}")
                current_page += 1  # Try to continue with the next page even if there was an error
            
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        # Close the browser
        driver.quit()
        print("Browser closed")

if __name__ == "__main__":
    START_PAGE = int(input("enter starting page no:")) 
    END_PAGE = int(input("enter ending page no:")) 
    
    print(f"Scraping tenders from page {START_PAGE} to page {END_PAGE}")
    scrape_japan_tenders(start_page=START_PAGE, end_page=END_PAGE)