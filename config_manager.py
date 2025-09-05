"""
Configuration management for Plex Radio Client.
Handles loading and validation of YAML configuration files.
"""
import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """Manages configuration loading and access for the radio client."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the configuration manager.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = Path(config_path)
        self._config = None
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from the YAML file."""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            
            # Validate required sections
            self._validate_config()
            print(f"[INFO] Configuration loaded from {self.config_path}")
            
        except Exception as e:
            print(f"[ERROR] Failed to load configuration: {e}")
            print("[INFO] Using default configuration")
            self._config = self._get_default_config()
    
    def _validate_config(self) -> None:
        """Validate that all required configuration sections exist."""
        required_sections = ['api', 'hardware', 'gpio', 'display', 'logging']
        
        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"Missing required configuration section: {section}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            'api': {
                'base_url': 'http://localhost:5000'
            },
            'hardware': {
                'enabled': True
            },
            'gpio': {
                'power_pin': 25,
                'volume_up_pin': 23,
                'volume_down_pin': 24,
                'channel_up_pin': 14,
                'channel_down_pin': 15
            },
            'display': {
                'enabled': True
            },
            'logging': {
                'quiet_mode': True,
                'log_level': 'INFO'
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to the configuration value (e.g., 'gpio.power_pin')
            default: Default value if the key is not found
            
        Returns:
            The configuration value or default
        """
        if self._config is None:
            return default
        
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get an entire configuration section.
        
        Args:
            section: Name of the configuration section
            
        Returns:
            Dictionary containing the section configuration
        """
        if self._config is None:
            return {}
        
        return self._config.get(section, {})
    
    def is_enabled(self, feature_path: str) -> bool:
        """Check if a feature is enabled.
        
        Args:
            feature_path: Dot-separated path to the feature flag
            
        Returns:
            True if the feature is enabled, False otherwise
        """
        return self.get(feature_path, False) is True
    
    def reload_config(self) -> None:
        """Reload the configuration from file."""
        self.load_config()


# Global configuration instance
config = ConfigManager()
