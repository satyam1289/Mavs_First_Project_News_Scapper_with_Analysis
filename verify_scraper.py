
import asyncio
import aiohttp
from article_scraper import scrape_article_content_async

async def test_scraper():
    # Use a bot-friendly URL for testing logic
    url = "https://example.com"
    print(f"Testing URL: {url}")
    
    async with aiohttp.ClientSession() as session:
        result = await scrape_article_content_async(session, url)
        
        if result:
            print("\n✅ Scraping Successful!")
            print(f"Title/Summary: {result.get('summary', '')[:100]}...")
            print(f"Full Text Length: {len(result.get('full_text', ''))} chars")
            print("--- Snippet ---")
            print(result.get('full_text', '')[:200])
        else:
            print("\n❌ Scraping Failed: Returned None")

if __name__ == "__main__":
    asyncio.run(test_scraper())
