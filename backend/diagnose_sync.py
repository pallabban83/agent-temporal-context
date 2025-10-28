#!/usr/bin/env python3
"""
Diagnostic script to check sync status between Vector Search, RAG Engine, and metadata cache.

This script helps identify:
1. Missing metadata entries
2. Orphaned documents in RAG Engine or Vector Search
3. ID mismatches between systems
4. Citation information completeness

Usage:
    python diagnose_sync.py
"""

import os
import json
import logging
from typing import Dict, List, Set, Any
from pathlib import Path
from google.cloud import storage
from vertexai.preview import rag
import vertexai
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SyncDiagnostics:
    """Diagnose sync issues between Vector Search, RAG Engine, and metadata."""

    def __init__(self):
        """Initialize diagnostic tool."""
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        self.location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
        self.corpus_name = os.getenv('VERTEX_AI_CORPUS_NAME', 'temporal-context-corpus')
        self.bucket_name = os.getenv('GCS_BUCKET_NAME')

        # Validate required environment variables
        if not self.bucket_name:
            raise ValueError("GCS_BUCKET_NAME must be set in .env file")
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT must be set in .env file")

        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)

        # Initialize storage client
        self.storage_client = storage.Client(project=self.project_id)

        logger.info(f"Initialized diagnostics for corpus: {self.corpus_name}")
        logger.info(f"Project: {self.project_id}, Location: {self.location}")
        logger.info(f"Bucket: {self.bucket_name}")

    def load_metadata_from_gcs(self) -> Dict[str, Any]:
        """Load document metadata from GCS."""
        try:
            metadata_path = f"rag_corpus/{self.corpus_name}/metadata/document_metadata.json"
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(metadata_path)

            if blob.exists():
                metadata_json = blob.download_as_text()
                metadata = json.loads(metadata_json)
                logger.info(f"✓ Loaded metadata for {len(metadata)} documents from GCS")
                return metadata
            else:
                logger.warning(f"✗ Metadata file not found at: gs://{self.bucket_name}/{metadata_path}")
                return {}
        except Exception as e:
            logger.error(f"✗ Error loading metadata: {str(e)}")
            return {}

    def list_gcs_documents(self) -> List[str]:
        """List all document JSON files in GCS."""
        try:
            prefix = f"rag_corpus/{self.corpus_name}/documents/"
            bucket = self.storage_client.bucket(self.bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)

            doc_ids = []
            for blob in blobs:
                if blob.name.endswith('.json'):
                    # Extract doc ID from filename
                    doc_id = os.path.basename(blob.name).replace('.json', '')
                    doc_ids.append(doc_id)

            logger.info(f"✓ Found {len(doc_ids)} JSON documents in GCS")
            return doc_ids
        except Exception as e:
            logger.error(f"✗ Error listing GCS documents: {str(e)}")
            return []

    def get_rag_corpus(self):
        """Get RAG corpus."""
        try:
            # Try to find corpus by display name
            corpora = rag.list_corpora()
            for corpus in corpora:
                if corpus.display_name == self.corpus_name:
                    logger.info(f"✓ Found RAG corpus: {corpus.name}")
                    return corpus

            logger.warning(f"✗ RAG corpus not found: {self.corpus_name}")
            return None
        except Exception as e:
            logger.error(f"✗ Error getting RAG corpus: {str(e)}")
            return None

    def list_rag_files(self, corpus) -> List[str]:
        """List files imported into RAG Engine."""
        try:
            # List files in the corpus
            files = rag.list_files(corpus_name=corpus.name)

            file_uris = []
            for rag_file in files:
                # Extract doc ID from GCS URI
                # Example: gs://bucket/rag_corpus/corpus-name/documents/doc_id.json
                if hasattr(rag_file, 'gcs_uri'):
                    uri = rag_file.gcs_uri
                elif hasattr(rag_file, 'name'):
                    # The name might contain the path
                    uri = rag_file.name
                else:
                    continue

                doc_id = os.path.basename(uri).replace('.json', '')
                file_uris.append(doc_id)

            logger.info(f"✓ Found {len(file_uris)} files in RAG Engine")
            return file_uris
        except Exception as e:
            logger.error(f"✗ Error listing RAG files: {str(e)}")
            return []

    def analyze_sync_status(self) -> Dict[str, Any]:
        """Analyze sync status across all systems."""
        logger.info("\n" + "="*80)
        logger.info("STARTING SYNC DIAGNOSTICS")
        logger.info("="*80 + "\n")

        # 1. Load metadata cache
        logger.info("Step 1: Checking metadata cache...")
        metadata = self.load_metadata_from_gcs()
        metadata_ids = set(metadata.keys())

        # 2. List GCS documents
        logger.info("\nStep 2: Checking GCS documents...")
        gcs_doc_ids = set(self.list_gcs_documents())

        # 3. Get RAG corpus and list files
        logger.info("\nStep 3: Checking RAG Engine...")
        corpus = self.get_rag_corpus()
        rag_doc_ids = set(self.list_rag_files(corpus)) if corpus else set()

        # 4. Analyze differences
        logger.info("\n" + "="*80)
        logger.info("SYNC ANALYSIS")
        logger.info("="*80 + "\n")

        report = {
            "metadata_count": len(metadata_ids),
            "gcs_documents_count": len(gcs_doc_ids),
            "rag_files_count": len(rag_doc_ids),
            "metadata_ids": sorted(list(metadata_ids))[:10],  # Sample
            "gcs_doc_ids": sorted(list(gcs_doc_ids))[:10],    # Sample
            "rag_doc_ids": sorted(list(rag_doc_ids))[:10],    # Sample
        }

        # Find mismatches
        logger.info("Checking for inconsistencies...\n")

        # Documents in GCS but not in metadata
        missing_metadata = gcs_doc_ids - metadata_ids
        if missing_metadata:
            logger.warning(f"⚠ {len(missing_metadata)} documents in GCS missing from metadata cache")
            logger.warning(f"  Examples: {list(missing_metadata)[:5]}")
            report['missing_metadata'] = list(missing_metadata)
        else:
            logger.info("✓ All GCS documents have metadata entries")

        # Documents in metadata but not in GCS
        orphaned_metadata = metadata_ids - gcs_doc_ids
        if orphaned_metadata:
            logger.warning(f"⚠ {len(orphaned_metadata)} metadata entries without GCS documents")
            logger.warning(f"  Examples: {list(orphaned_metadata)[:5]}")
            report['orphaned_metadata'] = list(orphaned_metadata)
        else:
            logger.info("✓ All metadata entries have corresponding GCS documents")

        # Documents in GCS but not in RAG Engine
        missing_rag = gcs_doc_ids - rag_doc_ids
        if missing_rag:
            logger.warning(f"⚠ {len(missing_rag)} GCS documents not registered with RAG Engine")
            logger.warning(f"  Examples: {list(missing_rag)[:5]}")
            logger.warning("  → Solution: Call POST /corpus/register-existing-documents")
            report['missing_rag'] = list(missing_rag)
            report['needs_rag_sync'] = True
        else:
            logger.info("✓ All GCS documents are registered with RAG Engine")
            report['needs_rag_sync'] = False

        # Documents in RAG Engine but not in GCS
        orphaned_rag = rag_doc_ids - gcs_doc_ids
        if orphaned_rag:
            logger.warning(f"⚠ {len(orphaned_rag)} RAG files without corresponding GCS documents")
            logger.warning(f"  Examples: {list(orphaned_rag)[:5]}")
            report['orphaned_rag'] = list(orphaned_rag)
        else:
            logger.info("✓ All RAG files have corresponding GCS documents")

        # 5. Check citation completeness
        logger.info("\nChecking citation metadata completeness...")

        citation_issues = []
        for doc_id, doc_info in list(metadata.items())[:100]:  # Sample first 100
            issues = []

            # Check for original file URL (most important for citations)
            doc_metadata = doc_info.get('metadata', {})
            if 'original_file_url' not in doc_metadata:
                issues.append("missing_original_file_url")

            # Check for title
            if not doc_info.get('title') or doc_info.get('title') == 'Unknown Document':
                issues.append("missing_title")

            # Check for temporal info
            if 'document_date' not in doc_metadata:
                issues.append("missing_document_date")

            if issues:
                citation_issues.append({
                    "doc_id": doc_id,
                    "issues": issues
                })

        if citation_issues:
            logger.warning(f"⚠ {len(citation_issues)} documents with incomplete citation metadata")
            logger.warning(f"  Common issues: {citation_issues[:3]}")
            report['citation_issues_count'] = len(citation_issues)
            report['citation_issues_sample'] = citation_issues[:10]
        else:
            logger.info("✓ Citation metadata appears complete")

        # 6. Summary
        logger.info("\n" + "="*80)
        logger.info("SUMMARY")
        logger.info("="*80 + "\n")

        if not missing_metadata and not missing_rag and not citation_issues:
            logger.info("✅ SYNC STATUS: HEALTHY")
            logger.info("All systems are in sync with complete metadata")
            report['status'] = 'healthy'
        elif missing_rag:
            logger.warning("⚠️  SYNC STATUS: NEEDS RAG ENGINE SYNC")
            logger.warning(f"   {len(missing_rag)} documents need to be registered with RAG Engine")
            logger.warning("   Run: POST /corpus/register-existing-documents")
            report['status'] = 'needs_rag_sync'
        else:
            logger.warning("⚠️  SYNC STATUS: PARTIAL ISSUES")
            logger.warning("   Some metadata or citation issues detected")
            report['status'] = 'partial_issues'

        logger.info("\n")
        return report

    def save_report(self, report: Dict[str, Any], output_file: str = "sync_diagnostic_report.json"):
        """Save diagnostic report to file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"✓ Diagnostic report saved to: {output_file}")
        except Exception as e:
            logger.error(f"✗ Error saving report: {str(e)}")


def main():
    """Run diagnostics."""
    try:
        diagnostics = SyncDiagnostics()
        report = diagnostics.analyze_sync_status()
        diagnostics.save_report(report)

        # Exit with appropriate code
        if report.get('status') == 'healthy':
            exit(0)
        else:
            exit(1)

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        exit(2)


if __name__ == "__main__":
    main()
