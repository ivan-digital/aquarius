# Selenium WebDriver Usage in Aquarius

This document outlines the use of Selenium WebDriver and related libraries within the Aquarius project for browser automation tasks, primarily for web scraping and UI testing.

## Key Libraries

-   **Selenium**: The core library for browser automation. It provides APIs to control web browsers programmatically.
    -   `selenium.webdriver`: Main module for accessing WebDriver implementations (e.g., Chrome, Firefox).
    -   `selenium.webdriver.chrome.options.Options` / `selenium.webdriver.firefox.options.Options`: Used to configure browser-specific settings, such as headless mode, window size, and user agent.
    -   `selenium.webdriver.chrome.service.Service` / `selenium.webdriver.firefox.service.Service`: Manages the browser driver executable (e.g., chromedriver, geckodriver).
-   **WebDriver Manager**: A library that simplifies the management of browser driver executables. It automatically downloads and sets up the appropriate driver for the installed browser version.
    -   `webdriver_manager.chrome.ChromeDriverManager`: Specifically for managing ChromeDriver.
    -   `webdriver_manager.firefox.GeckoDriverManager`: Specifically for managing GeckoDriver (for Firefox).

## `WebDriverService` (`app/server/web_driver.py`)

The `WebDriverService` class is a singleton responsible for initializing and managing a Selenium WebDriver instance.

### Initialization

-   The service is initialized based on the `browser` (e.g., "chrome", "firefox") and `headless` (boolean) parameters.
-   It uses `ConfigManager` for any potential future configuration needs.
-   **Chrome**:
    -   `ChromeOptions` are configured. In headless mode, `--no-sandbox` and `--disable-dev-shm-usage` are added, which are common for running Chrome in Docker containers.
    -   It attempts to use `ChromeDriverManager().install()` to get the path to `chromedriver` and initializes `ChromeService` with it.
    -   If `ChromeDriverManager` fails, it falls back to using the default `chromedriver` expected to be in the system's PATH.
-   **Firefox**:
    -   `FirefoxOptions` are configured (e.g., adding `--headless`).
    -   It previously used `GeckoDriverManager().install()` but has been updated to attempt to use the `geckodriver` from the system's PATH directly. *(Note: The user's latest code shows GeckoDriverManager commented out)*.

### Key Methods

-   `__init__(self, config_manager: ConfigManager, headless: bool = True, browser: str = "chrome")`: Constructor that sets up the WebDriver based on the specified browser and headless mode.
-   `get_driver(self) -> webdriver.Remote`: Returns the initialized WebDriver instance.
-   `query(self, url: str, wait_time: int = 10) -> str`: Navigates to a given URL, waits for a specified time (to allow JavaScript rendering), and returns the page source.
-   `close(self)`: Quits the WebDriver and closes the browser.

### Usage Pattern

The `WebDriverService` is instantiated as a global `webDriverService` object if the `APP_COMPONENT` environment variable is set to "api". This makes a single WebDriver instance available throughout the API component of the application.

```python
# Example of how webDriverService is initialized in web_driver.py
webDriverService = None
if os.environ.get("APP_COMPONENT") == "api":
    webDriverService = WebDriverService(config_manager=configManager, headless=True, browser="chrome") # Defaulting to Chrome
```

## Dockerfile Considerations (`Dockerfile.base`)

-   The `Dockerfile.base` installs system dependencies required for running headless browsers, including `xvfb`, `wget`, `gnupg`, `ca-certificates`.
-   It installs `chromium` and `chromium-driver`. This is crucial because `WebDriverService` relies on these being available in the Docker container's environment when not using a driver manager to download them on the fly (or as a fallback).
-   The `CHROME_BIN`, `CHROME_PATH`, and `CHROMEDRIVER_PATH` environment variables are set in the Dockerfile, pointing to the locations of the installed Chromium browser and its driver. This helps Selenium locate them.

## Best Practices and Notes

-   **Singleton Pattern**: `WebDriverService` is implemented as a singleton to ensure only one browser instance is managed, which is generally good practice for resource management.
-   **Error Handling**: The service includes `try-except` blocks to catch errors during WebDriver initialization and logs them.
-   **Headless Operation**: The `headless` parameter is crucial for running in server environments or CI/CD pipelines where a GUI is not available.
-   **Driver Management**: While `webdriver-manager` is convenient for local development, ensuring the correct browser and driver versions are installed in the Docker image (as done with `chromium` and `chromium-driver` in `Dockerfile.base`) is a more robust approach for production/containerized environments.
-   **Configuration**: Browser selection and headless mode are configurable at instantiation, allowing flexibility.
