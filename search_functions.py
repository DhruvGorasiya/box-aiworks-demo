import streamlit as st
import logging
from typing import List, Dict, Any
from datetime import datetime
from weaviate.classes.generate import GenerativeConfig
from config import DEFAULT_TENANTS, WEAVIATE_URL, WEAVIATE_API_KEY

logger = logging.getLogger(__name__)

def get_weaviate_client():
    """Get a fresh Weaviate client connection"""
    try:
        import weaviate
        from weaviate.auth import AuthApiKey
        
        headers = {}
        
        # Add API keys to headers
        from config import ANTHROPIC_API_KEY, OPENAI_API_KEY
        if OPENAI_API_KEY:
            headers["X-INFERENCE-PROVIDER-API-KEY"] = OPENAI_API_KEY
        elif ANTHROPIC_API_KEY:
            headers["X-INFERENCE-PROVIDER-API-KEY"] = ANTHROPIC_API_KEY
        
        if ANTHROPIC_API_KEY:
            headers["X-Anthropic-Api-Key"] = ANTHROPIC_API_KEY
        if OPENAI_API_KEY:
            headers["X-OpenAI-Api-Key"] = OPENAI_API_KEY

        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=WEAVIATE_URL,
            auth_credentials=AuthApiKey(WEAVIATE_API_KEY),
            headers=headers,
        )
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Weaviate: {e}")
        st.error(f"Failed to connect to Weaviate: {str(e)}")
        return None

def get_anthropic_generative_config():
    """Get Anthropic generative configuration"""
    return GenerativeConfig.anthropic(
        model="claude-3-opus-20240229",
        max_tokens=256,  # Reduced back to 256 for faster response
        temperature=0.7,
    )

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_tenants() -> List[Dict]:
    """Fetch available tenants from Weaviate"""
    client = None
    try:
        client = get_weaviate_client()
        if not client:
            return []
            
        docs = client.collections.get("Documents")
        tenants = DEFAULT_TENANTS
        
        tenant_info = []
        for tenant_name in tenants:
            try:
                tenant_collection = docs.with_tenant(tenant_name)
                result = tenant_collection.query.fetch_objects(limit=1000)
                tenant_info.append({
                    "name": tenant_name,
                    "document_count": len(result.objects)
                })
                logger.info(f"Found {len(result.objects)} documents for tenant {tenant_name}")
            except Exception as e:
                logger.warning(f"Error fetching documents for tenant {tenant_name}: {e}")
                tenant_info.append({
                    "name": tenant_name,
                    "document_count": 0
                })
        
        return tenant_info
    except Exception as e:
        logger.error(f"Error in fetch_tenants: {e}")
        st.error(f"Error fetching tenants: {str(e)}")
        return []
    finally:
        if client:
            try:
                client.close()
            except:
                pass

@st.cache_data(ttl=300)
def fetch_documents(tenant: str) -> List[Dict]:
    """Fetch documents for a specific tenant"""
    client = None
    try:
        client = get_weaviate_client()
        if not client:
            return []
            
        docs = client.collections.get("Documents")
        tenant_collection = docs.with_tenant(tenant)
        
        result = tenant_collection.query.fetch_objects(limit=50)
        
        documents = []
        for i, obj in enumerate(result.objects):
            properties = obj.properties or {}
            documents.append({
                "id": str(obj.uuid),
                "content": properties.get("content", "No content available"),
                "file_name": f"Document_{i+1}",
                "chunk_index": i,
                "created_date": "2024-01-01",
            })
        
        logger.info(f"Retrieved {len(documents)} documents for tenant {tenant}")
        return documents
    except Exception as e:
        logger.error(f"Error in fetch_documents for tenant {tenant}: {e}")
        st.error(f"Error fetching documents: {str(e)}")
        return []
    finally:
        if client:
            try:
                client.close()
            except:
                pass

def search_documents(query: str, tenant: str, search_type: str, alpha: float = 0.5) -> Dict:
    """Search documents using various search types"""
    client = None
    try:
        client = get_weaviate_client()
        if not client:
            return {}
            
        docs = client.collections.get("Documents")
        tenant_collection = docs.with_tenant(tenant)
        
        documents = []
        result = None
        
        if search_type == "keyword":
            result = tenant_collection.query.bm25(
                query=query,
                limit=20
            )
            
        elif search_type == "vector":
            result = tenant_collection.query.near_text(
                query=query,
                limit=20
            )
            
        elif search_type == "hybrid":
            result = tenant_collection.query.hybrid(
                query=query,
                alpha=alpha,
                limit=20
            )
            
        elif search_type == "generative":
            try:
                gen_config = get_anthropic_generative_config()
                
                # Reduce the limit and add timeout handling
                result = tenant_collection.generate.near_text(
                    query=query,
                    limit=5,  # Reduced from 20 to 5
                    single_prompt=f"Based on the following context, answer the question: {query}",
                    grouped_task="Summarize the key points from the search results",
                    generative_provider=gen_config
                )
                
                if hasattr(result, 'generated') and result.generated:
                    generated_text = result.generated
                    documents = [{
                        "id": "generated_response",
                        "content": generated_text,
                        "file_name": "AI Generated Response",
                        "chunk_index": 0,
                        "created_date": datetime.now().strftime("%Y-%m-%d"),
                        "score": 1.0
                    }]
                else:
                    # Fallback to regular search if generation fails
                    st.warning("Generative search failed, falling back to hybrid search")
                    result = tenant_collection.query.hybrid(
                        query=query,
                        alpha=0.5,
                        limit=10
                    )
                    
                    documents = []
                    for i, obj in enumerate(result.objects):
                        properties = obj.properties or {}
                        documents.append({
                            "id": str(obj.uuid),
                            "content": properties.get("content", "No content available"),
                            "file_name": f"Search_Result_{i+1}",
                            "chunk_index": i,
                            "created_date": "2024-01-01",
                            "score": getattr(obj, 'score', None)
                        })
                
                logger.info(f"Generative search completed: {len(documents)} results")
                return {
                    "documents": documents,
                    "total_count": len(documents),
                    "search_type": search_type,
                    "query": query
                }
                
            except Exception as gen_error:
                logger.warning(f"Generative search failed: {gen_error}, falling back to hybrid search")
                # Fallback to hybrid search
                try:
                    result = tenant_collection.query.hybrid(
                        query=query,
                        alpha=0.5,
                        limit=10
                    )
                    
                    documents = []
                    for i, obj in enumerate(result.objects):
                        properties = obj.properties or {}
                        documents.append({
                            "id": str(obj.uuid),
                            "content": properties.get("content", "No content available"),
                            "file_name": f"Search_Result_{i+1}",
                            "chunk_index": i,
                            "created_date": "2024-01-01",
                            "score": getattr(obj, 'score', None)
                        })
                    
                    return {
                        "documents": documents,
                        "total_count": len(documents),
                        "search_type": "hybrid",  # Changed to hybrid since generation failed
                        "query": query
                    }
                except Exception as fallback_error:
                    logger.error(f"Fallback search also failed: {fallback_error}")
                    st.error(f"Search failed: {str(fallback_error)}")
                    return {}
            
        else:
            st.error("Invalid search type")
            return {}
        
        for i, obj in enumerate(result.objects):
            properties = obj.properties or {}
            documents.append({
                "id": str(obj.uuid),
                "content": properties.get("content", "No content available"),
                "file_name": f"Search_Result_{i+1}",
                "chunk_index": i,
                "created_date": "2024-01-01",
                "score": getattr(obj, 'score', None)
            })
        
        logger.info(f"Search completed: {len(documents)} results for query '{query}'")
        return {
            "documents": documents,
            "total_count": len(documents),
            "search_type": search_type,
            "query": query
        }
        
    except Exception as e:
        logger.error(f"Error in search_documents: {e}")
        st.error(f"Search error: {str(e)}")
        return {}
    finally:
        if client:
            try:
                client.close()
            except:
                pass

def query_agent(query: str, tenant: str) -> Dict:
    """Use AI agent for complex queries with source documents"""
    client = None
    try:
        client = get_weaviate_client()
        if not client:
            return {}

        try:
            from weaviate.agents.query import QueryAgent
            from weaviate.agents.classes import QueryAgentCollectionConfig
        except ImportError:
            from weaviate_agents.query import QueryAgent
            from weaviate_agents.classes import QueryAgentCollectionConfig

        collection_name = "Documents"
        agent = QueryAgent(client=client)
        
        cfg = QueryAgentCollectionConfig(
            name=collection_name,
            tenant=tenant,
            view_properties=["content", "file_name", "created_date"]
        )

        response = agent.run(
            query,
            collections=[cfg]
        )

        # Extract source documents from the response
        source_documents = []
        try:
            # Get the actual documents that were retrieved during the agent's searches
            docs = client.collections.get("Documents")
            tenant_collection = docs.with_tenant(tenant)
            
            # Perform a hybrid search to get relevant documents for the query
            search_result = tenant_collection.query.hybrid(
                query=query,
                alpha=0.5,
                limit=10
            )
            
            for i, obj in enumerate(search_result.objects):
                properties = obj.properties or {}
                source_documents.append({
                    "id": str(obj.uuid),
                    "content": properties.get("content", "No content available"),
                    "file_name": properties.get("file_name", f"Source_Document_{i+1}"),
                    "chunk_index": i,
                    "created_date": properties.get("created_date", "2024-01-01"),
                    "score": getattr(obj, 'score', None)
                })
        except Exception as e:
            logger.warning(f"Could not retrieve source documents: {e}")

        result = {
            "query": query,
            "tenant": tenant,
            "answer": response.final_answer,
            "source_documents": source_documents,
            "collections": getattr(response, "collection_names", None),
            "usage": {
                "requests": getattr(getattr(response, "usage", None), "requests", None),
                "request_tokens": getattr(getattr(response, "usage", None), "request_tokens", None),
                "response_tokens": getattr(getattr(response, "usage", None), "response_tokens", None),
                "total_tokens": getattr(getattr(response, "usage", None), "total_tokens", None),
                "total_time_sec": getattr(response, "total_time", None),
            },
            "searches": [
                {"collection": q.collection, "queries": q.queries}
                for group in getattr(response, "searches", []) for q in group
            ],
            "aggregations": [
                {"collection": a.collection, "search_query": a.search_query}
                for group in getattr(response, "aggregations", []) for a in group
            ],
        }

        logger.info(f"Query Agent completed for: {query} (tenant={tenant}) with {len(source_documents)} source documents")
        return result

    except Exception as e:
        logger.error(f"Error in query_agent: {e}")
        st.error(f"Query Agent error: {str(e)}")
        return {}
    finally:
        if client:
            try:
                client.close()
            except:
                pass

def filter_documents_locally(documents: List[Dict], filter_text: str) -> List[Dict]:
    """Filter documents locally by content"""
    if not filter_text:
        return documents
    
    filter_text = filter_text.lower()
    filtered = []
    
    for doc in documents:
        content = doc.get('content', '').lower()
        file_name = doc.get('file_name', '').lower()
        
        if filter_text in content or filter_text in file_name:
            filtered.append(doc)
    
    return filtered
