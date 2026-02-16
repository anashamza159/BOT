import requests
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional  # أضف Optional هنا

logger = logging.getLogger(__name__)

class BaseChecker(ABC):
    """Base class for all site checkers"""
    
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.name = self.__class__.__name__.replace('Checker', '').lower()
        
    @abstractmethod
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        """Check single account, must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        """Determine if account should be saved based on conditions"""
        pass
    
    @abstractmethod
    def save_format(self, account_data: Dict[str, Any]) -> str:
        """Format account data for saving"""
        pass
    
    def get_stats_keyboard(self, stats: Dict[str, int]) -> Dict[str, Any]:
        """Generate stats keyboard for Telegram"""
        return {
            "type": "inline_keyboard",
            "buttons": [
                [{"text": f"🔄 Checked: {stats['checked']}/{stats['total']}", "callback_data": "progress"}],
                [
                    {"text": f"✅ Valid: {stats['valid']}", "callback_data": "valid"},
                    {"text": f"❌ Bad: {stats['bad']}", "callback_data": "bad"}
                ],
                [
                    {"text": f"⚠️ Error: {stats['error']}", "callback_data": "error"},
                    {"text": f"💾 Saved: {stats['saved']}", "callback_data": "saved"}
                ]
            ]
        }