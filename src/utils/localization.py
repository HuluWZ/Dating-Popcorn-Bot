"""
Localization utility for Dating Popcorn Bot
Handles YAML-based translations with hierarchical structure and variables
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from config.settings import DEFAULT_LANGUAGE

class LocalizationManager:
    """Manages localization using YAML files with hierarchical structure and variables"""
    
    def __init__(self, locales_dir: str = "locales"):
        self.locales_dir = Path(locales_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._variables: Dict[str, Dict[str, str]] = {}
        self._load_all_locales()
    
    def _load_all_locales(self):
        """Load all available locale files"""
        if not self.locales_dir.exists():
            raise FileNotFoundError(f"Locales directory not found: {self.locales_dir}")
        
        for locale_dir in self.locales_dir.iterdir():
            if locale_dir.is_dir():
                locale_code = locale_dir.name
                messages_file = locale_dir / "messages.yaml"
                
                if messages_file.exists():
                    try:
                        with open(messages_file, 'r', encoding='utf-8') as f:
                            data = yaml.safe_load(f)
                            self._cache[locale_code] = data
                            
                            # Extract variables for this locale
                            self._variables[locale_code] = self._extract_variables(data)
                    except Exception as e:
                        print(f"Error loading locale {locale_code}: {e}")
    
    def _extract_variables(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Extract variables from the common.variables section"""
        variables = {}
        if 'common' in data and 'variables' in data['common']:
            variables = data['common']['variables']
        return variables
    
    def get_message(self, locale: str, key: str, **kwargs) -> str:
        """
        Get localized message with optional formatting and variable substitution
        
        Args:
            locale: Language code (e.g., 'en', 'es')
            key: Message key (e.g., 'bot.welcome.message', 'common.buttons.write_review')
            **kwargs: Formatting parameters (for {variable} syntax)
        
        Returns:
            Localized and formatted message
        """
        # Fallback to default language if locale not found
        if locale not in self._cache:
            locale = DEFAULT_LANGUAGE
        
        # Get message from cache
        messages = self._cache.get(locale, {})
        message = self._get_nested_value(messages, key)
        
        # Fallback to default language if key not found in current locale
        if not message and locale != DEFAULT_LANGUAGE:
            messages = self._cache.get(DEFAULT_LANGUAGE, {})
            message = self._get_nested_value(messages, key)
        
        # Fallback to key itself if not found anywhere
        if not message:
            message = key
        
        # Substitute YAML variables first (${variable} syntax)
        message = self._substitute_variables(message, locale)
        
        # Format message with kwargs (for {variable} syntax)
        if kwargs:
            try:
                return message.format(**kwargs)
            except (KeyError, ValueError) as e:
                print(f"Error formatting message '{key}': {e}")
                return message
        
        return message
    
    def _substitute_variables(self, message: str, locale: str) -> str:
        """
        Substitute variables in message using common.variables with ${variable} syntax
        
        Args:
            message: Message string that may contain variable references
            locale: Current locale for variable lookup
        
        Returns:
            Message with variables substituted
        """
        if not message or '${' not in message:
            return message
        
        # Get variables for this locale, fallback to default language
        variables = self._variables.get(locale, {})
        if not variables and locale != DEFAULT_LANGUAGE:
            variables = self._variables.get(DEFAULT_LANGUAGE, {})
        
        # Substitute variables using ${variable} syntax
        for var_name, var_value in variables.items():
            message = message.replace(f'${{{var_name}}}', var_value)
        
        return message
    
    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Optional[str]:
        """
        Get value from nested dictionary using dot notation
        
        Args:
            data: Dictionary to search in
            key: Key in dot notation (e.g., 'bot.welcome.message')
        
        Returns:
            Value if found, None otherwise
        """
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return current if isinstance(current, str) else None
    
    def get_variable(self, locale: str, variable_name: str) -> Optional[str]:
        """
        Get a variable value for a specific locale
        
        Args:
            locale: Language code
            variable_name: Variable name (e.g., 'bot_name', 'max_review_length')
        
        Returns:
            Variable value or None if not found
        """
        variables = self._variables.get(locale, {})
        if not variables and locale != DEFAULT_LANGUAGE:
            variables = self._variables.get(DEFAULT_LANGUAGE, {})
        
        return variables.get(variable_name)
    
    def get_available_locales(self) -> list:
        """Get list of available locale codes"""
        return list(self._cache.keys())
    
    def get_available_variables(self, locale: str = DEFAULT_LANGUAGE) -> Dict[str, str]:
        """Get all available variables for a locale"""
        return self._variables.get(locale, {})
    
    def reload_locales(self):
        """Reload all locale files (useful for development)"""
        self._cache.clear()
        self._variables.clear()
        self._load_all_locales()

# Global localization manager instance
localization_manager = LocalizationManager()

def get_message(locale: str, key: str, **kwargs) -> str:
    """
    Convenience function to get localized message
    
    Args:
        locale: Language code
        key: Message key
        **kwargs: Formatting parameters
    
    Returns:
        Localized message
    """
    return localization_manager.get_message(locale, key, **kwargs)

def get_available_locales() -> list:
    """Get list of available locales"""
    return localization_manager.get_available_locales()
