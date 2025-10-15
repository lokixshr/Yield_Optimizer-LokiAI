#!/usr/bin/env python3
"""
Simple script to start the server and provide testing instructions
"""

import subprocess
import sys
import time
import threading
import requests

def start_server():
    """Start the FastAPI server"""
    print("🚀 Starting Yield Optimizer server...")
    from app.main import app
    import uvicorn
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

def test_basic_functionality():
    """Test basic functionality after a delay"""
    time.sleep(3)  # Wait for server to start
    
    print("\n" + "="*60)
    print("🔍 BASIC FUNCTIONALITY TEST")
    print("="*60)
    
    # Test health endpoint
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and responding!")
            print(f"✅ Health check response: {response.json()}")
        else:
            print(f"⚠️ Server responded with status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server - make sure it's running")
    except Exception as e:
        print(f"❌ Test error: {e}")
    
    print("\n" + "="*60)
    print("📖 NEXT STEPS TO TEST YOUR API:")
    print("="*60)
    print("1. Open your browser and go to: http://localhost:8000/docs")
    print("2. You'll see the interactive API documentation")
    print("3. Use this curl command to test the health endpoint:")
    print("   curl http://localhost:8000/health")
    print("\n4. To test authenticated endpoints, use:")
    print("   curl -H \"x-wallet-address: 0x742C5c2eDF43e426C4bb9caCBb8D99b8C1f29b7d\" \\")
    print("        http://localhost:8000/api/yield/status")
    print("\n5. Press Ctrl+C to stop the server when done")
    print("="*60)

if __name__ == "__main__":
    # Start testing in a separate thread
    test_thread = threading.Thread(target=test_basic_functionality)
    test_thread.daemon = True
    test_thread.start()
    
    # Start the server (this will block)
    start_server()