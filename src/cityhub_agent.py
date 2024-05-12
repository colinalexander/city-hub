import os
from typing import List, Literal
from typing_extensions import TypedDict
import json
from dotenv import load_dotenv
from loguru import logger
from datetime import date

from langchain.schema import Document
#from langchain import hub
from langchain.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools import BraveSearch
from langgraph.graph import END, StateGraph

load_dotenv()

# Tools
## RAG tool
def get_retriever(index_path, model_name = "Alibaba-NLP/gte-base-en-v1.5"):
    model_kwargs = {'device': 'cpu', 'trust_remote_code': True} #'cuda'
    encode_kwargs = {'normalize_embeddings': False}
    embedding_function = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )
    vectorstore = Chroma(collection_name="rag-chroma", 
                         persist_directory=index_path, 
                         embedding_function=embedding_function)
    logger.info(f"Number of docs loaded from vector store: {len(vectorstore)}")
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    return retriever
retriever = get_retriever("../data/chroma_db")


## Web search tool
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
web_search_tool = BraveSearch.from_api_key(api_key=BRAVE_API_KEY, search_kwargs={"count": 3})

# Data model
class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""
    datasource: Literal["vectorstore", "websearch"] = Field(
        ...,
        description="Given a user question choose to route it to web search or a vectorstore.",
    )

def get_question_router():
    # LLM with function call 
    llm = ChatGroq(model="llama3-70b-8192")
    structured_llm_router = llm.with_structured_output(RouteQuery)

    # Prompt 
    system = """You are an expert at routing a user question to a vectorstore or web search.
    The vectorstore contains documents related to the public city services in San Francisco, such as the slow stree problem.
    Use the vectorstore for questions on these topics. For all else, for example current news, events and travel guides, use web-search."""
    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "{question}"),
        ]
    )

    question_router = route_prompt | structured_llm_router
    return question_router
question_router = get_question_router()


class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""

    binary_score: str = Field(description="Documents are relevant to the question, 'yes' or 'no'")

def get_retrieval_grader():
    # LLM with function call 
    llm = ChatGroq(model="llama3-70b-8192")
    structured_llm_grader = llm.with_structured_output(GradeDocuments)

    # Prompt 
    system = """You are a grader assessing relevance of a retrieved document to a user question. \n 
        If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant. \n
        Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
    grade_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "Retrieved document: \n\n {document} \n\n User question: {question}"),
        ]
    )

    retrieval_grader = grade_prompt | structured_llm_grader
    return retrieval_grader
retrieval_grader = get_retrieval_grader()


# generation
def get_rag_chain():
    # Prompt
    #prompt = hub.pull("rlm/rag-prompt")
    prompt = PromptTemplate(
    template="""
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    You are an AI assistant to help residents and visitors to navigate city services and query information easier.\n
    Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. 
    Only use the relevant documents related to the user query and keep the answer concise. \n

    <|eot_id|><|start_header_id|>user<|end_header_id|>
    Question: {question} 
    Context: {context} 

    <|eot_id|><|start_header_id|>assistant<|end_header_id|>
    Answer:
    """,
    input_variables=["question", "context"],
    )

    # LLM
    llm = ChatGroq(model="llama3-70b-8192")

    # Chain
    rag_chain = prompt | llm | StrOutputParser()
    return rag_chain
rag_chain = get_rag_chain()

### Hallucination Grader 
# Data model
class GradeHallucinations(BaseModel):
    """Binary score for hallucination present in generation answer."""

    binary_score: str = Field(description="Answer is grounded in the facts, 'yes' or 'no'")

def get_hallucination_grader():
    # LLM with function call 
    llm = ChatGroq(model="llama3-70b-8192")
    structured_llm_grader = llm.with_structured_output(GradeHallucinations)

    # Prompt 
    system = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts. \n 
        Give a binary score 'yes' or 'no'. 'Yes' means that the answer is grounded in / supported by the set of facts."""
    hallucination_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "Set of facts: \n\n {documents} \n\n LLM generation: {generation}"),
        ]
    )

    hallucination_grader = hallucination_prompt | structured_llm_grader
    return hallucination_grader
hallucination_grader = get_hallucination_grader()

### Answer Grader 
# Data model
class GradeAnswer(BaseModel):
    """Binary score to assess answer addresses question."""

    binary_score: str = Field(description="Answer addresses the question, 'yes' or 'no'")

def get_answer_grader():
    # LLM with function call 
    llm = ChatGroq(model="llama3-70b-8192")
    structured_llm_grader = llm.with_structured_output(GradeAnswer)

    # Prompt 
    system = """You are a grader assessing whether an answer addresses / resolves a question \n 
        Give a binary score 'yes' or 'no'. Yes' means that the answer resolves the question."""
    answer_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "User question: \n\n {question} \n\n LLM generation: {generation}"),
        ]
    )
    answer_grader = answer_prompt | structured_llm_grader
    return answer_grader
answer_grader = get_answer_grader()


# Graph
class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        web_search: whether to add search
        documents: list of documents 
    """
    question : str
    generation : str
    web_search : str
    documents : List[Document]


# Nodes
def retrieve(state):
    """
    Retrieve documents from vectorstore

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """
    logger.info("---RETRIEVE---")
    question = state["question"]

    # Retrieval
    documents = retriever.invoke(question)
    logger.info(f"Retrived {len(documents)} docs")
    if len(documents) == 0:
        logger.warning("No documents found")
    return {"documents": documents, "question": question}

def generate(state):
    """
    Generate answer using RAG on retrieved documents

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation, that contains LLM generation
    """
    logger.info("---GENERATE---")
    question = state["question"]
    documents = state["documents"]
    
    # RAG generation
    generation = rag_chain.invoke({"context": documents, "question": question})
    logger.info(f"{generation=}")
    return {"documents": documents, "question": question, "generation": generation}

def grade_documents(state):
    """
    Determines whether the retrieved documents are relevant to the question
    If any document is not relevant, we will set a flag to run web search

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Filtered out irrelevant documents and updated web_search state
    """

    logger.info("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state["question"]
    documents = state["documents"]
    
    if documents:
        web_search = "No"
    else:
        # if no docs then use web search
        web_search = "Yes"
        return {"documents": [], "question": question, "web_search": web_search}
    # Score each doc
    filtered_docs = []
    for d in documents:
        score = retrieval_grader.invoke({"question": question, "document": d.page_content})
        grade = score.binary_score
        # Document relevant
        if grade.lower() == "yes":
            logger.info("---GRADE: DOCUMENT RELEVANT---")
            filtered_docs.append(d)
        # Document not relevant
        else:
            logger.info("---GRADE: DOCUMENT NOT RELEVANT---")
            # We do not include the document in filtered_docs
            # We set a flag to indicate that we want to run web search
            web_search = "Yes"
            continue
    return {"documents": filtered_docs, "question": question, "web_search": web_search}
    
def web_search(state):
    """
    Web search based based on the question

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Appended web results to documents
    """

    logger.info("---WEB SEARCH---")
    question = state["question"]
    documents = state["documents"]

    # query augmentation
    if ' now ' in question or 'right now' in question:
        # Get today's date
        today = date.today()
        question += f"arround {today}"

    # Web search
    docs = web_search_tool.invoke({"query": question})
    logger.info(f"Web search query: {question} \n docs: {docs}")
    if docs:
      docs = json.loads(docs)
    web_results = "\n".join([d["snippet"] for d in docs])
    web_results = Document(page_content=web_results)
    if documents is not None:
        documents.append(web_results)
    else:
        documents = [web_results]
    return {"documents": documents, "question": question}

## Edges
def route_question(state):
    """
    Route question to web search or RAG 

    Args:
        state (dict): The current graph state

    Returns:
        str: Next node to call
    """

    logger.info("---ROUTE QUESTION---")
    question = state["question"]
    source = question_router.invoke({"question": question})   
    if source.datasource == 'websearch':
        logger.info("---ROUTE QUESTION TO WEB SEARCH---")
        return "websearch"
    elif source.datasource == 'vectorstore':
        logger.info("---ROUTE QUESTION TO RAG---")
        return "vectorstore"

def decide_to_generate(state):
    """
    Determines whether to generate an answer, or add web search

    Args:
        state (dict): The current graph state

    Returns:
        str: Binary decision for next node to call
    """

    logger.info("---ASSESS GRADED DOCUMENTS---")
    question = state["question"]
    web_search = state["web_search"]
    filtered_documents = state["documents"]

    if web_search == "Yes":
        # All documents have been filtered check_relevance
        # We will re-generate a new query
        logger.info("---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, INCLUDE WEB SEARCH---")
        return "websearch"
    else:
        # We have relevant documents, so generate answer
        logger.info("---DECISION: GENERATE---")
        return "generate"

def grade_generation_v_documents_and_question(state):
    """
    Determines whether the generation is grounded in the document and answers question

    Args:
        state (dict): The current graph state

    Returns:
        str: Decision for next node to call
    """

    logger.info("---CHECK HALLUCINATIONS---")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]

    score = hallucination_grader.invoke({"documents": documents, "generation": generation})
    grade = score.binary_score

    # Check hallucination
    if grade == "yes":
        logger.info("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        # Check question-answering
        logger.info("---GRADE GENERATION vs QUESTION---")
        score = answer_grader.invoke({"question": question,"generation": generation})
        grade = score.binary_score
        if grade == "yes":
            logger.info("---DECISION: GENERATION ADDRESSES QUESTION---")
            return "useful"
        else:
            logger.info("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
            return "not useful"
    else:
        logger.info("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        return "not supported"
    

# Define the workflow
def get_cityhub_agent():
    workflow = StateGraph(GraphState)

    # Define the nodes
    workflow.add_node("websearch", web_search) # web search
    workflow.add_node("retrieve", retrieve) # retrieve
    workflow.add_node("grade_documents", grade_documents) # grade documents
    workflow.add_node("generate", generate) # generatae

    # Build graph
    workflow.set_conditional_entry_point(
        route_question,
        {
            "websearch": "websearch",
            "vectorstore": "retrieve",
        },
    )
    workflow.add_edge("websearch", "generate")
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "websearch": "websearch",
            "generate": "generate",
        },
    )
    workflow.add_conditional_edges(
        "generate",
        grade_generation_v_documents_and_question,
        {
            "not supported": "generate",
            "useful": END,
            "not useful": "websearch",
        },
    )

    # Compile
    app = workflow.compile()
    return app