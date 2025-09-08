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

@st.cache_data(ttl=0)  # Set to 0 to disable caching temporarily
def fetch_tenants() -> List[Dict]:
    """Fetch available tenants from Weaviate"""
    client = None
    try:
        client = get_weaviate_client()
        if not client:
            return []
            
        docs = client.collections.get("BoxDocuments")
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
            
        docs = client.collections.get("BoxDocuments")
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
            
        docs = client.collections.get("BoxDocuments")
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

# def query_agent(query: str, tenant: str) -> Dict:
#     """Use AI agent for complex queries with source documents"""
#     client = None
#     try:
#         client = get_weaviate_client()
#         if not client:
#             return {}

#         try:
#             from weaviate.agents.query import QueryAgent
#             from weaviate.agents.classes import QueryAgentCollectionConfig
#         except ImportError:
#             from weaviate_agents.query import QueryAgent
#             from weaviate_agents.classes import QueryAgentCollectionConfig

#         collection_name = "Documents"
#         agent = QueryAgent(client=client)
        
#         cfg = QueryAgentCollectionConfig(
#             name=collection_name,
#             tenant=tenant,
#             view_properties=["content", "file_name", "created_date"]
#         )

#         response = agent.run(
#             query,
#             collections=[cfg]
#         )

#         # Extract source documents from the response
#         source_documents = []
#         try:
#             # Get the actual documents that were retrieved during the agent's searches
#             docs = client.collections.get("Documents")
#             tenant_collection = docs.with_tenant(tenant)
            
#             # Perform a hybrid search to get relevant documents for the query
#             search_result = tenant_collection.query.hybrid(
#                 query=query,
#                 alpha=0.5,
#                 limit=10
#             )
            
#             for i, obj in enumerate(search_result.objects):
#                 properties = obj.properties or {}
#                 source_documents.append({
#                     "id": str(obj.uuid),
#                     "content": properties.get("content", "No content available"),
#                     "file_name": properties.get("file_name", f"Source_Document_{i+1}"),
#                     "chunk_index": i,
#                     "created_date": properties.get("created_date", "2024-01-01"),
#                     "score": getattr(obj, 'score', None)
#                 })
#         except Exception as e:
#             logger.warning(f"Could not retrieve source documents: {e}")

#         result = {
#             "query": query,
#             "tenant": tenant,
#             "answer": response.final_answer,
#             "source_documents": source_documents,
#             "collections": getattr(response, "collection_names", None),
#             "usage": {
#                 "requests": getattr(getattr(response, "usage", None), "requests", None),
#                 "request_tokens": getattr(getattr(response, "usage", None), "request_tokens", None),
#                 "response_tokens": getattr(getattr(response, "usage", None), "response_tokens", None),
#                 "total_tokens": getattr(getattr(response, "usage", None), "total_tokens", None),
#                 "total_time_sec": getattr(response, "total_time", None),
#             },
#             "searches": [
#                 {"collection": q.collection, "queries": q.queries}
#                 for group in getattr(response, "searches", []) for q in group
#             ],
#             "aggregations": [
#                 {"collection": a.collection, "search_query": a.search_query}
#                 for group in getattr(response, "aggregations", []) for a in group
#             ],
#         }

#         logger.info(f"Query Agent completed for: {query} (tenant={tenant}) with {len(source_documents)} source documents")
#         return result

#     except Exception as e:
#         logger.error(f"Error in query_agent: {e}")
#         st.error(f"Query Agent error: {str(e)}")
#         return {}
#     finally:
#         if client:
#             try:
#                 client.close()
#             except:
#                 pass

# Replace your existing query_agent with this version
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

        collection_name = "BoxDocuments"
        agent = QueryAgent(client=client)
        
        cfg = QueryAgentCollectionConfig(
            name=collection_name,
            tenant=tenant,
            view_properties=["content"]
        )

        response = agent.run(
            query,
            collections=[cfg]
        )

        # Extract source documents from the response
        source_documents = []
        try:
            # Get the actual documents that were retrieved during the agent's searches
            docs = client.collections.get("BoxDocuments")
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

        # Normalize total time for usage table
        try:
            if result.get("usage") is not None and result["usage"].get("total_time_sec") is None:
                if hasattr(response, "total_time"):
                    result["usage"]["total_time_sec"] = getattr(response, "total_time")
        except Exception:
            pass

        # Build pretty, boxed strings for the frontend (Streamlit)
        try:
            pretty = format_query_agent_response_for_ui(result)
            result["pretty_text"] = pretty.get("pretty_text")
            result["pretty_blocks"] = pretty.get("pretty_blocks")
            result["usage_block"] = pretty.get("usage_block")
        except Exception as _fmt_err:
            logger.warning(f"Could not format pretty QueryAgent output: {_fmt_err}")

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


# === Pretty printing helpers to mirror weaviate.agents.utils.print_query_agent_response ===
_BOX_WIDTH = 97  # tuned for Streamlit code blocks

def _hr(width: int) -> str:
    return "\u2500" * width

def _boxed(title: str, body: str) -> str:
    # ┍──────────────── title ────────────────┑ / └──────────────────────────────┘
    title = f" {title} "
    pad_left = 1
    pad_right = 1
    inner_width = _BOX_WIDTH
    top = f"\u256D{_hr(inner_width)}{title}{_hr(inner_width)}\u256E"
    if not body.strip():
        body = "\n \n"
    else:
        body = f"\n{body}\n"
    lines = [top]
    for line in body.splitlines():
        lines.append(f"\u2502{' ' * pad_left}{line}{' ' * pad_right}")
    bottom_len = len(top) - 1
    bottom = f"\u2570{_hr(bottom_len)}"
    lines.append(bottom)
    return "\n".join(lines)

def _format_usage_table(usage: dict, total_time) -> str:
    if not usage:
        return ""
    rows = [
        ("LLM Requests:", str(usage.get("requests", "-"))),
        ("Input Tokens:", str(usage.get("request_tokens", "-"))),
        ("Output Tokens:", str(usage.get("response_tokens", "-"))),
        ("Total Tokens:", str(usage.get("total_tokens", "-"))),
    ]
    c1 = max(len(k) for k, _ in rows)
    c2 = max(len(v) for _, v in rows)
    top = "\u250C" + "\u2500" * (c1 + 2) + "\u252C" + "\u2500" * (c2 + 2) + "\u2510"
    mid = "\u251C" + "\u2500" * (c1 + 2) + "\u253C" + "\u2500" * (c2 + 2) + "\u2524"
    bot = "\u2514" + "\u2500" * (c1 + 2) + "\u2534" + "\u2500" * (c2 + 2) + "\u2518"
    lines = [top]
    for i, (k, v) in enumerate(rows):
        lines.append(f"\u2502 {k.ljust(c1)} \u2502 {v.rjust(c2)} \u2502")
        if i == 0:
            lines.append(mid)
    lines.append(bot)
    footer = f"Total Time Taken: {total_time:.2f}s" if isinstance(total_time, (int, float)) else ""
    return f"   \ud83d\udcca Usage Statistics   \n" + "\n".join(lines) + ("\n" + footer if footer else "")

def format_query_agent_response_for_ui(result: dict) -> dict:
    """Create clean, simple strings without fancy box formatting.
    Returns a dict with `pretty_text`, `pretty_blocks`, and `usage_block`.
    """
    query = result.get("query", "")
    answer = result.get("answer", "")
    searches = result.get("searches", []) or []
    aggregations = result.get("aggregations", []) or []
    usage = result.get("usage", {}) or {}
    total_time = usage.get("total_time_sec") or result.get("total_time_sec")

    # Simple headers without fancy boxes, with spacing
    s_query = f"🔍 Original Query\n{query}\n\n"
    s_answer = f"📝 Final Answer\n{answer}\n\n"

    # Searches block
    if searches:
        search_lines = []
        for s in searches:
            q = s.get("queries") or s.get("query") or []
            coll = s.get("collection") or "Documents"
            filters = s.get("filters") or []
            filter_ops = s.get("filter_operators") or "AND"
            search_lines.append("QueryResultWithCollection(")
            search_lines.append(f"    queries={repr(q)},")
            search_lines.append(f"    filters={repr(filters)},")
            search_lines.append(f"    filter_operators='{filter_ops}',")
            search_lines.append(f"    collection='{coll}'")
            search_lines.append(")")
        s_searches = f"🔍 Searches Executed {len(searches)}/{len(searches)}\n" + "\n".join(search_lines) + "\n\n"
    else:
        s_searches = f"🔍 Searches Executed 0/0\n\n"

    # Aggregations block
    if aggregations:
        ag_lines = [repr(a) for a in aggregations]
        s_aggs = f"📊 Aggregations\n" + "\n".join(ag_lines) + "\n\n"
    else:
        s_aggs = f"📊 No Aggregations Run\n\n"

    # Sources block
    src_docs = result.get("source_documents", []) or []
    src_lines = []
    for d in src_docs:
        oid = d.get("id") or d.get("uuid") or "?"
        coll = d.get("collection") or "Documents"
        src_lines.append(f" - object_id='{oid}' collection='{coll}'")
    s_sources = f"🔗 Sources\n" + "\n".join(src_lines) + "\n\n"

    s_usage = _format_usage_table(usage, total_time)

    # Combine all sections with proper spacing
    pretty_text = s_query + s_answer + s_searches + s_aggs + s_sources + s_usage

    return {
        "pretty_text": pretty_text,
        "pretty_blocks": [s_query, s_answer, s_searches, s_aggs, s_sources],
        "usage_block": s_usage
    }