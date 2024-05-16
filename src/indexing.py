from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import json
from loguru import logger

# Open the JSON file
with open('../data/visited_urls.json', 'r') as file:
    # Load the JSON data
    data = json.load(file)
urls = list(data.keys())

# Define embedding model
model_name = "Alibaba-NLP/gte-base-en-v1.5" #"all-MiniLM-L6-v2" #"intfloat/multilingual-e5-small"

model_kwargs = {'device': 'cpu', 'trust_remote_code': True} #'cuda'
encode_kwargs = {'normalize_embeddings': False}
embedding_function = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs
)

# add more custom urls if needed
urls = urls + [
    "https://www.sfmta.com/getting-around/drive-park/how-avoid-parking-tickets",
    "https://www.sfmta.com/getting-around/safety/motorcycle-safety",
    "https://www.sf.gov/register-vote",
    "https://www.sfmta.com/permits/residential-parking-permits-rpp",
    "https://www.sfmta.com/projects/slow-streets-program",
    "https://www.sf.gov/give-feedback-slow-streets-program",
    "https://www.sfmta.com/getting-around/drive-park/color-curbs"
]

docs = WebBaseLoader(urls).load()
logger.info("Finished loading urls")

text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=500, chunk_overlap=100
)
doc_splits = text_splitter.split_documents(docs)
logger.info("Finished chunking")


# Add to vectorDB
index_path = "../data/chroma_db"
vectorstore = Chroma.from_documents(
    documents=doc_splits,
    collection_name="rag-chroma",
    embedding=embedding_function,
    persist_directory=index_path
)
logger.info(f"Number of docs indexed: {len(vectorstore)}")
del vectorstore

# testing
vectorstore = Chroma(collection_name="rag-chroma", 
                    persist_directory=index_path, 
                    embedding_function=embedding_function)
logger.info(f"Number of docs loaded from vector store: {len(vectorstore)}")

