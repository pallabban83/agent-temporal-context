# RAG Corpus Sync Troubleshooting Guide

## Overview

Your Temporal RAG system uses a **hybrid architecture** with three interconnected components:

1. **Vector Search Index** - Stores temporal-aware embeddings for semantic search
2. **RAG Engine** - Retrieves document text content via Google's RAG API
3. **Metadata Cache** - Provides citation information (titles, dates, source URLs)

When these components fall out of sync, you'll see symptoms like:
- Documents showing as "Imported" in RAG Engine but missing proper citations
- Query results without clickable source links
- Missing document titles or temporal information
- Inconsistent document counts across systems

## Problem: Document ID Mismatch

### Root Cause

When documents are imported:
1. They're stored in GCS with a unique ID: `gs://bucket/rag_corpus/{corpus}/documents/{doc_id}.json`
2. RAG Engine registers these files and returns them via `source_uri` during queries
3. The system extracts `doc_id` from `source_uri` and looks it up in the **metadata cache**
4. **If the lookup fails**, citations are broken

### Why Lookups Fail

- **Metadata not saved**: Error during import prevented metadata persistence
- **Server restart**: Metadata cache is in-memory and wasn't reloaded from GCS
- **Manual GCS operations**: Files added/removed directly without updating metadata
- **ID format mismatch**: Document IDs don't match between systems

## Diagnostic Tools

### 1. Web UI Diagnostics (Recommended)

**Location**: Navigate to the **🔧 Diagnostics** tab in the web interface

**Actions Available**:

#### Run Diagnostics
- Checks sync status across all three components
- Identifies missing metadata, orphaned documents, and citation issues
- Provides specific recommendations for fixing problems
- **Use this first** to understand what's wrong

#### Rebuild Metadata
- Reconstructs the metadata cache by reading all GCS documents
- Fixes citation issues caused by missing or corrupted metadata
- Safe operation - doesn't modify GCS files or RAG Engine
- **Use when**: Citations are broken but documents exist in GCS

#### Full Repair
- Most comprehensive fix - rebuilds metadata AND re-registers with RAG Engine
- Re-registers all GCS documents with RAG Engine (fixes "documents not searchable")
- Rebuilds complete metadata cache with citation info
- **Use when**: Multiple sync issues detected or after major changes

### 2. Command Line Diagnostics

#### Run Diagnostic Check

```bash
cd backend
python diagnose_sync.py
```

**Output includes**:
- Document counts for each system (metadata, GCS, RAG Engine)
- List of missing metadata entries
- List of documents not registered with RAG Engine
- Citation completeness report
- Specific recommendations

**Exit codes**:
- `0` - All systems healthy
- `1` - Issues detected (check logs)
- `2` - Fatal error

#### Repair Sync Issues

```bash
# Dry run (show what would be done without making changes)
python repair_sync.py --full-repair --dry-run

# Rebuild metadata cache from GCS documents
python repair_sync.py --rebuild-metadata

# Re-register documents with RAG Engine
python repair_sync.py --sync-rag-engine

# Full repair (both operations)
python repair_sync.py --full-repair
```

### 3. API Endpoints

#### Check Sync Status
```bash
curl http://localhost:8000/corpus/diagnostics
```

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "needs_rag_sync",
    "metadata_count": 150,
    "gcs_documents_count": 150,
    "rag_files_count": 130,
    "missing_rag": ["doc_id_1", "doc_id_2", ...],
    "needs_rag_sync": true
  },
  "recommendations": [
    "Run POST /corpus/register-existing-documents to sync documents with RAG Engine"
  ]
}
```

#### Rebuild Metadata Cache
```bash
curl -X POST http://localhost:8000/corpus/rebuild-metadata
```

#### Re-register Documents with RAG Engine
```bash
curl -X POST http://localhost:8000/corpus/register-existing-documents
```

#### Full Repair
```bash
curl -X POST http://localhost:8000/corpus/full-repair
```

## Common Scenarios & Solutions

### Scenario 1: Documents Imported but No Citations

**Symptoms**:
- Documents appear in Vertex AI Studio as "Imported"
- Query results have no title or source URL
- Missing `original_file_url` in metadata

**Diagnosis**:
```bash
python diagnose_sync.py
# Look for: "⚠ X documents in GCS missing from metadata cache"
```

**Solution**:
1. **Via Web UI**: Go to 🔧 Diagnostics tab → Click "Rebuild Metadata"
2. **Via CLI**: `python repair_sync.py --rebuild-metadata`
3. **Via API**: `curl -X POST http://localhost:8000/corpus/rebuild-metadata`

**Why this works**: Reconstructs metadata by reading the JSON files stored in GCS, which contain all original metadata including `original_file_url`.

---

### Scenario 2: Documents Not Appearing in Query Results

**Symptoms**:
- Documents show in GCS bucket
- Diagnostics report: "X GCS documents not registered with RAG Engine"
- Vector Search index has embeddings but RAG retrieval returns nothing

**Diagnosis**:
```bash
python diagnose_sync.py
# Look for: "⚠ X GCS documents not registered with RAG Engine"
```

**Solution**:
1. **Via Web UI**: Go to 🗄️ Corpus tab → Click "Re-register Existing Documents"
2. **Via CLI**: `python repair_sync.py --sync-rag-engine`
3. **Via API**: `curl -X POST http://localhost:8000/corpus/register-existing-documents`

**Why this works**: Tells RAG Engine about documents that were manually upserted to Vector Search but never registered with the RAG API.

---

### Scenario 3: Multiple Issues (Metadata + RAG Sync)

**Symptoms**:
- Both citation issues AND missing query results
- Diagnostics show multiple red flags
- System was recently migrated or restored

**Solution**:
1. **Via Web UI**: Go to 🔧 Diagnostics tab → Click "Full Repair"
2. **Via CLI**: `python repair_sync.py --full-repair`
3. **Via API**: `curl -X POST http://localhost:8000/corpus/full-repair`

**Why this works**: Performs both metadata rebuild and RAG Engine sync in one operation, ensuring all three components are aligned.

---

### Scenario 4: Incomplete Citation Metadata

**Symptoms**:
- Documents have citations but missing temporal info or titles
- Diagnostics report: "X documents with incomplete citation metadata"

**Possible Causes**:
- Documents imported without `document_date` parameter
- Files uploaded without title metadata
- Source URLs not provided during import

**Solution**:
- For **existing documents**: Re-import with complete metadata
- For **new documents**: Always provide:
  - `document_date` (YYYY-MM-DD format)
  - `title` (descriptive document name)
  - Source file (upload via `/documents/upload`)

**Prevention**: Use the file upload endpoint (`POST /documents/upload`) instead of manual import, as it automatically captures:
- Original file URL (stored in GCS)
- Upload timestamp
- File metadata

---

## Best Practices

### 1. Always Use File Upload for Documents

**Recommended**:
```bash
# Upload file with metadata
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@earnings_report.pdf" \
  -F "document_date=2024-10-21" \
  -F "title=Q3 2024 Earnings Report"
```

**Why**: Automatically captures original file URL for proper citations

---

### 2. Run Diagnostics After Major Operations

**When to check**:
- After bulk document imports
- After system restarts
- After manual GCS operations
- Before deploying to production

**How**:
```bash
python diagnose_sync.py
# Or via web UI: 🔧 Diagnostics tab → "Run Diagnostics"
```

---

### 3. Monitor Metadata Cache Size

**Check in-memory metadata**:
```python
# In Python backend
print(f"Metadata entries: {len(agent.rag_manager.document_metadata)}")
```

**If count is 0 or low**:
```bash
python repair_sync.py --rebuild-metadata
```

---

### 4. Backup Metadata Before Repairs

**Manual backup**:
```bash
# Download metadata from GCS
gsutil cp gs://{bucket}/rag_corpus/{corpus}/metadata/document_metadata.json ./backup_metadata.json

# Or via gcloud console
gcloud storage cp gs://{bucket}/rag_corpus/{corpus}/metadata/document_metadata.json ./backup_metadata.json
```

---

## Understanding the Diagnostic Report

### Status Levels

#### ✅ HEALTHY
- All systems in sync
- Complete citation metadata
- No action needed

#### ⚠️ NEEDS RAG ENGINE SYNC
- Documents exist in GCS but not registered with RAG Engine
- They won't appear in query results
- **Action**: Re-register documents with RAG Engine

#### ❌ PARTIAL ISSUES
- Some metadata or citation problems
- System mostly functional but citations may be incomplete
- **Action**: Review specific issues and apply targeted fixes

### Key Metrics

```
Metadata Entries: 150      ← In-memory cache (for citations)
GCS Documents: 150         ← Source of truth (JSON files)
RAG Engine Files: 145      ← Registered for retrieval
```

**Ideal state**: All three numbers match

**Common issues**:
- `GCS > Metadata`: Run rebuild metadata
- `GCS > RAG Engine`: Re-register documents
- `Metadata > GCS`: Orphaned metadata (clean up)

---

## Architecture Deep Dive

### Document Import Flow

```
User uploads PDF
    ↓
[Parse & Chunk]
    ↓
[Extract Temporal Info]
    ↓
[Generate Embeddings] ← Temporal context added to text
    ↓
[Store in GCS] ← JSON files with full metadata
    ↓
[Upsert to Vector Search] ← Embeddings only
    ↓
[Register with RAG Engine] ← Links Vector Search to GCS
    ↓
[Save Metadata Cache] ← In-memory + GCS backup
```

### Query Flow

```
User query
    ↓
[Generate Query Embedding] ← With temporal context
    ↓
[Vector Search] ← Finds similar embeddings
    ↓
[RAG Engine Retrieval] ← Fetches text from GCS via source_uri
    ↓
[Metadata Lookup] ← Extract doc_id from source_uri
    ↓
[Format Citations] ← Add title, date, URL from metadata
    ↓
Return results with citations
```

**Critical point**: If metadata lookup fails at step 5, citations are empty!

---

## Troubleshooting Workflow

```
START
  ↓
Run Diagnostics (Web UI or CLI)
  ↓
Status = HEALTHY? → ✅ Done
  ↓ No
Missing Metadata? → YES → Rebuild Metadata
  ↓ No
Missing RAG Sync? → YES → Re-register Documents
  ↓ No
Multiple Issues? → YES → Full Repair
  ↓
Re-run Diagnostics
  ↓
Status = HEALTHY? → ✅ Done
  ↓ No
Check logs for specific errors
```

---

## FAQ

### Q: Will these repairs delete my documents?

**A**: No. All repair operations are **read-and-register only**:
- Rebuild Metadata: Reads GCS files, rebuilds cache
- Sync RAG Engine: Registers existing GCS files
- Full Repair: Combination of above

None of these operations delete or modify your GCS documents or Vector Search embeddings.

---

### Q: How long does Full Repair take?

**A**: Depends on document count:
- 100 documents: ~30 seconds
- 1,000 documents: ~5 minutes
- 10,000 documents: ~30-60 minutes

Batching is automatic (25 documents per RAG Engine call).

---

### Q: Can I run diagnostics in production?

**A**: Yes. The diagnostic tool only **reads** data and doesn't modify anything. It's safe to run anytime.

---

### Q: What if Full Repair fails?

**A**: Check backend logs:
```bash
tail -f backend/logs/app.log
```

Common failures:
- **RAG Engine quota exceeded**: Wait and retry
- **GCS permission denied**: Check service account permissions
- **Corpus not found**: Re-create corpus (Step 2 in Corpus Manager)

---

### Q: Do I need to re-run diagnostics after each import?

**A**: Not necessary for normal operations. The system should stay in sync. Only run diagnostics if:
- You notice citation issues
- After system crashes or restarts
- After manual GCS operations

---

## Getting Help

If you're still experiencing sync issues after trying these solutions:

1. **Check backend logs**:
   ```bash
   tail -f backend/logs/app.log
   ```

2. **Verify GCS bucket structure**:
   ```bash
   gsutil ls -r gs://{bucket}/rag_corpus/{corpus}/
   ```

3. **Check Vector Search index status**:
   - Go to Vertex AI Console → Vector Search
   - Verify index and endpoint are "READY"

4. **Verify RAG corpus exists**:
   ```bash
   gcloud ai indexes list --location=us-central1
   ```

5. **Run verbose diagnostics**:
   ```bash
   python diagnose_sync.py 2>&1 | tee diagnostic_output.log
   ```

---

## Summary

| Problem | Solution | Tool |
|---------|----------|------|
| No citations | Rebuild metadata | Web UI or `repair_sync.py --rebuild-metadata` |
| Missing query results | Re-register with RAG | Web UI or `repair_sync.py --sync-rag-engine` |
| Multiple issues | Full repair | Web UI or `repair_sync.py --full-repair` |
| Not sure what's wrong | Run diagnostics | Web UI or `diagnose_sync.py` |

**Remember**: Always run diagnostics first to understand the issue before applying repairs!
