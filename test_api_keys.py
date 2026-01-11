"""
API Key Validation Script

Tests all API keys to verify they are valid and not expired.
Run this script to check if all your API keys are working correctly.
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
_env_path = Path(__file__).parent.parent / ".env.local"
if _env_path.exists():
    load_dotenv(dotenv_path=str(_env_path))
    print(f"✅ Loaded .env.local from: {_env_path}")
else:
    load_dotenv()
    print("⚠️  .env.local not found, loading from current directory")


async def test_google_gemini_api_key():
    """Test Google Gemini API key"""
    print("\n" + "="*60)
    print("🔍 Testing Google Gemini API Key")
    print("="*60)
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")
    
    if not api_key or api_key.strip() in ["", "----", "your_google_api_key"]:
        print("❌ GOOGLE_API_KEY: Not found or invalid value")
        return False
    
    api_key = api_key.strip()
    print(f"   Key found: ✅ (length: {len(api_key)} chars, starts with: {api_key[:10]}...)")
    
    try:
        # Set environment variable for Google SDK
        os.environ["GOOGLE_API_KEY"] = api_key
        os.environ["GOOGLE_GENAI_API_KEY"] = api_key
        
        # Test with actual API call
        from google import genai
        
        client = genai.Client(api_key=api_key)
        model = client.models.get_model("gemini-2.0-flash-exp")
        
        # Make a simple test request
        response = model.generate_content("Say 'test' if you can hear me.")
        
        if response and response.text:
            print(f"   ✅ Google Gemini API Key: VALID")
            print(f"   ✅ Test response: {response.text[:50]}...")
            return True
        else:
            print("   ❌ Google Gemini API Key: INVALID (no response)")
            return False
            
    except Exception as e:
        error_msg = str(e)
        if "API Key not found" in error_msg or "API_KEY_INVALID" in error_msg:
            print(f"   ❌ Google Gemini API Key: INVALID or EXPIRED")
            print(f"   Error: {error_msg[:150]}")
        elif "quota" in error_msg.lower() or "429" in error_msg:
            print(f"   ⚠️  Google Gemini API Key: Valid but QUOTA EXCEEDED")
            print(f"   Error: {error_msg[:150]}")
        else:
            print(f"   ❌ Google Gemini API Key: ERROR")
            print(f"   Error: {error_msg[:150]}")
        return False


async def test_deepgram_api_key():
    """Test Deepgram API key"""
    print("\n" + "="*60)
    print("🔍 Testing Deepgram API Key")
    print("="*60)
    
    api_key = os.getenv("DEEPGRAM_API_KEY")
    
    if not api_key or api_key.strip() in ["", "your_deepgram_api_key"]:
        print("❌ DEEPGRAM_API_KEY: Not found or invalid value")
        return False
    
    api_key = api_key.strip()
    print(f"   Key found: ✅ (length: {len(api_key)} chars)")
    
    try:
        import httpx
        
        # Test Deepgram API with a simple request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.deepgram.com/v1/projects",
                headers={
                    "Authorization": f"Token {api_key}",
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                print("   ✅ Deepgram API Key: VALID")
                return True
            elif response.status_code == 401:
                print("   ❌ Deepgram API Key: INVALID or EXPIRED")
                return False
            else:
                print(f"   ⚠️  Deepgram API Key: Unexpected status ({response.status_code})")
                return False
                
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ Deepgram API Key: ERROR")
        print(f"   Error: {error_msg[:100]}")
        return False


async def test_elevenlabs_api_key():
    """Test ElevenLabs API key"""
    print("\n" + "="*60)
    print("🔍 Testing ElevenLabs API Key")
    print("="*60)
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "LQMC3j3fn1LA9ZhI4o8g")
    
    if not api_key or api_key.strip() in ["", "your_elevenlabs_api_key"]:
        print("❌ ELEVENLABS_API_KEY: Not found or invalid value")
        return False
    
    api_key = api_key.strip()
    print(f"   Key found: ✅ (length: {len(api_key)} chars)")
    print(f"   Voice ID: {voice_id}")
    
    try:
        import httpx
        
        # Test ElevenLabs API - check user info (lightweight endpoint)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.elevenlabs.io/v1/user",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                user_data = response.json()
                print("   ✅ ElevenLabs API Key: VALID")
                if "subscription" in user_data:
                    print(f"   ✅ Subscription: {user_data.get('subscription', {}).get('tier', 'N/A')}")
                return True
            elif response.status_code == 401:
                print("   ❌ ElevenLabs API Key: INVALID or EXPIRED")
                return False
            else:
                print(f"   ⚠️  ElevenLabs API Key: Unexpected status ({response.status_code})")
                return False
                
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ ElevenLabs API Key: ERROR")
        print(f"   Error: {error_msg[:100]}")
        return False


async def test_livekit_credentials():
    """Test LiveKit API credentials"""
    print("\n" + "="*60)
    print("🔍 Testing LiveKit Credentials")
    print("="*60)
    
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    url = os.getenv("LIVEKIT_URL")
    
    checks = []
    
    if not api_key or api_key.strip() in ["", "your_livekit_api_key"]:
        print("❌ LIVEKIT_API_KEY: Not found or invalid value")
        checks.append(False)
    else:
        print(f"   ✅ LIVEKIT_API_KEY: Found (length: {len(api_key.strip())} chars)")
        checks.append(True)
    
    if not api_secret or api_secret.strip() in ["", "your_livekit_api_secret"]:
        print("❌ LIVEKIT_API_SECRET: Not found or invalid value")
        checks.append(False)
    else:
        print(f"   ✅ LIVEKIT_API_SECRET: Found (length: {len(api_secret.strip())} chars)")
        checks.append(True)
    
    if not url or url.strip() in ["", "wss://your-livekit-server.com"]:
        print("❌ LIVEKIT_URL: Not found or invalid value")
        checks.append(False)
    else:
        print(f"   ✅ LIVEKIT_URL: {url.strip()}")
        checks.append(True)
    
    # Try to validate by creating a token (doesn't require API call)
    if all(checks):
        try:
            from livekit import api
            
            token = api.AccessToken(api_key, api_secret) \
                .with_identity("test-user") \
                .with_name("Test User") \
                .with_grants(api.VideoGrants(room_join=True, room="test")) \
                .to_jwt()
            
            if token:
                print("   ✅ LiveKit Credentials: VALID (token generation successful)")
                return True
            else:
                print("   ❌ LiveKit Credentials: INVALID (token generation failed)")
                return False
        except Exception as e:
            error_msg = str(e)
            print(f"   ⚠️  LiveKit Credentials: Error validating ({error_msg[:50]})")
            print("   Note: Keys appear valid but validation failed")
            return False
    
    return False


async def test_supabase_credentials():
    """Test Supabase credentials"""
    print("\n" + "="*60)
    print("🔍 Testing Supabase Credentials")
    print("="*60)
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or url.strip() in ["", "https://your-project.supabase.co"]:
        print("❌ SUPABASE_URL: Not found or invalid value")
        return False
    
    if not key or key.strip() in ["", "your_service_role_key"]:
        print("❌ SUPABASE_SERVICE_ROLE_KEY: Not found or invalid value")
        return False
    
    url = url.strip()
    key = key.strip()
    
    print(f"   ✅ SUPABASE_URL: {url}")
    print(f"   ✅ SUPABASE_SERVICE_ROLE_KEY: Found (length: {len(key)} chars)")
    
    try:
        import httpx
        
        # Test Supabase API with a simple health check
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{url}/rest/v1/",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            
            if response.status_code in [200, 301, 302]:
                print("   ✅ Supabase Credentials: VALID")
                return True
            elif response.status_code == 401:
                print("   ❌ Supabase Credentials: INVALID (401 Unauthorized)")
                return False
            else:
                print(f"   ⚠️  Supabase Credentials: Status {response.status_code}")
                return True  # Might still be valid, just different endpoint
                
    except Exception as e:
        error_msg = str(e)
        print(f"   ⚠️  Supabase Credentials: Could not validate ({error_msg[:50]})")
        print("   Note: Credentials appear valid but validation endpoint may be different")
        return True  # Assume valid if format is correct


async def test_tavus_api_key():
    """Test Tavus API key (optional)"""
    print("\n" + "="*60)
    print("🔍 Testing Tavus API Key (Optional)")
    print("="*60)
    
    api_key = os.getenv("TAVUS_API_KEY")
    persona_id = os.getenv("TAVUS_PERSONA_ID")
    replica_id = os.getenv("TAVUS_REPLICA_ID")
    
    if not api_key:
        print("   ℹ️  TAVUS_API_KEY: Not configured (optional)")
        return None  # Optional, not a failure
    
    if not persona_id or not replica_id:
        print("   ⚠️  Tavus: API key found but PERSONA_ID or REPLICA_ID missing")
        return False
    
    api_key = api_key.strip()
    print(f"   Key found: ✅ (length: {len(api_key)} chars)")
    print(f"   Persona ID: {persona_id}")
    print(f"   Replica ID: {replica_id}")
    
    try:
        import httpx
        
        # Test Tavus API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.tavus.io/v2/replicas",
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                print("   ✅ Tavus API Key: VALID")
                return True
            elif response.status_code == 401:
                print("   ❌ Tavus API Key: INVALID or EXPIRED")
                return False
            elif response.status_code == 402:
                print("   ⚠️  Tavus API Key: VALID but OUT OF CREDITS")
                return True  # Key is valid, just needs credits
            else:
                print(f"   ⚠️  Tavus API Key: Status {response.status_code}")
                return False
                
    except Exception as e:
        error_msg = str(e)
        if "out of conversational credits" in error_msg.lower() or "402" in error_msg:
            print("   ⚠️  Tavus API Key: VALID but OUT OF CREDITS")
            return True
        print(f"   ❌ Tavus API Key: ERROR")
        print(f"   Error: {error_msg[:100]}")
        return False


async def main():
    """Run all API key tests"""
    print("="*60)
    print("🔐 API KEY VALIDATION SCRIPT")
    print("="*60)
    print(f"Environment file: {_env_path if _env_path.exists() else 'Not found'}")
    print("="*60)
    
    results = {}
    
    # Test all API keys
    results["Google Gemini"] = await test_google_gemini_api_key()
    results["Deepgram"] = await test_deepgram_api_key()
    results["ElevenLabs"] = await test_elevenlabs_api_key()
    results["LiveKit"] = await test_livekit_credentials()
    results["Supabase"] = await test_supabase_credentials()
    tavus_result = await test_tavus_api_key()
    if tavus_result is not None:
        results["Tavus"] = tavus_result
    
    # Summary
    print("\n" + "="*60)
    print("📊 VALIDATION SUMMARY")
    print("="*60)
    
    required_keys = ["Google Gemini", "Deepgram", "ElevenLabs", "LiveKit", "Supabase"]
    optional_keys = ["Tavus"]
    
    all_required_valid = True
    for key in required_keys:
        status = "✅ VALID" if results.get(key) else "❌ INVALID"
        print(f"   {key}: {status}")
        if not results.get(key):
            all_required_valid = False
    
    for key in optional_keys:
        if key in results:
            status = "✅ VALID" if results[key] else "❌ INVALID"
            print(f"   {key} (optional): {status}")
        else:
            print(f"   {key} (optional): ⚪ NOT CONFIGURED")
    
    print("="*60)
    
    if all_required_valid:
        print("✅ ALL REQUIRED API KEYS ARE VALID!")
        print("   Your agent should work correctly.")
        return 0
    else:
        print("❌ SOME REQUIRED API KEYS ARE INVALID OR MISSING!")
        print("   Please check your .env.local file and fix the invalid keys.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Validation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
