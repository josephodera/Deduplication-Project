A Python-based pipeline to clean, normalize, and deduplicate business contact data.  
Outputs include:
- Updated master list
- HubSpot-ready contacts CSV
- Possible matches for review
- Log reports

## Features
 Normalize business names, addresses, websites, and phone numbers  
 Fuzzy matching with weighted similarity scoring  
 Identify duplicates, possibles, and unique records  
 Append uniques to master list automatically  
 Generate HubSpot-ready CSV with valid E.164 phone numbers  
 Export results to a single combined PDF report  


## Usage
1. Clone the repo:

git clone https://github.com/josephodera/Deduplication_Project.git
cd Deduplication_Project
**Install dependencies:**
   pip install -r requirements.txt
   Place your input files into data/:

   master_list.csv

   new_scraped_data.csv

**Run deduplication:
**

    dedup.py


**Example Output**
results/updated_master_YYYYMMDD.xlsx

    results/hubspot_ready_new_uniques_YYYYMMDD.csv

    results/possibles_YYYYMMDD.csv

    results/report_YYYYMMDD.txt


**Tech Stack**
   Python

   Pandas

   ReportLab
