import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from app.config_manager import ConfigManager, configManager


class WebDriverService:
    """
    A Selenium WebDriver service that instantiates a browser driver based on configuration.
    Supports Chrome (default), Firefox, and Safari.
    """

    def __init__(self, config_manager: ConfigManager, headless: bool = True):
        browser = config_manager.get("browser", "chrome").lower()
        driver_path = config_manager.get("driver_path", None)
        self.browser = browser

        if browser == "firefox":
            firefox_options = FirefoxOptions()
            if headless:
                firefox_options.headless = True
                firefox_options.add_argument("--headless")
            if driver_path:
                firefox_service = FirefoxService(executable_path=driver_path)
                self.driver = webdriver.Firefox(service=firefox_service, options=firefox_options)
            else:
                self.driver = webdriver.Firefox(options=firefox_options)
        elif browser == "safari":
            # Safari does not currently support headless mode.
            self.driver = webdriver.Safari()
        else:  # default to chrome
            chrome_options = ChromeOptions()
            if headless:
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--disable-gpu")
            if driver_path:
                chrome_service = ChromeService(executable_path=driver_path)
                self.driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)

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


webDriverService = WebDriverService(config_manager=configManager, headless=True)
