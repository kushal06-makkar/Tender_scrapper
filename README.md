
# Government Tender Scrapers 🌍

This project provides automated web scrapers for extracting public procurement tender data from four countries: **Italy, Japan, Macedonia, and South Korea**. Using Selenium and translation tools, it captures relevant tender information and exports the data into structured Excel files for further analysis.

## 🌐 Supported Countries

- 🇮🇹 **Italy** – [acquistinretepa.it](https://www.acquistinretepa.it)
- 🇯🇵 **Japan** – [JETRO Procurement Database](https://www.jetro.go.jp/en/database/procurement/national/)
- 🇲🇰 **Macedonia** – [e-pazar.gov.mk](https://e-pazar.gov.mk/activeTenders)
- 🇰🇷 **South Korea** – [g2b.go.kr](https://www.g2b.go.kr/)


M## 🔍 Features

- Automated scraping with Selenium WebDriver  
- Translates non-English tender data into English using `deep-translator`  
- Date/time formatting and deadline validation  
- Supports pagination, dynamic content loading, and modal handling  
- Exports data to Excel files for each country
  
## 📁 Folder Structure

├── italy_scrapper.py
├── japan_scrapper.py
├── macedonia_scrapper.py
├── southkorea_scrapper.py
├── /tenders/ # Output folder containing Excel files

## 🛠 Requirements

Install the dependencies using pip:
pip install selenium pandas openpyxl webdriver-manager deep-translator

Chrome and ChromeDriver must be installed.

🚀 Usage
Run any script individually:

bash
Copy
Edit
python italy_scrapper.py
python japan_scrapper.py
python macedonia_scrapper.py
python southkorea_scrapper.py
Each script will prompt for page range (if applicable) and save output Excel files in a local directory.

📌 Notes
Translation may fail for extremely long or malformed text.

South Korea scraper includes scrolling logic for dynamically loading data.

Macedonia scraper filters out expired tenders based on deadline validation.

📄 License
This project is released under the MIT License.

🤝 Contributing
Pull requests and suggestions are welcome! Feel free to fork and submit improvements.


Things to Note:

The scripts handle various date formats and languages.

Macedonian tenders are filtered to exclude expired entries.

The South Korea script scrolls through dynamically loading tables and saves data in batches.
