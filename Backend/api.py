import os
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

# Import the RAG logic, including the new delete function
from rag_pipeline import (
    process_and_store_document,
    create_rag_chain,
    delete_document_vectors,  # <-- IMPORT THE NEW FUNCTION
    UPLOAD_DIRECTORY
)

app = FastAPI(
    title="Multimodal RAG Project API",
    description="API for uploading, managing, and querying documents for a RAG pipeline.",
    version="2.1.0",  # Version bump for new feature
)

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Welcome to the Multimodal RAG API!"}


@app.post("/upload/", status_code=201)
async def upload_file(
        gemini_api_key: str = Header(...),
        file: UploadFile = File(...)
):
    file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)

    if os.path.exists(file_path):
        raise HTTPException(status_code=409, detail="File with this name already exists.")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")
    finally:
        file.file.close()

    try:
        process_and_store_document(file_path, file.filename, gemini_api_key)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to process and ingest document: {e}")

    return {"filename": file.filename, "status": "Successfully uploaded and processed."}


@app.post("/query/{filename}")
async def query_document(
        filename: str,
        query: str,
        gemini_api_key: str = Header(...)
):
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        rag_chain = create_rag_chain(filename, gemini_api_key)
        answer = rag_chain.invoke(query)
        return {"filename": filename, "query": query, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during query processing: {e}")


@app.get("/documents/", response_model=List[str])
def list_documents():
    try:
        return os.listdir(UPLOAD_DIRECTORY)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not read directory: {e}")


@app.delete("/documents/{filename}")
def delete_document(filename: str):
    """
    Deletes a document AND its associated vector store data.
    """
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")

    try:
        # Step 1: Delete the physical file
        os.remove(file_path)

        # *** Step 2: Call the new function to delete the vectors ***
        delete_document_vectors(filename)

        return {"status": "ok", "message": f"File '{filename}' and its vector data deleted successfully."}
    except Exception as e:
        # Return a more specific error if something goes wrong during deletion
        raise HTTPException(status_code=500, detail=f"Error during deletion process: {e}")

# import os
# import shutil
# from typing import List
# from fastapi import FastAPI, UploadFile, File, HTTPException, Header
# from fastapi.responses import JSONResponse
# # *** NEW: Import CORS Middleware ***
# from fastapi.middleware.cors import CORSMiddleware
#
# # Import the RAG logic from our new module
# # Make sure you have the 'rag_pipeline.py' file from our previous steps
# from rag_pipeline import process_and_store_document, create_rag_chain, UPLOAD_DIRECTORY
#
# # ==============================================================================
# # 2. Initialize the FastAPI Application
# # ==============================================================================
# app = FastAPI(
#     title="Multimodal RAG Project API",
#     description="API for uploading, managing, and querying documents for a RAG pipeline.",
#     version="2.0.0",
# )
#
# # ==============================================================================
# # *** NEW: Add CORS Middleware ***
# # ==============================================================================
# # This allows your React frontend (running on a different port) to communicate with this backend.
# origins = [
#     "http://localhost",
#     "http://localhost:3000",
#     "http://localhost:5173",  # Default Vite dev server port
#     # Add any other origins you might use for your frontend
# ]
#
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
#     allow_headers=["*"],  # Allows all headers
# )
#
#
# # ==============================================================================
# # 3. Define API Endpoints
# # ==============================================================================
#
# @app.get("/")
# def read_root():
#     """A simple root endpoint to confirm the API is running."""
#     return {"status": "ok", "message": "Welcome to the Multimodal RAG API!"}
#
#
# @app.post("/upload/", status_code=201)
# async def upload_file(
#         gemini_api_key: str = Header(...),
#         file: UploadFile = File(...)
# ):
#     """
#     Handles file upload and triggers the RAG ingestion pipeline.
#     The user's Gemini API key must be passed in the request headers.
#     """
#     file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
#
#     if os.path.exists(file_path):
#         raise HTTPException(status_code=409, detail="File with this name already exists.")
#
#     try:
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error saving file: {e}")
#     finally:
#         file.file.close()
#
#     # --- Trigger the RAG processing ---
#     try:
#         process_and_store_document(file_path, file.filename, gemini_api_key)
#     except Exception as e:
#         # If processing fails, clean up the uploaded file
#         os.remove(file_path)
#         raise HTTPException(status_code=500, detail=f"Failed to process and ingest document: {e}")
#
#     return {"filename": file.filename, "status": "Successfully uploaded and processed."}
#
#
# @app.post("/query/{filename}")
# async def query_document(
#         filename: str,
#         query: str,
#         gemini_api_key: str = Header(...)
# ):
#     """
#     Queries a specific, previously uploaded document.
#     """
#     file_path = os.path.join(UPLOAD_DIRECTORY, filename)
#     if not os.path.exists(file_path):
#         raise HTTPException(status_code=404, detail="Document not found.")
#
#     try:
#         rag_chain = create_rag_chain(filename, gemini_api_key)
#         answer = rag_chain.invoke(query)
#         return {"filename": filename, "query": query, "answer": answer}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during query processing: {e}")
#
#
# @app.get("/documents/", response_model=List[str])
# def list_documents():
#     """Lists all the files currently uploaded."""
#     try:
#         return os.listdir(UPLOAD_DIRECTORY)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Could not read directory: {e}")
#
#
# @app.delete("/documents/{filename}")
# def delete_document(filename: str):
#     """
#     Deletes a document and its associated vector store.
#     (Note: Vector store deletion is simplified for this example)
#     """
#     file_path = os.path.join(UPLOAD_DIRECTORY, filename)
#
#     if not os.path.exists(file_path):
#         raise HTTPException(status_code=404, detail="File not found.")
#
#     try:
#         os.remove(file_path)
#         # In a real app, you'd have a more robust way to delete the Chroma collection.
#         # For this project, we assume the collection directory might be manually cleaned if needed.
#         print(f"File {filename} deleted.")
#         return {"status": "ok", "message": f"File '{filename}' deleted successfully."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error deleting file: {e}")
#
# #
# # import os
# # from fastapi import FastAPI, UploadFile, File, HTTPException
# # from fastapi.responses import JSONResponse
# # import shutil
# # from typing import List
# #
# # # ==============================================================================
# # # 2. Initialize the FastAPI Application
# # # ==============================================================================
# # # This 'app' instance is the main entry point for our API.
# # app = FastAPI(
# #     title="Multimodal RAG Project API",
# #     description="API for uploading, managing, and querying documents for a RAG pipeline.",
# #     version="1.1.0",
# # )
# #
# # # Define the directory where uploaded files will be stored temporarily.
# # UPLOAD_DIRECTORY = "./uploaded_files"
# # os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
# #
# #
# # # ==============================================================================
# # # 3. Define a Root Endpoint for Health Checks
# # # ==============================================================================
# # @app.get("/")
# # def read_root():
# #     """
# #     A simple root endpoint to confirm the API is running.
# #     """
# #     return {"status": "ok", "message": "Welcome to the Multimodal RAG API!"}
# #
# #
# # # ==============================================================================
# # # 4. Create the File Management Endpoints (CRUD)
# # # ==============================================================================
# #
# # @app.post("/upload/", status_code=201)
# # async def upload_file(file: UploadFile = File(...)):
# #     """
# #     Handles the uploading of a single file (PDF, Image, or CSV).
# #
# #     This endpoint will:
# #     1. Validate the file type.
# #     2. Save the file to a local directory.
# #     3. (Future) Trigger the RAG ingestion pipeline for that file.
# #     """
# #     allowed_content_types = {
# #         "application/pdf": ".pdf",
# #         "image/jpeg": ".jpg",
# #         "image/png": ".png",
# #         "text/csv": ".csv",
# #         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx"
# #     }
# #
# #     content_type = file.content_type
# #     if content_type not in allowed_content_types:
# #         raise HTTPException(
# #             status_code=400,
# #             detail=f"Invalid file type. Allowed types are: {', '.join(allowed_content_types.keys())}"
# #         )
# #
# #     file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
# #
# #     if os.path.exists(file_path):
# #         raise HTTPException(status_code=409,
# #                             detail="File with this name already exists. Use the update endpoint instead.")
# #
# #     try:
# #         with open(file_path, "wb") as buffer:
# #             shutil.copyfileobj(file.file, buffer)
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"There was an error saving the file: {e}")
# #     finally:
# #         file.file.close()
# #
# #     # In the next phase, we will call our RAG processing logic from here.
# #     processing_status = "File uploaded successfully. Ready for RAG processing."
# #
# #     return {
# #         "filename": file.filename,
# #         "content_type": content_type,
# #         "saved_path": file_path,
# #         "status": processing_status,
# #     }
# #
# #
# # @app.get("/documents/", response_model=List[str])
# # def list_documents():
# #     """
# #     Lists all the files currently in the upload directory.
# #     """
# #     try:
# #         files = os.listdir(UPLOAD_DIRECTORY)
# #         return files
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"Could not read directory: {e}")
# #
# #
# # @app.delete("/documents/{filename}")
# # def delete_document(filename: str):
# #     """
# #     Deletes a specific document from the upload directory.
# #
# #     In a full application, this would also trigger the deletion of
# #     all associated vectors from the vector database.
# #     """
# #     file_path = os.path.join(UPLOAD_DIRECTORY, filename)
# #
# #     if not os.path.exists(file_path):
# #         raise HTTPException(status_code=404, detail="File not found.")
# #
# #     try:
# #         os.remove(file_path)
# #         # Placeholder for vector deletion logic
# #         print(f"File {filename} deleted. (Placeholder for vector deletion)")
# #         return {"status": "ok", "message": f"File '{filename}' deleted successfully."}
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"Error deleting file: {e}")
# #
# #
# # @app.put("/documents/{filename}")
# # async def update_document(filename: str, file: UploadFile = File(...)):
# #     """
# #     Updates an existing document by replacing it with a new one.
# #
# #     This is effectively a delete-then-add operation.
# #     """
# #     file_path = os.path.join(UPLOAD_DIRECTORY, filename)
# #
# #     if not os.path.exists(file_path):
# #         raise HTTPException(status_code=404,
# #                             detail="File to update not found. Use the upload endpoint to create a new file.")
# #
# #     # First, delete the old file
# #     try:
# #         os.remove(file_path)
# #         # Placeholder for vector deletion logic
# #         print(f"Old file {filename} removed for update. (Placeholder for vector deletion)")
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"Could not remove old file for update: {e}")
# #
# #     # Now, save the new file
# #     try:
# #         with open(file_path, "wb") as buffer:
# #             shutil.copyfileobj(file.file, buffer)
# #         print(f"Successfully saved updated file to: {file_path}")
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"There was an error saving the new file: {e}")
# #     finally:
# #         file.file.close()
# #
# #     return {
# #         "status": "ok",
# #         "message": f"File '{filename}' updated successfully.",
# #         "new_file_content_type": file.content_type
# #     }
# #
# # # To run this application:
# # # 1. Save the code as 'api.py'.
# # # 2. Make sure you are in the same directory and your virtual environment is active.
# # # 3. Run the command in your terminal: uvicorn api:app --reload
# # # 4. Open your browser to http://127.0.0.1:8000/docs to see the interactive API documentation.
