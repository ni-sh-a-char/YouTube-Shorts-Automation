# FILE: scripts/config.py
# Configuration management for YouTube Shorts automation
# Loads settings from .env and config.yaml with proper precedence

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import json

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    import yaml
except ImportError:
    yaml = None


class Config:
    """Centralized configuration management."""
    
    def __init__(self, config_file: Optional[Path] = None, env_file: Optional[Path] = None):
        """
        Initialize configuration from .env and config.yaml.
        
        Args:
            config_file: Path to config.yaml (default: ./config.yaml)
            env_file: Path to .env file (default: ./.env)
        """
        self.config_file = config_file or Path("config.yaml")
        self.env_file = env_file or Path(".env")
        self.root_dir = Path.cwd()
        
        # Load environment variables from .env
        if self.env_file.exists():
            if load_dotenv is not None:
                load_dotenv(self.env_file)
            else:
                self._load_dotenv_manual(self.env_file)
        
        # Load config from YAML
        self._config = self._load_yaml_config()
        
        # Validate required keys
        self._validate_required()
    
    def _load_dotenv_manual(self, env_file: Path):
        """Manual .env loading if python-dotenv is not available."""
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_file.exists():
            return {}
        
        if yaml is None:
            # If PyYAML is not available, return empty dict
            return {}
        
        try:
            with open(self.config_file) as f:
                config = yaml.safe_load(f) or {}
            return config
        except Exception as e:
            print(f"⚠️ Failed to load {self.config_file}: {e}")
            return {}
    
    def _validate_required(self):
        """Validate that all required API keys are present."""
        required_keys = ['GEMINI_API_KEY', 'YOUTUBE_CLIENT_ID', 'YOUTUBE_CLIENT_SECRET']
        missing = [k for k in required_keys if not os.getenv(k)]
        
        if missing:
            print(f"⚠️ WARNING: Missing required environment variables: {', '.join(missing)}")
            print(f"   Please set these in .env file")
    
    # ========================================================================
    # API CONFIGURATION
    # ========================================================================
    
    @property
    def gemini_api_key(self) -> str:
        """Google Gemini API key."""
        return os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY') or ''
    
    @property
    def gemini_model(self) -> str:
        """Gemini model to use."""
        return os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')

    @property
    def llm_provider(self) -> str:
        """LLM provider to use: 'gemini' or 'groq'."""
        return os.getenv('LLM_PROVIDER', 'gemini').lower()

    @property
    def groq_api_key(self) -> Optional[str]:
        """Groq API key (if using Groq)."""
        return os.getenv('GROQ_API_KEY')

    @property
    def groq_model(self) -> str:
        """Groq model name to use. Default set to gpt-oss-120b."""
        # Use the canonical provider/model namespace as used by Groq examples
        return os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')

    @property
    def groq_api_url(self) -> Optional[str]:
        """Optional custom Groq API URL (inference endpoint). If not set, the code will try to use an SDK."""
        return os.getenv('GROQ_API_URL')
    
    @property
    def gemini_temperature(self) -> float:
        """Gemini temperature (creativity level)."""
        yaml_val = self._get_nested(self._config, 'api.gemini.temperature')
        return float(yaml_val or os.getenv('GEMINI_TEMPERATURE', 0.7))
    
    @property
    def youtube_client_id(self) -> str:
        """YouTube OAuth2 client ID."""
        return os.getenv('YOUTUBE_CLIENT_ID', '')
    
    @property
    def youtube_client_secret(self) -> str:
        """YouTube OAuth2 client secret."""
        return os.getenv('YOUTUBE_CLIENT_SECRET', '')
    
    @property
    def youtube_refresh_token(self) -> Optional[str]:
        """YouTube refresh token (optional, auto-generated)."""
        return os.getenv('YOUTUBE_REFRESH_TOKEN')
    
    @property
    def youtube_category_id(self) -> str:
        """YouTube video category ID."""
        return os.getenv('YOUTUBE_CATEGORY_ID', '28')  # 28 = Science & Technology
    
    @property
    def youtube_privacy_status(self) -> str:
        """YouTube video privacy status."""
        return os.getenv('YOUTUBE_PRIVACY_STATUS', 'public')
    
    # ========================================================================
    # TTS CONFIGURATION
    # ========================================================================
    
    @property
    def tts_provider(self) -> str:
        """TTS provider: 'gtts' or 'ttsmaker'."""
        return os.getenv('TTS_PROVIDER', 'gtts')
    
    @property
    def tts_language(self) -> str:
        """TTS language code."""
        return os.getenv('TTS_LANGUAGE', 'en')
    
    @property
    def tts_speed(self) -> str:
        """TTS speed: 'slow', 'normal', 'fast'."""
        return os.getenv('TTS_SPEED', 'normal')
    
    @property
    def ttsmaker_api_key(self) -> Optional[str]:
        """TTSMaker API key (optional)."""
        return os.getenv('TTSMAKER_API_KEY')
    
    # ========================================================================
    # VIDEO CONFIGURATION
    # ========================================================================
    
    @property
    def video_resolution(self) -> tuple:
        """Video resolution as (width, height)."""
        res_str = os.getenv('VIDEO_RESOLUTION', '1080x1920')
        try:
            w, h = map(int, res_str.split('x'))
            return (w, h)
        except:
            return (1080, 1920)  # Default vertical Shorts format
    
    @property
    def video_fps(self) -> int:
        """Video frames per second."""
        yaml_val = self._get_nested(self._config, 'video.fps')
        return int(yaml_val or os.getenv('VIDEO_FPS', 24))
    
    @property
    def video_duration_seconds(self) -> int:
        """Target video duration in seconds (minimum 30 for better engagement)."""
        yaml_val = self._get_nested(self._config, 'video.duration_seconds')
        duration = int(yaml_val or os.getenv('TARGET_VIDEO_DURATION', 30))
        # Enforce minimum 30 seconds
        return max(duration, 30)
    
    # ========================================================================
    # CONTENT CONFIGURATION
    # ========================================================================
    
    @property
    def target_topic(self) -> str:
        """Primary topic for Shorts generation."""
        return os.getenv('TARGET_TOPIC', 'Python')
    
    @property
    def topics_rotation(self) -> List[str]:
        """Topics to cycle through."""
        topics_str = os.getenv('TOPICS_ROTATION', '')
        if topics_str:
            return [t.strip() for t in topics_str.split(',')]
        return [self.target_topic]
    
    @property
    def content_niche(self) -> str:
        """Content niche/category."""
        return os.getenv('CONTENT_NICHE', 'tech/coding')
    
    # ========================================================================
    # AUTOMATION CONFIGURATION
    # ========================================================================
    
    @property
    def batch_size(self) -> int:
        """Number of shorts to generate per run."""
        yaml_val = self._get_nested(self._config, 'automation.batch_size')
        return int(yaml_val or os.getenv('BATCH_SIZE', 1))
    
    @property
    def dry_run(self) -> bool:
        """Enable dry-run mode (no upload to YouTube)."""
        return os.getenv('DRY_RUN', 'false').lower() == 'true'
    
    @property
    def cleanup_temp(self) -> bool:
        """Auto-cleanup temporary files."""
        return os.getenv('CLEANUP_TEMP', 'true').lower() == 'true'
    
    @property
    def verbose(self) -> bool:
        """Enable verbose logging."""
        return os.getenv('VERBOSE', 'false').lower() == 'true'
    
    # ========================================================================
    # PATHS CONFIGURATION
    # ========================================================================
    
    @property
    def output_dir(self) -> Path:
        """Output directory for final files."""
        path = Path(os.getenv('OUTPUT_DIR', './data/output'))
        if not path.is_absolute():
            path = self.root_dir / path
        return path
    
    @property
    def temp_dir(self) -> Path:
        """Temporary directory for intermediate files."""
        path = Path(os.getenv('TEMP_DIR', './data/temp'))
        if not path.is_absolute():
            path = self.root_dir / path
        return path
    
    @property
    def log_dir(self) -> Path:
        """Logging directory."""
        path = Path(os.getenv('LOG_DIR', './logs'))
        if not path.is_absolute():
            path = self.root_dir / path
        return path
    
    @property
    def stock_footage_dir(self) -> Path:
        """Stock footage cache directory."""
        path = Path(os.getenv('STOCK_FOOTAGE_DIR', './data/stock_footage'))
        if not path.is_absolute():
            path = self.root_dir / path
        return path
    
    # Output subdirectories
    @property
    def videos_dir(self) -> Path:
        """Directory for final video files."""
        return self.output_dir / 'videos'
    
    @property
    def thumbnails_dir(self) -> Path:
        """Directory for thumbnail images."""
        return self.output_dir / 'thumbnails'
    
    @property
    def captions_dir(self) -> Path:
        """Directory for caption files."""
        return self.output_dir / 'captions'
    
    @property
    def metadata_dir(self) -> Path:
        """Directory for metadata JSON files."""
        return self.output_dir / 'metadata'
    
    @property
    def audio_dir(self) -> Path:
        """Directory for audio files."""
        return self.temp_dir / 'audio'
    
    # ========================================================================
    # LOGGING CONFIGURATION
    # ========================================================================
    
    @property
    def log_level(self) -> str:
        """Logging level."""
        return os.getenv('LOG_LEVEL', 'INFO').upper()
    
    @property
    def log_to_file(self) -> bool:
        """Enable file logging."""
        return os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
    
    # ========================================================================
    # CAPTIONS CONFIGURATION
    # ========================================================================
    
    @property
    def captions_enabled(self) -> bool:
        """Enable caption generation."""
        return os.getenv('CAPTIONS_ENABLED', 'true').lower() == 'true'
    
    @property
    def captions_format(self) -> str:
        """Caption format: 'srt' or 'vtt'."""
        return os.getenv('CAPTIONS_FORMAT', 'srt')
    
    @property
    def captions_embed_on_video(self) -> bool:
        """Embed captions on video."""
        return os.getenv('CAPTIONS_EMBED_ON_VIDEO', 'true').lower() == 'true'
    
    @property
    def captions_font_size(self) -> int:
        """Caption font size (pixels)."""
        return int(os.getenv('CAPTIONS_FONT_SIZE', 40))
    
    @property
    def captions_font_color(self) -> str:
        """Caption font color (hex)."""
        return os.getenv('CAPTIONS_FONT_COLOR', '#FFFFFF')
    
    # ========================================================================
    # STOCK FOOTAGE CONFIGURATION
    # ========================================================================
    
    @property
    def pexels_api_key(self) -> Optional[str]:
        """Pexels API key (optional)."""
        return os.getenv('PEXELS_API_KEY')
    
    @property
    def pixabay_api_key(self) -> Optional[str]:
        """Pixabay API key (optional)."""
        return os.getenv('PIXABAY_API_KEY')
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _get_nested(self, d: Dict, keys: str, default=None):
        """Get nested dictionary value using dot notation."""
        keys_list = keys.split('.')
        for key in keys_list:
            if isinstance(d, dict):
                d = d.get(key)
            else:
                return default
        return d
    
    def ensure_directories(self):
        """Create all required directories."""
        dirs = [
            self.output_dir,
            self.temp_dir,
            self.log_dir,
            self.videos_dir,
            self.thumbnails_dir,
            self.captions_dir,
            self.metadata_dir,
            self.audio_dir,
            self.stock_footage_dir,
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    @property
    def viral_format(self) -> bool:
        """Toggle to enable viral-style script/video formatting."""
        return os.getenv('VIRAL_FORMAT', 'false').lower() == 'true'
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return {
            'gemini_api_key': '***' if self.gemini_api_key else '',
            'gemini_model': self.gemini_model,
            'youtube_client_id': '***' if self.youtube_client_id else '',
            'target_topic': self.target_topic,
            'topics_rotation': self.topics_rotation,
            'video_resolution': self.video_resolution,
            'video_fps': self.video_fps,
            'video_duration_seconds': self.video_duration_seconds,
            'batch_size': self.batch_size,
            'dry_run': self.dry_run,
            'verbose': self.verbose,
            'viral_format': os.getenv('VIRAL_FORMAT', 'false').lower() == 'true',
            'output_dir': str(self.output_dir),
            'temp_dir': str(self.temp_dir),
            'log_dir': str(self.log_dir),
        }


# Singleton instance
_config_instance: Optional[Config] = None


def get_config(config_file: Optional[Path] = None, env_file: Optional[Path] = None) -> Config:
    """Get or create the configuration singleton."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_file, env_file)
    return _config_instance


def reset_config():
    """Reset the configuration singleton."""
    global _config_instance
    _config_instance = None


if __name__ == '__main__':
    # Test configuration loading
    config = get_config()
    print("Configuration loaded successfully!")
    print(json.dumps(config.to_dict(), indent=2))
    config.ensure_directories()
    print("✅ All directories created")
