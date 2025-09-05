
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
    /* Logo positioning */
    .logo-container {
        position: fixed;
        top: 10px;
        left: 10px;
        z-index: 1000;
        background: rgba(255, 255, 255, 0.95);
        padding: 8px 12px;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
    }
    
    .logo-container img {
        height: 40px;
        width: auto;
        max-width: 150px;
        border-radius: 8px; /* This makes the logo corners rounded */
    }
    
    /* Style the Streamlit image directly */
    .stImage img {
        border-radius: 12px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    /* Adjust main content to account for logo */
    .main .block-container {
        padding-top: 80px;
    }
    
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .tenant-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        cursor: pointer;
        transition: transform 0.3s;
        margin: 1rem 0;
    }
    .tenant-card:hover {
        transform: translateY(-5px);
    }
    .search-container {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 15px;
        margin: 2rem 0;
    }
    .document-card {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 4px solid #667eea;
        color: #000000 !important;
    }
    .document-card h4 {
        color: #1a1a1a !important;
        margin-bottom: 1rem;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .document-card p {
        color: #2d2d2d !important;
        line-height: 1.6;
        margin-bottom: 0.5rem;
        font-size: 1rem;
    }
    .document-card small {
        color: #4a4a4a !important;
        font-size: 0.9rem;
    }
    .document-card strong {
        color: #1a1a1a !important;
        font-weight: bold;
    }
    .search-type-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
        margin: 0.25rem;
    }
    .keyword { background: #e3f2fd; color: #1976d2; }
    .vector { background: #f3e5f5; color: #7b1fa2; }
    .hybrid { background: #e8f5e8; color: #388e3c; }
    .generative { background: #fff3e0; color: #f57c00; }
    
    .document-card * {
        color: #2d2d2d !important;
    }
    
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: white !important;
    }
    
    .stSidebar h1, .stSidebar h2, .stSidebar h3, .stSidebar h4, .stSidebar h5, .stSidebar h6 {
        color: white !important;
    }
    
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        color: white !important;
    }
    
    .document-card h1, .document-card h2, .document-card h3, .document-card h4, .document-card h5, .document-card h6 {
        color: #1a1a1a !important;
    }
    
    .stMarkdown p {
        color: #2d2d2d !important;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Add logo using Streamlit's native method
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        try:
            st.image("logo.png", width=150)
        except:
            st.write("Logo not found")
    
    st.markdown('<h1 class="main-header">🔍 Weaviate Enterprise Search</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">Advanced Search & AI-Powered Document Discovery</p>', unsafe_allow_html=True)
    
    if 'selected_tenant' not in st.session_state:
        st.session_state.selected_tenant = None
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'all_documents' not in st.session_state:
        st.session_state.all_documents = []
    if 'current_view' not in st.session_state:
        st.session_state.current_view = "documents"
    
    with st.sidebar:
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
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 Select Department")
        
        tenants = fetch_tenants()
        if tenants:
            cols = st.columns(len(tenants))
            for i, tenant in enumerate(tenants):
                with cols[i]:
                    if st.button(
                        f"**{tenant['name']}**\n\n📄 {tenant['document_count']} documents",
                        key=f"tenant_{tenant['name']}",
                        help=f"Click to view {tenant['name']} documents"
                    ):
                        st.session_state.selected_tenant = tenant['name']
                        st.session_state.search_results = None
                        st.session_state.current_view = "documents"
                        st.session_state.all_documents = fetch_documents(tenant['name'])
                        st.rerun()
        else:
            st.error("Unable to fetch tenants. Please check your API connection.")
    
    with col2:
        if st.session_state.selected_tenant:
            st.success(f"✅ Selected: **{st.session_state.selected_tenant}**")
            
            documents = st.session_state.all_documents
            st.metric("Total Documents", len(documents))
            
            view_icons = {
                "documents": "📄",
                "search": "🔍", 
                "agent": "🤖"
            }
            st.info(f"{view_icons.get(st.session_state.current_view, '📄')} Viewing: {st.session_state.current_view.title()}")
        else:
            st.info("👈 Select a department to get started")
    
    if st.session_state.selected_tenant:
        if st.session_state.current_view == "search" and st.session_state.search_results:
            st.header("🔍 Search Results")
            
            search_type_badge = f'<span class="search-type-badge {st.session_state.search_results["search_type"]}">{st.session_state.search_results["search_type"].upper()}</span>'
            st.markdown(f"Search Type: {search_type_badge}", unsafe_allow_html=True)
            st.markdown(f"Query: **{st.session_state.search_results['query']}**")
            st.markdown(f"Found: **{st.session_state.search_results['total_count']}** results")
            
            for doc in st.session_state.search_results['documents']:
                with st.container():
                    # Check if this is a generated response
                    is_generated = doc.get('file_name') == 'AI Generated Response'
                    
                    if is_generated:
                        # Show full content for generated responses
                        st.markdown(f"""
                        <div class="document-card">
                            <h4>🤖 {doc['file_name']}</h4>
                            <p><strong>Generated Answer:</strong></p>
                            <div style="background: #f8f9fa; padding: 1rem; border-radius: 5px; margin: 1rem 0;">
                                {doc['content']}
                            </div>
                            <small>Date: {doc['created_date']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Truncate regular documents
                        st.markdown(f"""
                        <div class="document-card">
                            <h4> {doc['file_name']} (Chunk {doc['chunk_index']})</h4>
                            <p><strong>Content:</strong> {doc['content']}</p>
                            <small>ID: {doc['id'][:8]}... | Date: {doc['created_date']}</small>
                        </div>
                        """, unsafe_allow_html=True)
        
        elif st.session_state.current_view == "agent" and hasattr(st.session_state, 'agent_response') and st.session_state.agent_response:
            st.header("🤖 Agent Response")
            agent_resp = st.session_state.agent_response
            
            st.markdown(f"**Query:** {agent_resp['query']}")
            st.markdown(f"**Answer:** {agent_resp.get('answer', 'No answer available')}")
        
        else:
            st.header(f"📄 {st.session_state.selected_tenant} Documents")
            
            filter_text = st.text_input(
                "🔍 Filter Documents",
                placeholder="Type to filter documents by content...",
                help="Filter documents by typing keywords"
            )
            
            documents = st.session_state.all_documents
            if documents:
                filtered_documents = filter_documents_locally(documents, filter_text)
                
                if filter_text:
                    st.info(f"Showing {len(filtered_documents)} of {len(documents)} documents matching '{filter_text}'")
                
                for doc in filtered_documents[:10]:
                    with st.container():
                        st.markdown(f"""
                        <div class="document-card">
                            <h4> {doc['file_name']} (Chunk {doc['chunk_index']})</h4>
                            <p><strong>Content:</strong> {doc['content']}...</p>
                            <small>ID: {doc['id'][:8]}... | Date: {doc['created_date']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                
                if len(filtered_documents) > 10:
                    st.info(f"Showing first 10 of {len(filtered_documents)} filtered documents.")
            else:
                st.warning("No documents found for this tenant.")
    
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem;">
        <p> Powered by <strong>Weaviate</strong> | Built with <strong>FastAPI</strong> & <strong>Streamlit</strong></p>
        <p>Features: Keyword Search | Vector Search | Hybrid Search | Generative AI | Query Agent</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
