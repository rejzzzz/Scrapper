# AI Agents Data Scraper

A sophisticated Python web scraper designed to collect comprehensive information about AI agents and educational content from various platforms. The project currently supports data extraction from Agent.ai and Metaschool.so, with an extensible architecture for future platform additions.

## Table of Contents

-   [Features](#features)
-   [Project Structure](#project-structure)
-   [Requirements](#requirements)
-   [Installation](#installation)
-   [Configuration](#configuration)
-   [Usage](#usage)
-   [Data Collection](#data-collection)
-   [Architecture](#architecture)
-   [Error Handling](#error-handling)
-   [Contributing](#contributing)
-   [License](#license)

## Features

### Core Capabilities

-   **Multi-Platform Support**: Modular design for scraping different websites
-   **JavaScript Rendering**: Handles dynamic content using Selenium
-   **Robust Error Handling**: Implements retry mechanisms and graceful degradation
-   **Rate Limiting**: Built-in delays to prevent server overload
-   **Comprehensive Logging**: Detailed activity and error tracking
-   **Multiple Export Formats**: Data saved in both CSV and JSON formats

### Data Collection Fields

-   Agent/Course Names
-   URLs
-   Brief Descriptions
-   Features and Capabilities
-   Advantages (Pros)
-   Limitations (Cons)
-   User Reviews
-   Pricing Information
-   Ratings
-   Categories

## Project Structure

```
ai-agents-data/
│
├── data/                    # Output directory
│   ├── ai_agents_data.csv  # CSV export
│   ├── ai_agents_data.json # JSON export
│   └── scraper.log         # Activity logs
│
├── scraper.py              # Main scraper implementation
├── requirements.txt        # Python dependencies
└── README.md              # Project documentation
```

## Requirements

### System Dependencies

-   Python 3.6+
-   Chrome/Chromium browser
-   ChromeDriver (matching Chrome version)

### Python Packages

```
requests>=2.28.0
beautifulsoup4>=4.11.0
pandas>=1.5.0
lxml>=4.9.0
selenium
```

## Installation

1. **Clone the Repository**

```powershell
git clone <repository-url>
cd ai-agents-data
```

2. **Set Up Virtual Environment**

```powershell
python -m venv venv
.\venv\Scripts\Activate
```

3. **Install Dependencies**

```powershell
pip install -r requirements.txt
```

4. **ChromeDriver Setup**

-   Download ChromeDriver matching your Chrome version from [official site](https://sites.google.com/chromium.org/driver/)
-   Add to system PATH or project directory

## Configuration

The scraper can be customized through environment variables:

```env
DELAY=2                # Time between requests (seconds)
MAX_RETRIES=3         # Maximum retry attempts
LOG_LEVEL=INFO        # Logging verbosity
HEADLESS=True         # Run browser in headless mode
```

## Usage

1. **Basic Execution**

```powershell
python scraper.py
```

2. **Output Files**

-   `data/ai_agents_data.csv`: Tabular data format
-   `data/ai_agents_data.json`: Detailed JSON format
-   `data/scraper.log`: Execution logs

## Architecture

### Key Components

1. **AgentData (DataClass)**

```python
@dataclass
class AgentData:
    name: str
    url: str
    brief_description: str
    features: str
    pros: str
    cons: str
    user_reviews: str
    pricing: str
    rating: str
    category: str
    source_site: str
```

2. **BaseScraper (Abstract Base Class)**

-   Core functionality for all scrapers
-   Handles web requests and parsing
-   Manages Selenium WebDriver
-   Implements retry logic

3. **Site-Specific Scrapers**

-   `AgentAIScraper`: Specializes in Agent.ai content
-   `MetaschoolScraper`: Handles Metaschool.so data

4. **Main Coordinator**

-   `AIAgentScraper`: Orchestrates the scraping process
-   Manages multiple platform scrapers
-   Handles data export

## Error Handling

The scraper implements multiple layers of error handling:

1. **Request Retries**

-   Exponential backoff
-   Configurable retry attempts
-   Timeout handling

2. **Data Validation**

-   Null checks
-   Content validation
-   Error logging

3. **Resource Management**

-   Proper cleanup of resources
-   Browser session management
-   File handling

## Extending the Scraper

### Adding New Platforms

1. Create a new scraper class:

```python
class NewPlatformScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://newplatform.com")

    def get_agent_urls(self) -> List[str]:
        # Implement URL collection logic
        pass

    def scrape_agent(self, url: str) -> AgentData:
        # Implement scraping logic
        pass
```

2. Register in AIAgentScraper:

```python
self.scrapers['newplatform.com'] = NewPlatformScraper()
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes
4. Add tests if applicable
5. Submit a pull request

## Future Improvements

-   [ ] Add support for more platforms
-   [ ] Implement parallel scraping
-   [ ] Add data validation layer
-   [ ] Create data analysis tools
-   [ ] Add unit tests
-   [ ] Implement proxy rotation
-   [ ] Add API endpoints

## License

[MIT License](https://opensource.org/licenses/MIT) or choose appropriate license

## Disclaimer

This tool should be used responsibly and in accordance with websites' terms of service and robots.txt files. Implement appropriate delays between requests and respect rate limits while scraping.
