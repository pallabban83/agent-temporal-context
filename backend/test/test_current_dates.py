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

print('Checking ALL document dates in index...')
print('=' * 70)

# Count by date
date_counts = {}
for doc_id, doc_info in manager.document_metadata.items():
    metadata = doc_info.get('metadata', {})
    doc_date = metadata.get('document_date', 'NO_DATE')
    date_counts[doc_date] = date_counts.get(doc_date, 0) + 1

print(f'\nTotal documents: {len(manager.document_metadata)}')
print(f'Unique dates: {len(date_counts)}\n')

# Show date distribution
for date in sorted(date_counts.keys()):
    count = date_counts[date]
    if date == '2024':
        print(f'✗ {date:20} : {count:3} docs  <- WRONG! (just year)')
    elif date == 'NO_DATE':
        print(f'✗ {date:20} : {count:3} docs  <- WRONG! (no date)')
    elif len(date) == 10 and date.startswith('2024'):
        print(f'✓ {date:20} : {count:3} docs  <- CORRECT')
    else:
        print(f'? {date:20} : {count:3} docs')

# Check specific Aug 27 docs
print('\n' + '=' * 70)
print('Aug 27, 2024 documents specifically:')
print('=' * 70)

aug_docs = []
for doc_id, doc_info in manager.document_metadata.items():
    metadata = doc_info.get('metadata', {})
    filename = metadata.get('filename', '')
    
    if 'Aug 27' in filename or 'aug 27' in filename.lower():
        aug_docs.append({
            'filename': filename,
            'date': metadata.get('document_date', 'NO DATE'),
            'uploaded': metadata.get('uploaded_at', 'UNKNOWN')[:19]
        })

for doc in sorted(aug_docs, key=lambda x: x['uploaded'], reverse=True):
    status = '✓' if doc['date'] == '2024-08-27' else '✗'
    print(f'{status} {doc["filename"]:30} date={doc["date"]:15} uploaded={doc["uploaded"]}')

print('=' * 70)
