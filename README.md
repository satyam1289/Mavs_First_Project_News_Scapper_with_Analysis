<div align="center">

# 🌐 Enterprise News Analyzer & Media Intelligence Platform

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Streamlit App](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![AI Powered](https://img.shields.io/badge/AI-Gemini%20%7C%20Transformers-blueviolet.svg)](#)
[![Database](https://img.shields.io/badge/Database-SQLite-003B57.svg)](#)

*A production-ready, full-stack intelligence application that automates the collection, extraction, and deep AI-driven analysis of global news articles.*

</div>

---

## 📖 What is this project?

The **News Analyzer with Analytics** is a powerful tool designed for researchers, analysts, and businesses. Instead of manually searching and reading hundreds of news articles to understand public sentiment or track brand mentions, this platform does the heavy lifting for you.

You simply tell it what to look for (e.g., "Artificial Intelligence", "Electric Vehicles") and specify an optional date range. The system will automatically:
1. **Find** relevant news articles from the global GDELT database.
2. **Download** the text of those articles (bypassing blocks using advanced scraping and Tor proxies).
3. **Analyze** the text using Artificial Intelligence (AI) to:
   - Figure out if the news is **Positive, Negative, or Neutral** (Sentiment Analysis).
   - Identify specific **Companies, Brands, Locations, and People** mentioned (Named Entity Recognition).
   - Categorize the article into a **Business Sector** like Technology, Finance, or Healthcare (using Google's Gemini AI).
4. **Display** all these insights on a beautiful, interactive dashboard where you can filter data and see trends over time.

---

## ✨ Key Features at a Glance

- 🔐 **Secure Login System:** Personalized accounts keep your searches and databases secure.
- 📅 **Smart Searching:** Find exact articles by entering keywords and a specific timeframe.
- 🛡️ **Anti-Blocking Technology:** Uses smart scraping and the Tor network to ensure it can read articles even from strict websites.
- 🧠 **Deep AI Understanding:** Goes beyond searching words. It completely understands *who* is being talked about and *how* they are being talked about.
- 📈 **Interactive Dashboards:** Click through beautiful charts to see sentiment trends, top companies in the news, and sector breakdowns.
- 📥 **Excel Export:** Download all analysis data instantly into neat Excel spreadsheets for presentations or further offline work.

---

## ⚙️ How It Works (The Complete Workflow)

The system operates through a highly automated, step-by-step pipeline. Here is the visual workflow of how data travels from your search request to the final dashboard showing actionable intelligence:

```text
 ╭────────────────────────────────────────────────────────────────────────╮
 │                                                                        │
 │  1️⃣  USER INPUT & AUTHENTICATION                                         │
 │      • User logs securely into the Streamlit Web Interface.            │
 │      • User types in search Keywords (e.g., "Apple", "Google").        │
 │      • User selects a specific Date & Time Range.                      │
 │                                                                        │
 ╰──────────────────────────────────┬─────────────────────────────────────╯
                                    │
                                    ▼
 ╭────────────────────────────────────────────────────────────────────────╮
 │                                                                        │
 │  2️⃣  URL DISCOVERY (GDELT NETWORK)                                       │
 │      • The app contacts the GDELT open data project.                   │
 │      • It translates your keywords into a global news search.          │
 │      • It returns a raw list of News Article URLs matching your query. │
 │                                                                        │
 ╰──────────────────────────────────┬─────────────────────────────────────╯
                                    │
                                    ▼
 ╭────────────────────────────────────────────────────────────────────────╮
 │                                                                        │
 │  3️⃣  SMART ARTICLE DOWNLOADER (SCRAPER)                                  │
 │      • The app visits every URL in the list automatically.             │
 │      • It extracts the main headline and body text cleanly.            │
 │      • 🛡️ If a site blocks it, it actively rotates its IP address       │
 │        using the Tor Proxy Network to try again successfully.          │
 │                                                                        │
 ╰──────────────────────────────────┬─────────────────────────────────────╯
                                    │
                                    ▼
 ╭────────────────────────────────────────────────────────────────────────╮
 │                                                                        │
 │  4️⃣  THE AI "BRAIN" (NLP PROCESSING ENGINE)                              │
 │      ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄      │
 │      • Sentiment Analysis: Reads the text & calculates a score         │
 │        (Is this article Happy, Angry, or Neutral?).                    │
 │      • Named Entity Recognition (NER): Highlights specific Brands,     │
 │        Organizations, and Executives (using HuggingFace Transformers). │
 │      • Sector Classification: Sends the summary to Google Gemini AI    │
 │        to confidently label the industry (e.g., "Automotive", "Tech"). │
 │                                                                        │
 ╰──────────────────────────────────┬─────────────────────────────────────╯
                                    │
                                    ▼
 ╭────────────────────────────────────────────────────────────────────────╮
 │                                                                        │
 │  5️⃣  SECURE STORAGE (DATABASE)                                           │
 │      • All the downloaded text and AI insights are saved neatly        │
 │        into a local SQLite Database (articles.db).                     │
 │      • This means you never lose past searches.                        │
 │                                                                        │
 ╰──────────────────────────────────┬─────────────────────────────────────╯
                                    │
                                    ▼
 ╭────────────────────────────────────────────────────────────────────────╮
 │                                                                        │
 │  6️⃣  VISUAL DASHBOARD & REPORTING                                        │
 │      • The data flows back to your screen.                             │
 │      • You see graphs showing Sentiment over the last 7 days.          │
 │      • You see word clouds of the most talked-about companies.         │
 │      • 💾 Click 'Export to Excel' to download the final report.          │
 │                                                                        │
 ╰────────────────────────────────────────────────────────────────────────╯
```

---

## 🛠️ The Technology Stack

This project was built using robust, modern tools:

### Front-End (Interactive UI)
- **[Streamlit](https://streamlit.io/):** The core framework used to build the beautiful, Python-based web application dashboard quickly.

### Data Acquisition (Fetching & Scraping)
- **`feedparser` & `aiohttp`:** For fast, asynchronous fetching of internet data.
- **`beautifulsoup4` & `trafilatura`:** The core tools used to parse HTML web pages and cleanly extract just the readable text without ads or menus.
- **`stem` (Tor):** Used to route traffic through the Tor network to stop websites from blocking the scraper during heavy data collection.

### Artificial Intelligence & NLP (The Brains)
- **Google Generative AI (Gemini):** Used as an intelligent supervisor to read summaries and classify the news into correct business sectors.
- **HuggingFace `transformers` & `sentence-transformers`:** State-of-the-art Deep Learning models used to spot Brands and analyze the exact sentiment of sentences. (Powered by `PyTorch`).

### Data Logic & Storage
- **`pandas`:** The backbone for organizing the data into tables for easy filtering and graphing.
- **`sqlite3` (SQLite Database):** A lightweight database that stores user accounts (`users.db`) and all downloaded news data (`articles.db`) securely on your machine.
- **`xlsxwriter`:** Automatically formats and color-codes the exported Excel `.xlsx` reports.

---

## 📂 Understanding the Code Structure

If you want to look at the code, here is what each main file does:

| File Name | What it does |
| :--- | :--- |
| **`main.py`** | 🌟 The core application. This file builds the Streamlit user interface, the buttons, and the charts. Run this to start the app! |
| **`auth.py`** | 🔐 Handles user registration, secure password checking, and logging in. |
| **`db_manager.py`** | 🗄️ Manages reading and saving data to the SQLite databases. |
| **`gdelt_fetcher.py`** | 📡 Connects to the global GDELT database to find raw News URLs matching your keywords. |
| **`article_scraper.py`** | 🕷️ The web scraper. It goes to the URLs found by `gdelt_fetcher.py` and copies the story text. |
| **`tor_manager.py`** | 🧅 Controls the Tor proxy connection if the scraper needs to rotate its IP address. |
| **`advanced_ner_extractor.py`**| 🧠 The AI script that highlights specific Locations, People, and Brands in the text. |
| **`sector_classifier.py`** | 🤖 Sends data to Google Gemini AI to figure out what industry the article is about. |
| **`export_excel.py`** | 📊 Creates the downloadable Excel reports from your data. |

---

## 🚀 Getting Started (How to Run It)

Want to run this on your own machine? Follow these simple steps:

### 1. Requirements First
Make sure you have **Python 3.9 or higher** installed on your computer.

### 2. Open your Terminal & Setup the Virtual Environment
Navigate to the project folder and start the virtual environment so the app has an isolated space to run:

**On Windows:**
```powershell
.\venv\Scripts\Activate.ps1
```
*(If you are using Command Prompt, use `.\venv\Scripts\activate.bat`)*

**On Mac / Linux:**
```bash
source venv/bin/activate
```

### 3. Install the Necessary Packages
Install all the required libraries (like Streamlit, Pandas, and the AI models):
```bash
pip install -r requirements.txt
```

### 4. Provide your Google Gemini API Key
The sector classifier requires a Google Gemini Artificial Intelligence key.

*   Set it in your terminal before running the app:
    **Windows PowerShell:** `$env:GEMINI_API_KEY="your-api-key-here"`
    **Mac / Linux:** `export GEMINI_API_KEY="your-api-key-here"`

### 5. Launch the Application!
Start the Streamlit web server:
```bash
streamlit run main.py
```
🎉 **Success!** Your browser will automatically open to `http://localhost:8501`, and you can start analyzing the news!
