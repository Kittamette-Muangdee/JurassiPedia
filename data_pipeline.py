import json
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

def run_pipeline():
    # =========================================================================
    # STEP 1: Load Preprocessed Dataset
    # =========================================================================
    print("--------------------------------------------------")
    print("Step 1: Loading raw dinosaur knowledge data...")
    print("--------------------------------------------------")
    dataset_path = "jurassipedia_dataset_full.json"
    
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset file '{dataset_path}' not found in the workspace.")
        
    with open(dataset_path, "r", encoding="utf-8") as f:
        dino_data = json.load(f)
    print(f"✅ Successfully loaded {len(dino_data)} dinosaur entries from dataset.")

    # =========================================================================
    # STEP 2: Text Chunking (Chunk Size: 1000, Overlap: 200)
    # =========================================================================
    print("\n--------------------------------------------------")
    print("Step 2: Processing and chunking knowledge documents...")
    print("--------------------------------------------------")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    all_chunks = []

    for title, text in dino_data.items():
        chunks = text_splitter.split_text(text)
        for chunk in chunks:
            # Anchor metadata for source tracking
            doc = Document(
                page_content=chunk,
                metadata={"dino_name": title, "source": "Wikipedia API"}
            )
            all_chunks.append(doc)

    print(f"✅ Chunking complete: Generated {len(all_chunks)} unique document chunks.")

    # =========================================================================
    # STEP 3: Vector Embeddings Generation & Chroma Database Indexing
    # =========================================================================
    print("\n--------------------------------------------------")
    print("Step 3: Indexing chunks into local Chroma Vector Store...")
    print("--------------------------------------------------")
    print("Downloading/initializing HuggingFace 'all-MiniLM-L6-v2' model...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    persist_directory = "./jurassic_db_full"
    print(f"Building embeddings database at '{persist_directory}'...")
    
    vector_db = Chroma.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    
    print("\n==================================================")
    print("🎉 JURASSIPEDIA VECTOR STORE SUCCESSFULLY PREPARED!")
    print(f"📍 Database directory: {os.path.abspath(persist_directory)}")
    print(f"📚 Total chunks indexed: {vector_db._collection.count()}")
    print("==================================================")

if __name__ == "__main__":
    run_pipeline()
