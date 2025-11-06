from vector_search_manager import VectorSearchManager
from temporal_embeddings import TemporalEmbeddingHandler
import os
from dotenv import load_dotenv

load_dotenv()

# Init
embedding_handler = TemporalEmbeddingHandler(
    os.getenv('GOOGLE_CLOUD_PROJECT'),
    os.getenv('GOOGLE_CLOUD_LOCATION')
)
manager = VectorSearchManager(
    project_id=os.getenv('GOOGLE_CLOUD_PROJECT'),
    location=os.getenv('GOOGLE_CLOUD_LOCATION'),
    index_name=os.getenv('VERTEX_AI_CORPUS_NAME'),
    embedding_handler=embedding_handler,
    vector_search_index=os.getenv('VECTOR_SEARCH_INDEX'),
    vector_search_endpoint=os.getenv('VECTOR_SEARCH_INDEX_ENDPOINT')
)

print('Looking for Aug_27,_2024 document...')
print('=' * 70)

# Find the specific document ID from logs
target_id = 'Aug_27,_2024_pdf_1762403043_page1_chunk0'

if target_id in manager.document_metadata:
    doc_info = manager.document_metadata[target_id]
    metadata = doc_info.get('metadata', {})
    
    print(f'✓ Found document: {target_id}\n')
    print('Metadata:')
    print(f'  filename: {metadata.get("filename", "MISSING")}')
    print(f'  document_date: {metadata.get("document_date", "MISSING")}')
    print(f'  uploaded_at: {metadata.get("uploaded_at", "MISSING")[:19]}')
    print(f'  imported_from_gcs: {metadata.get("imported_from_gcs", False)}')
    
    expected = '2024-08-27'
    actual = metadata.get('document_date', '')
    
    print(f'\nExpected date: {expected}')
    print(f'Actual date:   {actual}')
    print(f'Match: {expected == actual}')
    
    if expected != actual:
        print(f'\n✗ PROBLEM: Date is "{actual}" instead of "{expected}"')
        print('This document needs to be re-imported with fixed code!')
else:
    print(f'✗ Document not found: {target_id}')

print('=' * 70)
