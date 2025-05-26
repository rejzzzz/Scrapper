#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional
import json
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class AgentData:
    """Data structure for AI agent information"""
    name: str = ""
    url: str = ""
    brief_description: str = ""
    features: str = ""
    pros: str = ""
    cons: str = ""
    user_reviews: str = ""
    pricing: str = ""
    rating: str = ""
    category: str = ""
    source_site: str = ""

class BaseScraper(ABC):
    """Base class for website scrapers"""
    
    def __init__(self, base_url: str, headers: Dict[str, str] = None):
        self.base_url = base_url
        self.session = requests.Session()
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session.headers.update(self.headers)
        self.driver = self._init_selenium()
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1920,1080')
        try:
            return webdriver.Chrome(options=options)
        except WebDriverException as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {e}")
            raise
    
    def get_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage with retry logic using requests"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return BeautifulSoup(response.content, 'html.parser')
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        logger.error(f"Failed to fetch {url} after {retries} attempts")
        return None
    
    def get_page_with_js(self, url: str, retries: int = 3, timeout: int = 10) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage with Selenium for JavaScript rendering"""
        for attempt in range(retries):
            try:
                logger.info(f"Fetching {url} with Selenium")
                self.driver.get(url)
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)  # Additional wait for dynamic content
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                return soup
            except (TimeoutException, WebDriverException) as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        logger.error(f"Failed to fetch {url} with Selenium after {retries} attempts")
        return None
    
    def close_driver(self):
        """Close Selenium driver"""
        if hasattr(self, 'driver'):
            self.driver.quit()
    
    @abstractmethod
    def get_agent_urls(self) -> List[str]:
        """Get list of agent URLs to scrape"""
        pass
    
    @abstractmethod
    def scrape_agent(self, url: str) -> AgentData:
        """Scrape individual agent data"""
        pass

class AgentAIScraper(BaseScraper):
    """Scraper for Agent.ai marketplace"""
    
    def __init__(self):
        super().__init__("https://agent.ai")
    
    def get_agent_urls(self) -> List[str]:
        """Get agent URLs from the marketplace listing"""
        agent_urls = []
        listing_pages = ["/agents", "/marketplace", "/browse", "/"]
        
        for page in listing_pages:
            url = urljoin(self.base_url, page)
            soup = self.get_page_with_js(url)
            if soup:
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if any(keyword in href.lower() for keyword in ['agent', 'bot', 'ai']) and all(exclude not in href.lower() for exclude in ['linkedin', 'login', 'signup', 'community']):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in agent_urls:
                            agent_urls.append(full_url)
                if agent_urls:
                    break
        
        logger.info(f"Found {len(agent_urls)} agent URLs from Agent.ai")
        return agent_urls
    
    def scrape_agent(self, url: str) -> AgentData:
        """Scrape individual agent from Agent.ai"""
        soup = self.get_page_with_js(url)
        if not soup or "just a moment" in soup.title.text.lower():
            logger.info(f"Skipping {url}: likely a captcha or invalid page")
            return AgentData(url=url, source_site="Agent.ai")
        
        agent = AgentData(url=url, source_site="Agent.ai")
        
        try:
            # Extract name
            name_selectors = ['h1', '.agent-name', '.title', 'h2', 'title']
            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem:
                    agent.name = name_elem.get_text().strip()
                    break
            if not agent.name or any(keyword in agent.name.lower() for keyword in ['javascript', 'error', 'moment']):
                agent.name = urlparse(url).path.split('/')[-1] or "Unknown Agent"

            # Extract description
            desc_selectors = ['meta[name="description"]', '.agent-description', '.summary', 'p']
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    text = desc_elem.get('content', desc_elem.get_text()).strip()
                    if len(text) > 30 and all(keyword not in text.lower() for keyword in ['javascript', 'error']):
                        agent.brief_description = text[:500]
                        break
            
            # Extract features, pricing, and rating from mixed content
            features_list = []
            pricing_list = []
            rating_list = []
            feature_selectors = ['.features li', '.capabilities li', '.agent-details li']
            for selector in feature_selectors:
                features = soup.select(selector)
                if features:
                    for f in features:
                        text = f.get_text().strip()
                        if "credit" in text.lower():
                            pricing_list.append(text)
                        elif any(r in text.lower() for r in ['review', 'rating', '(']):
                            rating_list.append(text)
                        else:
                            features_list.append(text)
                    break
            if not features_list:
                main_content = soup.select_one('main, .content, .main-content, article')
                if main_content:
                    lists = main_content.select('ul li, ol li')
                    for li in lists:
                        text = li.get_text().strip()
                        if "credit" in text.lower():
                            pricing_list.append(text)
                        elif any(r in text.lower() for r in ['review', 'rating', '(']):
                            rating_list.append(text)
                        else:
                            features_list.append(text)
            agent.features = "; ".join(features_list[:5])
            agent.pricing = "; ".join(pricing_list[:3])
            agent.rating = "; ".join(rating_list[:3])
            
            # Extract pros
            pros_list = []
            pros_selectors = ['.pros li', '.advantages li', '.benefits li']
            for selector in pros_selectors:
                pros = soup.select(selector)
                if pros:
                    pros_list = [p.get_text().strip() for p in pros]
                    break
            if not pros_list:
                for p in soup.find_all('p'):
                    text = p.get_text().lower()
                    if any(keyword in text for keyword in ['benefit', 'advantage', 'strength']):
                        pros_list.append(p.get_text().strip())
            agent.pros = "; ".join(pros_list[:3])
            
            # Extract cons
            cons_list = []
            cons_selectors = ['.cons li', '.limitations li', '.disadvantages li']
            for selector in cons_selectors:
                cons = soup.select(selector)
                if cons:
                    cons_list = [c.get_text().strip() for c in cons]
                    break
            if not cons_list:
                for p in soup.find_all('p'):
                    text = p.get_text().lower()
                    if any(keyword in text for keyword in ['limitation', 'drawback', 'challenge']):
                        cons_list.append(p.get_text().strip())
            agent.cons = "; ".join(cons_list[:3])
            
            # Extract user reviews
            reviews_list = []
            review_selectors = ['.review', '.testimonial', '.user-review', '.comment']
            for selector in review_selectors:
                reviews = soup.select(selector)
                if reviews:
                    reviews_list = [r.get_text().strip()[:200] for r in reviews[:3]]
                    break
            agent.user_reviews = "; ".join(reviews_list)
            
            # Extract category
            category_selectors = ['.category', '.tag', '.type']
            for selector in category_selectors:
                category_elem = soup.select_one(selector)
                if category_elem:
                    agent.category = category_elem.get_text().strip()
                    break
        
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
        
        return agent

class MetaschoolScraper(BaseScraper):
    """Scraper for Metaschool.so"""
    
    def __init__(self):
        super().__init__("https://metaschool.so")
    
    def get_agent_urls(self) -> List[str]:
        """Get agent URLs from Metaschool"""
        agent_urls = []
        listing_paths = ["/courses", "/projects", "/agents", "/"]
        
        for path in listing_paths:
            url = urljoin(self.base_url, path)
            soup = self.get_page_with_js(url)
            if soup:
                cards = soup.select('.card, .course-card, .project-card, a[href*="course"], a[href*="project"]')
                for card in cards:
                    href = card.get('href') if card.name == 'a' else card.find('a', href=True)
                    if href:
                        full_url = urljoin(self.base_url, href['href'] if isinstance(href, dict) else href)
                        if full_url not in agent_urls and 'blockchain=' not in full_url:
                            agent_urls.append(full_url)
                if agent_urls:
                    break
        
        logger.info(f"Found {len(agent_urls)} URLs from Metaschool")
        return agent_urls
    
    def scrape_agent(self, url: str) -> AgentData:
        """Scrape individual project/course from Metaschool"""
        soup = self.get_page_with_js(url)
        if not soup or "just a moment" in soup.title.text.lower():
            logger.info(f"Skipping {url}: likely a captcha or invalid page")
            return AgentData(url=url, source_site="Metaschool")
        
        agent = AgentData(url=url, source_site="Metaschool")
        
        try:
            # Extract name
            title_elem = soup.select_one('h1, .title, .course-title, h2')
            if title_elem:
                agent.name = title_elem.get_text().strip()
            
            # Extract description
            desc_elem = soup.select_one('.description, .course-description, .overview, meta[name="description"], p')
            if desc_elem:
                text = desc_elem.get('content', desc_elem.get_text()).strip()
                if len(text) > 30:
                    agent.brief_description = text[:500]
            
            # Extract features and rating
            features_list = []
            rating_list = []
            feature_selectors = ['.outcomes li', '.features li', '.what-you-learn li']
            for selector in feature_selectors:
                features = soup.select(selector)
                if features:
                    for f in features:
                        text = f.get_text().strip()
                        if "review" in text.lower() or "(" in text:
                            rating_list.append(text)
                        elif any(keyword in text.lower() for keyword in ['learn', 'build', 'master']):
                            features_list.append(text)
                    break
            agent.features = "; ".join(features_list[:5])
            agent.rating = "; ".join(rating_list[:3])
            
            # Extract pros
            pros_list = []
            pros_selectors = ['.pros li', '.benefits li', '.why-take-this-course li']
            for selector in pros_selectors:
                pros = soup.select(selector)
                if pros:
                    pros_list = [p.get_text().strip() for p in pros]
                    break
            if not pros_list:
                for p in soup.find_all('p'):
                    text = p.get_text().lower()
                    if any(keyword in text for keyword in ['benefit', 'advantage', 'learn', 'skill']):
                        pros_list.append(p.get_text().strip())
            agent.pros = "; ".join(pros_list[:3])
            
            # Extract cons
            cons_list = []
            cons_selectors = ['.cons li', '.requirements li', '.prerequisites li']
            for selector in cons_selectors:
                cons = soup.select(selector)
                if cons:
                    cons_list = [c.get_text().strip() for c in cons]
                    break
            if not cons_list:
                for p in soup.find_all('p'):
                    text = p.get_text().lower()
                    if any(keyword in text for keyword in ['require', 'prerequisite', 'need']):
                        cons_list.append(p.get_text().strip())
            agent.cons = "; ".join(cons_list[:3])
            
            # Extract user reviews
            reviews_list = []
            review_selectors = ['.review', '.testimonial', '.user-review', '.comment']
            for selector in review_selectors:
                reviews = soup.select(selector)
                if reviews:
                    reviews_list = [r.get_text().strip()[:200] for r in reviews[:3]]
                    break
            agent.user_reviews = "; ".join(reviews_list)
            
            # Extract pricing
            price_selectors = ['.price', '.pricing', '.cost', '.enroll']
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    agent.pricing = price_elem.get_text().strip()
                    break
            if not agent.pricing:
                agent.pricing = "Free"  # Default for Metaschool courses
                for p in soup.find_all('p'):
                    text = p.get_text().lower()
                    if any(keyword in text for keyword in ['free', '$', '€', 'paid']):
                        agent.pricing = p.get_text().strip()[:200]
                        break
            
            # Extract category
            category_elem = soup.select_one('.category, .difficulty, .level, .tag')
            if category_elem:
                agent.category = category_elem.get_text().strip()
        
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
        
        return agent

class AIAgentScraper:
    """Main scraper coordinator"""
    
    def __init__(self):
        self.scrapers = {
            'agent.ai': AgentAIScraper(),
            'metaschool.so': MetaschoolScraper(),
        }
        self.all_agents = []
    
    def scrape_all(self) -> List[AgentData]:
        """Scrape all configured sites"""
        all_agents = []
        
        for site_name, scraper in self.scrapers.items():
            logger.info(f"Scraping {site_name}...")
            
            try:
                agent_urls = scraper.get_agent_urls()
                for i, url in enumerate(agent_urls):
                    logger.info(f"Scraping agent {i+1}/{len(agent_urls)}: {url}")
                    agent_data = scraper.scrape_agent(url)
                    if agent_data.name and agent_data.brief_description:
                        all_agents.append(agent_data)
                    else:
                        logger.info(f"Skipping {url}: insufficient data")
                    time.sleep(2)  # Delay to avoid rate limiting
            except Exception as e:
                logger.error(f"Error scraping {site_name}: {e}")
            finally:
                scraper.close_driver()
        
        self.all_agents = all_agents
        return all_agents
    
    def save_to_csv(self, filename: str = "data/ai_agents_data.csv"):
        """Save scraped data to CSV"""
        if not self.all_agents:
            logger.warning("No data to save")
            return
        data_dicts = [asdict(agent) for agent in self.all_agents]
        df = pd.DataFrame(data_dicts)
        df.to_csv(filename, index=False, encoding='utf-8')
        logger.info(f"Saved {len(df)} agents to {filename}")
        return df
    
    def save_to_json(self, filename: str = "data/ai_agents_data.json"):
        """Save scraped data to JSON"""
        if not self.all_agents:
            logger.warning("No data to save")
            return
        data_dicts = [asdict(agent) for agent in self.all_agents]
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data_dicts, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(data_dicts)} agents to {filename}")

def main():
    """Main execution function"""
    import os
    os.makedirs('data', exist_ok=True)
    scraper = AIAgentScraper()
    agents = scraper.scrape_all()
    if agents:
        scraper.save_to_csv()
        scraper.save_to_json()
    else:
        print("No data was scraped. Check the logs for errors.")

if __name__ == "__main__":
    main()