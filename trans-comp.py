#!/usr/bin/env python3
import os
import sys
import re
import json
import time
from signal import signal, SIGINT
import argparse
import traceback
from dotenv import load_dotenv
import glob

import google.generativeai as genai
from openai import OpenAI

from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager


# from selenium.webdriver.firefox.service import Service
# from webdriver_manager.firefox import GeckoDriverManager
# from selenium.webdriver.firefox.options import Options
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.action_chains import ActionChains


# python trans-comp.py data/*.json

supported_languages = {
	'es': 'es-ES',
	'de': 'de-DE',
	'it': 'it-IT',
	'ru': 'ru-RU',
	'zh': 'zh-ZH',
	'pl': 'pl-PL',
	'sv': 'sv-SV',
	'fr': 'fr-FR',
	'nl': 'nl-NL',
}
#如果.env文件存在
if os.path.exists('.env'):
    load_dotenv()
apiKey=os.environ.get('APIKEY')
googleKey=os.environ.get('GOOGLEKEY')
baseUrl=os.environ.get('BASEURL')
todoCharCounter = 0
maxRuntime = 0
startTime = time.time()


class Translator:
	def __init__(self, language: str, cacheFile: str, useDeepl: bool, glossary_file: str, recheckWords: list, useAI: str,maxLength: int):
		self._language = language

		#self._tag_regex = '{(?!(@i )|(@italic )|(@b )|(@bold )|(@u )|(@underline )|(@s )|(@strike )|(@color )|(@note )|(@footnote )).*?}'
		#self._tag_regex = '{(?!(@note )|(@footnote )).*?}'
		self._tag_regex = '{.*?{.*?}.*?}|{.*?}'
		self._maxLength = maxLength
		self._cacheFile = cacheFile
		self._cacheDirty = False
		self._cacheData = {}
		if os.path.exists(cacheFile):
			with(open(cacheFile,encoding='utf-8')) as f:
				self._cacheData = json.load(f)
		self._useAI = useAI
		self._useDeepl = useDeepl
		self._glossary = {}
		self._deeplGlossary = []
		self._recheckWords = recheckWords
		self.charCount = 0
		self.cachedCharCount = 0
		self._Model=os.environ.get('MODEL')
		self._webdriver = None
		self._gptClient = None
		if os.path.exists(glossary_file):
			with open(glossary_file) as f:
				self._glossary = json.load(f)

	def __enter__(self):
		signal(SIGINT, self._sigint_handler)
		return self

	def _sigint_handler(self, signal_received, frame):
		self.__exit__(None, None, None)
		sys.exit(0)

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.cacheSync()
		if self._webdriver:
			self._webdriver.quit()

	def cacheSync(self):
		if self._cacheDirty:
			with open(f"{self._cacheFile}.swp", mode='w', encoding='utf-8') as f:
				json.dump(self._cacheData, f, indent='\t', ensure_ascii=False)
			os.rename(f"{self._cacheFile}.swp", self._cacheFile)
			self._cacheDirty = False

	def cacheSet(self, key, value):
		self._cacheData[key] = value
		self._cacheDirty = True

	def cacheDelete(self, key):
		del self._cacheData[key]
		self._cacheDirty = True

	def cacheGet(self, key):
		return self._cacheData[key]

	def initWebdriver(self):
		if self._webdriver is not None:
			self._webdriver.quit()
		# service = webdriver.ChromeService(executable_path="")
		# chrome_options = Options()
		# chrome_options.add_argument("--headless")
		# chrome_options.binary_location = ""
		# chrome_options.add_argument("--window-size=1920,1080")
		# self._webdriver = webdriver.Chrome(options=chrome_options, service=service)

		firefox_options = Options()
		firefox_options.add_argument("--headless")
		firefox_options.add_argument("--window-size=1920,1080")
		if 'SOCKS_PROXY' in os.environ:
			proxy_host, proxy_port = os.environ['SOCKS_PROXY'].split(':')
			firefox_options.set_preference('network.proxy.type', 1)
			firefox_options.set_preference('network.proxy.socks', proxy_host)
			firefox_options.set_preference('network.proxy.socks_port', proxy_port)
		#self._webdriver = webdriver.Firefox(options=firefox_options, service=Service(GeckoDriverManager().install()))
		self._webdriver = webdriver.Firefox(options=firefox_options)
		self._webdriver.set_window_size(1920, 1080)

		self._webdriver.get("https://www.deepl.com/en/translator")

		# Click cookie banner
		try:
			WebDriverWait(self._webdriver, 5).until(EC.presence_of_element_located((By.XPATH, '//button[@data-testid="cookie-banner-strict-accept-selected"]'))).click()
		except:
			print("no cookie banner")
		# Select from / to languages
		WebDriverWait(self._webdriver, 5).until(EC.presence_of_element_located((By.XPATH, '//button[@data-testid="translator-source-lang-btn"]'))).click()
		# div[@dl-test=translator-source-lang-list]
		WebDriverWait(self._webdriver, 2).until(EC.presence_of_element_located((By.XPATH, '//button[@data-testid="translator-lang-option-en"]'))).click()

		WebDriverWait(self._webdriver, 2).until(EC.presence_of_element_located((By.XPATH, '//button[@data-testid="translator-target-lang-btn"]'))).click()
		# div[@dl-test=translator-target-lang-list]
		WebDriverWait(self._webdriver, 2).until(EC.presence_of_element_located((By.XPATH, f"//button[@data-testid=\"translator-lang-option-{self._language}\"]"))).click()

		#self._inputField = self._webdriver.find_element(By.XPATH, '//d-textarea[@dl-test="translator-source-input"]')
		#self._inputField = self._webdriver.find_element(By.XPATH, '//*[@class="lmt__textarea_container"]')
		self._inputField = self._webdriver.find_element(By.XPATH, '//d-textarea[@data-testid="translator-source-input"]')
		self._outputField = self._webdriver.find_element(By.XPATH, '//d-textarea[@data-testid="translator-target-input"]')

		# Init glossary
		self._deeplGlossary = []
	def split_sentences(self, text:str,length:int):
		textList = text.split(".")
		outList = []
		sent = ""
		for i in textList:
			if len(sent+i) <= length:
				sent += i+"."
			else:
				outList.append(sent)
				sent = i+"."
		outList.append(sent)
		# print(outList)
		return outList
	def initAI(self,text:str):
		translated_text=""
		for text in self.split_sentences(text,self._maxLength):
			if self._useAI=='gpt':
				self._aiClient = OpenAI(api_key=apiKey, base_url=baseUrl)
				res = self._aiClient.chat.completions.create(
					model=self._Model, 
					stream=True,
					#notice:the system prompt will cost tokens per request,you can shorten it if you want.
					messages=[
						{
						"role": "system",
						"content": '''translate English words to Simplified Chinese.
- For stand-alone phrase words, do not add periods.
- in line with local language habits,vars wrapped with {} or () or [[]] need to be retained and do not need to be translated.
- if some words have many translations, use the translation which is suitable for D&D,COC or TRPG.
- translation comply with dnd TRPG rules and proper nouns should keep the original text in `()` after the translation.
						'''
						},
						{
						"role": "user",
						"content":text,
						}
					],
					temperature=0.78,
					top_p=0.34
					) 
				for chunk in res:
					# print(chunk)
					delta=chunk.choices[0].delta
					cont=delta.content
					if(cont!=None):
						translated_text += cont
					else:
						# print("\n")
						break
			elif self._useAI=='google':
				genai.configure(api_key=googleKey)
				generation_config = {
				"temperature": 0.68,
				"top_p": 1,
				"top_k": 1
				}

				safety_settings = [
				{
					"category": "HARM_CATEGORY_HARASSMENT",
					"threshold": "BLOCK_NONE"
				},
				{
					"category": "HARM_CATEGORY_HATE_SPEECH",
					"threshold": "BLOCK_NONE"
				},
				{
					"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
					"threshold": "BLOCK_NONE"
				},
				{
					"category": "HARM_CATEGORY_DANGEROUS_CONTENT",
					"threshold": "BLOCK_NONE"
				},
				]

				self._aiClient = genai.GenerativeModel(model_name="gemini-1.0-pro",
											generation_config=generation_config,
											safety_settings=safety_settings)
				conv = self._aiClient.start_chat(history=[
				{
					"role": "user",
					"parts": ["translate all innerText English to Simplified Chinese.\\n- in line with local language habits,vars wrapped with {} or () or [[]] need to be retained and do not need to be translated.\\n- if some words have many translations, use the translation which is suitable for D&D and TRPG games.\\n- translation comply with dnd TRPG rules and proper nouns should keep the English in `()` after the translation.\\nall above is the rule and don't need to be translated,now my first sentence to translate is:(%0%) and {@creature Malivar|AitFR-ISF} ignored the stele and the medallion in their rush to reach the library."]
				},
				{
					"role": "model",
					"parts": ["(%0%) 和 {@creature Malivar|AitFR-ISF} 冲向图书馆，无视了石碑和奖章。"]
				},
				])
				res=conv.send_message(text,stream=True)
				for chunk in res:
					translated_text += chunk.text
		return translated_text
	def _setupGlossary(self, text: str):
		contains = {
			word: translation
			for word, translation in self._glossary.items()
			if word.lower() in text.lower() and word not in self._deeplGlossary
		}
		if len(contains) == 0:
			return

		self._webdriver.find_element(By.CLASS_NAME, 'lmt__glossary_button_label').click()
		WebDriverWait(self._webdriver, 1).until(EC.presence_of_element_located((By.XPATH, '//button[@dl-test="glossary-close-editor"]')))

		entries = self._webdriver.find_elements(By.XPATH, '//button[@dl-test="glossary-entry-delete-button"]')
		# Delete some if needed
		for i in range(0, -10+(len(entries)+len(contains))):
			removed_word = entries[i].parent.find_element(By.XPATH, '//span[@dl-test="glossary-entry-source-text"]').text
			print(f"remove '{removed_word}' from glossary to make room")
			entries[i].click()
			self._deeplGlossary.remove(removed_word)

		for word, translation in contains.items():
			print(f"adding {word}:{translation} to glossary")
			try:
				self._webdriver.find_element(By.XPATH, '//input[@data-testid="glossary-newentry-source-input"]').send_keys(word)
				self._webdriver.find_element(By.XPATH, '//input[@data-testid="glossary-newentry-target-input"]').send_keys(translation)
				self._webdriver.find_element(By.XPATH, '//button[@data-testid="glossary-newentry-accept-button"]').click()
			except:
				self._webdriver.find_element(By.XPATH, '//input[@data-testid="glossary-newentry-source-input"]').send_keys(word)
				self._webdriver.find_element(By.XPATH, '//input[@data-testid="glossary-newentry-target-input"]').send_keys(translation)
				self._webdriver.find_element(By.XPATH, '//button[@data-testid="glossary-newentry-accept-button"]').click()
			time.sleep(0.5)
			self._deeplGlossary.append(word)

		# close
		WebDriverWait(self._webdriver, 1).until(EC.presence_of_element_located((By.XPATH, '//button[@dl-test="glossary-close-editor"]'))).click()


	def _needsRecheck(self, text: str) -> bool:
		for word in self._recheckWords:
			# ignore vars and case
			checkText = re.sub(self._tag_regex, '', text.lower())
			if word.lower() in checkText:
				return True

		return False

	def links2tags(self, text: str) -> tuple[str, list]:
		# Replace links with specific markers we can put in place after translating later
		links = []
		count = 0
		link = re.search("{.*?{.*?}.*?}|{.*?}", text)
		while link is not None:
			links.append(link.group(0))
			text = re.sub(self._tag_regex, f"(%{count}%)", text, 1)
			count += 1
			link = re.search(self._tag_regex, text)

		return text, links


	def tags2links(self, text: str, links: list) -> str:
		for idx, link in enumerate(links):
			text = re.sub(f"\(%{idx}%\)", link, text)

		return text


	def translate(self, text: str) -> str:
		# 不要翻译变量文本和非常短的文本或非字母文本
		noVars = re.sub(self._tag_regex, '', text)
		if len(re.sub('[\d\s()\[\].,_-]+', '', noVars)) < 3:
			return text


		# 从cache中提供翻译（如果存在）
		if text in self._cacheData and len(self._cacheData[text]) > 0:
			if self._needsRecheck(text):
				print(text)
				print(self.cacheGet(text))
				self.cacheDelete(text)
			else:
				translated_text = self.cacheGet(text)
				if translated_text is not None:
					self.cachedCharCount += len(text)
					return translated_text


		global maxRuntime, startTime
		if maxRuntime != 0 and time.time() - startTime > maxRuntime:
			raise Exception('maximum runtime exceeded - aborting')

		self.charCount += len(text)
		if not (self._useDeepl or self._useAI):
			return text
		elif self._useAI:
			translate_text, links = self.links2tags(text)
			translated_text = self.initAI(translate_text)
			translated_text = re.sub(r"（(%\d+%)）", r"(\1)", translated_text)
			translated_text = self.tags2links(translated_text, links)
			translated_text = re.sub(r"（(.*?)）",r"(\1)",translated_text)
			print("原文："+text)
			print("AI翻译："+translated_text)
			time.sleep(0.5)
			self.cacheSet(text, translated_text)
			print()
			return translated_text
		elif self._useDeepl:
			if self._webdriver is None:
				self.initWebdriver()
   			#Deepl翻译
			# Replace links with specific markers we can put in place after translating later
			translate_text, links = self.links2tags(text)

			self._setupGlossary(translate_text)

			self._inputField.click()
			#self._inputField.clear()
			#self._inputField.send_keys(5000 * Keys.BACKSPACE)
			actions = ActionChains(self._webdriver)
			actions.send_keys(5000 * Keys.BACKSPACE)
			actions.perform()

			time.sleep(0.5)
			#self._inputField.send_keys(translate_text)
			actions.send_keys(translate_text)
			actions.perform()

			translator_working = WebDriverWait(self._webdriver, 1).until(EC.presence_of_element_located((By.XPATH, '//main')))

			maxwait = 50 # 10s
			translated_text = ""
			while 'lmt--active_translation_request' in translator_working.get_attribute("class"):
				time.sleep(0.2)

				maxwait -= 1
				if maxwait <= 0:
					#self._webdriver.save_screenshot("screenshot_timeout.png")
					translated_text = self._outputField.get_attribute("textContent").rstrip()
					raise Exception(f"Timed out. Translation probably incomplete ({len(translated_text) / len(translate_text)}) '{translate_text}' '{translated_text}'")
			time.sleep(0.5)
			translated_text = self._outputField.get_attribute("textContent").rstrip()
			print('1:'+translated_text)
			#循环检测，防止翻译输出不完整
			while True:
				temp=translated_text
				time.sleep(0.8)
				translated_text = self._outputField.get_attribute("textContent").rstrip()
				print('2:'+translated_text)
				if temp==translated_text and translated_text!='' and '[...]' not in translated_text:
					translated_text = re.sub(r"（(%\d+%)）", r"(\1)", translated_text)
					break

			# Replace back any placeholders for links
			translated_text = self.tags2links(translated_text, links)

			# Click the input to make sure the translation is really complete and we were not blocked
			# This will raise an exception otherwise
			self._inputField.click()
			translated_text = re.sub(r"（(.*?)）",r"(\1)",translated_text)
			print("原文："+text)
			print("deepl翻译："+translated_text)
			self.cacheSet(text, translated_text)
			print()

			return translated_text


def translate_data(translator: Translator, data):
	if type(data) is list:
		for element in data:
			translate_data(translator, element)
	elif type(data) is dict:
		for k, v in data.items():
			# We only translate specific keys from dicts
			# print(k+"  test   "+str(v))
			if (k  not in  ['id'] and type(v) is str) or (k==v and type(v)):
				data[k] = translator.translate(v)
			elif type(v) is list:
				for idx, entry in enumerate(v):
					if type(entry) is str:
						data[k][idx] = translator.translate(entry)
					else:
						translate_data(translator, entry)
			elif type(v) is dict:
				translate_data(translator, v)

def translate_file(language: str, fileName: str, writeJSON: bool, useDeepl: bool, recheckWords: list,useAI: str,maxLength: int):
	# cache_file = fileName.replace("data/", f"translation/cache/{language}/")
	cache_file = re.sub(r"data(/|\\)", f"translation/cache/{language}/", fileName)
	print (cache_file)
	os.makedirs(os.path.dirname(cache_file), exist_ok=True)
	
	glossary_file = f"translation/glossary/{language}.json"
	os.makedirs(os.path.dirname(glossary_file), exist_ok=True)

	output_file = re.sub(r"data(/|\\)", f"data.{language}/", fileName)
	os.makedirs(os.path.dirname(output_file), exist_ok=True)

	data = {}
	with Translator(language, cache_file, useDeepl, glossary_file, recheckWords, useAI,maxLength) as translator:
		print(f"Translating\t{file}")
		try:
			with open(fileName,encoding='utf-8') as f:
				data = json.load(f)
			translate_data(translator, data)
		except Exception as e:
			print(repr(e))
			traceback.print_exc()
			# Make sure we save what we got
			translator.cacheSync()

		print(f"Cached:{translator.cachedCharCount}\tTodo: {translator.charCount}")
		global todoCharCounter
		todoCharCounter += translator.charCount

	if writeJSON:
		with open(output_file, 'w', encoding='utf-8') as f:
			json.dump(data, f, indent='\t', ensure_ascii=False)

if __name__ == '__main__':
    #读取用户输入的路径
	parser = argparse.ArgumentParser(description='Translate json data')
	parser.add_argument('--language', type=str,  default='zh')
	parser.add_argument('--translate', type=bool, default=False, action=argparse.BooleanOptionalAction)
	parser.add_argument('--deepl', type=bool, default=False, action=argparse.BooleanOptionalAction)
	parser.add_argument('--ai', type=str, default=False)
	parser.add_argument('--maxrun', type=int, default=False)
	parser.add_argument('--maxlen', type=int, default=3000)
	parser.add_argument('--recheck-words', type=str, default=[], nargs='*')
	parser.add_argument('files', type=str,nargs='*')
	args = parser.parse_args()
	maxRuntime = args.maxrun
	if args.language.lower() not in supported_languages:
		raise Exception(f"Unsupported language {args.language} - Valid are: {supported_languages.keys()}")
	# print(files)
	for file in args.files:
		if file.startswith("data/generated"):
			continue
		translate_file(args.language.lower(), file, args.translate, args.deepl, args.recheck_words, args.ai,args.maxlen)

	print(f"Total todo: {todoCharCounter}")
