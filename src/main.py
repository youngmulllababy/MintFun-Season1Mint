import csv

from fake_useragent import UserAgent
from web3 import Web3, HTTPProvider, Account
import requests
import json, random, time
from datetime import date
from loguru import logger

from config import rpc, MINTFUN_SEASON1_CONTRACT, mintfun_season1_abi, private_keys, proxies
from settings import MAX_GWEI, MINTFUN_API_MAX_RETRIES, TRANSACTION_TIMEOUT, SLEEP_FROM, SLEEP_TO, CHECK_GWEI
from tqdm import tqdm

def get_gas():
    try:
        w3 = Web3(Web3.HTTPProvider(rpc["ethereum"]["rpc"][0]))
        gas_price = w3.eth.gas_price
        gwei = w3.from_wei(gas_price, 'gwei')
        return gwei
    except Exception as error:
        logger.error(error)


def wait_gas():
    logger.info("checking GWEI")
    while True:
        gas = get_gas()

        if gas > MAX_GWEI:
            logger.info(f'Current GWEI: {gas} > {MAX_GWEI}')
            time.sleep(60)
        else:
            logger.success(f"GWEI is normal | current: {gas} < {MAX_GWEI}")
            break


def get_mint_signature(main_address: str, proxy):
    retries=0
    while retries < MINTFUN_API_MAX_RETRIES:
        try:
            url = f'https://mint.fun/api/mintfun/fundrop/season1/mint?address={main_address}'
            ua = UserAgent()
            ua = ua.random

            headers = {
                'User-Agent': ua,
            }
            proxies = {
                "http": proxy,
                "https": proxy,
            }

            resp = requests.get(url, headers=headers, proxies=proxies)
            if resp.status_code == 200:
                json_res = json.loads(resp.text)
                logger.success('successfully got signature from mintfun API')
                sign = json_res['signature']
                return sign
            else:
                retries += 1
                logger.error(f'non 200 response from mintfun - {resp.status_code}\n{json.loads(resp.text)}| {retries}/{MINTFUN_API_MAX_RETRIES}')

        except Exception as e:
            retries += 1
            logger.error(f"error occurred during request to mintfun API | {e} | {retries}/{MINTFUN_API_MAX_RETRIES}")
            if retries == MINTFUN_API_MAX_RETRIES:
                raise e


def to_bytes(hex_str):
    return Web3.to_bytes(hexstr=hex_str)


def mint(private_key, proxy):
    w3 = Web3(HTTPProvider(rpc["ethereum"]["rpc"][0]))
    account = w3.eth.account.from_key(private_key)
    address = w3.to_checksum_address(account.address)
    contract_address = w3.to_checksum_address(MINTFUN_SEASON1_CONTRACT)
    contract = w3.eth.contract(address=contract_address, abi=mintfun_season1_abi)

    signature = get_mint_signature(address, proxy)

    swap_txn = contract.functions.mint([4], [1], 1, to_bytes(signature)).build_transaction({
        'from': address,
        'nonce': w3.eth.get_transaction_count(account.address),
    })

    estimated_gas_limit = round(w3.eth.estimate_gas(swap_txn))
    swap_txn.update({'gas': estimated_gas_limit})

    signed_txn = w3.eth.account.sign_transaction(swap_txn, private_key)
    txn_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    logger.info(f'{account.address} - waiting for transaction - {txn_hash.hex()}')
    txn_receipt = w3.eth.wait_for_transaction_receipt(txn_hash, timeout=TRANSACTION_TIMEOUT)

    if txn_receipt['status'] == 1:
        logger.success(f"{account.address} | Successfully minted season1 mintfun stickers\n"
                       f"https://etherscan.io/tx/{txn_hash.hex()}")
        return True
    elif txn_receipt['status'] == 0:
        logger.warning("Transaction was unsuccessful\n"
                       f"https://etherscan.io/tx/{txn_hash.hex()}")
        return False


def write_to_csv(res):
    with open(f'result_{str(date.today())}.csv', 'a', newline='') as file:
        writer = csv.DictWriter(file, res.keys())
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow(res)


def sleep(sleep_from: int, sleep_to: int):
    delay = random.randint(sleep_from, sleep_to)
    with tqdm(
            total=delay,
            desc="sleeping",
            bar_format="{desc}: |{bar:20}| {percentage:.0f}% | {n_fmt}/{total_fmt}",
            colour="green"
    ) as pbar:
        for _ in range(delay):
            time.sleep(1)
            pbar.update(1)


def main():
    random.shuffle(private_keys)
    for i, private_key in enumerate(private_keys):
        account = Account.from_key(private_key)
        res = {'Address': account.address, 'Key': private_key}

        if CHECK_GWEI:
            wait_gas()

        logger.info(f"Started work with wallet: {account.address}")

        try:
            if mint(private_key, random.choice(proxies)):
                res['status'] = 'success'
            else:
                res['status'] = 'failed'
        except Exception as e:
            logger.error(f'exception occurred during minting | {str(e)}')
            res['status'] = f'failed - {e}'

        write_to_csv(res)

        sleep(SLEEP_FROM, SLEEP_TO)


if __name__ == '__main__':
    main()
