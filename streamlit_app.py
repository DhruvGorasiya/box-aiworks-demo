
import streamlit as st
import requests
import json
from typing import List, Dict, Any
import time
import os
from dotenv import load_dotenv


import streamlit as st
from search_functions import (
    fetch_tenants, fetch_documents, search_documents, 
    query_agent, filter_documents_locally
)
from connect_and_collection import weaviate_client
from config import APP_TITLE, APP_ICON

import base64
from pathlib import Path

def _b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()

def read_full_documents(tenant: str) -> List[Dict]:
    """Read full documents from the data/[tenant] directory"""
    try:
        # Map tenant names to directory names
        tenant_dirs = {
            "HR": "HR",
            "Finance": "Finance", 
            "Customer-Service": "Customer-Service"
        }
        
        if tenant not in tenant_dirs:
            return []
        
        data_dir = f"data/{tenant_dirs[tenant]}"
        documents = []
        
        if os.path.exists(data_dir):
            for filename in os.listdir(data_dir):
                if filename.endswith('.md'):
                    file_path = os.path.join(data_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            content = file.read()
                            documents.append({
                                "file_name": filename,
                                "content": content,
                                "file_path": file_path,
                                "file_type": "markdown"
                            })
                    except Exception as e:
                        st.warning(f"Could not read file {filename}: {e}")
        
        return documents
    except Exception as e:
        st.error(f"Error reading full documents: {e}")
        return []

# Load environment variables from .env file
load_dotenv()

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Get API URL from environment variable or use default
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.markdown("""
<style>
  :root{
    --brand-1: #667eea;
    --brand-2: #764ba2;
    --brand-3: #f093fb;
    --brand-4: #f5576c;
    --ink: #1a1a2e;
    --sub: #6b7280;
    --card: #ffffff;
    --card-border: #e5e7eb;
    --chip: #eef2ff;
    --accent: #3b82f6;
    --accent-light: #dbeafe;
    --success: #10b981;
    --warning: #f59e0b;
    --error: #ef4444;
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  }

  /* App background with original image and improved overlay */
  [data-testid="stAppViewContainer"] {
      background-image: url("https://images.unsplash.com/photo-1554629947-334ff61d85dc?q=80&w=1336&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3Dd");
      background-size: cover;
      background-repeat: no-repeat;
      background-position: center;
      background-attachment: fixed;
      min-height: 100vh;
  }
  
  /* Add a subtle overlay for better text readability */
  [data-testid="stAppViewContainer"]::before {
      content: '';
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.3);
      pointer-events: none;
      z-index: 0;
  }
  
  /* Ensure content is above overlay */
  .main .block-container {
      position: relative;
      z-index: 1;
  }
            
/* Make the Streamlit header bar transparent */
[data-testid="stHeader"] {
    background-color: rgba(0, 0, 0, 0) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
}

/* Logos in the existing white band at the top (no background) */
.top-logos {
  position: fixed;
  top: 8px;
  left: 0;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 36px;
  z-index: 1000;
  background: transparent;
}

/* Sidebar logos */
[data-testid="stSidebar"] .sidebar-logos{
  display:flex;
  justify-content:center;
  align-items:center;
  gap:20px;
  padding:20px 0 24px;
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

[data-testid="stSidebar"] .sidebar-logos img{
  height:36px;
  display:block;
  filter: brightness(1.1);
}

.top-logos img {
  height: 40px;  
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
}

/* Enhanced sidebar with modern gradient */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e3a8a 0%, #1e40af 25%, #3b82f6 50%, #6366f1 75%, #8b5cf6 100%) !important;
    color: #f8fafc !important;
    box-shadow: var(--shadow-xl) !important;
}

/* Sidebar headings with better typography */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6 {
    color: #ffffff !important;
    font-weight: 700 !important;
    text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    margin-bottom: 16px !important;
}

/* Sidebar labels with improved styling */
[data-testid="stSidebar"] label {
    color: #e2e8f0 !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    margin-bottom: 8px !important;
}

/* Enhanced sidebar buttons */
[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 24px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    cursor: pointer;
    transition: all 0.3s ease !important;
    box-shadow: var(--shadow-md) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: var(--shadow-lg) !important;
    background: linear-gradient(135deg, #f5576c 0%, #f093fb 100%) !important;
}

[data-testid="stSidebar"] div[data-testid="stButton"] > button:disabled {
    background: linear-gradient(135deg, #9ca3af 0%, #6b7280 100%) !important;
    color: #ffffff !important;
    cursor: not-allowed;
    transform: none !important;
    box-shadow: var(--shadow-sm) !important;
}

/* Enhanced main title */
.main-header{
    font-size: 3.5rem;
    font-weight: 900;
    line-height: 1.1;
    text-align: center;
    margin: 0 0 1rem 0;
    color: #ffffff !important;
    text-shadow: 0 4px 8px rgba(0,0,0,0.5);
    letter-spacing: -0.02em;
    -webkit-text-stroke: 1px rgba(255, 255, 255, 0.8);
}

/* Enhanced subheading */
.subheader{
    text-align: center;
    font-size: 1.25rem;
    color: rgba(255, 255, 255, 0.9);
    margin-bottom: 2rem;
    font-weight: 500;
    text-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

/* Enhanced tenant cards */
.tenant-card,
.tenant-btn{
    display: block;
    width: 100%;
    text-align: center;
    padding: 1.5rem;
    border-radius: 16px;
    border: 2px solid rgba(255, 255, 255, 0.2);
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0.05) 100%);
    backdrop-filter: blur(10px);
    color: white;
    box-shadow: var(--shadow-lg);
    cursor: pointer;
    transition: all 0.3s ease;
    font-weight: 600;
    font-size: 1.1rem;
}

.tenant-card:hover,
.tenant-btn:hover{
    transform: translateY(-4px) scale(1.02);
    box-shadow: var(--shadow-xl);
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.25) 0%, rgba(255, 255, 255, 0.1) 100%);
    border-color: rgba(255, 255, 255, 0.4);
}

/* Enhanced document cards */
.document-card{
    background: rgba(255, 255, 255, 0.95);
    padding: 1.5rem;
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    box-shadow: var(--shadow-lg);
    margin: 1rem 0;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}

.document-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-xl);
    background: rgba(255, 255, 255, 1);
}

.document-card h4{
    margin: 0 0 1rem 0;
    font-size: 1.2rem;
    color: #1f2937;
    font-weight: 700;
    line-height: 1.4;
}

.document-card p{
    margin: 0.5rem 0;
    color: #374151;
    line-height: 1.6;
    font-size: 1rem;
}

.document-card small{
    color: #6b7280;
    font-size: 0.875rem;
    font-weight: 500;
}

.document-card strong{
    color: #1f2937;
    font-weight: 700;
}

/* Enhanced search type badges */
.search-type-badge{
    display: inline-block;
    padding: 0.5rem 1rem;
    border-radius: 50px;
    font-size: 0.875rem;
    font-weight: 700;
    margin: 0.25rem 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    box-shadow: var(--shadow-sm);
}

.keyword { 
    background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%); 
    color: #1e40af; 
    border: 1px solid #93c5fd;
}
.vector { 
    background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%); 
    color: #7c3aed; 
    border: 1px solid #c4b5fd;
}
.hybrid { 
    background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); 
    color: #059669; 
    border: 1px solid #6ee7b7;
}
.generative { 
    background: linear-gradient(135deg, #fed7aa 0%, #fdba74 100%); 
    color: #c2410c; 
    border: 1px solid #fb923c;
}

/* Enhanced section headers */
h2 {
    color: #ffffff !important; 
    font-weight: 700 !important;
    font-size: 1.5rem !important;
    margin-bottom: 1.5rem !important;
    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Enhanced text input labels */
div.stTextInput label {
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    margin-bottom: 8px !important;
    text-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

/* Enhanced text inputs */
div.stTextInput > div > div > input {
    background: rgba(255, 255, 255, 0.9) !important;
    border: 2px solid rgba(255, 255, 255, 0.3) !important;
    border-radius: 12px !important;
    padding: 12px 16px !important;
    font-size: 1rem !important;
    color: #1f2937 !important;
    box-shadow: var(--shadow-sm) !important;
    transition: all 0.3s ease !important;
}

div.stTextInput > div > div > input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    background: #ffffff !important;
}

/* Enhanced selectbox styling */
div.stSelectbox > div > div {
    background: rgba(255, 255, 255, 0.9) !important;
    border: 2px solid rgba(255, 255, 255, 0.3) !important;
    border-radius: 12px !important;
    box-shadow: var(--shadow-sm) !important;
}

div.stSelectbox label {
    color: #ffffff !important;
    font-weight: 700 !important;
    text-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

/* Enhanced slider styling */
div.stSlider > div > div > div {
    background: rgba(255, 255, 255, 0.9) !important;
    border-radius: 12px !important;
    padding: 8px !important;
}

/* Slider labels styling */
div.stSlider label {
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    text-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
}

/* Slider value labels (min/max) */
div.stSlider > div > div > div > div {
    color: #dc2626 !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}

/* Slider current value */
div.stSlider > div > div > div > div:first-child {
    color: #dc2626 !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
}

/* Additional targeting for slider min/max values */
div.stSlider > div > div > div > div:last-child,
div.stSlider > div > div > div > div:nth-child(2),
div.stSlider > div > div > div > div:nth-child(3) {
    color: #dc2626 !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}

/* Target all text within slider container */
div.stSlider * {
    color: #dc2626 !important;
}

/* Enhanced metric containers */
[data-testid="metric-container"] {
    background: rgba(255, 255, 255, 0.95) !important;
    border: 2px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 16px !important;
    color: #1f2937 !important;
    padding: 1.5rem !important;
    box-shadow: var(--shadow-lg) !important;
    backdrop-filter: blur(10px) !important;
}

[data-testid="metric-container"] [data-testid="metric-value"] {
    color: #1f2937 !important;
    font-weight: 800 !important;
    font-size: 2rem !important;
}

[data-testid="metric-container"] [data-testid="metric-label"] {
    color: #6b7280 !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
}

/* Enhanced success, info, warning messages */
.stSuccess {
    background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%) !important;
    color: #059669 !important;
    border: 1px solid #6ee7b7 !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    font-weight: 600 !important;
}

.stInfo {
    background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%) !important;
    color: #1e40af !important;
    border: 1px solid #93c5fd !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    font-weight: 600 !important;
}

.stWarning {
    background: linear-gradient(135deg, #fed7aa 0%, #fdba74 100%) !important;
    color: #c2410c !important;
    border: 1px solid #fb923c !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    font-weight: 600 !important;
}

/* Enhanced footer */
.footer-text {
    color: rgba(255, 255, 255, 0.8) !important;
    text-align: center !important;
    padding: 2rem !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    text-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

.footer-text strong {
    color: #ffffff !important;
    font-weight: 700 !important;
}

/* Enhanced container styling */
.stContainer {
    background: rgba(255, 255, 255, 0.05) !important;
    border-radius: 16px !important;
    padding: 1.5rem !important;
    margin: 1rem 0 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    backdrop-filter: blur(10px) !important;
}

/* Responsive design improvements */
@media (max-width: 768px) {
    .main-header {
        font-size: 2.5rem;
    }
    
    .subheader {
        font-size: 1.125rem;
    }
    
    .document-card {
        padding: 1rem;
    }
    
    .tenant-card,
    .tenant-btn {
        padding: 1rem;
    }
}

/* Smooth scrolling */
html {
    scroll-behavior: smooth;
}

/* Custom scrollbar */
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.3);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.5);
}

/* Animations */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes fadeIn {
    from {
        opacity: 0;
    }
    to {
        opacity: 1;
    }
}

@keyframes slideInLeft {
    from {
        opacity: 0;
        transform: translateX(-30px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

@keyframes slideInRight {
    from {
        opacity: 0;
        transform: translateX(30px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

/* Apply animations to main elements */
.main .block-container {
    animation: fadeIn 0.6s ease-out;
}

[data-testid="stSidebar"] {
    animation: slideInLeft 0.6s ease-out;
}

/* Pulse animation for interactive elements */
@keyframes pulse {
    0% {
        box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4);
    }
    70% {
        box-shadow: 0 0 0 10px rgba(59, 130, 246, 0);
    }
    100% {
        box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
    }
}

/* Hover effects for cards */
.document-card:hover,
.tenant-card:hover,
.tenant-btn:hover {
    animation: pulse 2s infinite;
}

/* Loading animation */
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.loading {
    animation: spin 1s linear infinite;
}

/* Removed gradient text animation for solid text */

/* Document content styling for black text */
.document-content h1, .document-content h2, .document-content h3, .document-content h4, .document-content h5, .document-content h6 {
    color: #000000 !important;
}
.document-content strong, .document-content b {
    color: #000000 !important;
}

</style>
""", unsafe_allow_html=True)


# st.markdown("""
# <style>
#     /* Page background */
#     [data-testid="stAppViewContainer"] {
#         background-image: url("https://images.unsplash.com/photo-1501426026826-31c667bdf23d");
#         background-size: cover;
#         background-repeat: no-repeat;
#         background-position: center;
#     }


#     .main-header {
#         font-size: 3rem;
#         font-weight: bold;
#         text-align: center;
#         margin-bottom: 2rem;
#         color: black !important;
#         background: none
#         -webkit-background-clip: text;
#         -webkit-text-fill-color: black !important;
#     }
#     .tenant-card {
#         padding: 2rem;
#         border-radius: 15px;
#         color: white;
#         text-align: center;
#         cursor: pointer;
#         transition: transform 0.3s;
#         margin: 1rem 0;
#     }
#     .tenant-card:hover {
#         transform: translateY(-5px);
#     }
#     .search-container {
#         background: #f8f9fa;
#         padding: 2rem;
#         border-radius: 15px;
#         margin: 2rem 0;
#     }
#     .document-card {
#         background: #ffffff;
#         padding: 1.5rem;
#         border-radius: 10px;
#         box-shadow: 0 2px 10px rgba(0,0,0,0.1);
#         margin: 1rem 0;
#         border-left: 4px solid #667eea;
#         color: #000000 !important;
#     }
#     .document-card h4 {
#         color: #1a1a1a !important;
#         margin-bottom: 1rem;
#         font-size: 1.2rem;
#         font-weight: bold;
#     }
#     .document-card p {
#         color: #2d2d2d !important;
#         line-height: 1.6;
#         margin-bottom: 0.5rem;
#         font-size: 1rem;
#     }
#     .document-card small {
#         color: #4a4a4a !important;
#         font-size: 0.9rem;
#     }
#     .document-card strong {
#         color: #1a1a1a !important;
#         font-weight: bold;
#     }
#     .search-type-badge {
#         display: inline-block;
#         padding: 0.25rem 0.75rem;
#         border-radius: 20px;
#         font-size: 0.8rem;
#         font-weight: bold;
#         margin: 0.25rem;
#     }
#     .keyword { background: #e3f2fd; color: #1976d2; }
#     .vector { background: #f3e5f5; color: #7b1fa2; }
#     .hybrid { background: #e8f5e8; color: #388e3c; }
#     .generative { background: #fff3e0; color: #f57c00; }
    
#     .document-card * {
#         color: #2d2d2d !important;
#     }
    
#     .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
#         color: white !important;
#     }
    
#     .stSidebar h1, .stSidebar h2, .stSidebar h3, .stSidebar h4, .stSidebar h5, .stSidebar h6 {
#         color: #334155 !important;
#     }
    
#     .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
#         color: white !important;
#     }
    
#     .document-card h1, .document-card h2, .document-card h3, .document-card h4, .document-card h5, .document-card h6 {
#         color: #1a1a1a !important;
#     }
    
#     .stMarkdown p {
#         color: #2d2d2d !important;
#     }
# </style>
# """, unsafe_allow_html=True)

def main():

    left, right = st.columns([0.25, 0.75])
    with left:
        st.image("images/logo.png", width=400)
        # st.markdown('<img src="images/logo.png" class="logo-img">', unsafe_allow_html=True)
    with right:
        st.markdown('<h1 class="main-header">Summit Sports</h1>', unsafe_allow_html=True)
        st.markdown('<p class="subheader">Advanced Search & AI-Powered Document Discovery</p>', unsafe_allow_html=True)
    
    if 'selected_tenant' not in st.session_state:
        st.session_state.selected_tenant = None
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'all_documents' not in st.session_state:
        st.session_state.all_documents = []
    if 'current_view' not in st.session_state:
        st.session_state.current_view = "documents"
    
    with st.sidebar:
        weaviate_b64 = _b64("images/weaviate-logo.png")
        box_b64 = _b64("images/box-logo.png")

        # top logos row (centered in the white strip)
        st.markdown(
            f"""
            <div class="sidebar-logos">
                <img src="data:image/png;base64,{weaviate_b64}" alt="Weaviate" />
                <img src="data:image/png;base64,{box_b64}" alt="Box" />
            </div>
            """,
            unsafe_allow_html=True
        )


        st.header(" Search Controls")
        
        search_type = st.selectbox(
            "Search Type",
            ["hybrid", "keyword", "vector", "generative"],
            help="Choose the type of search to perform"
        )
        
        if search_type == "hybrid":
            alpha = st.slider(
                "Alpha Parameter",
                min_value=0.0,
                max_value=1.0,
                value=0.5,
                step=0.1,
                help="0.0 = pure keyword search, 1.0 = pure vector search"
            )
        else:
            alpha = 0.5
        
        search_query = st.text_input(
            "Search Query",
            placeholder="Enter your search query...",
            help="Type your search query here"
        )
        
        if st.button("🔍 Search", type="primary"):
            if search_query and st.session_state.selected_tenant:
                with st.spinner("Searching..."):
                    results = search_documents(
                        search_query, 
                        st.session_state.selected_tenant, 
                        search_type, 
                        alpha
                    )
                    if results and results.get('documents'):
                        st.session_state.search_results = results
                        st.session_state.current_view = "search"
                        st.success(f"Found {len(results['documents'])} results!")
                    else:
                        st.warning("No results found. Try a different query.")
            else:
                st.warning("Please select a department and enter a search query.")
        
        if st.button("🗑️ Clear Search"):
            st.session_state.search_results = None
            st.session_state.current_view = "documents"
            st.rerun()
        
        st.header(" AI Agent")
        agent_query = st.text_input(
            "Agent Query",
            placeholder="Ask a complex question...",
            help="Use the AI agent for complex queries"
        )
        
        if st.button("🤖 Query Agent"):
            if agent_query and st.session_state.selected_tenant:
                with st.spinner("Agent is thinking..."):
                    agent_response = query_agent(agent_query, st.session_state.selected_tenant)
                    if agent_response:
                        st.session_state.agent_response = agent_response
                        st.session_state.current_view = "agent"
                        st.success("Agent response generated!")
                    else:
                        st.error("Agent query failed. Please try again.")
            else:
                st.warning("Please select a department and enter a query.")
    
    # Add a visual separator
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("""
        <div style="background: rgba(255, 255, 255, 0.1); padding: 1.5rem; border-radius: 16px; margin-bottom: 2rem; border: 1px solid rgba(255, 255, 255, 0.2); backdrop-filter: blur(10px);">
            <h2 style="color: #ffffff; margin-bottom: 1rem; text-align: center;">📁 Select Department</h2>
        </div>
        """, unsafe_allow_html=True)
        
        tenants = fetch_tenants()
        if tenants:
            for i, tenant in enumerate(tenants):
                # Add a subtle animation delay for each card
                animation_delay = i * 0.1
                if st.button(
                    f"**{tenant['name']}**\n\n📄 {tenant['document_count']} documents",
                    key=f"tenant_{tenant['name']}",
                    use_container_width=True,
                ):
                    st.session_state.selected_tenant = tenant['name']
                    st.session_state.search_results = None
                    st.session_state.current_view = "documents"
                    st.session_state.all_documents = fetch_documents(tenant['name'])
                    st.session_state.document_view_type = None  # Always reset view type to show selection
                    st.rerun()
        else:
            st.error("Unable to fetch tenants. Please check your API connection.")
    
    with col2:
        if st.session_state.selected_tenant:
            # Enhanced status display
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(5, 150, 105, 0.1) 100%); padding: 1.5rem; border-radius: 16px; margin-bottom: 1.5rem; border: 2px solid rgba(16, 185, 129, 0.3); backdrop-filter: blur(10px);">
                <h3 style="color: #ffffff; margin: 0 0 0.5rem 0; font-size: 1.25rem;">✅ Selected: <strong>{st.session_state.selected_tenant}</strong></h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Check if we should show search results
            if st.session_state.current_view == "search" and st.session_state.search_results:
                # Enhanced search results header
                st.markdown("""
                <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(99, 102, 241, 0.1) 100%); padding: 2rem; border-radius: 16px; margin-bottom: 2rem; border: 2px solid rgba(59, 130, 246, 0.3); backdrop-filter: blur(10px);">
                    <h2 style="color: #ffffff; margin: 0 0 1.5rem 0; text-align: center; font-size: 2rem;">🔍 Search Results</h2>
                </div>
                """, unsafe_allow_html=True)
                
                # Enhanced search info display
                search_type_badge = f'<span class="search-type-badge {st.session_state.search_results["search_type"]}">{st.session_state.search_results["search_type"].upper()}</span>'
                
                col_info1, col_info2, col_info3 = st.columns(3)
                with col_info1:
                    st.markdown(f"""
                    <div style="background: rgba(255, 255, 255, 0.1); padding: 1rem; border-radius: 12px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.2);">
                        <p style="color: #ffffff; margin: 0; font-weight: 600;">Search Type</p>
                        <div style="margin-top: 0.5rem;">{search_type_badge}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_info2:
                    st.markdown(f"""
                    <div style="background: rgba(255, 255, 255, 0.1); padding: 1rem; border-radius: 12px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.2);">
                        <p style="color: #ffffff; margin: 0; font-weight: 600;">Query</p>
                        <p style="color: #ffffff; margin: 0.5rem 0 0 0; font-size: 0.9rem;">{st.session_state.search_results['query']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_info3:
                    st.markdown(f"""
                    <div style="background: rgba(255, 255, 255, 0.1); padding: 1rem; border-radius: 12px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.2);">
                        <p style="color: #ffffff; margin: 0; font-weight: 600;">Results Found</p>
                        <p style="color: #ffffff; margin: 0.5rem 0 0 0; font-size: 1.5rem; font-weight: 700;">{st.session_state.search_results['total_count']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Enhanced document display
                for i, doc in enumerate(st.session_state.search_results['documents']):
                    with st.container():
                        # Check if this is a generated response
                        is_generated = doc.get('file_name') == 'AI Generated Response'
                        
                        if is_generated:
                            # Show full content for generated responses
                            st.markdown(f"""
                            <div class="document-card" style="animation: fadeInUp 0.5s ease-out {i * 0.1}s both;">
                                <h4>🤖 {doc['file_name']}</h4>
                                <p><strong>Generated Answer:</strong></p>
                                <div style="background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); padding: 1.5rem; border-radius: 12px; margin: 1rem 0; border: 1px solid #cbd5e1; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                                    {doc['content']}
                                </div>
                                <small>Date: {doc['created_date']}</small>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            # Truncate regular documents
                            st.markdown(f"""
                            <div class="document-card" style="animation: fadeInUp 0.5s ease-out {i * 0.1}s both;">
                                <h4>📄 {doc['file_name']} (Chunk {doc['chunk_index']})</h4>
                                <p><strong>Content:</strong> {doc['content']}</p>
                                <small>ID: {doc['id'][:8]}... | Date: {doc['created_date']}</small>
                            </div>
                            """, unsafe_allow_html=True)
            
            # Check if we should show agent response
            elif st.session_state.current_view == "agent" and hasattr(st.session_state, 'agent_response') and st.session_state.agent_response:
                agent_resp = st.session_state.agent_response
                
                # Display the beautifully formatted agent response using the pretty_text from search_functions.py
                if agent_resp.get('pretty_text'):
                    st.markdown("""
                    <div style="background: #ffffff; padding: 2rem; border-radius: 12px; margin: 1rem 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    """, unsafe_allow_html=True)
                    
                    # Clean the text to handle Unicode surrogates
                    try:
                        # Try to encode and decode to handle surrogates
                        clean_text = agent_resp['pretty_text'].encode('utf-8', errors='replace').decode('utf-8')
                        
                        # Use text_area with proper styling for better text wrapping
                        st.text_area(
                            value=clean_text, 
                            height=400, 
                            disabled=True, 
                            key="agent_response_display",
                            help="AI Agent Response"
                        )
                    except Exception as e:
                        # Fallback: display as markdown with monospace font and proper wrapping
                        # Apply the same encoding fix to handle Unicode surrogates
                        try:
                            clean_fallback_text = agent_resp['pretty_text'].encode('utf-8', errors='replace').decode('utf-8')
                        except:
                            clean_fallback_text = str(agent_resp['pretty_text']).encode('utf-8', errors='replace').decode('utf-8')
                        
                        st.markdown(f"""
                        <div style="font-family: 'Courier New', monospace; white-space: pre-wrap; word-wrap: break-word; overflow-wrap: break-word; background: #f8f9fa; padding: 1rem; border-radius: 8px; border: 1px solid #dee2e6; max-width: 100%;">
                            {clean_fallback_text}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Close the container
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    # Fallback to the old display if pretty_text is not available
                    st.markdown("""
                    <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.2) 0%, rgba(168, 85, 247, 0.1) 100%); padding: 2rem; border-radius: 16px; margin-bottom: 2rem; border: 2px solid rgba(139, 92, 246, 0.3); backdrop-filter: blur(10px);">
                        <h2 style="color: #ffffff; margin: 0 0 1.5rem 0; text-align: center; font-size: 2rem;">🤖 AI Agent Response</h2>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Enhanced agent info display
                    agent_badge = '<span class="search-type-badge generative">AGENT</span>'
                    
                    col_agent1, col_agent2 = st.columns(2)
                    with col_agent1:
                        st.markdown(f"""
                        <div style="background: rgba(255, 255, 255, 0.1); padding: 1rem; border-radius: 12px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.2);">
                            <p style="color: #ffffff; margin: 0; font-weight: 600;">Response Type</p>
                            <div style="margin-top: 0.5rem;">{agent_badge}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_agent2:
                        st.markdown(f"""
                        <div style="background: rgba(255, 255, 255, 0.1); padding: 1rem; border-radius: 12px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.2);">
                            <p style="color: #ffffff; margin: 0; font-weight: 600;">Query</p>
                            <p style="color: #ffffff; margin: 0.5rem 0 0 0; font-size: 0.9rem;">{agent_resp['query']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Enhanced agent response display
                    st.markdown(f"""
                    <div class="document-card" style="animation: fadeInUp 0.5s ease-out;">
                        <h4>🤖 AI Agent Response</h4>
                        <p><strong>Generated Answer:</strong></p>
                        <div style="background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); padding: 2rem; border-radius: 16px; margin: 1.5rem 0; border: 2px solid #cbd5e1; box-shadow: 0 4px 6px rgba(0,0,0,0.05); line-height: 1.7;">
                            {agent_resp.get('answer', 'No answer available')}
                        </div>
                        <small>Generated by AI Agent | Query: {agent_resp['query'][:50]}{'...' if len(agent_resp['query']) > 50 else ''}</small>
                    </div>
                    """, unsafe_allow_html=True)

                    # Display source documents if available
                    if agent_resp.get('source_documents'):
                        st.markdown("""
                        <div style="margin-top: 2rem;">
                            <h3 style="color: #ffffff; margin-bottom: 1.5rem; text-align: center; font-size: 1.5rem;">📚 Source Documents</h3>
                            <p style="color: rgba(255, 255, 255, 0.8); text-align: center; margin-bottom: 1.5rem;">Documents referenced by the AI Agent to generate the response</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Display each source document
                        for i, doc in enumerate(agent_resp['source_documents']):
                            st.markdown(f"""
                            <div class="document-card" style="animation: fadeInUp 0.5s ease-out {i * 0.1}s both; margin-bottom: 1rem;">
                                <p><strong>Content:</strong> {doc.get('content', 'No content available')}</p>
                                <small>ID: {doc.get('id', 'N/A')[:8]}... | Date: {doc.get('created_date', 'N/A')} | Score: {doc.get('score', 'N/A')}</small>
                            </div>
                            """, unsafe_allow_html=True)

            
            # Show document view selection only if not showing search results or agent response
            elif st.session_state.current_view not in ["search", "agent"]:
                # Document view type selection - always show buttons
                st.markdown("""
                <div style="background: rgba(255, 255, 255, 0.1); padding: 1.5rem; border-radius: 16px; margin-bottom: 2rem; border: 1px solid rgba(255, 255, 255, 0.2); backdrop-filter: blur(10px);">
                    <h3 style="color: #ffffff; margin: 0 0 1rem 0; text-align: center;">Choose Document View</h3>
                </div>
                """, unsafe_allow_html=True)
                
                col_chunks, col_docs = st.columns(2)
                
                with col_chunks:
                    if st.button("📄 Chunks", use_container_width=True, help="View document chunks for search"):
                        st.session_state.document_view_type = "chunks"
                        st.session_state.all_documents = fetch_documents(st.session_state.selected_tenant)
                        st.rerun()
                
                with col_docs:
                    if st.button("📚 All Documents", use_container_width=True, help="View complete documents"):
                        st.session_state.document_view_type = "full_documents"
                        st.session_state.all_documents = read_full_documents(st.session_state.selected_tenant)
                        st.rerun()
                
                # Show message only if no view type is selected
                if st.session_state.document_view_type is None:
                    st.markdown(f"""
                    <div style="background: rgba(255, 255, 255, 0.1); padding: 2rem; border-radius: 16px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.2); backdrop-filter: blur(10px);">
                        <h3 style="color: #ffffff; margin: 0 0 1rem 0;">👆 Please select a document view above</h3>
                        <p style="color: rgba(255, 255, 255, 0.8); margin: 0;">Choose either "Chunks" or "All Documents" to view the {st.session_state.selected_tenant} documents.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    return  # Exit early without showing documents
                
                # Document display based on view type - only show when user explicitly chooses
                if st.session_state.document_view_type == "chunks":
                    # Show chunks only when user clicks "Chunks" button
                    documents = st.session_state.all_documents
                    if documents:
                        for i, doc in enumerate(documents[:10]):
                            with st.container():
                                st.markdown(f"""
                                <div class="document-card" style="animation: fadeInUp 0.5s ease-out {i * 0.1}s both;">
                                    <h4> {doc['file_name']} (Chunk {doc.get('chunk_index', 'N/A')})</h4>
                                    <p><strong>Content:</strong> {doc['content']}...</p>
                                    <small>ID: {doc.get('id', 'N/A')[:8]}... | Date: {doc.get('created_date', 'N/A')}</small>
                                </div>
                                """, unsafe_allow_html=True)
                    
                    if len(documents) > 10:
                        st.markdown(f"""
                        <div style="background: rgba(255, 255, 255, 0.1); padding: 1rem; border-radius: 12px; margin: 1rem 0; border: 1px solid rgba(255, 255, 255, 0.2); text-align: center;">
                            <p style="color: #ffffff; margin: 0; font-weight: 600;">Showing first 10 of {len(documents)} documents.</p>
                        </div>
                        """, unsafe_allow_html=True)

                elif st.session_state.document_view_type == "full_documents":
                    # Show full documents only when user clicks "All Documents" button
                    documents = st.session_state.all_documents
                    if documents:
                        for i, doc in enumerate(documents):
                            with st.container():
                                # Create a unique key for each document's expand state
                                expand_key = f"expand_full_doc_{i}"
                                
                                # Initialize expand state if not exists
                                if expand_key not in st.session_state:
                                    st.session_state[expand_key] = False
                                
                                # Clickable document card
                                if st.button(
                                    f"📚 {doc['file_name']}\n\n"
                                    f"Content: {doc['content'][:200]}{'...' if len(doc['content']) > 200 else ''}",
                                    key=f"full_doc_button_{i}",
                                    use_container_width=True,
                                    help="Click to view the entire document"
                                ):
                                    st.session_state[expand_key] = not st.session_state[expand_key]
                                    st.rerun()
                                
                                # Show full content if expanded
                                if st.session_state[expand_key]:
                                    # Clean the content by removing ALL HTML tags
                                    import re
                                    clean_content = re.sub(r'<[^>]+>', '', doc['content'])
                                    
                                    st.markdown(f"""
                                    <div class="document-card" style="animation: fadeInUp 0.5s ease-out; margin-top: 1rem; background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); border: 2px solid #cbd5e1; border-radius: 12px; padding: 1.5rem;">
                                        <h4>📚 Full Document - {doc['file_name']}</h4>
                                        <div style="background: #ffffff; padding: 1.5rem; border-radius: 12px; margin: 1rem 0; border: 1px solid #e5e7eb; line-height: 1.6; max-height: 500px; overflow-y: auto; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                            <div style="color: #000000 !important; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; white-space: pre-wrap;">
                                                <div class="document-content">
                                                    {clean_content}
                                                    
                                                
                                    """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.2) 0%, rgba(217, 119, 6, 0.1) 100%); padding: 2rem; border-radius: 16px; margin: 2rem 0; border: 2px solid rgba(245, 158, 11, 0.3); text-align: center;">
                            <h3 style="color: #ffffff; margin: 0 0 1rem 0;">⚠️ No Documents Found</h3>
                            <p style="color: rgba(255, 255, 255, 0.8); margin: 0;">No documents found for this tenant. Please check your data or try a different department.</p>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: rgba(255, 255, 255, 0.1); padding: 2rem; border-radius: 16px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.2); backdrop-filter: blur(10px);">
                <h3 style="color: #ffffff; margin: 0 0 1rem 0;">👈 Select a department to get started</h3>
                <p style="color: rgba(255, 255, 255, 0.8); margin: 0;">Choose a department from the left panel to view documents and start searching.</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("""
    <div class="footer-text" style="text-align: center; padding: 2rem;">
        <p> Powered by <strong>Weaviate</strong> | Built with <strong>FastAPI</strong> & <strong>Streamlit</strong></p>
        <p>Features: Keyword Search | Vector Search | Hybrid Search | Generative AI | Query Agent</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
