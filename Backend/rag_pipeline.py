# rag_pipeline.py (Updated)

import os
from PIL import Image
from io import BytesIO

# LangChain and AI Model Imports
from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores.chroma import Chroma
from langchain.prompts import PromptTemplate
from langchain.schema.document import Document
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda, RunnableParallel
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Document Processing Imports
from unstructured.partition.auto import partition
from unstructured.documents.elements import Table, Image as UnstructuredImage
from sentence_transformers import CrossEncoder

# ==============================================================================
# Global Variables and Model Initialization
# ==============================================================================
VECTORSTORE_DIRECTORY = "./vector_store"
UPLOAD_DIRECTORY = "./uploaded_files"

os.makedirs(VECTORSTORE_DIRECTORY, exist_ok=True)
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

print("Initializing models...")
EMBEDDING_MODEL = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
CROSS_ENCODER_MODEL = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
print("Models initialized successfully.")


# ==============================================================================
# Helper Functions
# ==============================================================================

def sanitize_filename_for_collection(filename: str) -> str:
    """Sanitizes a filename to be a valid ChromaDB collection name."""
    safe_name = filename.replace(" ", "_").replace(".", "_")
    return f"rag_{safe_name}"


def get_image_description(image_bytes: bytes, api_key: str) -> str:
    """Generates a description for an image using Gemini Vision."""
    vision_llm = ChatGoogleGenerativeAI(
        model="gemini-pro-vision",
        google_api_key=api_key,
        safety_settings={
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        },
    )
    image = Image.open(BytesIO(image_bytes))
    prompt_text = "You are an expert at analyzing documents. Provide a detailed, comprehensive description of this image, which was extracted from a document. Describe all objects, charts, graphs, and any text visible. This description will be used for a retrieval system, so be as descriptive as possible."
    message = {"role": "user",
               "content": [{"type": "text", "text": prompt_text}, {"type": "image_url", "image_url": image}]}
    response = vision_llm.invoke([message])
    return response.content


def summarize_table(table_element: Table, api_key: str) -> str:
    """Summarizes a table element using Gemini."""
    table_html = table_element.metadata.text_as_html
    prompt = f"You are an expert at analyzing tables. Summarize the following HTML table. Describe its structure, columns, and a few example rows to capture its essence. This summary will be used for a retrieval system.\n\nTable:\n{table_html}"
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
    response = model.invoke(prompt)
    return response.content

# ==============================================================================
# Core RAG Ingestion and Querying Logic
# ==============================================================================

def process_and_store_document(file_path: str, filename: str, api_key: str):
    """
    The main ingestion pipeline. Parses a document, processes its elements,
    creates vector embeddings, and stores them in a persistent ChromaDB.
    """
    print(f"Starting ingestion for {filename}...")

    # Use Unstructured.io to partition the document
    elements = partition(filename=file_path, extract_images_in_pdf=True, infer_table_structure=True,
                         image_output_dir_path=UPLOAD_DIRECTORY)

    documents_to_embed = []
    raw_text = ""

    for element in elements:
        if isinstance(element, Table):
            summary = summarize_table(element, api_key)
            documents_to_embed.append(
                Document(page_content=summary, metadata={"source": filename, "type": "table_summary"}))
        elif isinstance(element, UnstructuredImage):
            try:
                with open(element.metadata.image_path, "rb") as img_file:
                    img_bytes = img_file.read()
                description = get_image_description(img_bytes, api_key)
                documents_to_embed.append(Document(page_content=description,
                                                   metadata={"source": element.metadata.image_path,
                                                             "type": "image_description"}))
            except Exception as e:
                print(f"Could not process image {element.metadata.image_path}: {e}")
        else:
            raw_text += element.text + "\n\n"

    # Intelligently chunk the collected raw text
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=750, chunk_overlap=100)
    text_chunks = text_splitter.split_text(raw_text)
    for chunk in text_chunks:
        documents_to_embed.append(Document(page_content=chunk, metadata={"source": filename, "type": "text"}))

    collection_name = sanitize_filename_for_collection(filename)

    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=EMBEDDING_MODEL,
        persist_directory=VECTORSTORE_DIRECTORY
    )
    vector_store.add_documents(documents_to_embed)
    vector_store.persist()
    print(f"Ingestion complete for {filename}. Vectors stored in collection: {collection_name}")


def create_rag_chain(filename: str, api_key: str):
    """
    Creates the full RAG chain with a retriever and re-ranker for a specific document.
    """
    collection_name = sanitize_filename_for_collection(filename)

    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=EMBEDDING_MODEL,
        persist_directory=VECTORSTORE_DIRECTORY
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": 25})

    def rerank_docs(inputs):
        query = inputs['question']
        docs = inputs['context']
        pairs = [[query, doc.page_content] for doc in docs]
        scores = CROSS_ENCODER_MODEL.predict(pairs)
        doc_scores = list(zip(docs, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, score in doc_scores[:5]]

    rag_prompt = PromptTemplate.from_template(
        """
        You are a helpful assistant. Answer the user's question based ONLY on the following context.
        If the context does not contain the answer, state that you don't have enough information.

        CONTEXT:
        {context}

        QUESTION:
        {question}

        ANSWER:
        """
    )
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)

    setup_and_retrieval = RunnableParallel(
        {"context": retriever, "question": RunnablePassthrough()}
    )

    rag_chain = (
            setup_and_retrieval
            | RunnablePassthrough.assign(context=RunnableLambda(rerank_docs))
            | {
                "context": lambda x: "\n\n".join(doc.page_content for doc in x["context"]),
                "question": lambda x: x["question"],
            }
            | rag_prompt
            | llm
            | StrOutputParser()
    )
    return rag_chain


# *** NEW FUNCTION TO DELETE VECTORS ***
def delete_document_vectors(filename: str):
    """
    Deletes all vectors associated with a specific filename from its ChromaDB collection.
    """
    collection_name = sanitize_filename_for_collection(filename)

    try:
        # Connect to the persistent ChromaDB
        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=EMBEDDING_MODEL,
            persist_directory=VECTORSTORE_DIRECTORY
        )

        # Get all documents in the collection to find their IDs
        # This is necessary because Chroma's delete works by ID
        all_docs = vector_store.get(include=["metadatas"])

        if not all_docs or not all_docs['ids']:
            print(f"No vectors found for document: {filename} in collection {collection_name}. Nothing to delete.")
            return

        ids_to_delete = [
            doc_id for i, doc_id in enumerate(all_docs['ids'])
            if all_docs['metadatas'][i].get('source') == filename
        ]

        if ids_to_delete:
            print(f"Found {len(ids_to_delete)} vectors to delete for document: {filename}")
            vector_store.delete(ids=ids_to_delete)
            vector_store.persist()
            print(f"Successfully deleted vectors for {filename}.")
        else:
            print(f"No vectors specifically matching source '{filename}' found for deletion.")

    except Exception as e:
        print(f"An error occurred while trying to delete vectors for {filename}: {e}")
        # Depending on the desired behavior, you might want to raise this exception
        # For now, we'll just print it.



# import os
# from PIL import Image
# from io import BytesIO
# from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory
# from langchain.embeddings import HuggingFaceEmbeddings
# from langchain.vectorstores.chroma import Chroma
# from langchain.prompts import PromptTemplate
# from langchain.schema.document import Document
# from langchain.schema.output_parser import StrOutputParser
# from langchain.schema.runnable import RunnablePassthrough, RunnableLambda, RunnableParallel
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from unstructured.partition.auto import partition
# from unstructured.documents.elements import Table, Image as UnstructuredImage
# from sentence_transformers import CrossEncoder
#
# # ==============================================================================
# # 2. Global Variables and Model Initialization
# # ==============================================================================
# # Directories for storing data
# VECTORSTORE_DIRECTORY = "./vector_store"
# UPLOAD_DIRECTORY = "./uploaded_files"
# os.makedirs(VECTORSTORE_DIRECTORY, exist_ok=True)
# os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
#
# # Initialize the models once to be reused across the application
# print("Initializing models...")
# EMBEDDING_MODEL = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
# CROSS_ENCODER_MODEL = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
# print("Models initialized successfully.")
#
#
# # ==============================================================================
# # 3. Helper Functions
# # ==============================================================================
#
# def sanitize_filename_for_collection(filename: str) -> str:
#     """
#     Sanitizes a filename to be a valid ChromaDB collection name.
#     Replaces spaces and periods with underscores.
#     """
#     # Replace spaces and periods with underscores
#     safe_name = filename.replace(" ", "_").replace(".", "_")
#     return f"rag_{safe_name}"
#
#
# def get_image_description(image_bytes: bytes, api_key: str) -> str:
#     """Generates a description for an image using Gemini Vision."""
#     vision_llm = ChatGoogleGenerativeAI(
#         model="gemini-pro-vision",
#         google_api_key=api_key,
#         safety_settings={
#             HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
#             HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
#             HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
#             HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
#         },
#     )
#     image = Image.open(BytesIO(image_bytes))
#     prompt_text = "You are an expert at analyzing documents. Provide a detailed, comprehensive description of this image, which was extracted from a document. Describe all objects, charts, graphs, and any text visible. This description will be used for a retrieval system, so be as descriptive as possible."
#     message = {"role": "user",
#                "content": [{"type": "text", "text": prompt_text}, {"type": "image_url", "image_url": image}]}
#     response = vision_llm.invoke([message])
#     return response.content
#
#
# def summarize_table(table_element: Table, api_key: str) -> str:
#     """Summarizes a table element using Gemini."""
#     table_html = table_element.metadata.text_as_html
#     prompt = f"You are an expert at analyzing tables. Summarize the following HTML table. Describe its structure, columns, and a few example rows to capture its essence. This summary will be used for a retrieval system.\n\nTable:\n{table_html}"
#     model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
#     response = model.invoke(prompt)
#     return response.content
#
#
# # ==============================================================================
# # 4. Core RAG Ingestion and Querying Logic
# # ==============================================================================
#
# def process_and_store_document(file_path: str, filename: str, api_key: str):
#     """
#     The main ingestion pipeline. Parses a document, processes its elements,
#     creates vector embeddings, and stores them in a persistent ChromaDB.
#     """
#     print(f"Starting ingestion for {filename}...")
#
#     # Use Unstructured.io to partition the document
#     elements = partition(filename=file_path, extract_images_in_pdf=True, infer_table_structure=True,
#                          image_output_dir_path=UPLOAD_DIRECTORY)
#
#     documents_to_embed = []
#     raw_text = ""
#
#     for element in elements:
#         if isinstance(element, Table):
#             summary = summarize_table(element, api_key)
#             documents_to_embed.append(
#                 Document(page_content=summary, metadata={"source": filename, "type": "table_summary"}))
#         # *** FIX: Re-added the missing logic to handle image elements ***
#         elif isinstance(element, UnstructuredImage):
#             try:
#                 with open(element.metadata.image_path, "rb") as img_file:
#                     img_bytes = img_file.read()
#                 description = get_image_description(img_bytes, api_key)
#                 documents_to_embed.append(Document(page_content=description,
#                                                    metadata={"source": element.metadata.image_path,
#                                                              "type": "image_description"}))
#             except Exception as e:
#                 print(f"Could not process image {element.metadata.image_path}: {e}")
#         else:
#             raw_text += element.text + "\n\n"
#
#     # Intelligently chunk the collected raw text
#     text_splitter = RecursiveCharacterTextSplitter(chunk_size=750, chunk_overlap=100)
#     text_chunks = text_splitter.split_text(raw_text)
#     for chunk in text_chunks:
#         documents_to_embed.append(Document(page_content=chunk, metadata={"source": filename, "type": "text"}))
#
#     # Sanitize the filename for the collection name
#     collection_name = sanitize_filename_for_collection(filename)
#
#     # Initialize ChromaDB with a persistent directory
#     vector_store = Chroma(
#         collection_name=collection_name,
#         embedding_function=EMBEDDING_MODEL,
#         persist_directory=VECTORSTORE_DIRECTORY
#     )
#     vector_store.add_documents(documents_to_embed)
#     vector_store.persist()
#     print(f"Ingestion complete for {filename}. Vectors stored in collection: {collection_name}")
#
#
# def create_rag_chain(filename: str, api_key: str):
#     """
#     Creates the full RAG chain with a retriever and re-ranker for a specific document.
#     """
#     # Sanitize the filename to find the correct collection
#     collection_name = sanitize_filename_for_collection(filename)
#
#     vector_store = Chroma(
#         collection_name=collection_name,
#         embedding_function=EMBEDDING_MODEL,
#         persist_directory=VECTORSTORE_DIRECTORY
#     )
#     retriever = vector_store.as_retriever(search_kwargs={"k": 25})
#
#     def rerank_docs(inputs):
#         query = inputs['question']
#         docs = inputs['context']
#         pairs = [[query, doc.page_content] for doc in docs]
#         scores = CROSS_ENCODER_MODEL.predict(pairs)
#         doc_scores = list(zip(docs, scores))
#         doc_scores.sort(key=lambda x: x[1], reverse=True)
#         return [doc for doc, score in doc_scores[:5]]
#
#     rag_prompt = PromptTemplate.from_template(
#         """
#         You are a helpful assistant. Answer the user's question based ONLY on the following context.
#         If the context does not contain the answer, state that you don't have enough information.
#
#         CONTEXT:
#         {context}
#
#         QUESTION:
#         {question}
#
#         ANSWER:
#         """
#     )
#     llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
#
#     setup_and_retrieval = RunnableParallel(
#         {"context": retriever, "question": RunnablePassthrough()}
#     )
#
#     rag_chain = (
#             setup_and_retrieval
#             | RunnablePassthrough.assign(context=RunnableLambda(rerank_docs))
#             | {
#                 "context": lambda x: "\n\n".join(doc.page_content for doc in x["context"]),
#                 "question": lambda x: x["question"],
#             }
#             | rag_prompt
#             | llm
#             | StrOutputParser()
#     )
#     return rag_chain
#
# # import os
# # from PIL import Image
# # from io import BytesIO
# #
# # # LangChain and AI Model Imports
# # from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory
# # from langchain.embeddings import HuggingFaceEmbeddings
# # from langchain.vectorstores.chroma import Chroma
# # from langchain.prompts import PromptTemplate
# # from langchain.schema.document import Document
# # from langchain.schema.output_parser import StrOutputParser
# # from langchain.schema.runnable import RunnablePassthrough, RunnableLambda, RunnableParallel
# # from langchain.text_splitter import RecursiveCharacterTextSplitter
# #
# # # Document Processing Imports
# # from unstructured.partition.pdf import partition_pdf
# # from unstructured.partition.auto import partition
# # from unstructured.documents.elements import Table, Image as UnstructuredImage
# # from sentence_transformers import CrossEncoder
# #
# # # ==============================================================================
# # # 2. Global Variables and Model Initialization
# # # ==============================================================================
# # # Directories for storing data
# # VECTORSTORE_DIRECTORY = "./vector_store"
# # UPLOAD_DIRECTORY = "./uploaded_files"
# #
# # # Ensure directories exist
# # os.makedirs(VECTORSTORE_DIRECTORY, exist_ok=True)
# # os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
# #
# # # Initialize the models once to be reused across the application
# # print("Initializing models...")
# # EMBEDDING_MODEL = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
# # CROSS_ENCODER_MODEL = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
# # print("Models initialized successfully.")
# #
# #
# # # ==============================================================================
# # # 3. Helper Functions
# # # ==============================================================================
# #
# # def sanitize_filename_for_collection(filename: str) -> str:
# #     """
# #     Sanitizes a filename to be a valid ChromaDB collection name.
# #     Replaces spaces and periods with underscores.
# #     """
# #     # Replace spaces and periods with underscores
# #     safe_name = filename.replace(" ", "_").replace(".", "_")
# #     return f"rag_{safe_name}"
# #
# #
# # def get_image_description(image_bytes: bytes, api_key: str) -> str:
# #     """Generates a description for an image using Gemini Vision."""
# #     vision_llm = ChatGoogleGenerativeAI(
# #         model="gemini-2.5-pro",
# #         google_api_key=api_key,
# #         safety_settings={
# #             HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
# #             HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
# #             HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
# #             HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
# #         },
# #     )
# #     image = Image.open(BytesIO(image_bytes))
# #     prompt_text = "You are an expert at analyzing documents. Provide a detailed, comprehensive description of this image, which was extracted from a document. Describe all objects, charts, graphs, and any text visible. This description will be used for a retrieval system, so be as descriptive as possible."
# #     message = {"role": "user",
# #                "content": [{"type": "text", "text": prompt_text}, {"type": "image_url", "image_url": image}]}
# #     response = vision_llm.invoke([message])
# #     return response.content
# #
# #
# # def summarize_table(table_element: Table, api_key: str) -> str:
# #     """Summarizes a table element using Gemini."""
# #     table_html = table_element.metadata.text_as_html
# #     prompt = f"You are an expert at analyzing tables. Summarize the following HTML table. Describe its structure, columns, and a few example rows to capture its essence. This summary will be used for a retrieval system.\n\nTable:\n{table_html}"
# #     model = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=api_key)
# #     response = model.invoke(prompt)
# #     return response.content
# #
# #
# # # ==============================================================================
# # # 4. Core RAG Ingestion and Querying Logic
# # # ==============================================================================
# #
# # def process_and_store_document(file_path: str, filename: str, api_key: str):
# #     """
# #     The main ingestion pipeline. Parses a document, processes its elements,
# #     creates vector embeddings, and stores them in a persistent ChromaDB.
# #     """
# #     print(f"Starting ingestion for {filename}...")
# #
# #     # Use Unstructured.io to partition the document
# #     elements = partition(filename=file_path, extract_images_in_pdf=True, infer_table_structure=True)
# #
# #     documents_to_embed = []
# #     raw_text = ""
# #
# #     for element in elements:
# #         if isinstance(element, Table):
# #             summary = summarize_table(element, api_key)
# #             documents_to_embed.append(
# #                 Document(page_content=summary, metadata={"source": filename, "type": "table_summary"}))
# #         # Note: Unstructured's image extraction is complex; focusing on text/tables for robustness
# #         else:
# #             raw_text += element.text + "\n\n"
# #
# #     # Intelligently chunk the collected raw text
# #     text_splitter = RecursiveCharacterTextSplitter(chunk_size=750, chunk_overlap=100)
# #     text_chunks = text_splitter.split_text(raw_text)
# #     for chunk in text_chunks:
# #         documents_to_embed.append(Document(page_content=chunk, metadata={"source": filename, "type": "text"}))
# #
# #     # *** FIX: Sanitize the filename for the collection name ***
# #     collection_name = sanitize_filename_for_collection(filename)
# #
# #     # Initialize ChromaDB with a persistent directory
# #     vector_store = Chroma(
# #         collection_name=collection_name,
# #         embedding_function=EMBEDDING_MODEL,
# #         persist_directory=VECTORSTORE_DIRECTORY
# #     )
# #     vector_store.add_documents(documents_to_embed)
# #     vector_store.persist()
# #     print(f"Ingestion complete for {filename}. Vectors stored in collection: {collection_name}")
# #
# #
# # def create_rag_chain(filename: str, api_key: str):
# #     """
# #     Creates the full RAG chain with a retriever and re-ranker for a specific document.
# #     """
# #     # *** FIX: Sanitize the filename to find the correct collection ***
# #     collection_name = sanitize_filename_for_collection(filename)
# #
# #     vector_store = Chroma(
# #         collection_name=collection_name,
# #         embedding_function=EMBEDDING_MODEL,
# #         persist_directory=VECTORSTORE_DIRECTORY
# #     )
# #     retriever = vector_store.as_retriever(search_kwargs={"k": 25})
# #
# #     def rerank_docs(inputs):
# #         query = inputs['question']
# #         docs = inputs['context']
# #         pairs = [[query, doc.page_content] for doc in docs]
# #         scores = CROSS_ENCODER_MODEL.predict(pairs)
# #         doc_scores = list(zip(docs, scores))
# #         doc_scores.sort(key=lambda x: x[1], reverse=True)
# #         return [doc for doc, score in doc_scores[:5]]
# #
# #     rag_prompt = PromptTemplate.from_template(
# #         """
# #         You are a helpful assistant. Answer the user's question based ONLY on the following context.
# #         If the context does not contain the answer, state that you don't have enough information.
# #
# #         CONTEXT:
# #         {context}
# #
# #         QUESTION:
# #         {question}
# #
# #         ANSWER:
# #         """
# #     )
# #     llm = ChatGoogleGenerativeAI(model="gemini-1.0-pro", google_api_key=api_key)
# #
# #     setup_and_retrieval = RunnableParallel(
# #         {"context": retriever, "question": RunnablePassthrough()}
# #     )
# #
# #     rag_chain = (
# #             setup_and_retrieval
# #             | RunnablePassthrough.assign(context=RunnableLambda(rerank_docs))
# #             | {
# #                 "context": lambda x: "\n\n".join(doc.page_content for doc in x["context"]),
# #                 "question": lambda x: x["question"],
# #             }
# #             | rag_prompt
# #             | llm
# #             | StrOutputParser()
# #     )
# #     return rag_chain
# #
# # # import os
# # # from PIL import Image
# # # from io import BytesIO
# # #
# # # # LangChain and AI Model Imports
# # # from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory
# # # from langchain.embeddings import HuggingFaceEmbeddings
# # # from langchain.vectorstores.chroma import Chroma
# # # from langchain.prompts import PromptTemplate
# # # from langchain.schema.document import Document
# # # from langchain.schema.output_parser import StrOutputParser
# # # from langchain.schema.runnable import RunnablePassthrough, RunnableLambda, RunnableParallel
# # # from langchain.text_splitter import RecursiveCharacterTextSplitter
# # #
# # # # Document Processing Imports
# # # from unstructured.partition.pdf import partition_pdf
# # # from unstructured.documents.elements import Table, Image as UnstructuredImage
# # # from sentence_transformers import CrossEncoder
# # #
# # # # ==============================================================================
# # # # 2. Global Variables and Model Initialization
# # # # ==============================================================================
# # # # Directories for storing data
# # # VECTORSTORE_DIRECTORY = "./vector_store"
# # # UPLOAD_DIRECTORY = "./uploaded_files"
# # #
# # # # Ensure directories exist
# # # os.makedirs(VECTORSTORE_DIRECTORY, exist_ok=True)
# # # os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
# # #
# # # # Initialize the models once to be reused across the application
# # # # This is efficient as they don't need to be loaded on every API call.
# # # print("Initializing models...")
# # # EMBEDDING_MODEL = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
# # # CROSS_ENCODER_MODEL = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
# # # print("Models initialized successfully.")
# # #
# # #
# # # # ==============================================================================
# # # # 3. Helper Functions for Multimodal Processing
# # # # ==============================================================================
# # #
# # # def get_image_description(image_bytes: bytes, api_key: str) -> str:
# # #     """Generates a description for an image using Gemini Vision."""
# # #     vision_llm = ChatGoogleGenerativeAI(
# # #         model="gemini-2.5-pro",
# # #         google_api_key=api_key,
# # #         safety_settings={
# # #             HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
# # #             HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
# # #             HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
# # #             HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
# # #         },
# # #     )
# # #     image = Image.open(BytesIO(image_bytes))
# # #     prompt_text = "You are an expert at analyzing documents. Provide a detailed, comprehensive description of this image, which was extracted from a document. Describe all objects, charts, graphs, and any text visible. This description will be used for a retrieval system, so be as descriptive as possible."
# # #     message = {"role": "user",
# # #                "content": [{"type": "text", "text": prompt_text}, {"type": "image_url", "image_url": image}]}
# # #     response = vision_llm.invoke([message])
# # #     return response.content
# # #
# # #
# # # def summarize_table(table_element: Table, api_key: str) -> str:
# # #     """Summarizes a table element using Gemini."""
# # #     table_html = table_element.metadata.text_as_html
# # #     prompt = f"You are an expert at analyzing tables. Summarize the following HTML table. Describe its structure, columns, and a few example rows to capture its essence. This summary will be used for a retrieval system.\n\nTable:\n{table_html}"
# # #     model = ChatGoogleGenerativeAI(model="gemini-1.0-pro", google_api_key=api_key)
# # #     response = model.invoke(prompt)
# # #     return response.content
# # #
# # #
# # # # ==============================================================================
# # # # 4. Core RAG Ingestion and Querying Logic
# # # # ==============================================================================
# # #
# # # def process_and_store_document(file_path: str, filename: str, api_key: str):
# # #     """
# # #     The main ingestion pipeline. Parses a document, processes its elements,
# # #     creates vector embeddings, and stores them in a persistent ChromaDB.
# # #     """
# # #     print(f"Starting ingestion for {filename}...")
# # #
# # #     # Use Unstructured.io to partition the PDF
# # #     raw_pdf_elements = partition_pdf(
# # #         filename=file_path,
# # #         extract_images_in_pdf=True,
# # #         infer_table_structure=True,
# # #         chunking_strategy="by_title",
# # #         max_characters=4000,
# # #         new_after_n_chars=3800,
# # #         combine_text_under_n_chars=2000,
# # #         image_output_dir_path=UPLOAD_DIRECTORY
# # #     )
# # #
# # #     documents_to_embed = []
# # #     raw_text = ""
# # #
# # #     for element in raw_pdf_elements:
# # #         if isinstance(element, Table):
# # #             summary = summarize_table(element, api_key)
# # #             documents_to_embed.append(
# # #                 Document(page_content=summary, metadata={"source": filename, "type": "table_summary"}))
# # #         elif isinstance(element, UnstructuredImage):
# # #             try:
# # #                 with open(element.metadata.image_path, "rb") as img_file:
# # #                     img_bytes = img_file.read()
# # #                 description = get_image_description(img_bytes, api_key)
# # #                 documents_to_embed.append(Document(page_content=description,
# # #                                                    metadata={"source": element.metadata.image_path,
# # #                                                              "type": "image_description"}))
# # #             except Exception as e:
# # #                 print(f"Could not process image {element.metadata.image_path}: {e}")
# # #         else:
# # #             raw_text += element.text + "\n\n"
# # #
# # #     # Intelligently chunk the collected raw text
# # #     text_splitter = RecursiveCharacterTextSplitter(chunk_size=750, chunk_overlap=100)
# # #     text_chunks = text_splitter.split_text(raw_text)
# # #     for chunk in text_chunks:
# # #         documents_to_embed.append(Document(page_content=chunk, metadata={"source": filename, "type": "text"}))
# # #
# # #     # Initialize ChromaDB with a persistent directory
# # #     vector_store = Chroma(
# # #         collection_name=f"rag_{filename.replace('.', '_')}",
# # #         embedding_function=EMBEDDING_MODEL,
# # #         persist_directory=VECTORSTORE_DIRECTORY
# # #     )
# # #     vector_store.add_documents(documents_to_embed)
# # #     vector_store.persist()
# # #     print(f"Ingestion complete for {filename}. Vectors stored.")
# # #
# # #
# # # def create_rag_chain(filename: str, api_key: str):
# # #     """
# # #     Creates the full RAG chain with a retriever and re-ranker for a specific document.
# # #     """
# # #     vector_store = Chroma(
# # #         collection_name=f"rag_{filename.replace('.', '_')}",
# # #         embedding_function=EMBEDDING_MODEL,
# # #         persist_directory=VECTORSTORE_DIRECTORY
# # #     )
# # #     retriever = vector_store.as_retriever(search_kwargs={"k": 25})
# # #
# # #     def rerank_docs(inputs):
# # #         query = inputs['question']
# # #         docs = inputs['context']
# # #         pairs = [[query, doc.page_content] for doc in docs]
# # #         scores = CROSS_ENCODER_MODEL.predict(pairs)
# # #         doc_scores = list(zip(docs, scores))
# # #         doc_scores.sort(key=lambda x: x[1], reverse=True)
# # #         return [doc for doc, score in doc_scores[:5]]
# # #
# # #     rag_prompt = PromptTemplate.from_template(
# # #         """
# # #         You are a helpful assistant. Answer the user's question based on the following context.
# # #         If the context does not contain the answer,try to form answer based on the context without false data or else state that you don't have enough information.
# # #
# # #         CONTEXT:
# # #         {context}
# # #
# # #         QUESTION:
# # #         {question}
# # #
# # #         ANSWER:
# # #         """
# # #     )
# # #     llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=api_key)
# # #
# # #     setup_and_retrieval = RunnableParallel(
# # #         {"context": retriever, "question": RunnablePassthrough()}
# # #     )
# # #
# # #     rag_chain = (
# # #             setup_and_retrieval
# # #             | RunnablePassthrough.assign(context=RunnableLambda(rerank_docs))
# # #             | {
# # #                 "context": lambda x: "\n\n".join(doc.page_content for doc in x["context"]),
# # #                 "question": lambda x: x["question"],
# # #             }
# # #             | rag_prompt
# # #             | llm
# # #             | StrOutputParser()
# # #     )
# # #     return rag_chain
# # #
# # #
# # #
# # #
