#!/usr/bin/env python3
"""
Test script to verify the Yield Optimizer API is working
"""

import requests
import json
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8000"
WALLET_ADDRESS = "0x742C5c2eDF43e426C4bb9caCBb8D99b8C1f29b7d"  # Example wallet address

def test_health_endpoint():
    """Test the health endpoint (no auth required)"""
    print("🔍 Testing Health Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health Check: PASSED")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Health Check: FAILED (Status: {response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Health Check: FAILED - Cannot connect to server")
        return False
    except Exception as e:
        print(f"❌ Health Check: FAILED - {e}")
        return False

def test_status_endpoint():
    """Test the status endpoint (requires wallet header)"""
    print("\n🔍 Testing Status Endpoint...")
    try:
        headers = {"x-wallet-address": WALLET_ADDRESS}
        response = requests.get(f"{BASE_URL}/api/yield/status", headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Status Check: PASSED")
            data = response.json()
            print(f"   Pools tracked: {data.get('pools_tracked', 'N/A')}")
            print(f"   Chains tracked: {data.get('chains_tracked', [])}")
            print(f"   Average APY: {data.get('avg_apy', 0):.2f}%")
            return True
        else:
            print(f"❌ Status Check: FAILED (Status: {response.status_code})")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Status Check: FAILED - {e}")
        return False

def test_top_yields_endpoint():
    """Test the top yields endpoint"""
    print("\n🔍 Testing Top Yields Endpoint...")
    try:
        headers = {"x-wallet-address": WALLET_ADDRESS}
        params = {"limit": 5}
        response = requests.get(f"{BASE_URL}/api/yield/top", headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            print("✅ Top Yields: PASSED")
            data = response.json()
            print(f"   Found {len(data)} yield opportunities")
            if data:
                print(f"   Top yield: {data[0].get('protocol', 'Unknown')} - {data[0].get('apy', 0):.2f}% APY")
            return True
        else:
            print(f"❌ Top Yields: FAILED (Status: {response.status_code})")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Top Yields: FAILED - {e}")
        return False

def test_optimize_endpoint():
    """Test the optimize endpoint"""
    print("\n🔍 Testing Optimize Endpoint...")
    try:
        headers = {"x-wallet-address": WALLET_ADDRESS, "Content-Type": "application/json"}
        payload = {
            "allocation_usd": 1000.0,
            "risk_tolerance": "medium",
            "preferred_chains": ["ethereum"],
            "min_apy": 5.0
        }
        response = requests.post(f"{BASE_URL}/api/yield/optimize", 
                               headers=headers, 
                               json=payload, 
                               timeout=20)
        if response.status_code == 200:
            print("✅ Optimization: PASSED")
            data = response.json()
            print(f"   Total allocation: ${data.get('total_allocation_usd', 0):.2f}")
            print(f"   Expected APY: {data.get('expected_apy', 0):.2f}%")
            return True
        else:
            print(f"❌ Optimization: FAILED (Status: {response.status_code})")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Optimization: FAILED - {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 YIELD OPTIMIZER API TESTING")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 4
    
    # Run tests
    if test_health_endpoint():
        tests_passed += 1
    
    if test_status_endpoint():
        tests_passed += 1
        
    if test_top_yields_endpoint():
        tests_passed += 1
        
    if test_optimize_endpoint():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 TEST SUMMARY: {tests_passed}/{total_tests} tests passed")
    print("=" * 60)
    
    if tests_passed == total_tests:
        print("🎉 ALL TESTS PASSED! The Yield Optimizer is working perfectly!")
    elif tests_passed > 0:
        print("⚠️  PARTIAL SUCCESS - Some endpoints are working")
    else:
        print("❌ ALL TESTS FAILED - Check if the server is running")
    
    print("\n🌐 Access the API documentation at: http://localhost:8000/docs")
    print("🔧 Server should be running on: http://localhost:8000")

if __name__ == "__main__":
    main()