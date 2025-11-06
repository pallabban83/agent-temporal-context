"""
WARNING: This script deletes ALL documents from your Vector Search index!
Only run this if you want to start fresh.
"""

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

print('=' * 70)
print('⚠️  WARNING: About to delete ALL documents from Vector Search index')
print('=' * 70)
print(f'\nTotal documents to delete: {len(manager.document_metadata)}')

response = input('\nType "DELETE ALL" to confirm (anything else to cancel): ')

if response == "DELETE ALL":
    print('\n🗑️  Deleting all documents...')
    # TODO: Implement batch delete - Vector Search doesn't have a simple delete all API
    # You'll need to delete the index and recreate it, or delete embeddings individually
    print('\n❌ Batch delete not implemented yet.')
    print('   You need to either:')
    print('   1. Delete and recreate the index via GCP Console')
    print('   2. Or just re-import - duplicates will be overwritten')
else:
    print('\n✓ Cancelled. No documents deleted.')

print('=' * 70)
