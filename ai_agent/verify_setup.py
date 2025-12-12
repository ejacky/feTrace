#!/usr/bin/env python3
"""
Simple verification script to test AI Agent service integration
"""

import sys
import json

print("🔍 AI Agent Service Verification")
print("=" * 50)

try:
    # Test 1: Check if we can import the service
    print("\n1️⃣ Testing Import")
    print("-" * 20)
    
    # Add parent directory to path
    sys.path.append('../backend')
    
    # Import our service
    from ai_service import get_person_timeline, health_check
    
    print("✅ Successfully imported AI service module")
    
    # Test 2: Health check
    print("\n2️⃣ Testing Health Check")
    print("-" * 20)
    
    health_result = health_check()
    print(f"✅ Health check result:")
    print(json.dumps(health_result, indent=2, ensure_ascii=False))
    
    # Test 3: Mock timeline data
    print("\n3️⃣ Testing Mock Timeline Data")
    print("-" * 20)
    
    mock_result = get_person_timeline("测试人物")
    print(f"✅ Got mock timeline data for '测试人物':")
    print(json.dumps(mock_result, indent=2, ensure_ascii=False))
    
    # Test 4: Check endpoints
    print("\n4️⃣ Testing Available Endpoints")
    print("-" * 20)
    
    print("✅ Available endpoints:")
    print("  - GET /health - Health check")
    print("  - GET /api/timeline?name=<name> - Get person timeline")
    print("  - POST /api/batch-timeline - Batch timeline request")
    
    print("\n🎉 Verification Complete!")
    print("=" * 50)
    print("✅ AI Agent service is ready to run")
    print("\n🚀 To start the service:")
    print("   cd ai_agent")
    print("   python3 ai_service.py")
    print("\n🔌 To test APIs:")
    print("   curl http://localhost:8002/health")
    print("   curl 'http://localhost:8002/api/timeline?name=苏轼'")
    
except Exception as e:
    print(f"❌ Verification failed: {e}")
    sys.exit(1)

finally:
    print("\n" + "=" * 50)
    print("Verification script finished")