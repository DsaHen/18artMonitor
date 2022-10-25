import os
import time
import json

import fire
import requests

from rich.console import Console

console = Console()

class SzcpMonitor(object):

	def __init__(self, phone="", code="", keyword="", token="", price=""):
		self.header_url     = "http://103.205.252.30:3000/irabbit"
		self.login_url      = "https://app-001.cloud.servicewechat.com/nft-web/v1.1/nft/user/login"
		self.search_url     = "https://app-001.cloud.servicewechat.com/nft-web/nft/market/search?pageSize=20&page=1&sort=0&content="
		self.price_url      = "https://app-001.cloud.servicewechat.com/nft-web/v1.2/nft/product/getProductListByAlbumId?pageSize=20&albumId={albumId}&onSale=1&page=1&order=1"
		self.order_url      = "https://app-001.cloud.servicewechat.com/nft-web/v1/nft/order/create"
		self.headers        = {
			"X-Cloudbase-Phone": str(phone),
			"Referer": "https://app-001.cloud.servicewechat.com/nft-web/v1/nft/order/create",
			"Language": "zh-CN",
			"PLATFORM-TYPE": "android",
			"APP-VERSION": "1.2.4",
			"Host": "app-001.cloud.servicewechat.com"
	    }

		self.phone          = phone
		self.code           = code
		self.keyword        = keyword
		self.token          = token
		self.price          = price


	def __getHeader(self):
		header_req = requests.get(self.header_url)
		return header_req.json()

	def __getToken(self, phone, code):
		"""
		parame: phone 
		code: code

		return user-token
		"""
		data = json.dumps({"phoneNumber":phone,"code":code,"inviteCode":""})
		token_req = requests.post(self.login_url, headers=self.headers, data=data)
		if token_req.json()["code"] != 1:
			console.print(f"[!] {token_req.json()['message']}")
			exit()
		return token_req.json()["data"]["token"]

	def __search(self, keyword):
		"""
		parame: keyword 搜索关键字

		return 藏品ID
		"""
		url = self.search_url+keyword
		search_req = requests.get(url, headers=self.headers)
		if not search_req.json().get("data", False):
			console.print("获取搜索结果失败，原因：", search_req.json())
			time.sleep(3)
			self.__search(keyword)
		for album in search_req.json()["data"]["list"]:
			if album["albumName"] == keyword:
				return album["albumId"]
		return -1

	def __getProductById(self, albumId, price):
		"""
		parame: albumId 藏品ID
		parame: price 

		return 实时藏品信息
		"""
		url = self.price_url.format(albumId=albumId)
		price_req = requests.get(url, headers=self.headers)
		if not price_req.json().get("data", False):
			console.print("获取价格列表失败，原因：", price_req.json())
			time.sleep(3)
			self.__getProductById(albumId, price)
		for album in price_req.json()["data"]["list"]:
			if (album["gStatus"] == 6 and int(album["priceCny"]) <= price):
				return album

		time.sleep(1)
		self.__getProductById(albumId, price)

	def __orderCreate(self, album_data):
		"""
		parame: album_data 藏品信息

		return 付款信息
		"""
		# console.print(album_data)
		data = json.dumps({
			"gId":str(album_data["gId"]),
			"price":str(int(album_data["priceCny"])),
			"albumId":str(album_data["albumId"]),
			"payChannel":"23",
			"type":album_data["albumType"],
			"gNum":album_data["gNum"]
		})
		# for k,v in self.headers.items():
		# 	console.print(f"{k}: {v}")
		# print(repr(data))

		req = requests.post(self.order_url, headers=self.headers, data=data)
		# for k,v in req.request.headers.items():
		# 	console.print(f"{k}: {v}")

		if not req.json().get("data", False):
			console.print("下单失败，原因：", req.json())
			time.sleep(1)
			self.__orderCreate(album_data)

		return req.json()["data"]["orderStr"]

	def run(self):
		headers = self.__getHeader()
		for k,v in headers.items():
			self.headers[k] = v

		if self.phone == "":
			console.print("[!] Phone is Null.")
			exit()

		if self.token == "":
			if self.code == "":
				console.print("[!] Code is Null.")
				exit()
			self.token = self.__getToken(self.phone, self.code)

		console.print(f"[*] Token -> {self.token}")
		self.headers["USER-TOKEN"] = self.token
		time.sleep(1)

		if self.keyword == "":
			console.print("[*] Keyword is Null.")
			exit()

		albumId = self.__search(self.keyword)
		console.print(f"[*] albumId -> {albumId}")

		if albumId == -1:
			console.print("[!] search error. Keyword not found.")
			return

		if self.price == "":
			console.print("[*] Price is Null.")
			exit()

		cp_info = self.__getProductById(albumId, int(self.price))
		console.print(f"[*] Lock price -> {cp_info['priceCny']}")

		order_link = self.__orderCreate(cp_info)
		console.print("支付链接：", order_link)
		os.system(f'start "{order_link}"')

def main():
	fire.Fire(SzcpMonitor)

if __name__ ==  "__main__":
	main()