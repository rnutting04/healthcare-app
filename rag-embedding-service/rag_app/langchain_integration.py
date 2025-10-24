"""Simplified LangChain integration for RAG responses"""
import logging
from typing import List, Dict, Any, Optional
from langchain.schema import Document, BaseRetriever
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from django.conf import settings

from .utils import query_embeddings
from .exceptions import ProcessingError

logger = logging.getLogger(__name__)

# Medical Q&A prompt template
MEDICAL_QA_PROMPT = PromptTemplate(
    template="""You are a helpful medical information assistant. Use the following context to answer the question accurately and comprehensively.

Context from medical documents:
{context}

Patient Question: {question}

Instructions:
- If the context contains relevant information, provide a complete answer based on it
- If the context mentions lists or multiple items, include all of them
- Use clear, easy-to-understand language
- If specific medical terms are used, briefly explain them
- If the context doesn't contain enough information to fully answer the question, acknowledge this
- Always answer in {language} if the response is in another language reject and retry immediately

Answer:""",
    input_variables=["context", "question", "language"]
)


class CustomRetriever(BaseRetriever):
    """Custom retriever that uses database service for vector search"""
    
    cancer_type_id: Optional[int] = None
    k: int = 5
    
    def _get_relevant_documents(
        self, query: str, *, run_manager: Optional[CallbackManagerForRetrieverRun] = None
    ) -> List[Document]:
        """Retrieve relevant documents for a query"""
        # Get more results initially for better filtering
        results = query_embeddings(query, self.cancer_type_id, self.k * 2)
        
        # Convert to LangChain documents with deduplication
        documents = []
        seen_content = set()
        
        for result in results:
            if not isinstance(result, dict):
                continue
                
            content = result.get('chunk_text', '').strip()
            if not content or content in seen_content:
                continue
                
            seen_content.add(content)
            
            # Create document with metadata
            doc = Document(
                page_content=content,
                metadata=self._extract_metadata(result)
            )
            documents.append(doc)
            
            # Stop when we have enough unique documents
            if len(documents) >= self.k:
                break
        
        return documents
    
    @staticmethod
    def _extract_metadata(result: dict) -> dict:
        """Extract and normalize metadata from result"""
        metadata = result.get('metadata', {})
        
        # Ensure metadata is a dict
        if not isinstance(metadata, dict):
            metadata = {}
        
        return {
            'id': result.get('id'),
            'chunk_index': result.get('chunk_index', 0),
            'similarity_score': result.get('distance', result.get('similarity_score', 0)),
            'document_id': result.get('document_id'),
            'filename': metadata.get('filename', result.get('document_name', 'Unknown')),
            'page': metadata.get('page', 0)
        }


class RAGChain:
    """Simplified RAG chain wrapper"""
    
    def __init__(self, cancer_type_id: Optional[int] = None, 
                 model_name: str = "gpt-3.5-turbo",
                 k: int = 8):
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0,
            openai_api_key=settings.OPENAI_API_KEY,
            max_tokens=500
        )
        self.retriever = CustomRetriever(cancer_type_id=cancer_type_id, k=k)
        self.prompt_template = MEDICAL_QA_PROMPT
        self.qa_chain = None
    
    def _create_chain(self, prompt: PromptTemplate):
        """Create the QA chain"""
        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt,
                               "document_variable_name": "context"}
        )
    
    def query(self, question: str, chat_history: List = None, language: str = 'English') -> Dict[str, Any]:
        """Process a query with optional chat history"""
        # Add chat history context if available
        logger.info(language)
        prompt = self.prompt_template.partial(language=language)

        logger.info(f"Prompt template: {prompt}")
        self.qa_chain = self._create_chain(prompt)
        full_query = self._build_query_with_history(question, chat_history, language)
        
        # Run the chain
        try:
            result = self.qa_chain.invoke({"query": full_query})
            logger.debug(f"Chain result type: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
        except Exception as e:
            logger.error(f"Chain invoke failed: {e}")
            raise
        
        # Ensure result is a dict
        if isinstance(result, str):
            result = {"result": result, "source_documents": []}
        
        # Extract and format respons
        return self._format_response(result, question)
    
    @staticmethod
    def _build_query_with_history(question: str, chat_history: List, language: str) -> str:
        """Build query with chat history context"""
        if not chat_history:
            return question
        
        # Format recent history
        history_parts = []
        for item in chat_history[-4:]:  # Last 2 exchanges
            formatted = RAGChain._format_history_item(item)
            if formatted:
                history_parts.extend(formatted)
        
        if not history_parts:
            return question
            
        history_context = "\n\nPrevious conversation:\n" + "\n".join(history_parts)
        return f"{question}{history_context}\n\nCurrent question: {question}"
    
    @staticmethod
    def _format_history_item(item) -> List[str]:
        """Format a single history item"""
        if isinstance(item, tuple) and len(item) == 2:
            return [f"Patient: {item[0]}", f"Assistant: {item[1]}"]
        
        if isinstance(item, dict):
            role = "Patient" if item.get('role') == 'human' else "Assistant"
            content = item.get('content', '')
            return [f"{role}: {content}"] if content else []
        
        if isinstance(item, str):
            return [item]
        
        return []
    
    @staticmethod
    def _format_response(result: dict, original_query: str) -> Dict[str, Any]:
        """Format the chain response"""
        answer = result.get("result", "I couldn't generate a response.")
        source_documents = result.get("source_documents", [])
        
        # Extract unique sources
        sources = []
        seen_files = {}
        
        for doc in source_documents:
            if not hasattr(doc, 'metadata'):
                continue
                
            filename = doc.metadata.get('filename', 'Unknown')
            page = doc.metadata.get('page', 0)
            
            if filename not in seen_files:
                seen_files[filename] = set()
            if page > 0:
                seen_files[filename].add(page)
        
        # Format sources
        for filename, pages in list(seen_files.items())[:3]:  # Top 3 sources
            if pages:
                page_list = sorted(pages)
                pages_str = f"pages {', '.join(map(str, page_list))}"
                sources.append(f"{filename} ({pages_str})")
            else:
                sources.append(filename)

        logger.info(f"RAG response: {answer}")
        
        return {
            'success': True,
            'answer': answer,
            'sources': sources,
            'documents_used': len(source_documents)
        }


def process_rag_query(query: str, cancer_type_id: Optional[int] = None,
                     chat_history: List = None, k: int = 5, language: str = 'English') -> Dict[str, Any]:
    """Main entry point for processing RAG queries"""
    try:
        # Create and run chain
        rag_chain = RAGChain(cancer_type_id=cancer_type_id, k=max(k, 5))
        
        result = rag_chain.query(query, chat_history, language)
        
        # Add raw results for compatibility
        result['raw_results'] = query_embeddings(query, cancer_type_id, k)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in RAG chain: {str(e)}", exc_info=True)
        
        # Try fallback to raw search
        try:
            raw_results = query_embeddings(query, cancer_type_id, k)
            if raw_results:
                # Format basic response from raw results
                response_parts = ["Based on the available information:\n"]
                for result in raw_results[:3]:
                    if isinstance(result, dict) and 'chunk_text' in result:
                        text = result['chunk_text'][:200]
                        response_parts.append(f"\n{text}...")
                
                return {
                    'success': True,
                    'answer': '\n'.join(response_parts),
                    'sources': [],
                    'raw_results': raw_results,
                    'documents_used': len(raw_results)
                }
        except Exception as fallback_error:
            logger.error(f"Fallback search also failed: {fallback_error}")
        
        # Return error response
        return {
            'success': False,
            'answer': "I apologize, but I'm having trouble accessing the medical information right now.",
            'sources': [],
            'error': str(e)
        }
