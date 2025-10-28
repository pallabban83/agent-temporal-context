"""
Cleanup script to delete old Vector Search resources
This is needed to recreate the index with StreamUpdate enabled
"""

from google.cloud import aiplatform
import os
import sys

def cleanup_resources():
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'gen-lang-client-0960748570')
    location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')

    aiplatform.init(project=project_id, location=location)

    print("Starting cleanup of old Vector Search resources...")
    print("=" * 60)

    try:
        # Step 1: Get the endpoint and undeploy the index
        print("\n1. Finding endpoint...")
        endpoints = aiplatform.MatchingEngineIndexEndpoint.list()
        endpoint = None

        for ep in endpoints:
            if ep.display_name == "temporal-context-corpus-endpoint":
                endpoint = ep
                print(f"   Found endpoint: {ep.resource_name}")
                break

        if endpoint and endpoint.deployed_indexes:
            print("\n2. Undeploying index from endpoint...")
            for deployed_index in endpoint.deployed_indexes:
                print(f"   Undeploying: {deployed_index.id}")
                endpoint.undeploy_index(deployed_index_id=deployed_index.id)
                print("   ✓ Index undeployed successfully")

        # Step 2: Delete the endpoint
        if endpoint:
            print("\n3. Deleting endpoint...")
            endpoint.delete(force=True)
            print("   ✓ Endpoint deleted successfully")

        # Step 3: Delete the index
        print("\n4. Finding and deleting index...")
        indices = aiplatform.MatchingEngineIndex.list()

        for idx in indices:
            if idx.display_name == "temporal-context-corpus":
                print(f"   Found index: {idx.resource_name}")
                print("   Deleting index...")
                idx.delete()
                print("   ✓ Index deleted successfully")
                break

        print("\n" + "=" * 60)
        print("✓ Cleanup completed successfully!")
        print("\nYou can now create a new corpus with StreamUpdate enabled.")
        print("Use the 'Create Corpus' button in the UI.")

    except Exception as e:
        print(f"\n✗ Error during cleanup: {str(e)}")
        print("\nYou may need to manually delete resources via GCP Console:")
        print("https://console.cloud.google.com/vertex-ai/matching-engine/indexes")
        sys.exit(1)

if __name__ == "__main__":
    response = input("This will delete the existing index and endpoint. Continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        cleanup_resources()
    else:
        print("Cleanup cancelled.")
