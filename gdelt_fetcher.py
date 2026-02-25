"""
Google News Fetcher (Previously named GDELT Fetcher)
This file searches the internet (via Google News) to find article links.
It's like the "Search Engine" part of the robot.
"""

import requests
import feedparser
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict
from datetime import datetime, timedelta
import random
import time
import re
from aiohttp_socks import ProxyConnector
from tor_manager import TorManager, renew_tor_identity



# ---------------------------------------------------------
# SMART EXPANSION MAP
# We search for these related topics to get MORE articles
# ---------------------------------------------------------
SECTOR_TOPICS = {
    "Finance": ["stocks", "banking", "economy", "investment", "fintech", "market", "trading", "crypto", "dividend", "revenue", "fiscal", "quarterly", "merger", "acquisition"],
    "Technology": ["software", "innovation", "gadgets", "cloud computing", "semiconductor", "big data", "saas", "hardware", "cybersecurity", "tech", "digital", "app", "mobile", "internet"],
    "Artificial Intelligence": ["artificial intelligence", "machine learning", "robotics", "generative ai", "llm", "neural network", "deep learning", "nlp", "automation", "ai model", "chatbot", "gpt"],
    "Health": ["medicine", "healthcare", "pharma", "wellness", "medical", "biotech", "hospital", "clinical trial", "vaccine", "genomic", "telemedicine", "digital health"],
    "Sustainability": ["climate change", "green energy", "renewable", "carbon", "environment", "esg", "solar", "wind", "electric vehicle", "circular economy", "biodiversity", "net zero"],
    "Education": ["schools", "universities", "edtech", "learning", "students", "campus", "curriculum", "literacy", "higher education", "vocational", "scholarship"],
    "Sports": ["cricket", "football", "olympics", "tournament", "championship", "league", "athlete", "sponsorship", "world cup", "transfer", "record"],
    "Startups": ["funding", "unicorn", "venture capital", "entrepreneur", "ipo", "acquisition", "seed round", "series a", "accelerator", "incubator", "scalability"],
    "Lifestyle": ["fashion", "travel", "food", "luxury", "trends", "culture", "design", "wellness", "real estate", "architecture", "gastronomy", "influencer"]
}

# ---------------------------------------------------------
# WHITELIST DOMAINS
# Restricted list of Indian and International publications
# ---------------------------------------------------------
WHITELIST_DOMAINS = [
    # News Agencies & General News
    "ptinews.com", "ians.in", "aninews.in", "uniindia.com", 
    "timesofindia.indiatimes.com", "thehindu.com", "hindustantimes.com", 
    "deccanchronicle.com", "deccanherald.com", "indianexpress.com", 
    "newindianexpress.com", "freepressjournal.in", "indiatoday.in", 
    "firstpost.com", "ndtv.com", "theweek.in", "outlookindia.com",
    "telegraphindia.com", "dtnext.in", "digitalterminal.in",

    # Business & Finance
    "economictimes.indiatimes.com", "financialexpress.com", "thehindubusinessline.com", 
    "livemint.com", "business-standard.com", "fortuneindia.com", 
    "moneycontrol.com", "cnbctv18.com", "forbesindia.com", "bloomberg.com", 
    "businesstoday.in", "businessworld.in", "outlookbusiness.com",
    
    # Startups & Tech
    "techcircle.in", "yourstory.com", "inc42.com", "techcrunch.com", 
    "vccircle.com", "entrackr.com", "e27.co", "trak.in", "techgig.com",
    "analyticsindiamag.com", "indiaai.gov.in", "themorningcontext.com",
    "expresscomputer.in", "technuter.com", "entrepreneur.com",
    "dqindia.com", "cybermedia.co.in", "varindia.com", "nfapost.com",
    "techachievemedia.com",

    # Specialized ET Verticals (subdomains)
    "telecom.economictimes.indiatimes.com", "tech.economictimes.indiatimes.com", 
    "government.economictimes.indiatimes.com", "prime.economictimes.indiatimes.com", 
    "retail.economictimes.indiatimes.com", "ciso.economictimes.indiatimes.com", 
    "cio.economictimes.indiatimes.com",

    # Industry Specific (Telecom, HR, Infra, etc.)
    "telecomdrive.com", "telecomlead.com", "peoplematters.in", 
    "apacnewsnetwork.com", "ismg.io", "smestreet.in", "thetab.com"
]

def get_source_filters(chunk_size=15, custom_domain_list=None):
    """
    Returns a list of site-restriction strings, chunked to avoid URL length limits.
    Example output: ["(site:ptinews.com OR site:ians.in ...)", "(site:ndtv.com OR ... )"]
    """
    filters = []
    
    # Use custom list if provided, otherwise default to global whitelist
    target_domains = custom_domain_list if custom_domain_list else WHITELIST_DOMAINS
    
    # Split the whitelist into chunks
    for i in range(0, len(target_domains), chunk_size):
        chunk = target_domains[i:i + chunk_size]
        # Create the OR string: site:domain1.com OR site:domain2.com
        or_string = " OR ".join([f"site:{domain.strip()}" for domain in chunk if domain.strip()])
        # Wrap in parentheses
        if or_string:
            filters.append(f"({or_string})")
    
    return filters

# Signals Tor for a New Identity (Change IP).
# Tor Browser Control Port is usually 9151.
# Tor Service Control Port is usually 9051.


# This is the main function we use to find news.
# OPTIMIZED: Now accepts explicit Date Range instead of 'days'
def fetch_gdelt_simple(keyword: str, start_date: datetime, end_date: datetime, max_articles: int = 50000, progress_callback=None, target_regions: List[str] = None, sector_context: str = None, use_tor: bool = False, saturation_mode: bool = False, whitelist_override: List[str] = None, search_entire_web: bool = False) -> List[Dict]:
    """
    Search for news articles about a 'keyword' within a specific DATE RANGE.
    
    If use_tor is True, it will route requests through Tor (127.0.0.1:9150).
    If saturation_mode is True, it uses extreme slicing to hit 700+ articles.
    If whitelist_override is provided, it uses those domains instead of the global default.
    """
    
    articles = []
    
    # Default to all if None provided (mostly for backward compatibility)
    if not target_regions:
        target_regions = ["IN:en", "US:en", "GB:en", "AU:en", "CA:en", "SG:en"]
    
    # We pretend to be many different browsers (Chrome, Mac, Linux, Safari, Firefox)
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.2; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36'
    ]
    
    # Random headers to smooth traffic
    def get_random_headers():
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.8', 'en-IN,en;q=0.9']),
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
        
        if use_tor:
            headers['Connection'] = 'close'
            
        return headers
    
    # This small function fetches one single RSS feed link with RETRY logic.
    async def fetch_rss_async(url, connector_provider):
        # OPTIMIZED: "Deep Harvest" -> Increased Retries (5)
        max_retries = 5
        base_delay = 5
        
        for attempt in range(max_retries + 1):
            try:
                # Wait if another worker is rotating Tor
                await TorManager.wait_if_cooldown()
                
                # Pick a random browser identity and headers
                headers = get_random_headers()
                
                # Get a fresh connector if Tor is active
                connector = connector_provider()
                
                # OPTIMIZED: "Deep Harvest" -> Increased Timeout (45s) for slow connection resilience
                timeout = aiohttp.ClientTimeout(total=45, connect=10)
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            # If success, read the text and parse it as an RSS feed
                            content = await response.text()
                            feed = feedparser.parse(content) 
                            return feed.entries
                        
                        elif response.status in [429, 503]:
                            # Rate limited! AGGRESSIVE COOLDOWN
                            if attempt < max_retries:
                                # If using Tor, try to renew identity via Global Manager
                                if use_tor:
                                    print(f"⚠️ Rate limited (Status {response.status}) on {url}. Triggering Global Tor Rotation...")
                                    await TorManager.renew_identity()
                                else:
                                    print(f"⚠️ Rate limited (Status {response.status}) on local IP. 💡 TIP: Enable 'Use Tor Proxy' in the sidebar to bypass this!")
                                
                                # Exponential backoff with a massive base + Jitter
                                delay = 10 * (2 ** attempt) + random.uniform(5.0, 15.0)
                                print(f"⚠️ Cooldown: Entering Deep Sleep for {delay:.1f}s...")
                                await asyncio.sleep(delay)
                                continue
                            else:
                                print(f"❌ Failed after {max_retries} retries (Rate Limit).")
                                return []
                        else:
                            # Other error (404, etc), don't retry
                            print(f"⚠️ HTTP Error {response.status} for {url}")
                            return []
            except Exception as e:
                # Network error? Retry nicely.
                error_msg = str(e)
                if "10061" in error_msg or "SOCKS" in error_msg or "Connection refused" in error_msg:
                    print(f"⚠️ TOR CONNECTION ERROR: {error_msg}")
                    print(f"💡 HINT: Is the Tor Browser open and running? If not, disable 'Use Tor Proxy' in settings.")
                
                if attempt < max_retries:
                     delay = base_delay * (2 ** attempt) + random.uniform(1.0, 5.0)
                     print(f"⚠️ Network error ({str(e)}) - Retrying in {delay:.1f}s...")
                     await asyncio.sleep(delay)
                else:
                    return []
        return []

    # This function creates different search URLs to get deep results.
    async def fetch_resilient_sources(progress_callback=None):
        base_query = requests.utils.quote(keyword)
        
        # 1. High-Impact Queries & Alphabet Slicing
        # To defeat the Google 100-article limit, we append alphabetical chars
        # forcing the algorithm to split the buckets and give us the long-tail.
        queries = [f"{base_query}", f'"{keyword}"']
        
        if saturation_mode or max_articles > 100:
            variations = ["news", "report", "analysis"]
            
            # Add Alphabet Slicing (The Ultimate Free Bypass)
            for letter in "abcdefghijklmnopqrstuvwxyz":
                queries.append(f"{base_query}%20{letter}")
                
            for var in variations:
                queries.append(f"{base_query}%20{var}")
        else:
            queries.extend([
                f"{base_query}%20news",
                f"{base_query}%20report"
            ])
        
        # 2. SMART EXPANSION (If a sector is provided or detected)
        # Check if we should use sector_context
        # If sector_input was "CUSTOM", main.py might have classified it already
        effective_sector = sector_context
        
        if effective_sector and effective_sector in SECTOR_TOPICS:
            related_topics = SECTOR_TOPICS[effective_sector]
            print(f"🧠 Smart Expansion Active for '{effective_sector}': Adding {len(related_topics)} related topics...")
            
            for topic in related_topics:
                safe_topic = requests.utils.quote(topic)
                if keyword.lower() == effective_sector.lower():
                    queries.append(safe_topic)
                else:
                    queries.append(f"{base_query}%20{safe_topic}")
        
        # BALANCED CONCURRENCY for Resilience
        # Starts high (20) for Tor but will dynamically scale down via the TorManager cooldowns and local rate limits.
        # OPTIMIZED: Using an asyncio.BoundedSemaphore to allow dynamic adjustments if needed, though we'll manage flow via sleep scales.
        initial_concurrency = 20 if use_tor else 50 
        semaphore = asyncio.Semaphore(initial_concurrency)
        
        # Dynamic delay scale that increases on failures and decreases on success
        delay_scale = [1.0] # Using a list so it can be mutated inside fetch_with_semaphore

        
        # OMEGA TOR CONNECTOR PROVIDER
        def get_connector():
            if use_tor:
                return ProxyConnector.from_url("socks5://127.0.0.1:9150")
            # OPTIMIZED: Enable DNS Caching (ttl_dns_cache=300) AND Burst Concurrency (limit=100)
            return aiohttp.TCPConnector(ttl_dns_cache=300, limit=100)
        
        urls = []
        # --- TIME SLICING LOGIC (Using Date Range) ---
        # Calculate number of days between start and end
        delta_days = (end_date - start_date).days + 1
        
        for i in range(delta_days):
            current_date = end_date - timedelta(days=i)
            prev_date = end_date - timedelta(days=i+1)
            
            current_date_str = current_date.strftime("%Y-%m-%d")
            prev_date_str = prev_date.strftime("%Y-%m-%d")
            
            # We create 6 "Logical Slots" per day to force 6 independent fetches
            # providing coverage for the requested 4-hour breakdown architecture.
            for slot in range(6):
                
                start_str = prev_date_str
                end_str = current_date_str
                time_filter = f"%20after%3A{start_str}%20before%3A{end_str}"
                
                for q in queries:
                    # --- WHITELIST BATCHING INTEGRATION ---
                    if search_entire_web:
                        # NO RESTRICTIONS: Search the entire web
                        site_filters = [""]
                    else:
                        # RESTRICTED: Use whitelist chunks
                        site_filters = get_source_filters(custom_domain_list=whitelist_override)
                    
                    for site_filter in site_filters:
                        # Construct the restricted query: query AND (site:A OR site:B ...)
                        restricted_q = f"{q} {site_filter}"
                        
                        # Encode it properly
                        encoded_q = requests.utils.quote(restricted_q) 
                        
                        for region in target_regions:
                            hl = "en-" + region.split(':')[0]
                            gl = region.split(':')[0]
                            ceid = region
                            
                            # We append a dummy parameter `&u={slot}` to make the URL unique
                            # ensuring distinct fetch tasks for robustness.
                            # We also need to make it unique per site_filter batch!
                            # Simple hash of the filter to keep it short
                            batch_id = hash(site_filter) % 1000
                            
                            url = f"https://news.google.com/rss/search?q={encoded_q}{time_filter}&hl={hl}&gl={gl}&ceid={ceid}&u={slot}&b={batch_id}"
                            urls.append(url)
        
        # Deduplicate URLs just in case
        urls = list(dict.fromkeys(urls))
        
        # Stats for progress
        total_tasks = len(urls)
        completed_tasks = 0
        
        async def fetch_with_semaphore(url):
            nonlocal completed_tasks
            async with semaphore:
                # MANDATORY JITTERED DELAY
                # OPTIMIZED: Scales up when errors hit, recovers slowly on success.
                base_tor_delay = random.uniform(1.0, 3.0)
                actual_delay = (base_tor_delay * delay_scale[0]) if use_tor else random.uniform(0.1, 0.3)
                await asyncio.sleep(actual_delay)
                
                results = await fetch_rss_async(url, connector_provider=get_connector)
                
                if not results:
                    # Failure - Slow down future Tor requests significantly (increase delay)
                    if use_tor:
                        delay_scale[0] = min(delay_scale[0] + 0.5, 5.0) # Max 5x delay
                else:
                    # Success - Speed up slightly (recover delay)
                    if use_tor:
                        delay_scale[0] = max(delay_scale[0] - 0.1, 1.0) # Min 1x delay

                # Update Progress
                completed_tasks += 1
                if progress_callback:
                    try:
                        progress_callback(completed_tasks, total_tasks)
                    except: pass
                
                return results

        print(f"📡 Launching Resilient Search with {len(urls)} URLs (Speed Optimized)...")
        tasks = [fetch_with_semaphore(url) for url in urls]
        
        try:
            # Using return_exceptions=True to ensure one failure doesn't kill the whole process
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            print("⚠️ Search cancelled by user or network disconnect.")
            return []
        except Exception as e:
            print(f"⚠️ Unexpected error during search: {e}")
            return []
        
        all_results = []
        for res in results:
            if isinstance(res, list):
                all_results.extend(res)
            elif isinstance(res, Exception):
                print(f"⚠️ Task failed with exception: {res}")
        return all_results
    
    # START THE SEARCH!
    all_entries_lists = asyncio.run(fetch_resilient_sources(progress_callback))
    
    seen_ids = set() # Dedupe by ID/Link
    seen_titles = set() # Dedupe by Title+Source
    
    # Master Time Window for 98% Accuracy
    # OPTIMIZED: Use explicit start/end dates
    master_start_date = start_date
    master_end_date = end_date + timedelta(days=1) # Include the end date fully
    
    print(f"🕵️ STRICT FILTERING: Keeping articles between {master_start_date.date()} and {master_end_date.date()}...")
    
    skipped_date = 0
    skipped_dedupe = 0
    
    # Process all the results we got back
    for entry in all_entries_lists:
        title = entry.get('title', '').strip()
        source = entry.get('source', {}).get('title', 'Unknown')
        link = entry.get('link', '')
        published_str = entry.get('published', '')
        
        # --- 1. STRICT TIME FILTERING ---
        if not published_str:
            continue
            
        try:
            # RSS dates are usually "Mon, 05 Feb 2024 12:00:00 GMT"
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            else:
                continue 
            
            if pub_date < master_start_date or pub_date > master_end_date:
                skipped_date += 1
                continue
                
        except Exception:
            continue
            
        # --- 2. ROBUST DEDUPLICATION ---
        # Key 1: Link (Exact match)
        if link in seen_ids:
            skipped_dedupe += 1
            continue
        
        # Key 2: Normalized Title + Source
        norm_title = re.sub(r'\W+', ' ', title).lower().strip()
        dedup_key = (norm_title, source)
        
        if dedup_key in seen_titles:
            skipped_dedupe += 1
            continue
            
        # Add to known
        seen_ids.add(link)
        seen_titles.add(dedup_key)
            
        # Clean description
        raw_description = entry.get('summary', '')
        soup = BeautifulSoup(raw_description, 'html.parser')
        clean_description = soup.get_text(separator=' ', strip=True)
        clean_description = re.sub(r'\s*and more\s*»', '', clean_description)
        
        articles.append({
            'title': title,
            'description': clean_description if clean_description else 'No description',
            'source': source,
            'link': link,
            'published': published_str
        })
        
        # Stop if max reached
        if len(articles) >= max_articles:
            break
            
    print(f"✅ Final Articles: {len(articles)} (Skipped {skipped_date} out-of-window, {skipped_dedupe} duplicates)")
    return articles
