#!/usr/bin/env python3
"""
Sync repair utility to fix inconsistencies between Vector Search, RAG Engine, and metadata.

This script can:
1. Rebuild metadata cache from GCS documents
2. Re-register documents with RAG Engine
3. Validate and fix citation information
4. Remove orphaned entries

Usage:
    # Rebuild metadata from GCS documents
    python repair_sync.py --rebuild-metadata

    # Re-register all GCS documents with RAG Engine
    python repair_sync.py --sync-rag-engine

    # Full repair (both operations)
    python repair_sync.py --full-repair

    # Dry run (show what would be done without making changes)
    python repair_sync.py --full-repair --dry-run
"""

import os
import json
import logging
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime
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


class SyncRepairer:
    """Repair sync issues between Vector Search, RAG Engine, and metadata."""

    def __init__(self, dry_run: bool = False):
        """Initialize repair tool.

        Args:
            dry_run: If True, only show what would be done without making changes
        """
        self.dry_run = dry_run
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

        if dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")

        logger.info(f"Initialized repair tool for corpus: {self.corpus_name}")

    def get_rag_corpus(self):
        """Get RAG corpus."""
        try:
            corpora = rag.list_corpora()
            for corpus in corpora:
                if corpus.display_name == self.corpus_name:
                    logger.info(f"✓ Found RAG corpus: {corpus.name}")
                    return corpus

            logger.error(f"✗ RAG corpus not found: {self.corpus_name}")
            return None
        except Exception as e:
            logger.error(f"✗ Error getting RAG corpus: {str(e)}")
            return None

    def rebuild_metadata_from_gcs(self) -> Dict[str, Any]:
        """Rebuild metadata cache by reading all JSON documents from GCS.

        Returns:
            Rebuilt metadata dictionary
        """
        logger.info("\n" + "="*80)
        logger.info("REBUILDING METADATA FROM GCS DOCUMENTS")
        logger.info("="*80 + "\n")

        try:
            prefix = f"rag_corpus/{self.corpus_name}/documents/"
            bucket = self.storage_client.bucket(self.bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)

            metadata = {}
            processed = 0
            errors = 0

            for blob in blobs:
                if not blob.name.endswith('.json'):
                    continue

                try:
                    # Download and parse JSON
                    doc_json = blob.download_as_text()
                    doc_data = json.loads(doc_json)

                    # Extract doc ID from filename
                    doc_id = os.path.basename(blob.name).replace('.json', '')

                    # Build metadata entry
                    doc_metadata = doc_data.get('metadata', {})

                    metadata[doc_id] = {
                        'id': doc_id,
                        'content': doc_data.get('content', ''),
                        'metadata': doc_metadata,
                        'source': doc_metadata.get('source_url') or doc_metadata.get('filename', 'Unknown'),
                        'title': doc_metadata.get('title', doc_metadata.get('filename', f'Document {processed+1}')),
                        'images': doc_data.get('images', []),
                        # Add GCS paths for citations
                        'gcs_path': f'gs://{self.bucket_name}/{blob.name}',
                        'gcs_url': f'https://storage.cloud.google.com/{self.bucket_name}/{blob.name}',
                        'gcs_console_url': f'https://console.cloud.google.com/storage/browser/_details/{self.bucket_name}/{blob.name}',
                    }

                    # Preserve original file URL if present
                    if 'original_file_url' in doc_metadata:
                        metadata[doc_id]['metadata']['original_file_url'] = doc_metadata['original_file_url']

                    processed += 1

                    if processed % 100 == 0:
                        logger.info(f"Processed {processed} documents...")

                except Exception as e:
                    logger.error(f"Error processing {blob.name}: {str(e)}")
                    errors += 1

            logger.info(f"\n✓ Rebuilt metadata for {processed} documents")
            if errors > 0:
                logger.warning(f"⚠ {errors} documents had errors")

            return metadata

        except Exception as e:
            logger.error(f"✗ Error rebuilding metadata: {str(e)}")
            return {}

    def save_metadata_to_gcs(self, metadata: Dict[str, Any]) -> bool:
        """Save metadata to GCS.

        Args:
            metadata: Metadata dictionary to save

        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would save metadata for {len(metadata)} documents")
            return True

        try:
            metadata_path = f"rag_corpus/{self.corpus_name}/metadata/document_metadata.json"
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(metadata_path)

            metadata_json = json.dumps(metadata, indent=2)
            blob.upload_from_string(metadata_json, content_type='application/json')

            logger.info(f"✓ Saved metadata to: gs://{self.bucket_name}/{metadata_path}")
            return True

        except Exception as e:
            logger.error(f"✗ Error saving metadata: {str(e)}")
            return False

    def sync_rag_engine(self) -> bool:
        """Re-register all GCS documents with RAG Engine.

        Returns:
            True if successful, False otherwise
        """
        logger.info("\n" + "="*80)
        logger.info("SYNCING DOCUMENTS WITH RAG ENGINE")
        logger.info("="*80 + "\n")

        # Get RAG corpus
        corpus = self.get_rag_corpus()
        if not corpus:
            logger.error("Cannot sync without RAG corpus")
            return False

        try:
            # List all document JSON files
            prefix = f"rag_corpus/{self.corpus_name}/documents/"
            bucket = self.storage_client.bucket(self.bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)

            gcs_paths = []
            for blob in blobs:
                if blob.name.endswith('.json'):
                    gcs_path = f"gs://{self.bucket_name}/{blob.name}"
                    gcs_paths.append(gcs_path)

            if not gcs_paths:
                logger.warning("No documents found to sync")
                return False

            logger.info(f"Found {len(gcs_paths)} documents to register")

            if self.dry_run:
                logger.info(f"[DRY RUN] Would register {len(gcs_paths)} documents with RAG Engine")
                logger.info(f"[DRY RUN] Sample paths: {gcs_paths[:5]}")
                return True

            # Register in batches (RAG Engine limit: 25 per call)
            batch_size = 25
            total_batches = (len(gcs_paths) + batch_size - 1) // batch_size
            successful_batches = 0

            logger.info(f"Registering in {total_batches} batches of {batch_size}...")

            for i in range(0, len(gcs_paths), batch_size):
                batch = gcs_paths[i:i + batch_size]
                batch_num = (i // batch_size) + 1

                try:
                    logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)...")

                    import_response = rag.import_files(
                        corpus_name=corpus.name,
                        paths=batch,
                    )

                    successful_batches += 1
                    logger.info(f"✓ Batch {batch_num} completed")

                except Exception as batch_error:
                    logger.error(f"✗ Batch {batch_num} failed: {str(batch_error)}")
                    # Continue with next batch

            logger.info(f"\n✓ Successfully registered {successful_batches}/{total_batches} batches")

            if successful_batches == total_batches:
                logger.info("✓ All documents successfully registered with RAG Engine")
                return True
            else:
                logger.warning(f"⚠ Only {successful_batches}/{total_batches} batches succeeded")
                return False

        except Exception as e:
            logger.error(f"✗ Error syncing with RAG Engine: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def validate_citations(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and report on citation completeness.

        Args:
            metadata: Metadata dictionary to validate

        Returns:
            Validation report
        """
        logger.info("\n" + "="*80)
        logger.info("VALIDATING CITATION METADATA")
        logger.info("="*80 + "\n")

        report = {
            "total_documents": len(metadata),
            "complete_citations": 0,
            "missing_original_url": 0,
            "missing_title": 0,
            "missing_date": 0,
            "issues": []
        }

        for doc_id, doc_info in metadata.items():
            doc_metadata = doc_info.get('metadata', {})
            issues = []

            # Check original file URL
            if 'original_file_url' not in doc_metadata:
                report['missing_original_url'] += 1
                issues.append("missing_original_file_url")

            # Check title
            if not doc_info.get('title') or doc_info.get('title') == 'Unknown Document':
                report['missing_title'] += 1
                issues.append("missing_title")

            # Check document date
            if 'document_date' not in doc_metadata:
                report['missing_date'] += 1
                issues.append("missing_document_date")

            if not issues:
                report['complete_citations'] += 1
            else:
                report['issues'].append({
                    "doc_id": doc_id,
                    "issues": issues
                })

        # Print summary
        logger.info(f"Total documents: {report['total_documents']}")
        logger.info(f"Complete citations: {report['complete_citations']} ({report['complete_citations']/report['total_documents']*100:.1f}%)")

        if report['missing_original_url'] > 0:
            logger.warning(f"⚠ Missing original file URL: {report['missing_original_url']}")

        if report['missing_title'] > 0:
            logger.warning(f"⚠ Missing title: {report['missing_title']}")

        if report['missing_date'] > 0:
            logger.warning(f"⚠ Missing document date: {report['missing_date']}")

        return report

    def full_repair(self) -> bool:
        """Perform full repair: rebuild metadata and sync RAG Engine.

        Returns:
            True if successful, False otherwise
        """
        logger.info("\n" + "="*80)
        logger.info("FULL REPAIR MODE")
        logger.info("="*80 + "\n")

        success = True

        # Step 1: Rebuild metadata
        logger.info("Step 1: Rebuilding metadata from GCS...")
        metadata = self.rebuild_metadata_from_gcs()

        if not metadata:
            logger.error("Failed to rebuild metadata")
            success = False
        else:
            # Validate citations
            validation_report = self.validate_citations(metadata)

            # Save metadata
            if not self.save_metadata_to_gcs(metadata):
                logger.error("Failed to save metadata")
                success = False

        # Step 2: Sync with RAG Engine
        logger.info("\nStep 2: Syncing with RAG Engine...")
        if not self.sync_rag_engine():
            logger.error("Failed to sync with RAG Engine")
            success = False

        # Summary
        logger.info("\n" + "="*80)
        logger.info("REPAIR SUMMARY")
        logger.info("="*80 + "\n")

        if success:
            if self.dry_run:
                logger.info("✅ DRY RUN COMPLETE - No changes were made")
                logger.info("Run without --dry-run to apply changes")
            else:
                logger.info("✅ REPAIR COMPLETE")
                logger.info("All systems should now be in sync")
        else:
            logger.error("❌ REPAIR FAILED")
            logger.error("Some operations encountered errors")

        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Repair sync issues in Temporal RAG system"
    )

    parser.add_argument(
        '--rebuild-metadata',
        action='store_true',
        help='Rebuild metadata cache from GCS documents'
    )

    parser.add_argument(
        '--sync-rag-engine',
        action='store_true',
        help='Re-register all documents with RAG Engine'
    )

    parser.add_argument(
        '--full-repair',
        action='store_true',
        help='Perform full repair (rebuild metadata + sync RAG Engine)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )

    args = parser.parse_args()

    # Validate arguments
    if not (args.rebuild_metadata or args.sync_rag_engine or args.full_repair):
        parser.print_help()
        print("\nError: Must specify at least one repair operation")
        exit(1)

    try:
        repairer = SyncRepairer(dry_run=args.dry_run)

        success = True

        if args.full_repair:
            success = repairer.full_repair()
        else:
            if args.rebuild_metadata:
                metadata = repairer.rebuild_metadata_from_gcs()
                if metadata:
                    repairer.validate_citations(metadata)
                    if not repairer.save_metadata_to_gcs(metadata):
                        success = False
                else:
                    success = False

            if args.sync_rag_engine:
                if not repairer.sync_rag_engine():
                    success = False

        exit(0 if success else 1)

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        exit(2)


if __name__ == "__main__":
    main()
