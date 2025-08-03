# Facebook Ads Library Scraper Bot

A powerful Python-based chatbot that integrates with Lark/Feishu messaging platform to scrape and analyze Facebook Ads Library data. The bot provides automated web scraping capabilities through conversational commands, generating comprehensive Excel reports with ad thumbnails and metadata.

## 🌟 Key Features

- **Conversational Interface**: Easy-to-use chat commands through Lark/Feishu
- **Automated Web Scraping**: Selenium-based Facebook Ads Library crawler
- **Queue Management**: Handles multiple concurrent requests with intelligent queuing
- **Rich Excel Reports**: Generated reports include ad images, metadata, and clickable links
- **Real-time Progress Updates**: Interactive cards showing scraping progress
- **Cancellation Support**: Users can cancel ongoing processes at any time
- **Parallel Image Processing**: Optimized image downloading with ThreadPoolExecutor
- **State Management**: Robust user session and process state handling

## 🚀 Installation

### Prerequisites

- Python 3.8+
- Chrome browser installed
- ChromeDriver (automatically managed by Selenium)
- Lark/Feishu app credentials

### Dependencies Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd facebook-ads-scraper-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### Required Python Packages

```txt
selenium>=4.0.0
pandas>=1.3.0
requests>=2.25.0
openpyxl>=3.0.0
Pillow>=8.0.0
python-dotenv>=0.19.0
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Lark/Feishu App Credentials
LARK_APP_ID=your_app_id_here
LARK_APP_SECRET=your_app_secret_here
VERIFICATION_TOKEN=your_verification_token_here

# Optional: Custom configurations
MAX_WORKERS=10
REQUEST_TIMEOUT=15
```

### Lark/Feishu App Setup

1. Create a new app in [Lark Developer Console](https://open.larksuite.com/)
2. Enable the following permissions:
   - `im:message`
   - `im:message.group_at_msg`
   - `im:chat`
3. Configure webhook endpoints for message events
4. Copy App ID, App Secret, and Verification Token to your `.env` file

## 🎯 Usage

### Starting the Bot

```bash
# Activate virtual environment
source venv/bin/activate

# Run the main application
python main.py
```

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/help` or `/start` | Show command menu | `/help` |
| `/search <domain>` | Start scraping ads for domain | `/search shopee.com` |
| `/cancel` | Cancel ongoing process | `/cancel` |

### Example Workflow

1. **Start a search**:
   ```
   /search nike.com
   ```

2. **Monitor progress**:
   - Real-time progress cards show scraping status
   - Queue position updates if multiple requests

3. **Receive results**:
   - Excel file with ad data and thumbnails
   - Summary card with result count and direct link

4. **Cancel if needed**:
   ```
   /cancel
   ```

## 📊 Output Format

The bot generates Excel reports containing:

- **Library ID**: Facebook ad library identifier
- **Ad Start Date**: When the ad campaign began
- **Company**: Advertiser name
- **Pixel ID**: Facebook tracking pixel (if available)
- **Destination URL**: Landing page link
- **Ad Type**: Image or video advertisement
- **Ad URL**: Direct link to ad media
- **Thumbnail**: Embedded image preview

## 🏗️ Project Structure

```
facebook-ads-scraper-bot/
├── lark_bot/
│   ├── __init__.py
│   ├── command_handlers.py      # Command processing logic
│   ├── lark_api.py             # Lark/Feishu API integration
│   ├── state_managers.py       # User state and session management
│   ├── file_processor.py       # Excel report generation
│   ├── logger.py               # Message logging system
│   └── config.py               # Configuration management
├── tools/
│   ├── __init__.py
│   ├── facebook_crawler.py     # Core scraping engine
│   └── interactive_card_library.py  # UI card templates
├── logs/                       # Chat logs (auto-generated)
├── .env                        # Environment variables
├── requirements.txt            # Python dependencies
├── main.py                     # Application entry point
└── README.md                   # This file
```

### Core Components

- **CommandHandler**: Processes user commands and manages workflow
- **FacebookAdsCrawler**: Selenium-based web scraper
- **LarkAPI**: Handles all Lark/Feishu messaging operations
- **UserStateManager**: Manages user sessions and process states
- **CrawlerQueue**: Implements request queuing and processing
- **ExcelImageExporter**: Generates rich Excel reports with images

## 🔧 Advanced Configuration

### Crawler Settings

Modify `FacebookAdsCrawler` initialization parameters:

```python
crawler = FacebookAdsCrawler(
    keyword=domain,
    chat_id=chat_id,
    message_id=message_id
)

# Customize Excel export settings
exporter = ExcelImageExporter(
    image_size=(100, 100),        # Thumbnail dimensions
    row_height=100,               # Excel row height
    timeout=15,                   # Request timeout
    max_workers=10                # Parallel downloads
)
```

### Chrome Options

Customize browser behavior in `initialize_driver()`:

```python
options.add_argument('--headless')          # Run in background
options.add_argument('--window-size=1280,720')  # Browser window size
options.add_argument('--disable-gpu')       # Reduce resource usage
```

## 🚨 Error Handling

The bot includes comprehensive error handling:

- **Network Issues**: Automatic retries with exponential backoff
- **Rate Limiting**: Intelligent request spacing
- **Resource Cleanup**: Proper browser and file handle management
- **Cancellation**: Graceful process termination
- **Logging**: Detailed error logs for debugging

## 📝 Logging

All interactions are logged to monthly JSON files:

```json
{
  "uid": "user_id",
  "mid": "message_id", 
  "ts": "2025-01-15T10:30:00",
  "cid": "chat_id",
  "dir": "i",
  "msg": "search nike.com"
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints for new functions
- Include docstrings for public methods
- Write unit tests for new features
- Update documentation as needed

## 🔒 Security Considerations

- **Environment Variables**: Never commit `.env` files
- **Rate Limiting**: Respect Facebook's terms of service
- **User Data**: Implement proper data handling practices
- **Access Control**: Validate user permissions for commands

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for educational and research purposes only. Users are responsible for complying with:

- Facebook's Terms of Service
- Applicable data protection laws
- Website scraping policies
- Rate limiting requirements

Always ensure your usage complies with the target platform's robots.txt and terms of service.

---

**Built with ❤️ using Python, Selenium, and Lark SDK**