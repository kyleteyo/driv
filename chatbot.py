"""
MSC Safety Bot - AI chatbot using Hugging Face models and real safety data from Google Sheets
"""
import streamlit as st
import pandas as pd
import re
import json
import requests
from datetime import datetime
from difflib import SequenceMatcher

class MSCSafetyBot:
    def __init__(self):
        self.knowledge_base = []
        self.initialized = True
        self.hf_api_url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
        self.blip_api_url = "https://api-inference.huggingface.co/models/nlpconnect/vit-gpt2-image-captioning"
        
    def similarity_score(self, text1, text2):
        """Calculate similarity between two texts using built-in methods"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def query_huggingface(self, prompt, max_length=200):
        """Query Hugging Face API for text generation"""
        try:
            # Check if we have HF token from secrets or environment
            import os
            hf_token = None
            try:
                hf_token = st.secrets["HUGGINGFACE_API_TOKEN"]
            except:
                hf_token = os.environ.get("HUGGINGFACE_API_TOKEN")
            
            if not hf_token:
                return None
                
            headers = {"Authorization": f"Bearer {hf_token}"}
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_length": max_length,
                    "temperature": 0.7,
                    "do_sample": True,
                    "return_full_text": False
                }
            }
            
            response = requests.post(self.hf_api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('generated_text', '').strip()
            
            return None
            
        except Exception as e:
            return None
    
    def analyze_image_with_blip(self, image_url):
        """Analyze an image using Salesforce BLIP model"""
        try:
            # Check if we have HF token from secrets or environment
            import os
            hf_token = None
            try:
                hf_token = st.secrets["HUGGINGFACE_API_TOKEN"]
            except:
                hf_token = os.environ.get("HUGGINGFACE_API_TOKEN")
            
            if not hf_token:
                return "No Hugging Face token available"
                
            headers = {"Authorization": f"Bearer {hf_token}"}
            
            # Download image and send to BLIP model
            import requests
            try:
                image_response = requests.get(image_url, timeout=10)
                if image_response.status_code != 200:
                    return f"Failed to download image (HTTP {image_response.status_code})"
                    
                # Send image data in binary format for Hugging Face API
                response = requests.post(
                    self.blip_api_url, 
                    headers=headers, 
                    data=image_response.content,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        return result[0].get('generated_text', '').strip()
                    elif isinstance(result, dict):
                        return result.get('generated_text', '').strip()
                elif response.status_code == 503:
                    return "BLIP model is loading, please try again in a few minutes"
                else:
                    return f"BLIP API error (HTTP {response.status_code})"
                
                return "No response from BLIP model"
                
            except requests.exceptions.Timeout:
                return "Request timeout - BLIP model may be busy"
            except requests.exceptions.RequestException as e:
                return f"Network error: {str(e)}"
            
        except Exception as e:
            return f"Analysis error: {str(e)}"
    
    def prepare_knowledge_base(self, sheets_manager):
        """Prepare knowledge base from Google Sheets data"""
        try:
            knowledge_docs = []
            
            # Get safety infographics data
            infographics = sheets_manager.get_safety_infographics()
            for item in infographics:
                ai_analysis = item.get('AI_Analysis', '')
                doc = {
                    'type': 'infographic',
                    'title': item.get('Title', 'Safety Infographic'),
                    'content': f"Safety Infographic: {item.get('Title', '')}. Description: {item.get('Description', '')}. Tags: {item.get('Tags', '')}. AI Analysis: {ai_analysis}",
                    'submitter': item.get('Submitter', 'Unknown'),
                    'date': item.get('Date', ''),
                    'raw_data': item
                }
                knowledge_docs.append(doc)
            
            # Get safety pointers data
            pointers = sheets_manager.get_safety_pointers()
            for item in pointers:
                # Fix column mapping for safety pointers
                submitter = item.get('Observation_Date', 'Unknown')
                observation = item.get('Category', 'N/A')
                reflection = item.get('Reflection', 'N/A')
                recommendation = item.get('Recommendation', 'N/A')
                category = item.get('Submitter', 'Safety Observation')
                
                doc = {
                    'type': 'safety_pointer',
                    'title': f"{category} - Safety Pointer",
                    'content': f"Safety Observation: {observation}. Reflection: {reflection}. Recommendation: {recommendation}. Category: {category}",
                    'submitter': submitter,
                    'date': item.get('Observation', ''),
                    'raw_data': item
                }
                knowledge_docs.append(doc)
            
            self.knowledge_base = knowledge_docs
            return len(knowledge_docs)
            
        except Exception as e:
            st.error(f"Error preparing knowledge base: {str(e)}")
            return 0
    
    def retrieve_relevant_docs(self, query, top_k=3):
        """Retrieve most relevant documents for a query using keyword matching"""
        if not self.knowledge_base:
            return []
        
        try:
            query_lower = query.lower()
            query_keywords = re.findall(r'\b\w+\b', query_lower)
            
            doc_scores = []
            
            for i, doc in enumerate(self.knowledge_base):
                doc_text = doc['content'].lower()
                
                # Calculate keyword matching score
                keyword_score = 0
                for keyword in query_keywords:
                    if keyword in doc_text:
                        keyword_score += 1
                
                # Calculate text similarity score
                similarity_score = self.similarity_score(query, doc['content'])
                
                # Boost score for specific terms
                boost_score = 0
                if any(term in query_lower for term in ['terrex', 'belrex']):
                    if any(term in doc_text for term in ['terrex', 'belrex']):
                        boost_score += 0.3
                
                if any(term in query_lower for term in ['safety', 'pointer', 'recommendation']):
                    if doc['type'] == 'safety_pointer':
                        boost_score += 0.2
                
                if any(term in query_lower for term in ['infographic', 'image', 'visual']):
                    if doc['type'] == 'infographic':
                        boost_score += 0.2
                
                final_score = (keyword_score * 0.4) + (similarity_score * 0.4) + boost_score
                
                if final_score > 0.1:  # Minimum relevance threshold
                    doc_scores.append({
                        'doc': doc,
                        'similarity': final_score
                    })
            
            # Sort by score and return top k
            doc_scores.sort(key=lambda x: x['similarity'], reverse=True)
            return doc_scores[:top_k]
            
        except Exception as e:
            st.error(f"Error retrieving documents: {str(e)}")
            return []
    
    def generate_response(self, query, relevant_docs):
        """Generate response using Hugging Face AI and relevant documents"""
        if not relevant_docs:
            return "I couldn't find any relevant safety information for your question. Please try asking about specific vehicle types (Terrex/Belrex), safety procedures, or check the submitted safety pointers and infographics."
        
        # Create context from relevant documents
        context_parts = []
        for doc_info in relevant_docs:
            doc = doc_info['doc']
            context_parts.append(f"- {doc['title']}: {doc['content']}")
        
        context = "\n".join(context_parts)
        
        # Try to use Hugging Face for intelligent response generation
        prompt = f"""Based on the following safety information from MSC personnel, answer the question: "{query}"

Safety Information:
{context}

Provide a helpful response focusing on the safety recommendations and observations:"""
        
        ai_response = self.query_huggingface(prompt)
        
        if ai_response:
            # Combine AI response with factual data
            response_parts = []
            response_parts.append("🤖 **AI Analysis:**")
            response_parts.append(ai_response)
            response_parts.append("\n📊 **Source Data from MSC Personnel:**")
            
            for i, doc_info in enumerate(relevant_docs, 1):
                doc = doc_info['doc']
                submitter_info = f" (Submitted by: {doc['submitter']})" if doc['submitter'] != 'Unknown' else ""
                
                if doc['type'] == 'safety_pointer':
                    # Extract the actual content from the raw data
                    raw = doc['raw_data']
                    observation = raw.get('Category', 'N/A')
                    reflection = raw.get('Reflection', 'N/A')
                    recommendation = raw.get('Recommendation', 'N/A')
                    category = raw.get('Submitter', 'Safety Observation')
                    
                    response_parts.append(f"\n{i}. **{category}**{submitter_info}")
                    response_parts.append(f"   - Observation: {observation}")
                    response_parts.append(f"   - Reflection: {reflection}")
                    response_parts.append(f"   - Recommendation: {recommendation}")
                
                elif doc['type'] == 'infographic':
                    raw = doc['raw_data']
                    title = raw.get('Title', 'Safety Infographic')
                    description = raw.get('Description', 'N/A')
                    tags = raw.get('Tags', '')
                    
                    response_parts.append(f"\n{i}. **{title}**{submitter_info}")
                    if description != 'N/A':
                        response_parts.append(f"   - Description: {description}")
                    if tags:
                        response_parts.append(f"   - Tags: {tags}")
            
            return "\n".join(response_parts)
        else:
            # Fallback to structured response if AI is not available
            response_parts = []
            response_parts.append("📊 **Safety Information from MSC Personnel:**")
            
            for i, doc_info in enumerate(relevant_docs, 1):
                doc = doc_info['doc']
                submitter_info = f" (Submitted by: {doc['submitter']})" if doc['submitter'] != 'Unknown' else ""
                
                if doc['type'] == 'safety_pointer':
                    # Extract the actual content from the raw data
                    raw = doc['raw_data']
                    observation = raw.get('Category', 'N/A')
                    reflection = raw.get('Reflection', 'N/A')
                    recommendation = raw.get('Recommendation', 'N/A')
                    category = raw.get('Submitter', 'Safety Observation')
                    
                    response_parts.append(f"\n{i}. **{category}**{submitter_info}")
                    response_parts.append(f"   - Observation: {observation}")
                    response_parts.append(f"   - Reflection: {reflection}")
                    response_parts.append(f"   - Recommendation: {recommendation}")
                
                elif doc['type'] == 'infographic':
                    raw = doc['raw_data']
                    title = raw.get('Title', 'Safety Infographic')
                    description = raw.get('Description', 'N/A')
                    tags = raw.get('Tags', '')
                    
                    response_parts.append(f"\n{i}. **{title}**{submitter_info}")
                    if description != 'N/A':
                        response_parts.append(f"   - Description: {description}")
                    if tags:
                        response_parts.append(f"   - Tags: {tags}")
            
            return "\n".join(response_parts)
    
    def chat(self, query, sheets_manager):
        """Main chat function"""
        # Refresh knowledge base
        doc_count = self.prepare_knowledge_base(sheets_manager)
        
        if doc_count == 0:
            return "I don't have any safety data available yet. Please submit some safety pointers or infographics first!"
        
        # Retrieve relevant documents
        relevant_docs = self.retrieve_relevant_docs(query)
        
        # Generate response
        response = self.generate_response(query, relevant_docs)
        
        return response

def render_chatbot_interface(sheets_manager):
    """Render the chatbot interface in Streamlit"""
    st.markdown("### 🤖 MSC SAFETY BOT")
    st.markdown("*AI-powered assistant that searches through submitted safety content and provides intelligent responses.*")
    
    # Check if Hugging Face token is available
    import os
    hf_token = None
    try:
        hf_token = st.secrets["HUGGINGFACE_API_TOKEN"]
    except:
        hf_token = os.environ.get("HUGGINGFACE_API_TOKEN")
    
    if hf_token:
        st.success("🚀 AI Enhancement: Powered by Hugging Face")
    else:
        st.info("💡 Note: Add HUGGINGFACE_API_TOKEN to secrets for enhanced AI responses")
    
    # Initialize chatbot
    if 'safety_bot' not in st.session_state:
        st.session_state.safety_bot = MSCSafetyBot()
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Sample questions
    with st.expander("💡 Sample Questions"):
        st.markdown("""
        - "What are the most common reversing mistakes for Terrex?"
        - "Any pointers about Belrex movement safety?"
        - "Show me the latest safety infographic"
        - "Tips on night convoy safety?"
        - "What safety recommendations have been submitted?"
        """)
    
    # Chat input
    query = st.text_input("Ask about safety procedures:", placeholder="Type your safety question here...")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔍 Ask", type="primary"):
            if query.strip():
                with st.spinner("Searching safety database..."):
                    response = st.session_state.safety_bot.chat(query, sheets_manager)
                    
                    # Add to chat history
                    st.session_state.chat_history.append({
                        'query': query,
                        'response': response,
                        'timestamp': datetime.now().strftime("%H:%M")
                    })
    
    with col2:
        if st.button("🔄 Refresh Data"):
            # Clear cached data
            if hasattr(st.session_state.safety_bot, 'knowledge_base'):
                st.session_state.safety_bot.knowledge_base = []
                st.session_state.safety_bot.embeddings = None
            st.success("Data refreshed!")
    
    # Display chat history
    if st.session_state.chat_history:
        st.markdown("### 💬 Chat History")
        
        for i, chat in enumerate(reversed(st.session_state.chat_history[-5:])):  # Show last 5 chats
            with st.container():
                st.markdown(f"""
                <div style="border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin: 8px 0; background-color: #f8f9fa;">
                    <div style="color: #2C5530; font-weight: bold; margin-bottom: 8px;">
                        🙋 Question ({chat['timestamp']}):
                    </div>
                    <div style="margin-bottom: 12px; font-style: italic;">
                        {chat['query']}
                    </div>
                    <div style="color: #2C5530; font-weight: bold; margin-bottom: 8px;">
                        🤖 MSC Safety Bot:
                    </div>
                    <div style="background-color: white; padding: 10px; border-radius: 5px; border-left: 3px solid #2C5530;">
{chat['response'].replace(chr(10), '<br>')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Clear chat history button
    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()