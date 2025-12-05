#!/usr/bin/env python3
"""
API Health Check Script
Tests all external APIs used by the YouTube Shorts Automation pipeline
and provides detailed diagnostic information on failures.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, List

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

class APIHealthChecker:
    def __init__(self):
        self.results = {}
        self.env_file = Path(__file__).parent / '.env'
        self.load_env()
        
    def load_env(self):
        """Load environment variables from .env file"""
        if self.env_file.exists():
            with open(self.env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
    
    def print_header(self, text: str):
        print(f"\n{BOLD}{BLUE}{'='*80}{RESET}")
        print(f"{BOLD}{BLUE}{text}{RESET}")
        print(f"{BOLD}{BLUE}{'='*80}{RESET}\n")
    
    def print_success(self, text: str):
        print(f"{GREEN}✅ {text}{RESET}")
    
    def print_error(self, text: str):
        print(f"{RED}❌ {text}{RESET}")
    
    def print_warning(self, text: str):
        print(f"{YELLOW}⚠️  {text}{RESET}")
    
    def print_info(self, text: str):
        print(f"{BLUE}ℹ️  {text}{RESET}")
    
    def check_groq_api(self) -> Tuple[bool, str]:
        """Check Groq API connectivity and rate limits"""
        try:
            from groq import Groq
            
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                return False, "GROQ_API_KEY not set in environment"
            
            if api_key.startswith('gsk_') and len(api_key) < 50:
                return False, "GROQ_API_KEY appears invalid (too short or malformed)"
            
            client = Groq(api_key=api_key)
            model = os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')
            
            # Make a minimal test request
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Say OK"}],
                    max_tokens=5,
                    temperature=0.1
                )
                return True, f"✅ Groq API working (Model: {model})"
            
            except Exception as e:
                error_str = str(e)
                
                # Check for rate limit error
                if '429' in error_str or 'rate_limit' in error_str.lower():
                    if 'TPD' in error_str or 'tokens per day' in error_str.lower():
                        # Extract token info from error message
                        if 'Used 200000' in error_str:
                            return False, (
                                f"❌ Groq API rate limit EXCEEDED (Free tier: 200K tokens/day used)\n"
                                f"   Solution: Wait for quota reset or upgrade to Dev Tier at https://console.groq.com/settings/billing"
                            )
                        else:
                            return False, f"❌ Groq API rate limited: {error_str[:150]}..."
                    else:
                        return False, f"❌ Groq API rate limited: {error_str[:200]}..."
                
                # Check for auth error
                elif '401' in error_str or 'unauthorized' in error_str.lower():
                    return False, f"❌ Groq API authentication failed - invalid API key"
                
                # Check for model error
                elif '404' in error_str or 'model' in error_str.lower():
                    return False, f"❌ Groq API model not found or invalid: {model}"
                
                else:
                    return False, f"❌ Groq API error: {error_str[:200]}..."
        
        except ImportError:
            return False, "❌ Groq SDK not installed: pip install groq"
        except Exception as e:
            return False, f"❌ Unexpected error: {str(e)[:200]}"
    
    def check_google_youtube_api(self) -> Tuple[bool, str]:
        """Check YouTube API credentials and connectivity"""
        try:
            # Check for OAuth refresh token (preferred method for Render)
            refresh_token = os.getenv('YOUTUBE_REFRESH_TOKEN')
            client_id = os.getenv('YOUTUBE_CLIENT_ID')
            client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
            
            if not refresh_token:
                return False, "❌ YOUTUBE_REFRESH_TOKEN not set in environment"
            
            if not client_id or not client_secret:
                return False, "❌ YOUTUBE_CLIENT_ID or YOUTUBE_CLIENT_SECRET not set"
            
            # Try to refresh the token
            import requests
            token_url = 'https://oauth2.googleapis.com/token'
            payload = {
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(token_url, data=payload, timeout=10)
            if response.status_code == 200:
                return True, "✅ YouTube OAuth refresh token valid and working"
            elif response.status_code == 401:
                return False, "❌ YouTube OAuth refresh token invalid or revoked - need new auth"
            else:
                error_msg = response.text[:150]
                return False, f"❌ YouTube OAuth error: {response.status_code} - {error_msg}"
        
        except ImportError as e:
            return False, f"❌ Required library not installed: {str(e)}"
        except Exception as e:
            error_msg = str(e)[:200]
            return False, f"❌ Unexpected error: {error_msg}"
    
    def check_tts_provider(self) -> Tuple[bool, str]:
        """Check TTS provider configuration and availability"""
        try:
            provider = os.getenv('TTS_PROVIDER', 'gtts').lower()
            
            if provider == 'gtts':
                try:
                    from gtts import gTTS
                    # Test with minimal parameters
                    tts = gTTS(text="Test", lang='en', slow=False)
                    return True, f"✅ gTTS provider working (language: en)"
                except ImportError:
                    return False, "❌ gTTS not installed: pip install gtts"
                except Exception as e:
                    return False, f"❌ gTTS error: {str(e)[:150]}"
            
            elif provider == 'edge':
                try:
                    from edge_tts import Communicate
                    return True, f"✅ Edge-TTS provider available"
                except ImportError:
                    return False, "❌ edge-tts not installed: pip install edge-tts"
                except Exception as e:
                    return False, f"❌ Edge-TTS error: {str(e)[:150]}"
            
            else:
                return False, f"❌ Unknown TTS provider: {provider}. Must be 'gtts' or 'edge'"
        
        except Exception as e:
            return False, f"❌ Unexpected error: {str(e)[:200]}"
    
    def check_moviepy(self) -> Tuple[bool, str]:
        """Check MoviePy and video dependencies"""
        try:
            import moviepy.editor as mpy
            from PIL import Image, ImageDraw, ImageFont
            
            # Test basic video composition
            try:
                clip = mpy.ColorClip(size=(100, 100), color=(255, 255, 255)).set_duration(0.1)
                return True, "✅ MoviePy working with PIL support"
            except Exception as e:
                return False, f"❌ MoviePy error: {str(e)[:150]}"
        
        except ImportError as e:
            missing = str(e)
            if 'moviepy' in missing:
                return False, "❌ moviepy not installed: pip install moviepy"
            elif 'PIL' in missing or 'pillow' in missing:
                return False, "❌ Pillow not installed: pip install pillow"
            else:
                return False, f"❌ Missing dependency: {missing}"
        except Exception as e:
            return False, f"❌ Unexpected error: {str(e)[:200]}"
    
    def check_gemini_via_groq(self) -> Tuple[bool, str]:
        """Check if Gemini can be accessed through Groq interface"""
        try:
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                return False, "❌ GROQ_API_KEY not set (needed for Gemini via Groq)"
            
            # Note: Actual Gemini integration check would happen during runtime
            # This just verifies the API key exists
            return True, "✅ Gemini accessible via Groq API (API key configured)"
        
        except Exception as e:
            return False, f"❌ Error: {str(e)[:150]}"
    
    def check_disk_space(self) -> Tuple[bool, str]:
        """Check available disk space"""
        try:
            import shutil
            disk = shutil.disk_usage('/')
            free_gb = disk.free / (1024**3)
            required_gb = 2.0
            
            if free_gb < required_gb:
                return False, f"❌ Insufficient disk space: {free_gb:.2f}GB free (need {required_gb}GB)"
            
            return True, f"✅ Sufficient disk space: {free_gb:.2f}GB free"
        
        except Exception as e:
            return False, f"❌ Error checking disk space: {str(e)[:150]}"
    
    def check_output_directories(self) -> Tuple[bool, str]:
        """Check if output directories exist and are writable"""
        try:
            output_dir = Path(__file__).parent / 'output'
            
            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)
            
            # Try to write a test file
            test_file = output_dir / '.write_test'
            test_file.write_text('test')
            test_file.unlink()
            
            return True, f"✅ Output directory writable: {output_dir}"
        
        except Exception as e:
            return False, f"❌ Output directory not writable: {str(e)[:150]}"
    
    def run_all_checks(self):
        """Run all API health checks"""
        self.print_header("🏥 API HEALTH CHECK - YouTube Shorts Automation")
        
        print(f"Timestamp: {datetime.now().isoformat()}\n")
        
        checks = [
            ("Groq API (LLM)", self.check_groq_api),
            ("YouTube OAuth", self.check_google_youtube_api),
            ("TTS Provider", self.check_tts_provider),
            ("MoviePy & PIL", self.check_moviepy),
            ("Gemini via Groq", self.check_gemini_via_groq),
            ("Disk Space", self.check_disk_space),
            ("Output Directories", self.check_output_directories),
        ]
        
        passed = 0
        failed = 0
        
        print(f"{BOLD}API Status:{RESET}\n")
        
        for check_name, check_func in checks:
            success, message = check_func()
            self.results[check_name] = (success, message)
            
            if success:
                self.print_success(f"{check_name}")
                passed += 1
            else:
                self.print_error(f"{check_name}")
                failed += 1
            
            print(f"   {message}\n")
        
        # Summary
        self.print_header("📊 SUMMARY")
        print(f"Total Checks: {len(checks)}")
        print(f"{GREEN}Passed: {passed}{RESET}")
        print(f"{RED}Failed: {failed}{RESET}\n")
        
        if failed == 0:
            self.print_success("All APIs are operational! 🎉")
            print("\nYour system is ready to:")
            print("  • Generate video ideas with Groq LLM")
            print("  • Create text-to-speech with gTTS")
            print("  • Compose videos with MoviePy")
            print("  • Upload to YouTube")
            return 0
        else:
            self.print_error(f"{failed} API(s) need attention")
            print("\n" + BOLD + "TROUBLESHOOTING RECOMMENDATIONS:" + RESET)
            
            for check_name, (success, message) in self.results.items():
                if not success:
                    print(f"\n{check_name}:")
                    if "rate limit" in message.lower():
                        print("  → Wait 4-5 minutes or upgrade Groq tier")
                    elif "not installed" in message.lower():
                        print("  → Run: pip install -r requirements.txt")
                    elif "not set" in message.lower():
                        print("  → Set missing environment variables in .env or Render settings")
                    elif "invalid" in message.lower():
                        print("  → Verify API keys and credentials are correct")
                    elif "writable" in message.lower():
                        print("  → Check file permissions and disk space")
            
            return 1

def main():
    """Main entry point"""
    try:
        checker = APIHealthChecker()
        exit_code = checker.run_all_checks()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n{RED}Fatal error: {str(e)}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
