import json

with open('../data/private_keys.txt', 'r') as keys_file:
  private_keys = keys_file.read().splitlines()
with open('../data/proxy.txt', 'r', encoding='utf-8') as file:
  proxies = file.read().splitlines()
with open('../data/rpcs.json') as file:
  rpc = json.load(file)
with open('../data/abi/mintfun_season1.json') as file:
  mintfun_season1_abi = json.load(file)

MINTFUN_SEASON1_CONTRACT = '0xfFFffffFB9059A7285849baFddf324e2c308c164'



