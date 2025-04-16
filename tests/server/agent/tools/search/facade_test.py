import os
import unittest
import time

from app.config_manager import ConfigManager
from app.agent.tools import SearchFacade


class TestSearchService(unittest.TestCase):
    service = None

    @classmethod
    def setUpClass(cls):
        PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(PROJECT_DIR, "../../../config.yaml")
        config_manager = ConfigManager(config_path)
        config = config_manager.config
        cls.service = SearchFacade(config)
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        cls.service.close()

    def test_search_google(self):
        query = "Selenium Python"
        page_source = self.service.search_google(query)
        self.assertIn("Selenium", page_source, "Google tools results should contain the term 'Selenium'.")

    def test_search_google_enrich(self):
        query = "Selenium Python"
        page_source = self.service.search_google_enrich(query)
        self.assertIn("Page Content", page_source,
                      "Enriched Google search results should include page content excerpt.")

    def test_search_reddit(self):
        query = "Python testing"
        page_source = self.service.search_reddit(query)
        self.assertIn("Python", page_source, "Reddit tools results should contain the term 'Python'.")

    def test_search_github(self):
        query = "selenium"
        page_source = self.service.search_github(query)
        self.assertIn(query.lower(), page_source.lower(), "GitHub tools results should contain the term 'selenium'.")

    def test_search_arxiv(self):
        query = "machine learning"
        page_source = self.service.search_arxiv(query)
        self.assertIn("# arXiv Search Results", page_source,
                      "arXiv search results should contain the header '# arXiv Search Results'.")
        self.assertIn("Link", page_source,
                      "arXiv search results should include a paper link.")


if __name__ == '__main__':
    unittest.main()
