import streamlit as st
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
load_dotenv()

st.title("MD Rag Chatbot")

openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
model_name = st.sidebar.selectbox("Select OpenAI Model", ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o","gpt-5","text-embedding-3-small"])
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.7)
max_tokens = st.sidebar.slider("Max Tokens", 50, 500, 300)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

prompt = ChatPromptTemplate.from_template(
    """
    Answer the questions based on the provided context only.
    Please provide the most accurate response based on the question.
    {context}

    <context>
    Question: {input}
    """
)

def create_vector_embeddings():
    if "vectors" not in st.session_state:
        if not openai_api_key:
            st.error("Please enter your OpenAI API key in the sidebar.")
            return False
        
        try:
            # Use OpenAI embeddings
            st.session_state.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
            
            # Load PDFs from folder
            st.session_state.loader = PyPDFDirectoryLoader("sops")  # your folder path here
            st.session_state.docs = st.session_state.loader.load()
            
            # Split documents into chunks
            st.session_state.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            st.session_state.final_documents = st.session_state.text_splitter.split_documents(st.session_state.docs[:50])
            
            # Create FAISS vectorstore
            st.session_state.vectors = FAISS.from_documents(st.session_state.final_documents, st.session_state.embeddings)
            
            return True
        except Exception as e:
            st.error(f"Error creating embeddings: {e}")
            return False
    else:
        # Already created
        return True


if st.button("Create document embeddings"):
    success = create_vector_embeddings()
    st.session_state['embeddings_ready'] = success
    if success:
        st.success("Vector database is ready.")
    else:
        st.error("Embedding creation failed. Please try again.")

if st.session_state.get('embeddings_ready', False):
    user_prompt = st.text_input("Enter your question from documentation")
else:
    user_prompt = None

if user_prompt:
    if "vectors" not in st.session_state:
        st.warning("Please create document embeddings first by clicking the button above.")
    else:
        if not openai_api_key:
            st.error("Please enter your OpenAI API key in the sidebar.")
        else:
            # Initialize LLM with keys and settings from sidebar
            llm = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                openai_api_key=openai_api_key
            )
            
            # Create document chain and retrieval chain
            document_chain = create_stuff_documents_chain(llm, prompt)
            retriever = st.session_state.vectors.as_retriever()
            retrieval_chain = create_retrieval_chain(retriever, document_chain)
            
        
            response = retrieval_chain.invoke({'input': user_prompt})
            
            st.write(response['answer'])
            
            with st.expander("Document similarity Search"):
                for i, doc in enumerate(response['context']):
                    st.write(doc.page_content)
                    st.write('------------------------')
