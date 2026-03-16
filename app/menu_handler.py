import os
import pandas as pd
import PyPDF2
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.config import GEMINI_API_KEY

embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GEMINI_API_KEY)
vectorstore = None

def load_menu():
    global vectorstore
    text = ""
    data_dir = "data"
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        return
        
    for file in os.listdir(data_dir):
        filepath = os.path.join(data_dir, file)
        if file.endswith('.pdf'):
            reader = PyPDF2.PdfReader(filepath)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif file.endswith('.xlsx'):
            df = pd.read_excel(filepath)
            text += df.to_string() + "\n"
            
    if text.strip():
        splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
        chunks = splitter.split_text(text)
        vectorstore = FAISS.from_texts(chunks, embeddings)
        print("✅ Menu loaded into Vector Database successfully!")
    else:
        print("⚠️ No menu data found. Add a PDF/Excel to the /data folder.")

def search_menu_db(query: str) -> str:
    if not vectorstore:
        return "Menu is currently unavailable. Suggest general popular items."
    docs = vectorstore.similarity_search(query, k=3)
    return "\n".join([d.page_content for d in docs])
