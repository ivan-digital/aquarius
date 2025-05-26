import os
import time
import logging # Add logging import
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions # Add ChromeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService 
from selenium.webdriver.chrome.service import Service as ChromeService 
# from webdriver_manager.firefox import GeckoDriverManager # Comment out or remove
from webdriver_manager.chrome import ChromeDriverManager


from app.config_manager import ConfigManager, configManager


class WebDriverService:
    """
    A Selenium WebDriver service that instantiates a browser driver based on configuration.
    Supports Chrome (default), Firefox, and Safari.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(WebDriverService, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_manager: ConfigManager, headless: bool = True, browser: str = "chrome") -> None:
        """
        Initializes the WebDriverService.

        Args:
            config_manager: The configuration manager instance.
            headless: Whether to run the browser in headless mode. Defaults to True.
            browser: The browser to use ('chrome' or 'firefox'). Defaults to 'chrome'.
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.headless = headless
        self.browser = browser.lower()
        self.driver = None
        self._initialized = False
        
        self.logger.info(f"Initializing WebDriverService with browser: {self.browser}, headless: {self.headless}")

        try:
            if self.browser == "firefox":
                firefox_options = FirefoxOptions()
                if self.headless:
                    firefox_options.add_argument("--headless")
                
                try:
                    self.driver = webdriver.Firefox(options=firefox_options)
                    self.logger.info("Firefox WebDriver initialized using default geckodriver path.")
                except Exception as e_manager:
                    self.logger.warning(f"Firefox WebDriver initialization failed: {e_manager}. Check geckodriver installation.")
                    raise


            elif self.browser == "chrome":
                chrome_options = ChromeOptions()
                if self.headless:
                    chrome_options.add_argument("--headless")
                    chrome_options.add_argument("--no-sandbox")
                    chrome_options.add_argument("--disable-dev-shm-usage")
                
                chrome_bin_path = os.environ.get("CHROME_BIN")
                chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")

                if chrome_bin_path and chromedriver_path and os.path.exists(chromedriver_path):
                    self.logger.info(f"Using system ChromeDriver at {chromedriver_path} and Chrome at {chrome_bin_path}")
                    chrome_options.binary_location = chrome_bin_path
                    service = ChromeService(executable_path=chromedriver_path)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    self.logger.info("Chrome WebDriver initialized using system paths (likely from Docker environment).")
                else:
                    self.logger.info("System ChromeDriver not found or paths not set, attempting ChromeDriverManager.")
                    try:
                        service = ChromeService(ChromeDriverManager().install())
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                        self.logger.info("Chrome WebDriver initialized using ChromeDriverManager.")
                    except Exception as e_manager:
                        self.logger.warning(f"ChromeDriverManager failed: {e_manager}. Falling back to default chromedriver path.")
                        self.driver = webdriver.Chrome(options=chrome_options)
                        self.logger.info("Chrome WebDriver initialized using default Selenium resolution (may use Selenium Manager).")
            else:
                raise ValueError(f"Unsupported browser: {self.browser}. Choose 'firefox' or 'chrome'.")

            self._initialized = True
            self.logger.info(f"{self.browser.capitalize()} WebDriver initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver for {self.browser}: {e}", exc_info=True)
            raise

    def get_driver(self) -> webdriver.Remote:
        """
        Returns the initialized WebDriver instance.

        Raises:
            Exception: If the WebDriverService is not initialized.

        Returns:
            The WebDriver instance.
        """
        if not self._initialized or not self.driver:
            raise Exception("WebDriverService not initialized. Call 'query' method first.")
        return self.driver

    def query(self, url: str, wait_time: int = 10) -> str:
        """
        Loads the specified URL, waits for JavaScript to render,
        and returns the rendered HTML as a string.
        """
        self.driver.get(url)
        time.sleep(wait_time)
        return self.driver.page_source

    def close(self):
        """Closes the browser and quits the driver."""
        self.driver.quit()


webDriverService = None
if os.environ.get("APP_COMPONENT") == "api":
    webDriverService = WebDriverService(config_manager=configManager, headless=True)
