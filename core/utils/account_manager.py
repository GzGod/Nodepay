# account_manager.py
import asyncio
import traceback
import csv
import os
from datetime import datetime

from faker import Faker
from core.utils import logger
from core.models.account import Account
from core.models.exceptions import CloudflareException, LoginError
from core.nodepay_client import NodePayClient
from core.utils.file_manager import str_to_file
from core.utils.proxy_manager import get_proxy, release_proxy
from pyuseragents import random as random_useragent
import random


class AccountManager:
    def __init__(self, threads, ref_codes, captcha_service):
        self.ref_codes = ref_codes
        self.threads = threads
        self.fake = Faker()
        self.captcha_service = captcha_service
        self.should_stop = False
        self.earnings_file = 'data/earnings.csv'
        self.ensure_earnings_file_exists()

    def ensure_earnings_file_exists(self):
        os.makedirs('data', exist_ok=True)
        if not os.path.exists(self.earnings_file):
            with open(self.earnings_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Email', 'Last Update', 'Total Earnings'])

    def update_earnings(self, email: str, total_earning: float):
        temp_file = f'{self.earnings_file}.tmp'
        found = False
        
        # Read existing data
        rows = []
        try:
            with open(self.earnings_file, 'r', newline='') as f:
                reader = csv.reader(f)
                header = next(reader)  # Skip header
                rows = list(reader)
        except FileNotFoundError:
            header = ['Email', 'Last Update', 'Total Earnings']
            rows = []

        # Update or add new entry
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for i, row in enumerate(rows):
            if row[0] == email:
                rows[i] = [email, current_time, str(total_earning)]
                found = True
                break
        
        if not found:
            rows.append([email, current_time, str(total_earning)])

        # Write updated data
        with open(temp_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

        # Replace original file
        os.replace(temp_file, self.earnings_file)
        # logger.info(f"Updated earnings for {email}: {total_earning}")

    async def process_account(self, email: str, password: str, action: str):
        if self.should_stop:
            logger.info(f"Stopping process for {email}")
            return None
        
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries and not self.should_stop:
            proxy_url = await get_proxy()
            user_agent = random_useragent()
            client = None
            try:
                logger.info(f"{email} | {action.capitalize()}")

                client = NodePayClient(email=email, password=password, proxy=proxy_url, user_agent=user_agent)
                async with client:
                    if action == "register":
                        ref_code = random.choice([random.choice(self.ref_codes or [None]),
                                              random.choice(['Pf4yQYI8sYwLNT5'])])

                        res = await client.register(ref_code, self.captcha_service)

                        if not res.get("success"):
                            logger.error(f'{email} | Registration failed | {res["msg"]}')
                            with open('failed_accounts.txt', 'a') as f:
                                f.write(f'{email}:{password}\n')
                            return

                        uid, access_token = await client.get_auth_token(self.captcha_service)
                        await client.activate(access_token)
                        str_to_file('new_accounts.txt', f'{email}:{password}')
                        logger.success(f'{email} | registered')
                    elif action == "mine":
                        uid, access_token = await client.get_auth_token(self.captcha_service)
                        total_earning = await client.ping(uid, access_token)
                        self.update_earnings(email, total_earning)
                        logger.success(f"{email} | Points: {total_earning}")
                    
                    if action in ["login", "register"]:
                        return Account(
                            email=email,
                            password=password,
                            uid=uid,
                            access_token=access_token,
                            user_agent=user_agent,
                            proxy_url=proxy_url
                        )
                    return True
            except CloudflareException as e:
                logger.error(f'{email} | {e} error | Delaying...')
                await asyncio.sleep(10 * 60)
            except LoginError as e:
                logger.warning(f"{email} | Login error: {e}")
                return "exit"
            except Exception as e:
                logger.error(f"{email} | Unhandled error: {e}")
                logger.debug(f"{email} | Unhandled error: {e} | {traceback.format_exc()}")
            finally:
                retry_count += 1

                if client:
                    await client.safe_close()
                await release_proxy(proxy_url)
            
            if self.should_stop:
                logger.info(f"{email} | stopping process")
                return None
            
            await asyncio.sleep(2)  # Wait before retrying
        
        logger.error(f"Max retries reached for {email} during {action}")
        return False

    async def register_account(self, email: str, password: str):
        return await self.process_account(email, password, "register")

    async def mining_loop(self, email: str, password: str):
        logger.info(f"Starting mining for account {email}")
        return await self.process_account(email, password, "mine")

    def stop(self):
        logger.info("Stopping AccountManager")
        self.should_stop = True

class TokenError(Exception):
    pass



