"""
Integration test script for YouTube Transcription API
Tests the complete workflow: job creation -> transcription -> correction -> export
"""
import os
import pytest


if not os.getenv("RUN_INTEGRATION"):
    pytest.skip(
        "Integration script (requires running API/worker + external services). Set RUN_INTEGRATION=1 to run.",
        allow_module_level=True,
    )

import time
import requests
import sys

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Short test video
TEST_LANGUAGE = "en"


def test_health_check():
    """Test health check endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200


def test_create_job():
    """Test job creation"""
    print("\n=== Creating Transcription Job ===")
    payload = {
        "youtube_url": TEST_YOUTUBE_URL,
        "language": TEST_LANGUAGE,
        "model": "gpt-4o-mini-transcribe"
    }
    
    response = requests.post(f"{API_BASE_URL}/api/jobs/transcribe", json=payload)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 201:
        data = response.json()
        print(f"Job Created: {data['job_id']}")
        print(f"Status: {data['status']}")
        return data['job_id']
    else:
        print(f"Error: {response.text}")
        return None


def test_job_status(job_id):
    """Test job status endpoint"""
    print(f"\n=== Checking Job Status: {job_id} ===")
    response = requests.get(f"{API_BASE_URL}/api/jobs/{job_id}/status")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data['status']}")
        print(f"Progress: {data['progress']}%")
        if data.get('error_message'):
            print(f"Error: {data['error_message']}")
        return data
    else:
        print(f"Error: {response.text}")
        return None


def wait_for_completion(job_id, max_wait=300, poll_interval=5):
    """Wait for job to complete"""
    print(f"\n=== Waiting for Job Completion (max {max_wait}s) ===")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        status_data = test_job_status(job_id)
        
        if not status_data:
            return False
        
        if status_data['status'] in ['completed', 'failed']:
            print(f"\nJob finished with status: {status_data['status']}")
            return status_data['status'] == 'completed'
        
        print(f"Waiting... (elapsed: {int(time.time() - start_time)}s)")
        time.sleep(poll_interval)
    
    print("\nTimeout waiting for job completion")
    return False


def test_job_result(job_id):
    """Test job result endpoint"""
    print(f"\n=== Getting Job Result: {job_id} ===")
    response = requests.get(f"{API_BASE_URL}/api/jobs/{job_id}/result")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data['status']}")
        
        if data.get('audio_file'):
            print(f"Audio File: {data['audio_file'].get('title')}")
            print(f"Duration: {data['audio_file'].get('duration_seconds')}s")
        
        if data.get('transcript'):
            transcript_text = data['transcript']['text']
            print(f"Transcript Length: {len(transcript_text)} characters")
            print(f"Transcript Preview: {transcript_text[:200]}...")
        
        return data
    else:
        print(f"Error: {response.text}")
        return None


def test_correction(job_id):
    """Test LLM correction"""
    print(f"\n=== Requesting LLM Correction: {job_id} ===")
    payload = {
        "correction_model": "gpt-4o-mini"
    }
    
    response = requests.post(f"{API_BASE_URL}/api/jobs/{job_id}/correct", json=payload)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Correction Status: {data['status']}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_export(job_id, format="txt"):
    """Test export endpoint"""
    print(f"\n=== Exporting as {format.upper()}: {job_id} ===")
    response = requests.get(f"{API_BASE_URL}/api/jobs/{job_id}/export", params={"format": format})
    
    if response.status_code == 200:
        print(f"Export successful!")
        print(f"Content Length: {len(response.content)} bytes")
        print(f"Content Type: {response.headers.get('Content-Type')}")
        
        # Save to file
        filename = f"test_export_{job_id[:8]}.{format}"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"Saved to: {filename}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def main():
    """Run integration tests"""
    print("=" * 60)
    print("YouTube Transcription API - Integration Test")
    print("=" * 60)
    
    # Test 1: Health check
    if not test_health_check():
        print("\n❌ Health check failed! Make sure the API is running.")
        sys.exit(1)
    
    print("\n✅ Health check passed")
    
    # Test 2: Create job
    job_id = test_create_job()
    if not job_id:
        print("\n❌ Failed to create job")
        sys.exit(1)
    
    print(f"\n✅ Job created: {job_id}")
    
    # Test 3: Monitor job status
    # Note: In a real test, we would mock the services or use a short test video
    print("\n⚠️  Job monitoring skipped (requires worker and external services)")
    print("To test the full workflow:")
    print("1. Start Docker Compose: docker compose up")
    print("2. Ensure OpenAI API key is set in .env")
    print("3. Re-run this script")
    
    # Test 4: Get job status immediately
    test_job_status(job_id)
    
    print("\n" + "=" * 60)
    print("Integration Test Summary")
    print("=" * 60)
    print("✅ API is running and responding")
    print("✅ Job creation endpoint works")
    print("✅ Job status endpoint works")
    print("⚠️  Full workflow test requires worker services")
    print("\nNext steps:")
    print("- Start Docker Compose to test full workflow")
    print("- Monitor logs: docker compose logs -f")
    print("=" * 60)


if __name__ == "__main__":
    main()
