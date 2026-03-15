import json
import locale
import os

class BabelFish():
	def __init__(self,subpath=["resources","app","meta"],lang=None):
		localization_string = locale.getdefaultlocale()[0] #get set localization
		if localization_string is None:
			localization_string = "en"
		self.locale = localization_string[:2] if lang is None else lang #let caller override localization
		self.langs = ["en"] #start with English
		if(not self.locale == "en"): #add localization
			self.langs.append(self.locale)

		self.lang_defns = {} #collect translations
		self.add_translation_file() #start with default translation file
		self.add_translation_file(["resources","app","cli"]) #add help translation file
		self.add_translation_file(["resources","app","gui"]) #add gui label translation file
		self.add_translation_file(["resources","user","meta"]) #add user translation file

	def add_translation_file(self,subpath=["resources","app","meta"]):
		if not isinstance(subpath, list):
			subpath = [subpath]
		if "lang" not in subpath:
			subpath.append("lang") #look in lang folder
		subpath = os.path.join(*subpath) #put in path separators
		key = subpath.split(os.sep)
		for check in ["resources","app","user"]:
			if check in key:
				key.remove(check)
		key = os.path.join(*key) #put in path separators
		for lang in self.langs:
			if not lang in self.lang_defns:
				self.lang_defns[lang] = {}
			langs_filename = os.path.join(subpath,lang + ".json") #get filename of translation file
			if os.path.isfile(langs_filename): #if we've got a file
				with open(langs_filename,encoding="utf-8") as f: #open it
					self.lang_defns[lang][key[:key.rfind(os.sep)].replace(os.sep,'.')] = json.load(f) #save translation definitions
			else:
				pass
#				print(langs_filename + " not found for translation!")

	def translate(self, domain="", key="", subkey="", uselang=None): #three levels of keys
    # start with nothing
		display_text = ""

    # exits check for not exit first and then append Exit at end
    # multiRooms check for not chest name first and then append chest name at end
		specials = {
 			"exit": False,
 			"multiRoom": False
    }

    # Domain
		if os.sep in domain:
 			domain = domain.replace(os.sep,'.')
#		display_text = domain

		# Operate on Key
		if key != "":
			if display_text != "":
				display_text += '.'
#			display_text += key
      # Exits
			if "exit" in key and "gui" not in domain:
				key = key.replace("exit","")
				specials["exit"] = True
			if "Exit" in key and "gui" not in domain:
				key = key.replace("Exit","")
				specials["exit"] = True
			# Locations
			tmp = key.split(" - ")
			if len(tmp) >= 2:
				specials["multiRoom"] = tmp[len(tmp) - 1]
				tmp.pop()
				key = " - ".join(tmp)
			key = key.strip()

    # Operate on Subkey
		if subkey != "":
			if display_text != "":
 				display_text += '.'
			display_text += subkey
      # Exits
			if "exit" in subkey and "gui" not in domain:
				subkey = subkey.replace("exit","")
				specials["exit"] = True
			if "Exit" in subkey and "gui" not in domain:
				subkey = subkey.replace("Exit","")
				specials["exit"] = True
			# Locations
			tmp = subkey.split(" - ")
			if len(tmp) >= 2:
				specials["multiRoom"] = tmp[len(tmp) - 1]
				tmp.pop()
				subkey = " - ".join(tmp)
			subkey = subkey.strip()

		my_lang = self.lang_defns[uselang if uselang is not None else self.locale ] #handle for localization
		en_lang = self.lang_defns["en"] #handle for English

		if domain in my_lang and key in my_lang[domain] and subkey in my_lang[domain][key] and not my_lang[domain][key][subkey] == "": #get localization first
			display_text = my_lang[domain][key][subkey]
		elif domain in en_lang and key in en_lang[domain] and subkey in en_lang[domain][key] and not en_lang[domain][key][subkey] == "": #gracefully degrade to English
			display_text = en_lang[domain][key][subkey]
		elif specials["exit"]:
			specials["exit"] = False

		if specials["exit"]:
			display_text += " Exit"
		elif specials["multiRoom"] and specials["multiRoom"] not in display_text:
			display_text += " - " + specials["multiRoom"]

		return display_text
