# About the Project
Data on the attendance of Philippine lawmakers during House of Representatives sessions is fragmented across hundreds of House Journals. 
This project used AI-assisted Python coding to extract attendance data from 178 House Journals, representing 178 days of attendance during the 19th Congress.

The raw data was then cleaned for missing dates and for inconsistencies. 
An Excel dashboard was then developed to summarize, visualize, and perform surface-level analysis on the data.

The project finds that when Present, Late, and On Official Business are counted as present, more than half of lawmakers have attendance rates of 92% or higher.
The project also finds a weak linear relationship between session attendance and legislative activity.

> [!TIP]
> **Want to check how your representative did during the 19th Congress?**
> Click the excel file named `19th Congress.xlsx` and download the raw file in order to easily navigate through the data.
> Once downloaded and opened, proceed to the Dashboard sheet.
> You will be inputting the Congressional District or Party-list of your interest in the cells with a light blue fill.
> After that, relevant data will show up in the Dashboard and Data Visualization sheet.

# What's in the Excel File
<img width="700" height="325" alt="image" src="https://github.com/user-attachments/assets/5dd8f329-6fb7-48bd-a7d0-a6923b5d945f"/>
<img width="700" height="170" alt="image" src="https://github.com/user-attachments/assets/c97139fb-5988-4a9c-9103-9c76a951a206" />
<img width="700" height="334" alt="image" src="https://github.com/user-attachments/assets/50b72c5c-6afb-460e-ac39-caf22983467b" />

Aside from the ones featured above, there are also 6 other charts and graphs that may or may not be interesting.
Finally, the raw data and cleaned data are also included in the Excel file.

# Other Files
`Attendance Checker.py` contains the code for the PDF scraper.

`The List.csv` is the template for the list of lawmakers used by the program to compile the data in the PDF into a CSV format.

`master_attendance.csv` is the raw file output of the PDF scraping program.

`clean_attendance.csv` is the cleaned version of the raw data.

`19th Congress.xlsx` is the public-facing dashboard for navigating the data.

`attendance_pdfs` is the folder that contains all of the 178 House Journals Appendices that hold the attendance record of the congressmen. 
Aside from the data on the number of bills authored/co-authored by a lawmaker, which I sourced from the website of Congress directly, all primary data are sourced from here. 

# Issues
(1) The most glaring issue is the fact that there is one file that the scraper is only able to partially read. That file is `J80-1RS-20230531.pdf`.
The program cannot read about 106 names on this file due to an erroneous "`" character inside the source PDF. The missed data was inputted manually.

(2) Due to a change in how the House Journals files are named during the third regular session, the program misdated several files. 
For example, Journal No. 31 in the third regular session started on 2025 January 14 but it was named `Journal-01577-20250113.pdf` when I downloaded it.
Since that's what they're named when I downloaded them, I kept the file name and the date. I don't think a one-day difference on some files affects the output much anyway.

> [!CAUTION]
> This dataset was extracted and processed from House Journals using an automated program that was built with the help of AI.
> While the data has been reviewed and cleaned for observed inconsistencies, some extraction or classification errors may remain. 
> The dataset should therefore be treated as a research and reference resource rather than an authoritative record. 
> Users are encouraged to consult the original House Journals when exact accuracy is required.

# Recommendation
To be honest, I would not go through this if there was a centralized database for my representative's attendance hosted in the website of the House of Representatives.
In addition, I actually originally wanted to see *what* my representative voted for and *how they voted*. 
I feel like that is the more high impact output that can be done with the House Journals. 
Unfortunately, all votes are not published, searching for them is a pain, and their organization in the Journals is all over the place.
I feel like PDF scraping is not possible for that but more of web scraping since the voting data is available on the website itself (just hidden as usual).

> [!IMPORTANT]
> This project was done for fun and for my own personal curiosity to the question "is my representative attending work?"
> As such, I will not be making a version for other Congresses (like the 18th or 20th) or maintaining the database (aside from corrections) in the future.

