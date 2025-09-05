import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Weaviate configuration
WEAVIATE_URL = os.getenv('WCD_URL')
WEAVIATE_API_KEY = os.getenv('WCD_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_APIKEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# App configuration
APP_TITLE = "Summit Sports"
APP_ICON = "images/logo.png"
DEFAULT_TENANTS = ["HR", "Finance", "Customer-Service"]
