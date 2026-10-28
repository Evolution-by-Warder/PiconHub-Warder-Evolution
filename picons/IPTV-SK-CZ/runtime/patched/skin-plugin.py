# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.config import *
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.g17ConfigList import ConfigListScreen, ConfigList
from Plugins.Plugin import PluginDescriptor
from Screens.InfoBar import InfoBar
from Components.ServiceEventTracker import ServiceEventTracker
from enigma import BT_SCALE, BT_KEEP_ASPECT_RATIO, eConsoleAppContainer, ePoint, RT_HALIGN_CENTER, eListboxPythonMultiContent, eListbox, gFont, eSize, ePixmap, eTimer, eServiceCenter, eServiceReference, iServiceInformation, iRdsDecoder, iPlayableService, eDVBFrontendParametersSatellite, eDVBFrontendParametersTerrestrial, getEnigmaVersionString
import Screens.InfoBar
from Tools.Transponder import ConvertToHumanReadable
try:
	from string import upper
except: pass
from Tools.LoadPixmap import LoadPixmap
from Components.Console import Console as wConsole
from Components.Sources.List import List
from Components.NimManager import nimmanager
from Components.FileList import FileList
import time as time1
import re, os
import threading
from Plugins.Extensions.setupGlass17 import warderRadio
import unicodedata
import json
import hashlib
import shutil
import stat
import zipfile
import subprocess
import tempfile
import NavigationInstance
try:
	from urllib.request import Request, urlopen
except ImportError:
	from urllib2 import Request, urlopen
ENACI = False
try:
	from enigma import eDVBCI_UI
	from enigma import eDVBCIInterfaces
	ENACI = True
except: pass
ENAVFT = False
try:
	from enigma import CT_MPEG2, CT_H264, CT_MPEG1, CT_MPEG4_PART2, CT_VC1, CT_VC1_SIMPLE_MAIN, CT_H265, CT_DIVX311, CT_DIVX4, CT_SPARK, CT_VP6, CT_VP8, CT_VP9, CT_H263, CT_MJPEG, CT_REAL, CT_AVS, CT_UNKNOWN
	ENAVFT = True
except: pass
ENAHBB = False
try:
	from enigma import eHbbtv
	ENAHBB = True
except: pass
EACC = False
try:
	from enigma import iAudioType_ENUMS as iAt
	EACC = True
except: pass
ENA_TT = False
try:
	from enigma import iDVBFrontend
	ENA_TT = True
except: pass
ENA_POPEN = False
try:
	from os import popen
	ENA_POPEN = True
except: pass
try:
	from enigma import quitMainloop
except: pass
try:
	from Components.Sensors import sensors
except: pass
ENA_SLIDER = [False,False]
try:
	from enigma import eSlider
	if 'setForegroundColor' in dir(eSlider):
		ENA_SLIDER[0] = True		
	if 'setBackgroundColor' in dir(eSlider):
		ENA_SLIDER[1] = True
except: pass		
from socket import socket, AF_INET, SOCK_STREAM
from skin import parseColor
from .warderDialogs import InputBox
from Components.Input import Input
from os import statvfs, listdir
from Screens.Standby import TryQuitMainloop
from Tools.HardwareInfo import HardwareInfo
from Components.Pixmap import *
from Tools.Directories import fileExists
from ServiceReference import ServiceReference
from .warderDialogs import MessageBox
from .warderUpdateText import update_text
from .warderDialogs import ChoiceBox
from . import warderPiconSync
from .warderTools import find_sevenzip
from .warderUiText import ui_text
from .warderTypePreviews import thumbnail_path
from Screens.InfoBarGenerics import InfoBarPlugins
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmap, MultiContentEntryPixmapAlphaTest
from keymapparser import readKeymap
from xml.etree.cElementTree import parse, fromstring
from Components.Sources.StaticText import StaticText
from Components.g17SelectionList import SelectionList
import gettext
from Components.Sources.CanvasSource import CanvasSource
from Plugins.Extensions.setupGlass17.txt import helpTxt, SATLIST
try:
	from Plugins.Extensions.setupGlass17.warderProgramInfo import lookup as warderProgramLookup
except Exception:
	warderProgramLookup = None
from datetime import datetime
from Plugins.Extensions.setupGlass17.weaUtils import *
if ISP38:
	from urllib.parse import quote
	import importlib
else:
	from urllib import quote
ENA_POSTER = False
try:
	from enigma import loadJPG
	ENA_POSTER = True
except: pass
PLUGINPATH = "/usr/lib/enigma2/python/Plugins/Extensions/setupGlass17/"
# TEST106: install OpenWebif Radio-All hook lazily against the receiver-proven GrabScreenshot class.
_warderOwiHookInstalled = False
_warderNativeGrabRender = None
_warderOwiGetUrlArg = None

from Components.Converter.WarderRadioOnly import is_radio_reference, is_native_dab

def _warderRadioGrabRender(self, request):
	global _warderNativeGrabRender, _warderOwiGetUrlArg
	# TEST183: DVB radio service types 0x02 (digital radio sound) and 0x0A (advanced-codec radio) are both RADIO. Determine this from the live service at screenshot time.
	# The TEST106 marker remains only as a fallback. This removes the timing
	# dependency which left OpenWebif in TV mode on DVB radio services without RDS.
	is_radio = False
	try:
		ref = NavigationInstance.instance and NavigationInstance.instance.getCurrentlyPlayingServiceReference()
		refstr = ref.toString() if ref is not None else ""
		fields = refstr.split(":")
		is_radio = is_radio_reference(ref)
	except Exception:
		pass
	if not is_radio:
		try:
			with open("/tmp/warder-radio-current", "r") as marker:
				is_radio = marker.read().strip() == "A"
		except Exception:
			is_radio = False
	mode = _warderOwiGetUrlArg(request, "mode")
	if not is_radio or mode not in (None, "", "all"):
		return _warderNativeGrabRender(self, request)
	fmt = _warderOwiGetUrlArg(request, "format") or "jpg"
	if fmt not in ("jpg", "png", "bmp"):
		fmt = "bmp"
	master = "/usr/share/enigma2/hd_glass17/warder-radio-background.jpg"
	fd, osd = tempfile.mkstemp(prefix="warder-radio-http-osd-", suffix=".png", dir="/tmp"); os.close(fd)
	fd, out = tempfile.mkstemp(prefix="warder-radio-http-out-", suffix="." + fmt, dir="/tmp"); os.close(fd)
	try:
		subprocess.check_call(["/usr/bin/grab", "-q", "-o", "-p", osd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
		ffmpeg = "/usr/bin/ffmpeg" if os.path.isfile("/usr/bin/ffmpeg") else "ffmpeg"
		cmd = [ffmpeg, "-nostdin", "-y", "-loglevel", "error", "-i", master, "-i", osd, "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto", "-frames:v", "1"]
		if fmt == "jpg": cmd += ["-vcodec", "mjpeg", "-q:v", "2", out]
		elif fmt == "png": cmd += ["-vcodec", "png", out]
		else: cmd += ["-vcodec", "bmp", out]
		subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=12)
		with open(out, "rb") as image: payload = image.read()
		if not payload: raise IOError("empty Radio screenshot")
		request.setHeader("Content-Type", "image/" + ("jpeg" if fmt == "jpg" else fmt))
		request.setHeader("Content-Length", str(len(payload)))
		return payload
	except Exception as error:
		try:
			with open("/tmp/warder-radio-webif-error.log", "a") as log: log.write("%s render-error: %r\\n" % (time1.strftime("%Y-%m-%d %H:%M:%S"), error))
		except Exception: pass
		try:
			with open(master, "rb") as image: payload = image.read()
			request.setHeader("Content-Type", "image/jpeg"); request.setHeader("Content-Length", str(len(payload)))
			return payload
		except Exception:
			return _warderNativeGrabRender(self, request)
	finally:
		for path in (osd, out):
			try: os.unlink(path)
			except Exception: pass

def _warderInstallOpenWebifGrabHook():
	global _warderOwiHookInstalled, _warderNativeGrabRender, _warderOwiGetUrlArg
	if _warderOwiHookInstalled: return True
	try:
		from Plugins.Extensions.OpenWebif.controllers.models import grab as owiGrab
		from Plugins.Extensions.OpenWebif.controllers.utilities import getUrlArg as owiGetUrlArg
		_warderOwiGetUrlArg = owiGetUrlArg
		grabClass = getattr(owiGrab, "GrabScreenshot", None)
		if grabClass is None:
			raise AttributeError("OpenWebif grab module has no GrabScreenshot class")
		if grabClass.render is not _warderRadioGrabRender:
			_warderNativeGrabRender = grabClass.render
			grabClass.render = _warderRadioGrabRender
		_warderOwiHookInstalled = True
		with open("/tmp/warder-radio-webif-hook.log", "a") as log: log.write("%s installed GrabScreenshot.render\\n" % time1.strftime("%Y-%m-%d %H:%M:%S"))
		return True
	except Exception as error:
		try:
			with open("/tmp/warder-radio-webif-hook.log", "a") as log: log.write("%s install-error: %r\\n" % (time1.strftime("%Y-%m-%d %H:%M:%S"), error))
		except Exception: pass
		return False

config.plugins.setupGlass17 = ConfigSubsection()
config.plugins.setupGlass17.par49 = ConfigYesNo(default = True) # enable translation
CH_LOG = "AllAboutNew"
HIST = "history.txt"
try:
	if config.plugins.setupGlass17.par49.value:
		glass17_language = []
		glass17_language = config.osd.language.value.split("_")
		if "cs" in glass17_language or "sk" in glass17_language:
			CH_LOG += "Sk"
			HIST += "Sk"
		if os.path.exists(PLUGINPATH + "locale/%s" % (glass17_language[0])):
			_ = gettext.Catalog('setupGlass17', PLUGINPATH + 'locale', glass17_language).gettext
except: pass
ENA_ANIM = False
try:
	from Components.ScreenAnimations import *
	a = ScreenAnimations()
	a.fromXML(PLUGINPATH+"anim_definition.xml")
	ENA_ANIM = True
except: pass

def Writelog(txt):
	log = PLUGINPATH+"g17.txt"
	if os.path.isfile(log):
		if os.path.getsize(log) > 1000000:
			try:
				os.remove(log)
			except OSError:
				pass
	try:
		f = open(log,"a")
		f.write("%s\\n" % str(txt))
		f.close()
	except IOError: pass
##########################################################################################################################
def _warderUiText(text):
	"""Warder UI strings follow the active Enigma2 OSD language without legacy gettext collisions."""
	try:
		lang = config.osd.language.value.split("_")[0].lower()
	except Exception:
		lang = "en"
	warder = {
		"sk": {"PROGRAM INFO": "Info o programe", "Station name:": "Názov stanice:", "Close": "Zavrieť", "Add Timer": "Pridať časovač", "Goto Date/Time": "Prejsť na dátum/čas", "EPG Search": "Vyhľadať v EPG", "Station:": "Stanica:", "Genre:": "Žáner:", "Year:": "Rok:", "Country:": "Krajina:", "Duration:": "Dĺžka:", "Broadcast:": "Vysielanie:", "Rating:": "Hodnotenie:"},
		"cs": {"PROGRAM INFO": "Info o programu", "Station name:": "Název stanice:", "Close": "Zavřít", "Add Timer": "Přidat časovač", "Goto Date/Time": "Přejít na datum/čas", "EPG Search": "Vyhledat v EPG", "Station:": "Stanice:", "Genre:": "Žánr:", "Year:": "Rok:", "Country:": "Země:", "Duration:": "Délka:", "Broadcast:": "Vysílání:", "Rating:": "Hodnocení:"}
	}
	if text in warder.get(lang, {}):
		return warder[lang][text]
	try:
		translated = _(text)
		if translated and translated != text:
			return translated
	except Exception:
		pass
	return text

class WarderProgramInfo(Screen):
	"""FullHDGlass-owned programme detail. EPG is authoritative; unknown metadata stays hidden."""
	skin = """
	<screen name="WarderProgramInfo" position="15,15" size="1890,1050" title="PROGRAM INFO" backgroundColor="transpBlack2" flags="wfNoBorder">
		<eLabel position="18,18" size="1854,1014" backgroundColor="transpBlack3" zPosition="-5" />
		<widget name="nowDate" position="30,12" size="390,42" font="Prive4;30" foregroundColor="#e5b243" transparent="1" />
		<widget name="nowTime" position="435,12" size="210,42" font="Prive4;30" foregroundColor="#eeeeee" transparent="1" />
		<eLabel text="FullHDGlass · Warder Evolution" position="1260,12" size="585,42" font="Prive4;24" halign="right" foregroundColor="#888888" transparent="1" />
		<widget name="programArtwork" position="30,75" size="520,300" zPosition="2" alphatest="blend" />
		<widget name="title" position="580,80" size="760,62" font="Prive4;47" foregroundColor="#e5b243" transparent="1" />
		<widget name="stationPicon" position="125,425" size="180,90" zPosition="3" alphatest="blend" />
		<widget name="stationLabel" position="50,520" size="190,34" font="Prive3;24" foregroundColor="#3388dd" transparent="1" />
		<widget name="channel" position="225,520" size="235,34" font="Prive4;24" foregroundColor="#dddddd" transparent="1" />
		<widget name="genreLabel" position="50,560" size="170,32" font="Prive3;24" foregroundColor="#3388dd" transparent="1" />
		<widget name="genreMeta" position="225,560" size="235,32" font="Prive4;24" foregroundColor="#dddddd" transparent="1" />
		<widget name="yearLabel" position="50,593" size="170,32" font="Prive3;24" foregroundColor="#3388dd" transparent="1" />
		<widget name="yearMeta" position="225,593" size="235,32" font="Prive4;24" foregroundColor="#dddddd" transparent="1" />
		<widget name="countryLabel" position="50,626" size="170,32" font="Prive3;24" foregroundColor="#3388dd" transparent="1" />
		<widget name="countryMeta" position="225,626" size="235,32" font="Prive4;24" foregroundColor="#dddddd" transparent="1" />
		<widget name="ratingStars" position="1390,105" size="430,45" font="Prive4;36" halign="right" foregroundColor="#e53935" transparent="1" />
		<widget name="ratingMeta" position="1390,152" size="430,36" font="Prive4;25" halign="right" foregroundColor="#dddddd" transparent="1" />
		<widget name="when" position="580,170" size="760,42" font="Prive3;30" foregroundColor="#e5b243" transparent="1" />
		<widget name="short" position="580,235" size="1220,120" font="Prive3;28" foregroundColor="#dddddd" transparent="1" />
		<eLabel position="25,405" size="1840,2" backgroundColor="#707070" />
		<widget name="durationLabel" position="50,675" size="170,34" font="Prive3;29" foregroundColor="#3388dd" transparent="1" />
		<widget name="durationMeta" position="225,675" size="235,34" font="Prive4;29" foregroundColor="#dddddd" transparent="1" />
		<widget name="broadcastLabel" position="50,714" size="170,34" font="Prive3;29" foregroundColor="#3388dd" transparent="1" />
		<widget name="broadcast" position="225,714" size="235,82" font="Prive4;28" foregroundColor="#dddddd" transparent="1" />
		<eLabel position="500,425" size="2,490" backgroundColor="#707070" />
		<widget name="description" position="535,425" size="1300,490" font="Prive4;31" foregroundColor="#dddddd" transparent="1" />
		<eLabel position="25,940" size="1840,2" backgroundColor="#707070" />
		<eLabel position="25,955" size="420,62" backgroundColor="transpBlack3" zPosition="2" />
		<widget source="keyRed" render="Label" position="25,963" size="420,46" font="Prive3;30" halign="center" valign="center" foregroundColor="red" transparent="1" zPosition="4" />
		<eLabel position="490,955" size="420,62" backgroundColor="transpBlack3" zPosition="2" />
		<widget source="keyGreen" render="Label" position="490,963" size="420,46" font="Prive3;30" halign="center" valign="center" foregroundColor="green" transparent="1" zPosition="4" />
		<eLabel position="955,955" size="420,62" backgroundColor="transpBlack3" zPosition="2" />
		<widget source="keyYellow" render="Label" position="955,963" size="420,46" font="Prive3;30" halign="center" valign="center" foregroundColor="yellow" transparent="1" zPosition="4" />
		<eLabel position="1420,955" size="420,62" backgroundColor="transpBlack3" zPosition="2" />
		<widget source="keyBlue" render="Label" position="1420,963" size="420,46" font="Prive3;30" halign="center" valign="center" foregroundColor="#3388dd" transparent="1" zPosition="4" />
	</screen>"""

	def __init__(self, session, event=None, service=None):
		Screen.__init__(self, session)
		for name in ("nowDate", "nowTime", "title", "channel", "when", "short", "durationMeta", "broadcast", "description", "stationLabel", "genreLabel", "genreMeta", "yearLabel", "yearMeta", "countryLabel", "countryMeta", "ratingStars", "ratingMeta", "durationLabel", "broadcastLabel"):
			self[name] = Label("")
		for name in ("keyRed", "keyGreen", "keyYellow", "keyBlue"):
			self[name] = StaticText("")
		self["programArtwork"] = Pixmap()
		self["stationPicon"] = Pixmap()
		self._artworkPath = ""
		self["stationLabel"].setText(_warderUiText("Station name:"))
		self["genreLabel"].setText(_warderUiText("Genre:"))
		self["yearLabel"].setText(_warderUiText("Year:"))
		self["countryLabel"].setText(_warderUiText("Country:"))
		for field in ("genreMeta", "yearMeta", "countryMeta"):

			self[field].setText("-")
		self["durationLabel"].setText(_warderUiText("Duration:"))
		self["broadcastLabel"].setText(_warderUiText("Broadcast:"))
		self["keyRed"].setText(_warderUiText("Close"))
		self["keyGreen"].setText(_warderUiText("Add Timer"))
		self["keyYellow"].setText(_warderUiText("Goto Date/Time"))
		self["keyBlue"].setText(_warderUiText("EPG Search"))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"ok": self._closeProgramInfo, "cancel": self._closeProgramInfo, "red": self._closeProgramInfo, "green": lambda: self._closeProgramInfo("green"), "yellow": lambda: self._closeProgramInfo("yellow"), "blue": lambda: self._closeProgramInfo("blue")}, -2)
		self._serviceRef = self._normaliseServiceRef(service)
		self["nowDate"].setText(time1.strftime("%A  %d.%m.%Y", time1.localtime()))
		self["nowTime"].setText(time1.strftime("%H:%M:%S", time1.localtime()))
		if event is not None:
			try:
				eventName = event.getEventName() or ""
				self["title"].setText(eventName)
			except Exception: pass
			try:
				begin = int(event.getBeginTime()); duration = int(event.getDuration())
				startDate = time1.strftime("%d.%m.%Y", time1.localtime(begin)); startTime = time1.strftime("%H:%M", time1.localtime(begin)); endTime = time1.strftime("%H:%M", time1.localtime(begin + duration)); minutes = duration // 60
				self["when"].setText("%s   %s - %s  (%d min)" % (startDate, startTime, endTime, minutes))
				self["durationMeta"].setText("%d min" % minutes)
				self["broadcast"].setText("%s\n%s - %s" % (startDate, startTime, endTime))
			except Exception: pass
			try: self["short"].setText(event.getShortDescription() or "")
			except Exception: pass
			try: self["description"].setText(event.getExtendedDescription() or event.getShortDescription() or "")
			except Exception: pass
		self._metadataTitle = event.getEventName() or "" if event is not None else ""
		self._metadataContext = " ".join(filter(None, [event.getShortDescription() or "", event.getExtendedDescription() or ""])) if event is not None else ""
		self._metadataResult = None
		self._metadataDone = False
		self._metadataClosed = False
		self._metadataTimer = eTimer()
		self._metadataTimer.callback.append(self._pollMetadataLookup)
		serviceName = self._serviceName(service, self._serviceRef)
		self["channel"].setText(serviceName)
		self.onLayoutFinish.append(self._loadServicePicon)
		self.onLayoutFinish.append(self._startMetadataLookup)
	def _closeProgramInfo(self, *retVal):
		self._metadataClosed = True
		try:
			self._metadataTimer.stop()
		except Exception:
			pass
		try:
			self.hide()
		except Exception:
			pass
		return self.close(*retVal)

	def _startMetadataLookup(self):
		if not self._metadataTitle or warderProgramLookup is None:
			return
		def worker():
			try:
				self._metadataResult = warderProgramLookup(self._metadataTitle, self._metadataContext)
			except Exception as e:
				Writelog("WarderProgramInfo metadata: %s" % e)
				self._metadataResult = {}
			self._metadataDone = True
		thread = threading.Thread(target=worker)
		thread.daemon = True
		thread.start()
		self._metadataTimer.start(500, False)

	def _pollMetadataLookup(self):
		if self._metadataClosed:
			self._metadataTimer.stop()
			return
		if not self._metadataDone:
			# Keep a tiny real repaint heartbeat while the worker is pending. OpenATV gRC
			# shows its busy tile after a long no-paint interval; this prevents that
			# without manipulating global spinner state or blocking remote-key input.
			try:
				self["nowTime"].setText(time1.strftime("%H:%M:%S", time1.localtime()))
			except Exception:
				pass
			return
		self._metadataTimer.stop()
		meta = self._metadataResult or {}
		try:
			self._artworkPath = meta.get("artwork_path") or ""
			if meta.get("genre"): self["genreMeta"].setText(meta["genre"])
			if meta.get("year"): self["yearMeta"].setText(meta["year"])
			if meta.get("country"): self["countryMeta"].setText(meta["country"])
			if meta.get("rating"):
				rating_text = str(meta["rating"]).strip()
				rating = float(rating_text.split("/", 1)[0].strip())
				filled = max(0, min(5, int(round(rating / 2.0))))
				self["ratingStars"].setText("★" * filled + "☆" * (5 - filled))
				self["ratingMeta"].setText("%s · %s" % (rating_text, meta.get("provider", "TMDB")))
			self._loadProgramArtwork()
		except Exception as e:
			Writelog("WarderProgramInfo metadata apply: %s" % e)

	def _loadProgramArtwork(self):
		try:
			if self._artworkPath and os.path.isfile(self._artworkPath):
				pix = LoadPixmap(path=self._artworkPath)
				if pix is not None:
					self["programArtwork"].instance.setScale(1)
					self["programArtwork"].instance.setPixmap(pix)
					self["programArtwork"].show()
					return
		except Exception as e:
			Writelog("WarderProgramInfo artwork: %s" % e)
		try:
			self["programArtwork"].hide()
		except Exception:
			pass

	def _normaliseServiceRef(self, service):
		if service is None: return None
		try:
			if isinstance(service, eServiceReference): return service
		except Exception: pass
		try:
			ref = getattr(service, "ref", None)
			if ref is not None: return ref
		except Exception: pass
		try:
			if hasattr(service, "toString"): return eServiceReference(service.toString())
		except Exception: pass
		try: return eServiceReference(str(service))
		except Exception: return None

	def _serviceName(self, service, serviceRef):
		try:
			if service is not None and hasattr(service, "getServiceName"):
				name = service.getServiceName() or ""
				if name: return name.replace("\xc2\x86", "").replace("\xc2\x87", "")
		except Exception: pass
		try:
			if serviceRef is not None: return (ServiceReference(serviceRef).getServiceName() or "").replace("\xc2\x86", "").replace("\xc2\x87", "")
		except Exception: pass
		return ""

	def _loadServicePicon(self):
		if self._serviceRef is None: return
		try:
			from Components.Renderer.Picon import getPiconName
			picon = getPiconName(self._serviceRef.toString())
			if picon and os.path.isfile(picon) and self["stationPicon"].instance is not None:
				self["stationPicon"].instance.setScale(1)
				self["stationPicon"].instance.setPixmapFromFile(picon)
				self["stationPicon"].show()
		except Exception as e:
			Writelog("WarderProgramInfo picon: %s" % e)

##########################################################################################################################
def readHWtype():
	brand = "Unknown"  
	model = "Unknown"	
	if fileExists("/proc/stb/info/boxtype"):
		brand = "Clarke-Tech"
		f = open("/proc/stb/info/boxtype",'r')
		model = f.readline().strip()
		f.close()
	if not "et8500" in model:
		if fileExists("/proc/stb/info/vumodel"):
			brand = "Vu"
			f = open("/proc/stb/info/vumodel",'r')
			model = f.readline().strip()
			f.close()
		elif fileExists("/proc/stb/info/boxtype"):
			brand = "Clarke-Tech"
			f = open("/proc/stb/info/boxtype",'r')
			model = f.readline().strip()
			f.close()
		elif fileExists("/proc/stb/info/model"):
			brand = "Dream Multimedia"
			f = open("/proc/stb/info/model",'r')
			model = f.readline().strip()
			f.close()
			if "cuberevo" in model or "Cuberevo" in model or "Ipbox" in model or "ipbox" in model or "IPbox" in model:
				brand = "AB-Com"
			elif "premium" in model:
				brand = "AZbox"
	return brand, model	
##########################################################################################################################
XCPU = "mipsel"
try:
	cpu = open("/proc/cpuinfo", "r").read()
	if cpu.find("sh4") != -1:
		XCPU = "sh4"
	elif cpu.find("ARMv7") != -1:
		XCPU = "arm"
	elif HardwareInfo().get_device_name() in ('one', 'two'):
		XCPU = "aarch64"
except: pass
def chckVersion(ff="ViX"):
	what = False
	try:
		for t in ["image-version", "issue", "bpversion"]:
			tt = "/etc/%s" % t
			if os.path.exists(tt):
				a = open(tt, "r").read()
				if a.find(ff) != -1:
					what = True
					break
	except: pass
	return what
isATV = chckVersion("openATV")
HDDTMP = "/media/hdd/hdg_tmp"
SEVENZIP = os.path.join(PLUGINPATH, "bin", "7z_g")
NO_TUN = _("No tuner data")
ER_F = _(" failed") + " !!!\n"
DSC = '/tmp/.doscam/doscam.version'
NCM = '/tmp/.ncam/ncam.version'
GCM = '/tmp/.gcam/gcam.version'
CHANSEL_FILE = "/usr/lib/enigma2/python/Screens/ChannelSelection.py"
KMP_FILE = "/usr/share/enigma2/keymap.xml"
USERXML = "/etc/enigma2/skin_user.xml"
USERHDG = "/etc/enigma2/skin_user-hdg17.xml"
USERORI = "/etc/enigma2/skin_user-ori17.xml"
SKINXML = "/usr/share/enigma2/hd_glass17/skin.xml"
SCREENSPATH = "/usr/lib/enigma2/python/Screens/"  
ENC_U = SHAREPATH + "encoding-user17.conf"
ENC_O = SHAREPATH + "encoding-ori17.conf"
ENC_C = SHAREPATH + "encoding.conf"
PYTHONPATH = "/usr/lib/enigma2/python/"
SKINALL = PLUGINPATH + "hdg17Screens.xml"
TM_P = "/tmp/tmp.tmp"
ISVTI = os.path.exists(PYTHONPATH + "Plugins/SystemPlugins/VTIPanel")
ECL = not os.path.exists(PYTHONPATH + "Plugins/Extensions/ClearMem")
EFIFO = os.path.isfile(SCREENSPATH + "ServiceScan.py")
MAXSCREENS = 100
IS800SE = 'dm800se' in HardwareInfo().get_device_name()
IS820 = 'dm820' in HardwareInfo().get_device_name()
MAXICONS = 31
POSTER = '<widget render="g17Poster" source="session.Event_Now" position="%s,%s" size="%s" backgroundColor="transparent" zPosition="0" transparent="0" />\n'
NETSPEED = '<ePixmap position="%s,%s" size="270,50" pixmap="hd_glass17/icons/netspeed.png" zPosition="7" alphatest="off" />\n<widget source="global.CurrentTime" render="g17ShowNetSpeed" position="%s,%s" size="190,50" zPosition="8" font="Regular2;26" noWrap="1" valign="center" halign="center" foregroundColor="yellow" backgroundColor="background" transparent="1"/>\n'
NETSPEEDT = '<widget source="global.CurrentTime" render="g17ShowNetSpeed" position="%s,%s" size="220,40" zPosition="8" font="Prive3;27" noWrap="1" valign="center" halign="right" backgroundColor="un353e575e" shadowColor="#1A58A6" shadowOffset="-1,-1" transparent="1"/>\n'
FCAID = ["4AF4","4B63","4B24","4B64","4A70","4AEA","4AE1","4AE0","4ABF","4AEE","4AFC","2710","5581","1010","1702","1722","1762","4AD0","4AD1","1EC0","44A0","4AB0"]
CLR = '\n..............\n..............'
ALL_CFG = [
		'Icons type','Bitrate','Address in ecm','Enabled Extra infobar','Enabled Enhanced infobar','Extra screen','Menu type','Second picon type','','Special info x-pos.',
		'Special info y-pos.','Special info type','Weather location','Standard Infobar type','OLED type','Bar background','Ecmline info type','Volume type','Channel sel. type','ECMline, btr, CPU/Mem, Fan color',
		'HDD wake up','Path to hdd','HDD state','Display nighttime icons','Full bitrate','CAID PIDs','Fade in/out','Fade speed','Fade in','Typewriting',    
		'User info type','Permanent user info','Act/next event','Neutrino','Bitrate limit','','','','','OLED off',    
		'Black/white','Audio type','','Style','Title color','EPG list font size','Mute transparency','Sat names only','Translation','Display CW0/1',
		'Volume x-pos.','Volume y-pos.','Font size event','EPG selection type','Ignore timeout','Animated Weather Icons','Net connect','Clearmem','Encoding-user','Empty icons in menu type icons',
		'','ChannelSel 2xOK','Anim in menu type icons','screensaver in radio mode','','Animated icons eWeather','Service scan long list','PIG type','MenuIcons','',
		'Weather nextCity','IconsWeather','Special info timeout','ECM refresh','Update','Text rolling','Delay text rolling','Special info extensions','CH. name type','Address','Provider','Temp/RPM','CPU/Mem','Temp.HDD',
		'Special info mainmenu','Weather units','Weather reloading time','Weather provider','','','wea-autoreconnect time','Show yesterday',
		'Warm color','Cold color','Fair color','Warm temperature','Cold temperature','Ewea city','','','Show astro(eWea)','D.icon CAM','D.icon type',
		'Number of tuners','Active tuner color','B. active tuner color','Standby tuner color','Missing tuner color','Desc. color','Desc. selected color','Ch. name selected color',
		'Recording tuner color','Recording and live tuner color','Recording icon','Bitrate color','ECM color','Chsel. name color','ECM labels color','ECM values color','Progressive detection',
		'TP type color','TP info color','Video resolution color','User def. path','Path to picons','Ch. num. calculating','Date format ext. infobar','Date color','Time color','Seconds color',
		'Date format others','Date format ch.sel.','Date format menu','Date format infobar','Ch. name color','Event now color','Event next color','Ign. leading 0','Hide missing and standby tuners','',
		'Path to satellites.xml','Remaining time in extra EPG','OpenWeatherMap more days forecast','HDG conf path','Service name font size','Service info font size','CH. line Height',
		'Ext. desc. font size','Warm temperature F','Cold temperature F','Ewea units','','Listbox Bigger','Listbox Big','Listbox Medium','Listbox Small',
		'Listbox Smaller','Weather anim. speed','Ewea anim. speed','Movieplayer infobar HDD state','Enable Animations','Picon Animation','Second Picon Animation','ECM line Animation',
		'Menu Icons Animation','Ch.sel Icons Animation','TP info/type Animation','Tuner info','Animated WeaInf Icons','WeaInf anim. speed','Weather type special','Weather type user',
		'Weather title type','Wea/ewea date color','Wea/ewea state color','Wea UV color','Wea wind color','','Reference separating char','Netatmo stations','Netatmo stations switch time','',		
		'Extra Screen Offset','10 days switch time','Ewea date format','Weather date format','D.icon tuner','Ign. leading 0 date','Bitratecalc.so','On/Off pixmap','Unknown CAID',
		'CI informations','ECM from current displayed channel','','','Show PID in ECM line','Show CHID in ECM line','Show poster','','Poster x-position','Poster y-position','Poster size',
		'Poster animation','Poster provider','Poster search delay','','Removing current Poster','VTi SplitScreen','Net Speed','Net speed x-position','Net speed y-position','','Net speed color',		
		'Progress bar background color','Progress bar foreground color','','','','','','','Progress bar pixmap','Hide SNR/AGC (Q/S) if value is 0','Movie Selection type',
		'IPTV Radio Detection','Net Speed type','Extended Number ZAP','Weather API-Key OpenWeatherMap','EventView type'
		]
ENA_ELFS = False                                                                
ENA_ELPLI = False
ENA_BH = False
ENA_PLI2 = False
try:
	for x in ["skin_default.xml","skin.xml","PLi-FullHD/skin.xml","PLi-FullHD/skin_templates.xml","Vu_HD_1080P/skin.xml"]:
		if os.path.isfile(SHAREPATH + x):
			r = open(SHAREPATH + x, "r").read()
			if r.find('name="EPGlistFont1"') != -1 or r.find('name="EPGList0"') != -1:
				ENA_ELFS = True
			if r.find('setEventItemFont="') != -1:
				ENA_ELPLI = True    			
			if r.find('type="BhAnalogic') != -1:
				ENA_BH = True 
			if "PLi-FullHD" in x and r.find('objectTypes="') != -1:
				ENA_PLI2 = True 
except: pass
if os.path.isfile(PYTHONPATH + "Plugins/SystemPlugins/OBH/__pycache__/") or os.path.isfile(PYTHONPATH + "Plugins/Satdreamgr/__init__.pyo") or os.path.isfile(PYTHONPATH + "Plugins/Extensions/OpenSPAPlug/__init__.pyo"):
	ENA_ELPLI = True
	ENA_PLI2 = True
ENA_LS = False
try:
	r = open(SKINXML, "r").read()
	if r.find('type="Smaller"') != -1 and r.find('type="Bigger"') != -1:
		ENA_LS = True
except: pass
ENA_SYM = True
if ISVTI:
	ENA_SYM = False
ENA_D = 'mipsel'
RSTCMD = ['killall', '-9', 'enigma2']
ENA_P_CH = False
ENA_I_T = False
if os.path.exists('/etc/dpkg'):
	RSTCMD = ['systemctl', 'restart', 'enigma2']
	ENA_D = 'debpkg'
	try:
		from Components.Renderer.g17TunersLabel import getTunerDesc
		ENA_I_T = True
	except: pass
else:
	try:
		ENA_Z = config.usage.show_event_progress_in_servicelist.value
		f = config.usage.show_event_progress_in_servicelist.value
		while (True):
			if "perc" in f:			
				ENA_P_CH = True 
				config.usage.show_event_progress_in_servicelist.value = ENA_Z
				break
			config.usage.show_event_progress_in_servicelist.handleKey(1)
			f = config.usage.show_event_progress_in_servicelist.value
			if ENA_Z == f:			
				break                                                                                                                                                                                                                                                                              
	except: pass 
ENA_Z = False
try:
	from enigma import eMediaDatabase
	ENA_Z = True                                                                                                                                                                                                                                                                               
except: pass                                                                                                                                                                                                                                                                                                             
ENA_ONOFF = False
if ENA_D == 'debpkg':
	try:
		from Components.config import ConfigBoolean
		if str(len(ConfigBoolean._onOffPixmaps)).isdigit():
			ENA_ONOFF = True                                                                                                                                                                                                                                                                               
	except: pass
else:
	ENA_ONOFF = True
colors = [("AutoColors",_("AutoColors")),("#ffffff",_("White")),("#dddddd",_("White")+"2"),("#00d100",_("Green")),("#00ff00",_("Green")+"2"),("#ff9c00",_("Orange")),("#ff8000",_("Orange")+"2"),("#ff6000",_("Orange")+"3"),("#ff3300",_("Red")),("#ff0000",_("Red")+"2"),("#dd0000",_("Red")+"3"),("#dd00ff",_("Purple")),("#99bad6",_("Gray")),("#777777",_("Gray")+"2"),("#cdcdcd",_("Gray")+"3"),("#707070",_("Gray")+"4"),("#404040",_("Gray")+"5"),("#138AEC",_("Blue")),("#0000ff",_("Blue")+"2"),("#6cbcf0",_("Blue")+"3"),("#0077ff",_("Blue")+"4"),("#00497F",_("Blue")+"5"),("#ffcc00",_("Yellow")),("#ecb100",_("Yellow")+"2"),("#FFED00",_("Yellow")+"3"),("#bab329",_("Yellow")+"4")]         
colors1 = [("None","None")]         
dFormat = [("D",_("Auto")),("%A %B %d, %Y",_("Type")+" 1"),("%A  %d.%B %Y",_("Type")+" 2"),("%A, %d %B %Y",_("Type")+" 3"),("%d.%m.%Y",_("Type")+" 4"),("%A, %d.%B %Y",_("Type")+" 5"),("%d.%B %Y",_("Type")+" 6"),("%Y %B %e, %A",_("Type")+" 7"),("%Y.%m.%d",_("Type")+" 8"),("%Y %B %e",_("Type")+" 9"),("%A  %e %B",_("Type")+" 10")]
b,m = readHWtype()
oledT = [("0",_("from image")),("1",_("G17 (Ch. Name)")),("2",_("Default")),("3",_("only Picon")),("4",_("only Time")),("23",_("only Time")+"2"),("5",_("VU+ (Ch. Name)")),("6",_("VU+ (Act. event)")),("7",_("VU+ (Ch. Name + Act. event)")),("8",_("G17 (Act. event)")),("9",_("G17 (Ch. Name + Act. event)")),("10",_("G17 (Top:Ch. Name, Bottom:Act. event)")),("11",_("G17 (Top:Ch. Name, Bottom:Snr and Agc)")),("12",_("VU+ Ultimo")),("13",_("Picon and Time")),("14",_("Default 2")),("15",_("VU+ Duo2 Snr,Agc")),("16",_("VU+ Duo2 Snr,Agc,RPM,Temp.")),("17",_("VU+ 4k Snr,Agc")),("18",_("Duo2 Snr,Agc,RPM,Temp. 2")),("19",_("Classical")),("20",_("with ZZPicon")),("21",_("Classical")+"2"),("22",_("with Picon 400x240"))]
if "Dream" in b:
	if "dm8" in m or "dm7020" in m:
		oledT = oledT[0:6]+oledT[9:13]+oledT[14:16]
	elif "dm9" in m:
		oledT = oledT[0:1]+oledT[20:24]	
	else:
		oledT = oledT[0:1]	
elif "Vu" in b or "Clark" in b:
	if "duo2" in m:
		oledT = oledT[0:1]+oledT[16:18]+oledT[19:20]
	elif "4k" in m or "et8500" in m:
		oledT = oledT[0:1]+oledT[18:19]+oledT[20:24]
	elif "timo" in m:
		oledT = oledT[0:1]+oledT[13:14]
	else:
		oledT = oledT[0:1]+oledT[6:9]
chsT = [("1",_("Glass17")),("3",_("Glass17(+next event)")),("4",_("with PIG(+next event)")),("6",_("Glass17(+next, date)")),("8",_("New style")),("7",_("New style")+" 2"),("9",_("New style with PIG")),("10",_("PIG(+next event,left)")),("11",_("PIG(+act,next,left)")),("12",_("Classical")),("14",_("Classical")+" 2"),("13",_("The Core 88")),("18",_("The Core 88")+" 2"),("15",_("PIG(+several event)")),("16",_("G17(+several event)")),("39",_("G17(+several event)")+" 2"),("42",_("G17(+several event)")+" 3"),("43",_("G17(+several event)")+" 4"),("17",_("New style(+several event)")),("21",_("PIG(+act,several,left)")),("25",_("PIG(+act,several,left)")+" 2"),("49",_("PIG(+act,several,left)")+" 3"),("2",_("with PIG")),("31",_("with PIG")+" 2"),("32",_("with PIG")+" 3"),("28",_("with PIG")+" 4"),("37",_("with PIG")+" 5"),("50",_("with PIG")+" 6"),("33",_("with Picon 400x240")),("34",_("with ZZPicon")),("35",_("Default")),("29",_("G17 events")),("30",_("G17 events")+" 2"),("38",_("G17 events")+" 3"),("41",_("G17 events")+" 4"),("44",_("G17 events")+" 5"),("45",_("G17 events")+" 6"),("53",_("Big Icons")+" 1"),("54",_("Big Icons")+" 2"),("51",_("Poster")),("52",_("Poster")+" 2")]
aall = [("23",_("PIG + PIP")+" 1"),("24",_("PIG + PIP")+" 2"),("40",_("PIG + PIP")+" 3"),("46",_("PIG + PIP")+" 4"),("47",_("PIG + PIP")+" 5"),("48",_("PIG + PIP")+" 6"),("27",_("PIP")+" 4"),("36",_("PIP")+" 5")]
if isATV or os.path.isfile(SHAREPATH + "PLi-FullHD/skin.xml") or os.path.isfile(PYTHONPATH + "Plugins/SystemPlugins/OBH/__pycache__/") or os.path.isfile(PYTHONPATH + "Plugins/Satdreamgr/__init__.pyo"):
	aall = [("a23",_("PIG + PIP")+" 1"),("a24",_("PIG + PIP")+" 2"),("a40",_("PIG + PIP")+" 3"),("a46",_("PIG + PIP")+" 4"),("a47",_("PIG + PIP")+" 5"),("a48",_("PIG + PIP")+" 6"),("a27",_("PIP")+" 4"),("a36",_("PIP")+" 5")]
for x in aall:
	chsT.append(x)
E2OK = False
# The legacy ChannelSelection 2xOK feature rewrites image-owned Python.
# Warder Evolution must never offer or activate that patch on OpenATV.
if not isATV and os.path.isfile(CHANSEL_FILE):
	try:
		cpu = open(CHANSEL_FILE, 'r').read()
		if cpu.find('self.closePiG()') == -1 and cpu.find('__close:') == -1:
			E2OK = True
	except: pass
try:
	config.EMC.skin_able.value = True
except: pass
################################################################################## 
config.plugins.setupGlass17.par1 = ConfigInteger(1, (1,MAXICONS)) # num of icons
config.plugins.setupGlass17.par2 = ConfigYesNo(default = False) # enable bitrate
config.plugins.setupGlass17.par3 = ConfigYesNo(default = True) # address enable in ecm
config.plugins.setupGlass17.par4 = ConfigYesNo(default = True) # ei enable
config.plugins.setupGlass17.par5 = ConfigSelection(default="1", choices = [("1",_("yes")),("0",_("no"))]) # enable enhanced infobar
config.plugins.setupGlass17.par6 = ConfigInteger(1, (1,MAXSCREENS)) # num of screen
config.plugins.setupGlass17.par7 = ConfigSelection(default="List", choices = [("Icons",_("Icons")),("Icons Right",_("Icons Right")),("List",_("List")),("with PIG",_("with PIG")),("List and Icon",_("List and Icon")),("Icons Bar",_("Icons Bar")),("simply PIG",_("simply PIG")),("PIG2",_("with PIG")+"2"),("PIG4",_("with PIG")+"4"),("Li2",_("List and Icon")+"2"),("Li3",_("List and Icon")+"3")]) # type menu
config.plugins.setupGlass17.par8 = ConfigSelection(default="0", choices = [("0",_("Sat and Prov")),("1",_("only Sat")),("2",_("only Prov")),("3",_("only Weather")),("4",_("Sat and Weather")),("5",_("Prov and Weather")),("6",_("Sat, Prov and Weather"))]) # second picon type
config.plugins.setupGlass17.par9 = ConfigYesNo(default = False) # used for button              
config.plugins.setupGlass17.par10 = ConfigInteger(960, (1,1920)) # x-position
config.plugins.setupGlass17.par11 = ConfigInteger(150, (1,1080)) # y-position
config.plugins.setupGlass17.par12 = ConfigSelection(default="n", choices = [("g",_("Glass17")),("i",_("InfoECM by Duri")),("n",_("None")),("w",_("Weather")),("a","Netatmo")]) # type Special info
config.plugins.setupGlass17.par14 = ConfigSelection(default="1", choices = [("1",_("Standard")),("2",_("Simple")),("4",_("Standard")+"2"),("5",_("Standard")+"3")]) # Standard Infobar type
config.plugins.setupGlass17.par15 = ConfigSelection(default="0", choices = oledT) # type of Oled
config.plugins.setupGlass17.par16 = ConfigYesNo(default = False) # enable bar background
config.plugins.setupGlass17.par17 = ConfigSelection(default="0", choices = [("0",_("Ecminfo only")),("1",_("Ecminfo and CAID")),("2",_("CAID and SID")),("3",_("SID only")),("4",_("CAID, SID, VPID"))]) # ECM line type
config.plugins.setupGlass17.par18 = ConfigSelection(default="1", choices = [("1",_("Glass17")),("2",_("Percentage")),("3",_("Colored gauge")),("4",_("Percentage")+"2"),("5",_("Glass17")+" (2)"),("6",_("Glass17")+" (3)")]) # volume type 
config.plugins.setupGlass17.par19 = ConfigSelection(default="35", choices = chsT) # channel selection type
config.plugins.setupGlass17.par20 = ConfigSelection(default="AutoColors", choices = colors) # color of bitrate and ecmline, CPU/Mem, Fan 
config.plugins.setupGlass17.par21 = ConfigYesNo(default = False) # HDD forced wake up      
config.plugins.setupGlass17.par22 = ConfigSelection(default="/dev/sda", choices = [("A",_("Auto")),("None",_("None")),("/dev/sda","sda"),("/dev/sdb","sdb"),("/dev/sdc","sdc"),("/dev/sdd","sdd"),("/dev/sde","sde"),("/dev/sdf","sdf")]) # path to hdd - dev
config.plugins.setupGlass17.par23 = ConfigYesNo(default = False) # enable HDD state
config.plugins.setupGlass17.par24 = ConfigYesNo(default = True) # display nighttime icons
config.plugins.setupGlass17.par25 = ConfigYesNo(default = False) # enable full bitrate info
config.plugins.setupGlass17.par26 = ConfigYesNo(default = False) # enable CAID PIDs
config.plugins.setupGlass17.par27 = ConfigYesNo(default = False) # enable fade in/out
config.plugins.setupGlass17.par28 = ConfigSelection(default="5", choices = [("1","1"),("2","2"),("3","3"),("4","4"),("5","5"),("6","6"),("7","7"),("8","8"),("9","9"),("10","10")]) # fade speed
config.plugins.setupGlass17.par29 = ConfigYesNo(default = False) # enable fade in
config.plugins.setupGlass17.par30 = ConfigYesNo(default = False) # enable typewriting 
config.plugins.setupGlass17.par31 = ConfigSelection(default="e", choices = [("s",_("System info")),("e",_("Event - extended description")),("e2",_("Event - extended description")+" 2"),("si",_("Side infobar")),("esi",_("Event and side infobar")),("en",_("Event - now and next")),("ensi",_("Event now/next and side infobar")),("w",_("Weather")),("n",_("None")),("a","Netatmo")]) # type user info
config.plugins.setupGlass17.par32 = ConfigYesNo(default = False) # enable permanent user info
config.plugins.setupGlass17.par33 = ConfigYesNo(default = False) # enable act/next event
config.plugins.setupGlass17.par34 = ConfigYesNo(default = False) # enable neutrino keymap
config.plugins.setupGlass17.par35 = ConfigSelection(default="9999999", choices = [("9999999",_("None")),("15000","15000"),("17500","17500"),("20000","20000"),("22500","22500"),("25000","25000"),("27500","27500"),("30000","30000"),("32500","32500"),("35000","35000"),("37500","37500"),("40000","40000")]) # bitrate autostop limit
config.plugins.setupGlass17.par36 = NoSave(ConfigText("", False)) # piconProv
config.plugins.setupGlass17.par37 = NoSave(ConfigText("", False)) # piconSat
config.plugins.setupGlass17.par38 = NoSave(ConfigText("", False)) # ecm
config.plugins.setupGlass17.par39 = NoSave(ConfigText("", False)) # temp path to picons
config.plugins.setupGlass17.par40 = ConfigYesNo(default = False) # enable OLED off in standby
config.plugins.setupGlass17.par41 = ConfigSelection(default="Black", choices = [("Black",_("Black")),("White",_("White"))]) # picon default, next, marker ...
config.plugins.setupGlass17.par42 = ConfigYesNo(default = True) # detect audio type
config.plugins.setupGlass17.par43 = NoSave(ConfigYesNo(default = True)) # used for setup watchdog
config.plugins.setupGlass17.par44 = ConfigInteger(1, (1,MAXICONS)) # num windowstyle
config.plugins.setupGlass17.par45 = ConfigText("#006cbcf0", False) # title color
chsT = [("0",_("Default"))]
for x in range(28,43):
	chsT.append((str(x),str(x)))
config.plugins.setupGlass17.par46 = ConfigSelection(default="0", choices = chsT) # font size list epg
config.plugins.setupGlass17.par47 = ConfigYesNo(default = True) # mute transparency
config.plugins.setupGlass17.par48 = ConfigYesNo(default = False) # enable only sat names
config.plugins.setupGlass17.par49 = ConfigYesNo(default = True) # enable translation
config.plugins.setupGlass17.par50 = ConfigYesNo(default = False) # enable CW
config.plugins.setupGlass17.par51 = ConfigInteger(1200, (1,1920)) # x-position                                             
config.plugins.setupGlass17.par52 = ConfigInteger(120, (1,1080)) # y-position
config.plugins.setupGlass17.par54 = ConfigSelection(default="7", choices = [("7",_("Default")),("2",_("Standard")),("8",_("Standard")+"2"),("3",_("with PIG")),("1",_("with PIG(+ch.name,number)")),("5",_("The Core 88")),("4",_("Classical")),("6",_("with PIG(+ch.name,number)")+"2"),("9",_("Poster"))]) # type EPG selection
config.plugins.setupGlass17.par55 = ConfigSelection(default="0", choices = [("1",_("yes")),("0",_("no")),("2",_("no time"))]) # ignore Timeout press OK
config.plugins.setupGlass17.par56 = ConfigYesNo(default = False) # animated weather
config.plugins.setupGlass17.par57 = ConfigSelection(default="3", choices = [("1",_("yes")),("2",_("no")),("3",_("with internet check"))]) # enable net connect source
config.plugins.setupGlass17.par58 = ConfigYesNo(default = False) # enable Clearmem fnc
config.plugins.setupGlass17.par59 = ConfigYesNo(default = False) # enable encoding-user.conf
config.plugins.setupGlass17.par60 = ConfigYesNo(default = False) # enable empty icons in menu type icons
config.plugins.setupGlass17.par61 = ConfigText("0", False) # used for ok option - ignore infobar timeout
config.plugins.setupGlass17.par62 = ConfigYesNo(default = False) # enable ChannelSel patch 2xOK
config.plugins.setupGlass17.par63 = ConfigYesNo(default = False) # enable anim for menu: Icons Bar
config.plugins.setupGlass17.par64 = ConfigYesNo(default = False) # enable screensaver in radio mode  
config.plugins.setupGlass17.par65 = NoSave(ConfigYesNo(default = False)) # retired spinner setting; compatibility placeholder only
config.plugins.setupGlass17.par66 = ConfigYesNo(default = False) # animated ewea
config.plugins.setupGlass17.par67 = ConfigYesNo(default = False) # service scan long list
config.plugins.setupGlass17.par68 = ConfigSelection(default="0", choices = [("0",_("with frame")),("1",_("big"))]) # PIG type
config.plugins.setupGlass17.par69 = ConfigInteger(1, (1,MAXICONS)) # num of menuIcons
config.plugins.setupGlass17.par70 = NoSave(ConfigYesNo(default = False)) # tuner type			
config.plugins.setupGlass17.par71 = ConfigYesNo(default = False) # weather: enable nextCity
config.plugins.setupGlass17.par72 = ConfigInteger(1, (1,MAXICONS)) # num of iconsWeather
config.plugins.setupGlass17.par73 = ConfigYesNo(default = False) # enable scpecial info timeout
config.plugins.setupGlass17.par74 = ConfigSelection(default="6", choices = [("2","2"),("3","3"),("4","4"),("6","6"),("8","8"),("10","10")]) # ecm refresh
config.plugins.setupGlass17.par75 = ConfigYesNo(default = True) # enable update
config.plugins.setupGlass17.par76 = ConfigSelection(default = "Autostop", choices = [("None",_("None")),("Autostop",_("Autostop")),("Roll back",_("Roll back"))]) # enable desc. rolling
config.plugins.setupGlass17.par77 = ConfigSelection(default="8", choices = [("default",_("Default")),("6","6"),("8","8"),("10","10"),("12","12"),("14","14"),("16","16"),("20","20")]) # start delay desc. rolling
config.plugins.setupGlass17.par78 = ConfigSelection(default="n", choices = [("g",_("Glass17")),("i",_("InfoECM by Duri")),("n",_("None")),("w",_("Weather")),("e",_("Enhanced Weather")),("a","Netatmo")]) # special info in extensions
config.plugins.setupGlass17.par79 = ConfigSelection(default="1", choices = [("2",_("Satellite")+", "+_("Name")),("3",_("Number")+", "+_("Satellite")+", "+_("Name")),("1",_("Number")+", "+_("Name")),("0",_("Name"))]) # enable channel num
config.plugins.setupGlass17.par80 = ConfigText("204.79.197.203", False) # internet address
config.plugins.setupGlass17.par81 = ConfigYesNo(default = True) # provider
config.plugins.setupGlass17.par82 = ConfigYesNo(default = False) # Temp/RPM
config.plugins.setupGlass17.par83 = ConfigYesNo(default = False) # CPU/Mem
config.plugins.setupGlass17.par84 = ConfigYesNo(default = False) # Temp.HDD
config.plugins.setupGlass17.par85 = ConfigYesNo(default = True) # special info main menu
config.plugins.setupGlass17.par86 = ConfigSelection(default="c", choices = [("0","(my_)city_Code"),("c",DG+"C"),("f",DG+"F")]) # weather units
config.plugins.setupGlass17.par87 = ConfigSelection(default="15", choices = [("5","5"),("10","10"),("15","15"),("20","20"),("25","25"),("30","30"),("45","45"),("60","60")]) # reloading time weather
config.plugins.setupGlass17.par88 = NoSave(ConfigSelection(default="OpenMeteo", choices = [("OpenMeteo","Open-Meteo")])) # compatibility placeholder; provider UI retired
config.plugins.setupGlass17.par89 = NoSave(ConfigText("", False)) # last city weather
config.plugins.setupGlass17.par90 = NoSave(ConfigSelection(default="c", choices = [("c"," ")])) # find city
config.plugins.setupGlass17.par91 = ConfigSelection(default="10", choices = [("0",_("disabled")),("5","5"),("10","10"),("15","15"),("20","20")]) # autoreconnect time
config.plugins.setupGlass17.par92 = ConfigYesNo(default = True) # show yesterday
config.plugins.setupGlass17.par93 = ConfigSelection(default="AutoColors", choices = colors) # warm color 
config.plugins.setupGlass17.par94 = ConfigSelection(default="AutoColors", choices = colors) # cold color 
config.plugins.setupGlass17.par95 = ConfigSelection(default="None", choices = colors1[:]+colors[1:]) # neutral color
config.plugins.setupGlass17.par96 = ConfigInteger(20, (15,40)) # warm temp c                                             
config.plugins.setupGlass17.par97 = ConfigInteger(1, (1,14)) # cold temp c
config.plugins.setupGlass17.par98 = ConfigText("cEUR|SK|LO001|BANSKA BYSTRICA|", False)
config.plugins.setupGlass17.par99 = NoSave(ConfigText("", False)) # eWea data
config.plugins.setupGlass17.par100 = NoSave(ConfigText("", False)) # last city eWea
config.plugins.setupGlass17.par102 = ConfigYesNo(default = True) # d.icon CAM
config.plugins.setupGlass17.par103 = ConfigYesNo(default = True) # d.icon type                                                                             
config.plugins.setupGlass17.par104 = ConfigSelection(default="0", choices = [("99",_("disabled")),("0",_("Auto")),("1","1"),("2","2"),("3","3"),("4","4"),("5","5"),("6","6"),("7","7"),("8","8"),("9","9"),("10","10"),("11","11"),("12","12"),("13","13"),("14","14"),("15","15"),("16","16"),("17","17"),("18","18"),("19","19")]) # number of tuners
config.plugins.setupGlass17.par105 = ConfigSelection(default="#00d100", choices = colors) # active tuner
config.plugins.setupGlass17.par106 = ConfigSelection(default="#ecb100", choices = colors) # B. active tuner
config.plugins.setupGlass17.par107 = ConfigSelection(default="#0077ff", choices = colors) # Standby tuner
config.plugins.setupGlass17.par108 = ConfigSelection(default="#777777", choices = colors) # Missing tuner
config.plugins.setupGlass17.par109 = ConfigSelection(default="#cdcdcd", choices = colors[1:]) # desc.
config.plugins.setupGlass17.par110 = ConfigSelection(default="#6cbcf0", choices = colors[1:]) # desc. selected
config.plugins.setupGlass17.par111 = ConfigSelection(default="#6cbcf0", choices = colors[1:]) # foreground selected
config.plugins.setupGlass17.par112 = ConfigSelection(default="#dd0000", choices = colors) # recording tuner
config.plugins.setupGlass17.par113 = ConfigSelection(default="#dd00ff", choices = colors) # recording and live tuner
config.plugins.setupGlass17.par114 = ConfigYesNo(default = True) # display recording icon
config.plugins.setupGlass17.par115 = ConfigSelection(default="AutoColors", choices = colors) # bitrate color
config.plugins.setupGlass17.par116 = ConfigSelection(default="AutoColors", choices = colors) # ecm color
config.plugins.setupGlass17.par117 = ConfigSelection(default="#dddddd", choices = colors[1:]) # channel name
config.plugins.setupGlass17.par118 = ConfigSelection(default="AutoColors", choices = colors) # ecm labels color
config.plugins.setupGlass17.par119 = ConfigSelection(default="AutoColors", choices = colors) # ecm values color
config.plugins.setupGlass17.par120 = ConfigYesNo(default = True) # enable progressive detect
config.plugins.setupGlass17.par121 = ConfigSelection(default="AutoColors", choices = colors) # TP_type color
config.plugins.setupGlass17.par122 = ConfigSelection(default="AutoColors", choices = colors) # TP_info color
config.plugins.setupGlass17.par123 = ConfigSelection(default="AutoColors", choices = colors) # VideoSize color
config.plugins.setupGlass17.par124 = ConfigDirectory("/media/usb/") # user path
config.plugins.setupGlass17.par125 = ConfigSelection(default="/media/usb", choices = [("/media/usb","/media/usb"),("/data","/data"),("/media/hdd","/media/hdd"),("/media/cf","/media/cf"),("/usr/share/enigma2","/usr/share/enigma2"),("/etc","/etc"),("0",_("User defined path"))]) # path to picons
config.plugins.setupGlass17.par126 = ConfigSelection(default="0", choices = [("0",_("Static")),("1",_("Dynamic"))]) # ch. num. calculating
config.plugins.setupGlass17.par127 = ConfigSelection(default="D", choices = dFormat) # date format extra infobar
config.plugins.setupGlass17.par128 = ConfigSelection(default="AutoColors", choices = colors) # date color
config.plugins.setupGlass17.par129 = ConfigSelection(default="AutoColors", choices = colors) # time color
config.plugins.setupGlass17.par130 = ConfigSelection(default="AutoColors", choices = colors) # seconds color
config.plugins.setupGlass17.par131 = ConfigSelection(default="D", choices = dFormat) # date format others 
config.plugins.setupGlass17.par132 = ConfigSelection(default="D", choices = dFormat) # date format ch.sel.
config.plugins.setupGlass17.par133 = ConfigSelection(default="D", choices = dFormat) # date format menu
config.plugins.setupGlass17.par134 = ConfigSelection(default="D", choices = dFormat) # date format infobar
config.plugins.setupGlass17.par135 = ConfigSelection(default="AutoColors", choices = colors) # ch. name color
config.plugins.setupGlass17.par136 = ConfigSelection(default="AutoColors", choices = colors) # event now color
config.plugins.setupGlass17.par137 = ConfigSelection(default="AutoColors", choices = colors) # event next color
config.plugins.setupGlass17.par138 = ConfigYesNo(default = True) # ignore leading 0 in hours
config.plugins.setupGlass17.par139 = ConfigYesNo(default = False) # hide standby and missing tuners
config.plugins.setupGlass17.par140 = NoSave(ConfigText("", False)) # hdd dev path
config.plugins.setupGlass17.par141 = ConfigDirectory("/etc/tuxbox/") # satxml path
config.plugins.setupGlass17.par142 = ConfigYesNo(default = True) # display remaining time in extra EPG
config.plugins.setupGlass17.par143 = ConfigYesNo(default = True) # openwea more days forecast
config.plugins.setupGlass17.par144 = ConfigDirectory(SKINPATH) # conf path
chsT = [("0",_("Default"))]
for x in range(24,54):
	chsT.append((str(x),str(x)))
config.plugins.setupGlass17.par53 = ConfigSelection(default="0", choices = chsT) # font size event next - now
config.plugins.setupGlass17.par145 = ConfigSelection(default="0", choices = chsT) #service name font size
config.plugins.setupGlass17.par146 = ConfigSelection(default="0", choices = chsT) #service info font size
config.plugins.setupGlass17.par148 = ConfigSelection(default="0", choices = chsT) #ext. desc. font size
config.plugins.setupGlass17.par153 = ConfigSelection(default="0", choices = chsT) # listbox - Bigger
config.plugins.setupGlass17.par154 = ConfigSelection(default="0", choices = chsT) # listbox - Big
config.plugins.setupGlass17.par155 = ConfigSelection(default="0", choices = chsT) # listbox - Medium
config.plugins.setupGlass17.par156 = ConfigSelection(default="0", choices = chsT) # listbox - Small
config.plugins.setupGlass17.par157 = ConfigSelection(default="0", choices = chsT) # listbox - Smaller
chsT = [("0",_("Default"))]
chsT.append(("1",_("Auto")))
for x in range(26,64):
	chsT.append((str(x),str(x)))
config.plugins.setupGlass17.par147 = ConfigSelection(default="0", choices = chsT) #Ch. line Height
config.plugins.setupGlass17.par149 = ConfigInteger(68, (58,104)) # warm temp f                                             
config.plugins.setupGlass17.par150 = ConfigInteger(33, (33,57)) # cold temp f
config.plugins.setupGlass17.par151 = ConfigSelection(default="c", choices = [("0","ewea_city_Code"),("c",DG+"C"),("f",DG+"F")]) # ewea units
config.plugins.setupGlass17.par152 = NoSave(ConfigText("gg", False)) # wea/ewea units
config.plugins.setupGlass17.par158 = ConfigInteger(50, (20,500)) # weather anim. speed
config.plugins.setupGlass17.par159 = ConfigInteger(50, (20,500)) # ewea anim. speed
config.plugins.setupGlass17.par160 = ConfigYesNo(default = True) # moviepl. inf. HDD state
config.plugins.setupGlass17.par161 = ConfigYesNo(default = True) # enable Animations
chsT = [("None",_("None"))]
for x in range(1,16):
	chsT.append(("g17_Anim_"+str(x),_("Animation")+str(x)))
config.plugins.setupGlass17.par162 = ConfigSelection(default = "g17_Anim_1", choices = chsT) # picon
config.plugins.setupGlass17.par163 = ConfigSelection(default = "None", choices = chsT) # second picon
config.plugins.setupGlass17.par164 = ConfigSelection(default = "None", choices = chsT) # ecm line
config.plugins.setupGlass17.par165 = ConfigSelection(default = "None", choices = chsT) # menu icons
config.plugins.setupGlass17.par166 = ConfigSelection(default = "None", choices = chsT) # ch. sel. picon
config.plugins.setupGlass17.par167 = ConfigSelection(default = "None", choices = chsT) # tp info,type
config.plugins.setupGlass17.par203 = ConfigSelection(default = "None", choices = chsT) # poster
config.plugins.setupGlass17.par168 = ConfigSelection(default="T", choices = [("T",_("Transponder data")),("F",_("Real tuner data"))]) # tuner info
config.plugins.setupGlass17.par169 = ConfigYesNo(default = False) # animated weainf
config.plugins.setupGlass17.par170 = ConfigInteger(50, (20,500)) # weainf anim. speed
chsT = []
for x in range(1,13):
	chsT.append((str(x),str(x)))
config.plugins.setupGlass17.par171 = ConfigSelection(default = "3", choices = chsT) # wea type - special
a = []
a = chsT[0:2]
a.append(chsT[6])
a.append(chsT[7])
config.plugins.setupGlass17.par172 = ConfigSelection(default = "1", choices = a) # wea type - user
config.plugins.setupGlass17.par173 = ConfigSelection(default = "d", choices = [("d",_("Default")),("s","1")]) # wea title type
config.plugins.setupGlass17.par174 = ConfigSelection(default="AutoColors", choices = colors) # wea/ewea date color
config.plugins.setupGlass17.par175 = ConfigSelection(default="AutoColors", choices = colors) # wea/ewea state color
config.plugins.setupGlass17.par176 = ConfigSelection(default="AutoColors", choices = colors) # ewea uv color
config.plugins.setupGlass17.par177 = ConfigSelection(default="AutoColors", choices = colors) # ewea wind color
config.plugins.setupGlass17.par178 = NoSave(ConfigText("", False)) # ecm type
config.plugins.setupGlass17.par179 = ConfigSelection(default = "a", choices = [("a","_"),("b",":")]) # reference separator
config.plugins.setupGlass17.par180 = ConfigSelection(default = "a", choices = [("a",_("All available")),("b",_("Selected in Netatmo plugin"))]) # netatmo stations 
config.plugins.setupGlass17.par181 = ConfigSelection(default = "10", choices = [("5","5"),("10","10"),("15","15"),("20","20"),("30","30")]) # netatmo stations switch time
config.plugins.setupGlass17.par182 = NoSave(ConfigText("HDD", False)) # hdd type
config.plugins.setupGlass17.par183 = ConfigSelection(default = "0", choices = [("-30","-30"),("-25","-25"),("-20","-20"),("-15","-15"),("-10","-10"),("-5","-5"),("0","0"),("5","+5"),("10","+10"),("15","+15"),("20","+20"),("25","+25"),("30","+30")]) # extra screen offset
config.plugins.setupGlass17.par184 = ConfigSelection(default = "10", choices = [("5","5"),("10","10"),("15","15"),("20","20"),("30","30")]) # 10 days switch time
config.plugins.setupGlass17.par185 = ConfigSelection(default = "%A %d.%m.%Y", choices = [("%A %d.%m.%Y",_("Default")),("%A %Y.%m.%d",_("Type")+" 1"),("%d.%m.%Y",_("Type")+" 2"),("%Y.%m.%d",_("Type")+" 3"),("%Y %m %d",_("Type")+" 4"),("%d %m %Y",_("Type")+" 5"),("%d.%m.%Y %A",_("Type")+" 6"),("%Y.%m.%d %A",_("Type")+" 7"),("%d %m %Y %A",_("Type")+" 8"),("%Y %m %d %A",_("Type")+" 9"),("%A  %d %B",_("Type")+" 10")]) # ewea date format
config.plugins.setupGlass17.par186 = ConfigSelection(default = "%A  %d %B %Y", choices = [("%A  %d %B %Y",_("Default")),("%A %B %d, %Y",_("Type")+" 1"),("%A  %d.%B %Y",_("Type")+" 2"),("%d.%m.%Y",_("Type")+" 3"),("%d.%B %Y",_("Type")+" 4"),("%Y %B %d %A",_("Type")+" 5"),("%Y.%m.%d",_("Type")+" 6"),("%Y %B %d",_("Type")+" 7"),("%A  %d %B",_("Type")+" 8")]) # wea date format
config.plugins.setupGlass17.par187 = ConfigYesNo(default = True) # D.icon tuner
config.plugins.setupGlass17.par188 = ConfigYesNo(default = True) # ignore leading 0 in date
config.plugins.setupGlass17.par189 = ConfigYesNo(default = True) # enable bitratecalc.so
config.plugins.setupGlass17.par190 = ConfigYesNo(default = True) # enable on/off pixmap
config.plugins.setupGlass17.par191 = ConfigYesNo(default = True) # enable detection of Unknown CAID
config.plugins.setupGlass17.par192 = ConfigYesNo(default = True) # CI informations
config.plugins.setupGlass17.par193 = ConfigYesNo(default = True) # display ECM from current displayed channel only
config.plugins.setupGlass17.par194 = NoSave(ConfigText("", False)) # cw0/1
config.plugins.setupGlass17.par195 = NoSave(ConfigText("", False)) # chid,provider,provid 
config.plugins.setupGlass17.par196 = ConfigYesNo(default = True) # Show PID in ECM line
config.plugins.setupGlass17.par197 = ConfigYesNo(default = True) # Show CHID in ECM line
config.plugins.setupGlass17.par198 = ConfigYesNo(default = False) # Show poster
config.plugins.setupGlass17.par199 = NoSave(ConfigSelection(default="c", choices = [("c"," ")])) # set pos poster
config.plugins.setupGlass17.par200 = ConfigInteger(900, (1,1920)) # x-position poster                                             
config.plugins.setupGlass17.par201 = ConfigInteger(400, (1,1080)) # y-position poster
config.plugins.setupGlass17.par202 = ConfigSelection(default = "185,278", choices = [("185,278",_("Default")),("220,330","*1.19"),("231,347","*1.25"),("277,417","*1.5"),("324,487","*1.75"),("370,556","*2")]) #  poster size
# 203 used as anim poster
config.plugins.setupGlass17.par204 = ConfigSelection(default="a", choices = [("a",_("Auto")),("i",_("IMDb")),("m",_("TMDb"))]) # poster provider
config.plugins.setupGlass17.par205 = ConfigSelection(default="3", choices = [("1","1"),("2","2"),("3","3"),("4","4"),("5","5"),("6","6"),("7","7"),("8","8"),("9","9"),("10","10")]) # poster search delay
config.plugins.setupGlass17.par206 = NoSave(ConfigSelection(default="c", choices = [("c"," ")])) # clean chache posters
config.plugins.setupGlass17.par207 = ConfigYesNo(default = True) # Removing current Poster
config.plugins.setupGlass17.par208 = ConfigSelection(default="1", choices = [("1",_("Default")),("2","50:50"),("3","50:50 2")]) # VTi SplitScreen
config.plugins.setupGlass17.par209 = ConfigSelection(default="0", choices = [("0",_("disabled")),("1","kb/s"),("2","Mb/s")]) # Net speed 
config.plugins.setupGlass17.par210 = ConfigInteger(1000, (1,1920)) # x-position Net speed                                             
config.plugins.setupGlass17.par211 = ConfigInteger(100, (1,1080)) # y-position Net speed
config.plugins.setupGlass17.par212 = NoSave(ConfigSelection(default="c", choices = [("c"," ")])) # set pos Net speed
config.plugins.setupGlass17.par213 = ConfigSelection(default="AutoColors", choices = colors) # Net speed color
config.plugins.setupGlass17.par214 = ConfigSelection(default="AutoColors", choices = colors) # Progress bar foreground color
config.plugins.setupGlass17.par215 = ConfigSelection(default="AutoColors", choices = colors) # Progress bar background color
config.plugins.setupGlass17.par216 = NoSave(ConfigSelection(default="c", choices = [("c"," ")])) # set pos volume
config.plugins.setupGlass17.par217 = NoSave(ConfigSelection(default="c", choices = [("c"," ")])) # set pos spec. info
config.plugins.setupGlass17.par218 = NoSave(ConfigSelection(default="c", choices = [("c"," ")])) # infobar type
config.plugins.setupGlass17.par219 = NoSave(ConfigSelection(default="c", choices = [("c"," ")])) # icons type
config.plugins.setupGlass17.par220 = NoSave(ConfigSelection(default="c", choices = [("c"," ")])) # weather icons
config.plugins.setupGlass17.par221 = NoSave(ConfigSelection(default="c", choices = [("c"," ")])) # menu icons
config.plugins.setupGlass17.par222 = ConfigYesNo(default = True) # Progress bar pixmap
config.plugins.setupGlass17.par223 = ConfigYesNo(default = False) # Hide SNR/AGC (Q/S) if value is 0
config.plugins.setupGlass17.par224 = ConfigSelection(default="1", choices = [("1",_("Default")),("2",_("Classical")),("3",_("The Core 88"))]) # movie sel type
config.plugins.setupGlass17.par225 = ConfigYesNo(default = True) # IPTV Radio Detection
config.plugins.setupGlass17.par226 = ConfigSelection(default="1", choices = [("1",_("Default")),("2",_("Transparent"))]) # Net Speed type
config.plugins.setupGlass17.par227 = ConfigSelection(default="5", choices = [("5",_("Default")),("7",_("Default")+" 2"),("0",_("Auto")),("1","150x90"),("2","220x132"),("6","220x132 (2)"),("3","400x170"),("4","400x240")]) # Extended Number ZAP Picon Size
config.plugins.setupGlass17.par228 = ConfigText(default="-", fixed_size=False, visible_width=50)
config.plugins.setupGlass17.par229 = ConfigSelection(default="1", choices = [("1",_("Default")),("2",_("Poster"))]) # EventView
config.plugins.setupGlass17.par101 = ConfigYesNo(default = True) # 
##########################################################################################################################
ENA_MSN = chMSN()
ECM_LABELS, CLRDATA, CLRTP = readECMlabels()
       
def _cityLine(line):
	line = (line or "").strip()
	if not line or line.startswith("#"):
		return None
	if line.startswith("om|"):
		p = line.split("|")
		if len(p) >= 4 and p[1] and p[2] and p[3]:
			display = p[1]
			query = "|".join((p + ["", ""])[2:6])
			return ("om|" + query, display, line)
	tmp = line.split("-")
	def ch(w):
		return w.isdigit() or w.startswith("wc:") or w.startswith("fr:")
	if len(tmp) == 2 and ch(tmp[1]):
		return ("c" + tmp[1], tmp[0], line)
	if len(tmp) == 3 and ch(tmp[1]) and tmp[2].lower() in ("c", "f"):
		return (tmp[2].lower() + tmp[1], tmp[0], line)
	return None

def _citySearchKey(value):
	try:
		value = unicodedata.normalize("NFKD", str(value))
		value = "".join(ch for ch in value if not unicodedata.combining(ch))
	except Exception:
		value = str(value)
	return value.casefold().strip()

def getCitiesCode():
	choicelist = []
	fileName = "/etc/my_city_Code.txt"
	if not os.path.isfile(fileName):
		fileName = "/etc/city_Code-17.txt" if os.path.isfile("/etc/city_Code-17.txt") else "/etc/city_Code.txt"
	try:
		with open(fileName, "r") as f:
			for line in f:
				x = _cityLine(line)
				if x:
					name = x[1]
					if not ISP38:
						name = name.encode("utf-8")
					choicelist.append((x[0], name))
	except Exception:
		pass
	if not choicelist:
		choicelist.append(("None", "None"))
	return choicelist

ch_help = getCitiesCode()
config.plugins.setupGlass17.par13 = ConfigSelection(default=ch_help[0][0], choices = ch_help) # weather location

def _setWeatherCityChoices(selected=None):
	"""Reload /etc/my_city_Code.txt while preserving or explicitly selecting a city."""
	choices = getCitiesCode()
	values = [x[0] for x in choices]
	wanted = selected if selected in values else config.plugins.setupGlass17.par13.value
	if wanted not in values:
		wanted = choices[0][0]
	try:
		config.plugins.setupGlass17.par13.setChoices(choices, default=wanted)
	except Exception:
		config.plugins.setupGlass17.par13 = ConfigSelection(default=wanted, choices=choices)
	config.plugins.setupGlass17.par13.value = wanted
	return wanted

def _refreshLiveWeather():
	"""Push a city change to the active Infobar without restarting Enigma2."""
	try:
		if G17_EXTRAINFO_INSTANCE is not None:
			G17_EXTRAINFO_INSTANCE.refreshWeatherNow()
	except Exception as e:
		Writelog("weather live refresh: %s" % e)

def readAPIkey():
	# Compatibility shim only. Open-Meteo requires no API key and the legacy
	# OpenWeatherMap key must not affect the Warder weather path.
	return True

ch_help = readAPIkey()
	
def chckBtr():
	try:
		from Plugins.Extensions.BitrateViewer.bitratecalc import eBitrateCalculator
		if not fileExists(PYTHONPATH+"Plugins/Extensions/BitrateViewer/bitratecalc.la") or ENA_D == 'debpkg':
			return True
	except: pass
	return False
ENAEBTR = config.plugins.setupGlass17.par189.value and chckBtr()
ENAEBTR2 = False
if ENAEBTR:
	try:
		from Plugins.Extensions.BitrateViewer.bitratecalc import eBitrateCalculator
		f = open(PYTHONPATH + "Plugins/Extensions/BitrateViewer/plugin.py","r").read()
		if f.find("eBitrateCalculator(vpid, dvbnamespace") != -1: 
			ENAEBTR2 = True
	except: pass

del dFormat
del colors1
del ch_help
del b
del m
del oledT
del chsT

def spinnerOnOff():
	"""Retire the legacy FullHDGlass spinner override.

	The skin no longer replaces the image-provided spinner.  Keep this helper
	only as an upgrade compatibility repair for installations where an older
	FullHDGlass version left its symlink behind.
	"""
	spinner = os.path.join(SHAREPATH, "skin_default", "spinner")
	original = os.path.join(SHAREPATH, "skin_default", "spinner-ori")
	legacy = os.path.join(SHAREPATH, "hd_glass17", "skin_default", "spinner")
	if not os.path.islink(spinner):
		return ""
	try:
		target = os.path.realpath(spinner)
		if target != os.path.realpath(legacy):
			return ""
		# Never remove the legacy symlink unless the saved image spinner is
		# actually available to restore in the same operation.
		if not os.path.isdir(original):
			return _("System spinner restore failed") + "\n"
		os.unlink(spinner)
		os.rename(original, spinner)
		return _("System spinner restored") + "\n"
	except OSError:
		return _("System spinner restore failed") + "\n"
					
def autoHdd():
	if config.plugins.setupGlass17.par22.value == "A":
		try:
			cpu = open("/proc/mounts", "r").readlines()	
			for x in cpu:
				if x.find("/media/hdd") != -1 and not "." in x and not ":" in x:
					b = (((x.split("/media/hdd")[0]).strip()).split("/dev/")[1]).strip()[:3]  
					if len(b) == 3:
						if b.startswith("sd"):
							return "/dev/"+b
						elif b == "dis":
							b = (((((x.split("/media/hdd")[0]).strip()).split("/dev/disk/")[1]).strip()).split(" ")[0]).strip()
							try:
								blkid_output = subprocess.check_output(["blkid"], universal_newlines=True)
							except (OSError, subprocess.CalledProcessError):
								blkid_output = ""
							for i in blkid_output.splitlines():
								if i.find(b) != -1:
									b = (((i.split(":")[0]).strip()).split("/dev/")[1]).strip()[:3]
									if len(b) == 3 and b.startswith("sd"):
										break
							if len(b) == 3 and b.startswith("sd"):
								return "/dev/"+b
		except: pass   	
		return "None"
	return config.plugins.setupGlass17.par22.value
config.plugins.setupGlass17.par140.value = autoHdd()        	

def autoTypeHdd():
	tmp = config.plugins.setupGlass17.par140.value
	if "/dev/sd" in tmp:	
		try:
			tmp = open('/sys/block%s/queue/rotational' % tmp.replace("/dev","")).readline()
			if "0" in tmp:
				return "SSD"								
		except: pass
	return "HDD"
config.plugins.setupGlass17.par182.value = autoTypeHdd()
####################################################
def setPathFiles(chck=True):
	def makelnk(link_path):
		target = os.path.join(config.plugins.setupGlass17.par39.value, "picon")
		try:
			if not os.path.lexists(link_path):
				os.symlink(target, link_path)
		except OSError:
			pass
	if config.skin.primary_skin.value == "hd_glass17/skin.xml":
		if config.plugins.setupGlass17.par125.value == "0":
			config.plugins.setupGlass17.par39.value = config.plugins.setupGlass17.par124.value + "hdg17_files"
		else:
			config.plugins.setupGlass17.par39.value = config.plugins.setupGlass17.par125.value + "/hdg17_files"
		if chck and ENA_SYM:
			# Warder may manage its legacy root/removable-media convenience links,
			# but /usr/share/enigma2 is image/package-manager owned on OpenATV.
			# Never create, replace or retarget picon links there.
			links = ["/picon"]
			if ENA_D != 'debpkg':
				links.append("/media/usb/picon")
			for x in ("/picons/piconHD", "/picons/piconlcd"):
				# Never replace a real image/user directory. Only manage symlinks.
				if os.path.islink(x):
					links.append(x)
			for x in links:
				if os.path.islink(x):
					a = os.readlink(x)
					if config.plugins.setupGlass17.par39.value not in a and ("/hdg17_files" in a or "/hdg18_files" in a):
						try:
							os.unlink(x)
						except OSError:
							continue
						makelnk(x)
				elif not os.path.lexists(x):
					makelnk(x)
setPathFiles()
ENAFINDER = False
try:
	if ISP38:
		from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor
		from urllib.error import URLError, HTTPError
		import http.cookiejar as cookielib
	else:
		from urllib2 import Request, urlopen, URLError, HTTPError, build_opener, HTTPCookieProcessor
		import cookielib
	ENAFINDER = True
except: pass
Glass17__init__ = None
_warderOriginalShowRadioButton = None                          
FirstRun17 = False
enaFadeOut17 = True
enaFadeIn17 = True
transStep17 = 20
allSat = {}
allIcons = [
				"betecm-fs8", "betemm-fs8", "dreecm-fs8", "dreemm-fs8", "emunew-fs8", "ftanew-fs8", "ci1new-fs8",
				"bisecm-fs8", "bisemm-fs8", "i_dolby_now", "i_dolbyw", "i_format_now","rosecm-fs8", "rosemm-fs8",
				"bulecm-fs8", "bulemm-fs8", "i_formats", "i_formatw", "i_hdw", "i_rec-n", "xcrecm-fs8", "mdcemm-fs8",
				"conecm-fs8", "conemm-fs8", "i_sdw", "i_subw", "i_txt_now", "i_txtw", "i_subtit", "tvkecm-fs8",
				"crdnew-fs8", "crwecm-fs8", "icon_aw", "icon_a1w", "icon_a2w", "icon_bw", "i_hbb", "tvkemm-fs8",
				"sececm-fs8", "secemm-fs8", "viaecm-fs8", "viaemm-fs8", "verecm-fs8", "veremm-fs8", "ci2new-fs8",
				"icon_mw", "icon_nw", "icon_dw", "icon_ow", "icon_pw", "irdecm-fs8", "cdcecm-fs8", "cdcemm-fs8",
				"icon_a3w", "icon_a4w", "icon_a5w", "icon_b3w", "icon_b4w", "icon_a6w", "icon_a7w", "redemm-fs8",
				"icon_a8w", "icon_b5w", "icon_b6w", "icon_b7w", "icon_b8w", "digecm-fs8", "digemm-fs8", "mdcecm-fs8", 
				"irdemm-fs8", "nagecm-fs8", "nagemm-fs8", "ndsecm-fs8", "ndsemm-fs8", "netnew-fs8", "redecm-fs8",
				"crwemm-fs8", "drcecm-fs8", "drcemm-fs8", "icon_b1w", "icon_b2w", "icon_cw", "i_audiow", "croecm-fs8",
				"Gbox-fs8", "Mgcamd-fs8", "CCcam-fs8", "OScam-fs8", "Camd3-fs8", "Mbox-fs8", "xcremm-fs8", "croemm-fs8",
				"active", "no_hdd", "standby", "dgcecm-fs8", "dgcemm-fs8", "3g", "wifi", "eth", "error",
				"unk", "pncecm-fs8", "pncemm-fs8", "exsecm-fs8", "exsemm-fs8", "Scam-fs8", "Wicardd-fs8",
				"gfnecm-fs8", "gfnemm-fs8", "pwuecm-fs8", "pwuemm-fs8", "i_fhd", "i_uhd", "icon_ew", "icon_fw", "icon_gw",
				"icon_hw", "icon_iw", "icon_jw", "icon_kw", "icon_lw", "tanecm-fs8", "tanemm-fs8", "unk-ca",					
				"dd2", "dd5", "aac", "dts", "mpg", "Ncam-fs8", "ccwecm-fs8", "icon_qw", "icon_rw", "icon_sw", "Gcam-fs8", 
				"hdr", "hlg", "DOScam-fs8", "4k", "8k", "active_s", "no_hdd_s", "standby_s", "crgecm-fs8", "crgemm-fs8",
				"skpecm-fs8", "skpemm-fs8"
			]		
##########################################################################################################################
def chckEnaWea():
	return config.plugins.setupGlass17.par8.value in ("3","4","5","6") or "w" in config.plugins.setupGlass17.par78.value or "w" in config.plugins.setupGlass17.par12.value or "w" in config.plugins.setupGlass17.par31.value

def startSetup17(menuid, **kwargs):
	ret = [ ]
	if config.skin.primary_skin.value == "hd_glass17/skin.xml":
		if menuid == "mainmenu":
			if config.plugins.setupGlass17.par78.value != "n" and config.plugins.setupGlass17.par85.value:
				ret.append((config.plugins.setupGlass17.par78.getText()+" (FullHDGlass)", main17, str(config.plugins.setupGlass17.par78.value), 44))
	return ret
	
def Plugins(path, **kwargs):
	ret = [ ]
	if config.skin.primary_skin.value == "hd_glass17/skin.xml":
		ret = [ PluginDescriptor(name=ui_text("FullHDGlass configuration"), description=ui_text("Configure the FullHDGlass skin"), where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main, icon="images/warder-config.png"),
				PluginDescriptor(where=PluginDescriptor.WHERE_MENU, fnc=startSetup17),
							PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=startHdg17)]
		if config.plugins.setupGlass17.par78.value != "n":
			ret.append(PluginDescriptor(name=config.plugins.setupGlass17.par78.getText()+" (FullHDGlass)",where = PluginDescriptor.WHERE_EXTENSIONSMENU,fnc = main17))
	return ret

def main17(session,**kwargs):
	if config.plugins.setupGlass17.par78.value == "g":
		session.open(SpecialScreen)
	elif config.plugins.setupGlass17.par78.value == "i":
		from Plugins.Extensions.setupGlass17.infoEcm_by_duri import InfoEcmScreen
		session.open(InfoEcmScreen)		
	elif "w" in config.plugins.setupGlass17.par78.value:
		from Plugins.Extensions.setupGlass17.weather import WeatherScreen
		session.open(WeatherScreen, config.plugins.setupGlass17.par171.value)
	elif config.plugins.setupGlass17.par78.value == "e":
		from Plugins.Extensions.setupGlass17.E_weather import mainmenu
		session.open(mainmenu)
	elif config.plugins.setupGlass17.par78.value == "a":
		from Plugins.Extensions.setupGlass17.Netatmo import NetatmoScreen
		session.open(NetatmoScreen)	
        	
def main(session,**kwargs):
	ch_help = getCitiesCode()
	config.plugins.setupGlass17.par13 = ConfigSelection(default=ch_help[0][0], choices = ch_help)
	ch_help = readAPIkey()
	session.open(setupGlass17ScreenSetup)
##########################################################################################################################		
class ColorLabel(Label):
	def __init__(self, text=""):
		Label.__init__(self, text)

	def colorX(self,a):
		if self.instance:
			if a != "AutoColors":
				self.instance.setForegroundColor(parseColor(a)) 

	def color1(self,a):
		if self.instance:
			if a == "AutoColors":
				self.instance.setForegroundColor(parseColor(colors[1][0])) # white
			else:
				self.instance.setForegroundColor(parseColor(a))			

	def color2(self,a):
		if self.instance:
			if a == "AutoColors":
				self.instance.setForegroundColor(parseColor(colors[3][0]))	#  green
			else:
				self.instance.setForegroundColor(parseColor(a))

	def color3(self,a):
		if self.instance:
			if a == "AutoColors":
				self.instance.setForegroundColor(parseColor(colors[5][0])) # orange
			else:
				self.instance.setForegroundColor(parseColor(a))
			
	def color4(self,a):
		if self.instance:
			if a == "AutoColors":
				self.instance.setForegroundColor(parseColor(colors[8][0])) #  red
			else:
				self.instance.setForegroundColor(parseColor(a))

	def color5(self,a):
		if self.instance:
			if a == "AutoColors":
				self.instance.setForegroundColor(parseColor(colors[12][0])) #  gray
			else:
				self.instance.setForegroundColor(parseColor(a))
				
	def color6(self,a):
		if self.instance:
			if a == "AutoColors":
				self.instance.setForegroundColor(parseColor(colors[17][0])) #  blue	
			else:
				self.instance.setForegroundColor(parseColor(a))					

	def color7(self,a):
		if self.instance:
			if a == "AutoColors":
				self.instance.setForegroundColor(parseColor(colors[22][0])) #  yellow
			else:
				self.instance.setForegroundColor(parseColor(a))

def chckPMS():
	p = SCREENSPATH + "Menu"	
	w = False
	for x in ['.pyc','.pyo']:
		if fileExists(p + x) and fileExists(p + "-new17" + x):
			if os.path.getsize(p + x) != os.path.getsize(p + "-new17" + x):
				w = True
	return w
##########################################################################################################################
# Warder GraphicalEPGPIG title suppression. OpenATV sets the current bouquet via
# Screen.setTitle(), which is rendered by the desktop window decoration outside
# the skin screen. Keep the override scoped to our PIG graphical guide only.
WarderEPGSelection_setTitle = None
try:
	from Screens.EpgSelection import EPGSelection as WarderEPGSelection
	WarderEPGSelection_setTitle = WarderEPGSelection.setTitle
	def warderEPGSelectionSetTitle(self, title, *args, **kwargs):
		if config.skin.primary_skin.value == "hd_glass17/skin.xml" and getattr(self, "skinName", None) == "GraphicalEPGPIG":
			title = ""
		return WarderEPGSelection_setTitle(self, title, *args, **kwargs)
	WarderEPGSelection.setTitle = warderEPGSelectionSetTitle
	def _warderGraphicalEPGPIG(self):
		return config.skin.primary_skin.value == "hd_glass17/skin.xml" and getattr(self, "skinName", None) == "GraphicalEPGPIG"

	def _warderGraphicalEPGLabels(self):
		if not _warderGraphicalEPGPIG(self):
			return
		for key, text in (("warder_key_red", _warderUiText("PROGRAM INFO")), ("warder_key_green", _warderUiText("Add Timer")), ("warder_key_yellow", _warderUiText("Goto Date/Time")), ("warder_key_blue", _warderUiText("EPG Search"))):
			try:
				self[key].setText(text)
			except Exception:
				pass

	WarderEPGSelection_init = WarderEPGSelection.__init__
	def warderEPGSelectionInit(self, *args, **kwargs):
		WarderEPGSelection_init(self, *args, **kwargs)
		if _warderGraphicalEPGPIG(self):
			for key in ("warder_key_red", "warder_key_green", "warder_key_yellow", "warder_key_blue"):
				self[key] = StaticText("")
		_warderGraphicalEPGLabels(self)
	WarderEPGSelection.__init__ = warderEPGSelectionInit

	# OpenATV refreshes StaticText colour-key sources after construction. Re-apply
	# the FullHDGlass labels afterwards so the visible label always matches the handler.
	WarderEPGSelection_RefreshColouredKeys = WarderEPGSelection.RefreshColouredKeys
	def warderEPGSelectionRefreshColouredKeys(self, *args, **kwargs):
		result = WarderEPGSelection_RefreshColouredKeys(self, *args, **kwargs)
		_warderGraphicalEPGLabels(self)
		return result
	WarderEPGSelection.RefreshColouredKeys = warderEPGSelectionRefreshColouredKeys

	WarderEPGSelection_redButtonPressed = WarderEPGSelection.redButtonPressed
	def warderProgramInfoClosed(self, action=None):
		self._warderProgramInfoOpen = False
		if action == "green": return self.RecordTimerQuestion(True)
		if action == "yellow": return self.enterDateTime()
		if action == "blue": return self.openEPGSearch()
	WarderEPGSelection.warderProgramInfoClosed = warderProgramInfoClosed

	def warderEPGSelectionRedButtonPressed(self):
		if _warderGraphicalEPGPIG(self):
			# One physical RED press can be delivered more than once by the EPG key path.
			# Never stack two Program Info screens: the first close must reveal the EPG.
			if getattr(self, "_warderProgramInfoOpen", False):
				return None
			# Warder contract: RED in our graphical EPG has exactly one destination:
			# the local PROGRAM INFO screen for the currently selected EPG event.
			# Never fall through to OpenATV/legacy info/CSFD handlers.
			try:
				active = getattr(self, "activeList", 1)
				listing = self["list%s" % active]
				cur = listing.getCurrent()
				event = cur[0] if cur else None
				service = cur[1] if cur and len(cur) > 1 else None
				if event is not None:
					self._warderProgramInfoOpen = True
					try:
						return self.session.openWithCallback(self.warderProgramInfoClosed, WarderProgramInfo, event, service)
					except Exception:
						self._warderProgramInfoOpen = False
						raise
			except Exception as e:
				Writelog("WarderProgramInfo open: %s" % e)
			return None
		return WarderEPGSelection_redButtonPressed(self)
	WarderEPGSelection.redButtonPressed = warderEPGSelectionRedButtonPressed

	WarderEPGSelection_greenButtonPressed = WarderEPGSelection.greenButtonPressed
	def warderEPGSelectionGreenButtonPressed(self):
		if _warderGraphicalEPGPIG(self):
			return self.RecordTimerQuestion(True)
		return WarderEPGSelection_greenButtonPressed(self)
	WarderEPGSelection.greenButtonPressed = warderEPGSelectionGreenButtonPressed

	WarderEPGSelection_yellowButtonPressed = WarderEPGSelection.yellowButtonPressed
	def warderEPGSelectionYellowButtonPressed(self):
		if _warderGraphicalEPGPIG(self):
			return self.enterDateTime()
		return WarderEPGSelection_yellowButtonPressed(self)
	WarderEPGSelection.yellowButtonPressed = warderEPGSelectionYellowButtonPressed

	WarderEPGSelection_blueButtonPressed = WarderEPGSelection.blueButtonPressed
	def warderEPGSelectionBlueButtonPressed(self):
		if _warderGraphicalEPGPIG(self):
			return self.openEPGSearch()
		return WarderEPGSelection_blueButtonPressed(self)
	WarderEPGSelection.blueButtonPressed = warderEPGSelectionBlueButtonPressed

except Exception:
	pass


def _warderRadioButtonTrace(self, *args, **kwargs):
	try:
		stamp = time1.time()
		with open("/tmp/warder-radio-start", "w") as out:
			out.write("%.6f\\n" % stamp)
		with open("/tmp/warder-radio-artwork.log", "a") as out:
			out.write("RADIO_BUTTON epoch=%.6f\\n" % stamp)
	except Exception:
		pass
	return _warderOriginalShowRadioButton(self, *args, **kwargs)


def startHdg17(reason, **kwargs):
	if reason == 0 and config.skin.primary_skin.value == "hd_glass17/skin.xml":
		# TEST89: timestamp the actual RADIO key handler before any mode-switch work.
		global _warderOriginalShowRadioButton
		try:
			if _warderOriginalShowRadioButton is None:
				_warderOriginalShowRadioButton = InfoBar.showRadioButton
				InfoBar.showRadioButton = _warderRadioButtonTrace
		except Exception:
			pass
		# Warder native graphical EPG: picons only, compact service column.
		# Keep this scoped to FullHDGlass17 session start and tolerate images without these OpenATV keys.
		try:
			if hasattr(config, "epgselection") and hasattr(config.epgselection, "graph_servicetitle_mode"):
				config.epgselection.graph_servicetitle_mode.value = "picon"
			if hasattr(config, "epgselection") and hasattr(config.epgselection, "graph_piconwidth"):
				config.epgselection.graph_piconwidth.value = 60
			if hasattr(config, "epgselection"):
				if hasattr(config.epgselection, "graph_green"):
					config.epgselection.graph_green.value = "timer"
				if hasattr(config.epgselection, "graph_yellow"):
					config.epgselection.graph_yellow.value = "gotodatetime"
				if hasattr(config.epgselection, "graph_blue"):
					config.epgselection.graph_blue.value = "epgsearch"
		except Exception:
			pass
		enaOKstart = True                                                                                     
		if not fileExists(SKINPATH + "icons/about1.png"):
			if config.plugins.setupGlass17.par15.value != "0" and chckUserHdg():       
				enaOKstart = False
				msg = setOledMore()
			if config.plugins.setupGlass17.par7.value == "Icons" or config.plugins.setupGlass17.par7.value == "Icons Right" or config.plugins.setupGlass17.par7.value == "Icons Bar":
				if chckPMS():
					if setMenuPyo():                                 		
						enaOKstart = False
			if config.plugins.setupGlass17.par59.value:
				if not os.path.exists('/etc/dpkg') and fileExists(ENC_U):
					if os.path.getsize(ENC_U) != os.path.getsize(ENC_C):
						enaMenuPy = setEncodingUser()
						if enaMenuPy:                                 		
							enaOKstart = False
				else:
					setCFGoff(59)
			if config.plugins.setupGlass17.par62.value:
				if E2OK:
					tt = chnlSelChck()
					if tt == 0:
						if chnlSelPatch():
							enaOKstart = False
						else:
							setCFGoff()
					elif tt == 3:
						enaOKstart = False								
				else:
					setCFGoff()
			if EFIFO and config.plugins.setupGlass17.par67.value:
				if chckFifo():
					enaOKstart = False
		if not enaOKstart:
			autoStartChck17.updateChck(kwargs["session"])
		else:
			if fileExists(SKINPATH + "icons/about1.png"):
				autoStartChck17.startHdgchck(kwargs["session"])
			if config.plugins.setupGlass17.par12.value != "n" or config.plugins.setupGlass17.par64.value:
				keyManage.initKeyMng(kwargs["session"])
			global Glass17__init__
			if "session" in kwargs:
				if Glass17__init__ is None:
					Glass17__init__ = InfoBarPlugins.__init__
				InfoBarPlugins.__init__ = hdg17inicialize
				InfoBarPlugins.controlWindow17 = controlWindow17
				InfoBarPlugins.hideWindow17 = hideWindow17
				InfoBarPlugins.fadeEvent17 = fadeEvent17
				InfoBarPlugins.fadeEvent217 = fadeEvent217
				InfoBarPlugins.serviceStartNow17 = serviceStartNow17
				InfoBarPlugins.serviceStartNow172 = serviceStartNow172
				InfoBarPlugins.serviceStartNow173 = serviceStartNow173
				if config.plugins.setupGlass17.par12.value != "n":
					InfoBarPlugins.SpecialScreenWindow17 = SpecialScreenWindow17
			if not config.plugins.setupGlass17.par48.value:
				try:
					satXml = parse(config.plugins.setupGlass17.par141.value+"satellites.xml").getroot()
					if satXml is not None:
						global allSat
						for sat in satXml.findall("sat"):
							name = sat.get("name") or None
							position = sat.get("position") or None
							if name is not None and position is not None:
								position = "%s.%s" % (position[:-1], position[-1:])
								if position.startswith("-"):
									position = "%sW" % position[1:]
								else:
									position = "%sE" % position
								if position.startswith("."):
									position = "0%s" % position
								if not ISP38:
									name = name.encode("utf-8")
								allSat[position] = str(name)
				except: pass

def hdg17inicialize(self):
	global FirstRun17
	if not FirstRun17: 
		FirstRun17 = True
		def doNothing():
			pass
		if config.plugins.setupGlass17.par12.value == "n":
			if config.plugins.setupGlass17.par34.value:
				self["g17Actions"] = ActionMap(["g17Actions_neutrino"],{"ok_pressed": self.controlWindow17}, -1)
			else:
				self["g17Actions"] = ActionMap(["g17Actions"],{"ok_pressed": self.controlWindow17,"exit_pressed": self.hideWindow17}, -1)
		else:
			if config.plugins.setupGlass17.par34.value:
				self["g17Actions"] = ActionMap(["g17Actions_neutrinoSpecial"],{"showSpecialScreen": self.SpecialScreenWindow17,"ok_pressed": self.controlWindow17}, -1)
			else:
				self["g17Actions"] = ActionMap(["g17ActionsSpecial"],{"showSpecialScreen": self.SpecialScreenWindow17,"ok_pressed": self.controlWindow17,"exit_pressed": self.hideWindow17}, -1)
			self["helpActions"] = ActionMap(['HelpActions'],{"displayHelp": doNothing})
		f = open(KMP_FILE, "r").read()
		if f.find("LongOKPressed") != -1:
			self["ShowHideActions"] = ActionMap( ["InfobarShowHideActions"] ,{"toggleShow": doNothing,"hide": doNothing,})
		if ENA_Z:
			self.g17dialog = self.session.instantiateDialog(ExtraInfo17, zPosition=1000)
			self.g17dialog.shown = False
		else:
			self.g17dialog = self.session.instantiateDialog(ExtraInfo17)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evStart: self.serviceStartNow17, iPlayableService.evUpdatedEventInfo: self.serviceStartNow173,
			})
		try:
			ref = self.session.nav.getCurrentlyPlayingServiceReference()
			fields = ref.toString().split(":") if ref is not None else []
			with open("/tmp/warder-radio-current", "w") as marker:
				marker.write("A" if is_radio_reference(ref) else "TV")
		except Exception:
			pass
		global transStep17
		transStep17 = 20
		self.g17fadeTimer = eTimer()
		try:
			self.g17fadeTimer_conn = self.g17fadeTimer.timeout.connect(self.fadeEvent17)
		except AttributeError:
			self.g17fadeTimer.timeout.get().append(self.fadeEvent17)
		self.g17fadeTimer2 = eTimer()
		try:
			self.g17fadeTimer2_conn = self.g17fadeTimer2.timeout.connect(self.fadeEvent217)
		except AttributeError:
			self.g17fadeTimer2.timeout.get().append(self.fadeEvent217)
		if config.plugins.setupGlass17.par4.value:
			self.onShow.append(lambda: self.g17dialog.show())
			self.onHide.append(lambda: self.g17dialog.hide())
			if config.plugins.setupGlass17.par31.value != "n":
				if "w" in config.plugins.setupGlass17.par31.value:          
					from Plugins.Extensions.setupGlass17.weather import WeatherScreen
					if ENA_Z:
						self.g17dialogUser = self.session.instantiateDialog(WeatherScreen, config.plugins.setupGlass17.par172.value, zPosition=2000)
						self.g17dialogUser.shown = False
					else:
						self.g17dialogUser = self.session.instantiateDialog(WeatherScreen, config.plugins.setupGlass17.par172.value)
				elif config.plugins.setupGlass17.par31.value == "a":          
					from Plugins.Extensions.setupGlass17.Netatmo import NetatmoScreen
					if ENA_Z:
						self.g17dialogUser = self.session.instantiateDialog(NetatmoScreen, zPosition=2000)
						self.g17dialogUser.shown = False
					else:
						self.g17dialogUser = self.session.instantiateDialog(NetatmoScreen)
				else:
					from Screens.G17_UserInfo import UserInfo17
					if ENA_Z:
						self.g17dialogUser = self.session.instantiateDialog(UserInfo17, zPosition=2000)
						self.g17dialogUser.shown = False
					else:
						self.g17dialogUser = self.session.instantiateDialog(UserInfo17)
				self.g17dialogUser.hide()
		self.g17dialogTimer = eTimer()
		try:
			self.g17dialogTimer_conn = self.g17dialogTimer.timeout.connect(self.hideWindow17)
		except AttributeError:
			self.g17dialogTimer.callback.append(self.hideWindow17)
		def timerStateChck17():
			if self.g17dialogTimer.isActive():
				self.g17dialogTimer.stop()
			if self.g17eventupdTimer.isActive():
				self.g17eventupdTimer.stop()
		self.g17dialog.onHide.append(timerStateChck17)
		def hideTimerStop17():
			self.hideTimer.stop()
		self.killhideTimer = eTimer()
		try:
			self.killhideTimer_conn = self.killhideTimer.timeout.connect(hideTimerStop17)
		except AttributeError:
			self.killhideTimer.timeout.get().append(hideTimerStop17)
		self.g17eventupdTimer = eTimer()
		try:
			self.g17eventupdTimer_conn = self.g17eventupdTimer.timeout.connect(self.hideWindow17)
		except AttributeError:
			self.g17eventupdTimer.timeout.get().append(self.hideWindow17)
		self.onShow.append(self.serviceStartNow172)
		self.onHide.append(timerStateChck17)
	else:
		InfoBarPlugins.__init__ = InfoBarPlugins.__init__
		InfoBarPlugins.controlWindow17 = None
		InfoBarPlugins.hideWindow17 = None
		InfoBarPlugins.fadeEvent17 = None
		InfoBarPlugins.fadeEvent217 = None
		InfoBarPlugins.serviceStartNow17 = None
		InfoBarPlugins.serviceStartNow172 = None
		InfoBarPlugins.serviceStartNow173 = None
		if config.plugins.setupGlass17.par12.value != "n":
			InfoBarPlugins.SpecialScreenWindow17 = None
	Glass17__init__(self)
	if isinstance(self, InfoBar):
		from Plugins.Extensions.setupGlass17.warderRadioWindows import install_radio_window_transparency
		install_radio_window_transparency(self)

def SpecialScreenWindow17(self):
	ShowHideViaKey()

def serviceStartNow17(self):
	if isinstance(self,InfoBar):
		# TEST106: retry after OpenWebif has initialized; idempotent and receiver-proven class name.
		_warderInstallOpenWebifGrabHook()
		# TEST90/92: service-start is the reliable TV/RADIO transition boundary on this image.
		refstr = ""
		try:
			ref = self.session.nav.getCurrentlyPlayingServiceReference()
			refstr = ref.toString() if ref is not None else ""
			stamp = time1.time()
		except Exception:
			pass
		# TEST92: a TV -> RADIO service can start while ChannelSelectionRadio is still
		# open. Re-show the already native-owned RDS dialog at that proven boundary
		# so closing the bouquet exposes the Warder skin overlay immediately.
		# Do not replace or monkey-patch Screens.RdsDisplay.RdsInfoDisplay.
		try:
			fields = refstr.split(":")
			is_radio = is_radio_reference(ref)
			try:
				with open("/tmp/warder-radio-current", "w") as marker:
					marker.write("A" if is_radio else "TV")
			except Exception:
				pass
			controller = getattr(self, "_warderRadioWindows", None)
			if controller is not None:
				controller.update()
			rds = getattr(self, "rds_display", None)
			if rds is not None:
				if is_radio:
					# TEST114: keep native RDS ownership; the scoped top-only dialog handles InfoBar overlap.
					rds.show()
				else:
					# TEST94: TEST92 must be symmetrical. The native-owned RDS dialog
					# must not survive RADIO -> TV and bind its CurrentService widgets
					# to the TV service after the normal TV infobar closes.
					rds.hide()
		except Exception:
			pass
		if self.shown:
			if self.g17dialogTimer.isActive():
				self.g17dialogTimer.stop()
			idx = config.usage.infobar_timeout.index
			if idx:
				self.g17dialogTimer.start(idx*1000, True)
				self.killhideTimer.start(750, True)

def serviceStartNow172(self):
	if isinstance(self,InfoBar):
		if self.shown:
			if self.g17dialogTimer.isActive():
				self.g17dialogTimer.stop()
			if config.plugins.setupGlass17.par55.value != "1":
				idx = config.usage.infobar_timeout.index
				if idx:
					self.g17dialogTimer.start(idx*1000, True)
			self.killhideTimer.start(750, True)

def serviceStartNow173(self):
	if isinstance(self,InfoBar):
		if config.plugins.setupGlass17.par55.value == "1":
			idx = config.usage.infobar_timeout.index
			if idx:
				self.g17eventupdTimer.start(idx*1000, True)

def controlWindow17(self):
	global transStep17
	if isinstance(self,InfoBar):
		if config.plugins.setupGlass17.par55.value == "2":
			if config.usage.infobar_timeout.value != "0":
				config.plugins.setupGlass17.par61.value = config.usage.infobar_timeout.value
				config.usage.infobar_timeout.value = "0"
		if not config.plugins.setupGlass17.par4.value:
			if not self.shown and not self.g17dialog.shown:
				if config.plugins.setupGlass17.par27.value and config.plugins.setupGlass17.par29.value:
					alphaChange17(0)
					self.show()
					transStep17 = 0
					self.g17fadeTimer.start(250, True)
				else:
					self.show()
			elif self.shown and not self.g17dialog.shown:
				self.hide()
				self.g17dialog.show()
				if config.plugins.setupGlass17.par55.value != "1":
					idx = config.usage.infobar_timeout.index
					if idx:
						self.g17dialogTimer.start(idx*1000, True)
			elif not self.shown and self.g17dialog.shown:
				if config.plugins.setupGlass17.par27.value:
					transStep17 = 20
					self.g17fadeTimer2.start(5, True)
				else:
					self.g17dialog.hide()
				if config.plugins.setupGlass17.par55.value == "2":
					if config.usage.infobar_timeout.value == "0":
						config.usage.infobar_timeout.value = config.plugins.setupGlass17.par61.value
						config.plugins.setupGlass17.par61.value = "0"
			elif self.shown and self.g17dialog.shown:
				if config.plugins.setupGlass17.par27.value:
					transStep17 = 20
					self.g17fadeTimer2.start(5, True)
				else:
					self.hide()
					self.g17dialog.hide()
				if config.plugins.setupGlass17.par55.value == "2":
					if config.usage.infobar_timeout.value == "0":
						config.usage.infobar_timeout.value = config.plugins.setupGlass17.par61.value
						config.plugins.setupGlass17.par61.value = "0"
			else:
				if self.shown:
					if config.plugins.setupGlass17.par27.value:
						transStep17 = 20
						self.g17fadeTimer2.start(5, True)
					else:
						self.hide()
					self.hideTimer.stop()
					if config.plugins.setupGlass17.par55.value == "2":
						if config.usage.infobar_timeout.value == "0":
							config.usage.infobar_timeout.value = config.plugins.setupGlass17.par61.value
							config.plugins.setupGlass17.par61.value = "0"
				else:
					if config.plugins.setupGlass17.par27.value and config.plugins.setupGlass17.par29.value:
						alphaChange17(0)
						self.show()
						transStep17 = 0
						self.g17fadeTimer.start(250, True)
					else:
						self.show()
		else:
			if config.plugins.setupGlass17.par31.value != "n":
				if not self.g17dialog.shown and not self.shown and self.g17dialogUser.shown and config.plugins.setupGlass17.par32.value:
					if config.plugins.setupGlass17.par27.value:
						transStep17 = 20
						self.g17fadeTimer2.start(5, True)
					else:
						self.g17dialogUser.hide()
					if config.plugins.setupGlass17.par55.value == "2":
						if config.usage.infobar_timeout.value == "0":
							config.usage.infobar_timeout.value = config.plugins.setupGlass17.par61.value
							config.plugins.setupGlass17.par61.value = "0"
				elif not self.g17dialog.shown:
					if config.plugins.setupGlass17.par27.value and config.plugins.setupGlass17.par29.value:
						alphaChange17(0)
						self.show()
						transStep17 = 0
						self.g17fadeTimer.start(150, True)
					else:
						self.show()
				elif self.g17dialog.shown and not self.g17dialogUser.shown:
					self.g17dialogUser.show()
					if config.plugins.setupGlass17.par55.value != "1":
						idx = config.usage.infobar_timeout.index
						if idx:
							self.g17dialogTimer.start(idx*1000, True)
				elif self.g17dialog.shown and self.g17dialogUser.shown:
					if config.plugins.setupGlass17.par27.value:
						transStep17 = 20
						self.g17fadeTimer2.start(5, True)
					else:
						if not config.plugins.setupGlass17.par32.value:
							self.g17dialogUser.hide()
						else:
							if not self.shown and not self.g17dialog.shown:
								self.g17dialogUser.hide()
						self.hide()
						self.g17dialog.hide()
					if config.plugins.setupGlass17.par55.value == "2":
						if config.usage.infobar_timeout.value == "0":
							config.usage.infobar_timeout.value = config.plugins.setupGlass17.par61.value
							config.plugins.setupGlass17.par61.value = "0"
				else:
					if self.shown:
						if config.plugins.setupGlass17.par27.value:
							transStep17 = 20
							self.g17fadeTimer2.start(5, True)
						else:
							self.hide()
						self.hideTimer.stop()
						if config.plugins.setupGlass17.par55.value == "2":
							if config.usage.infobar_timeout.value == "0":
								config.usage.infobar_timeout.value = config.plugins.setupGlass17.par61.value
								config.plugins.setupGlass17.par61.value = "0"
					else:
						if config.plugins.setupGlass17.par27.value and config.plugins.setupGlass17.par29.value:
							alphaChange17(0)
							self.show()
							transStep17 = 0
							self.g17fadeTimer.start(250, True)
						else:
							self.show()		
			else:
				if self.shown:
					if config.plugins.setupGlass17.par27.value:
						transStep17 = 20
						self.g17fadeTimer2.start(5, True)
					else:
						self.hide()
					self.hideTimer.stop()
					if config.plugins.setupGlass17.par55.value == "2":
						if config.usage.infobar_timeout.value == "0":
							config.usage.infobar_timeout.value = config.plugins.setupGlass17.par61.value
							config.plugins.setupGlass17.par61.value = "0"
				else:
					if config.plugins.setupGlass17.par27.value and config.plugins.setupGlass17.par29.value:
						alphaChange17(0)
						self.show()
						transStep17 = 0
						self.g17fadeTimer.start(250, True)
					else:
						self.show()

def hideWindow17(self):
	if isinstance(self,InfoBar):
		if config.plugins.setupGlass17.par55.value == "2":
			if config.usage.infobar_timeout.value == "0":
				config.usage.infobar_timeout.value = config.plugins.setupGlass17.par61.value
				config.plugins.setupGlass17.par61.value = "0"
		if config.plugins.setupGlass17.par27.value:
			global transStep17
			transStep17 = 20
			self.g17fadeTimer2.start(5, True)
		else:
			if config.plugins.setupGlass17.par4.value and config.plugins.setupGlass17.par31.value != "n":
				if not config.plugins.setupGlass17.par32.value:
					self.g17dialogUser.hide()
				else:
					if not self.shown and not self.g17dialog.shown:
						self.g17dialogUser.hide()
			self.hide()
			self.g17dialog.hide()
	
def fadeEvent217(self):
	global enaFadeOut17
	if not enaFadeOut17: 
		return
	if config.plugins.setupGlass17.par4.value and config.plugins.setupGlass17.par31.value != "n":
		if config.plugins.setupGlass17.par32.value:
			if self.shown and self.g17dialog.shown and self.g17dialogUser.shown:
				self.hide()
				self.g17dialog.hide()
				return
	global enaFadeIn17
	enaFadeIn17 = False
	self.g17fadeTimer2.stop()
	global transStep17
	if transStep17 != 0:
		alphaChange17(config.av.osd_alpha.value*transStep17/20)
		transStep17 -= 1
		self.g17fadeTimer2.start((int(config.plugins.setupGlass17.par28.value) * 6), True)
	else:
		if config.plugins.setupGlass17.par4.value and config.plugins.setupGlass17.par31.value != "n":
			if not config.plugins.setupGlass17.par32.value:
				self.g17dialogUser.hide()
			else:
				if not self.shown and not self.g17dialog.shown:
					self.g17dialogUser.hide()
		self.hide()
		self.g17dialog.hide()
		self.transScrtimer = eTimer()
		try:
			self.transScrtimer_conn = self.transScrtimer.timeout.connect(transRestore17)
		except AttributeError:
			self.transScrtimer.timeout.get().append(transRestore17)
		self.transScrtimer.start(300, True)

def transRestore17():
	alphaChange17(config.av.osd_alpha.value)
	global enaFadeIn17
	enaFadeIn17 = True

def fadeEvent17(self):
	global enaFadeIn17
	if not enaFadeIn17: 
		return
	global enaFadeOut17
	enaFadeOut17 = False
	global transStep17
	self.g17fadeTimer.stop()
	if transStep17 != 21:
		alphaChange17(config.av.osd_alpha.value*transStep17/20)
		transStep17 += 1
		self.g17fadeTimer.start((int(config.plugins.setupGlass17.par28.value) * 6), True)
	else:
		enaFadeOut17 = True

def alphaChange17(alphastate):
	f=open("/proc/stb/video/alpha","w")
	f.write("%i" % (alphastate))
	f.close()
##########################################################################################################################      		
def piconSize(s):
	ret = "picon"
	try:
		s = s.split(",")
		if s[0] in ("400","600"):
			ret = "ZZPicon"
			if s[1] == "240":
				ret = "picon_400x240"
		elif s[0] == "220":
			ret = "picon"
	except: pass
	return ret
	
def chckPiconSize():
	ret = "1"
	try:
		from Screens.G17screens import g17_extraScreen	
		tmp = g17_extraScreen.get(str(config.plugins.setupGlass17.par6.value))
		typeScr = tmp.split("\n")
		for i in typeScr:
			if '"g17picon"' in i:
				tmp = (i.split('size="')[1]).split('"')[0]
				tmp = tmp.split(",")
				if "400" in tmp[0] or "600" in tmp[0]:
					ret = "3"
					if "240" in tmp[1]:
						ret = "4"
				elif "220" in tmp[0]:
					ret = "2"
				break
	except: pass
	return ret
	
def fromCfgB(w=True):
	try:
		from Screens.G17screens import g17_extraScreen	
		tmp = g17_extraScreen.get(str(config.plugins.setupGlass17.par6.value))
		if w:
			if tmp.find("bitrate_info") != -1:
				return True
		else:
			tmp = tmp.split("\n")
			for i in tmp:
				if '<widget source="session.Event_Now" render="Progress"' in i and not 'pixmap="' in i:
					return True
	except: pass
	return False
			
def fromCfg():
	isOk = checkScreen(config.plugins.setupGlass17.par6.value)
	if not isOk:
		config.plugins.setupGlass17.par6.value = 1
		config.plugins.setupGlass17.par6.save()
	from Screens.G17screens import g17_extraScreen	
	typeScr = g17_extraScreen.get(str(config.plugins.setupGlass17.par6.value))
	if ENA_POSTER and config.plugins.setupGlass17.par198.value:
		typeScr = typeScr.replace("</screen>",POSTER % (config.plugins.setupGlass17.par200.value,config.plugins.setupGlass17.par201.value,config.plugins.setupGlass17.par202.value) + "</screen>")
	if config.plugins.setupGlass17.par209.value != "0":
		if config.plugins.setupGlass17.par226.value != "2":
			isOk = NETSPEED % (config.plugins.setupGlass17.par210.value,config.plugins.setupGlass17.par211.value,config.plugins.setupGlass17.par210.value+80,config.plugins.setupGlass17.par211.value)
			if config.plugins.setupGlass17.par213.value != "AutoColors": 
				isOk = setFcolor(isOk,config.plugins.setupGlass17.par213.value)
		else:
			isOk = NETSPEEDT % (config.plugins.setupGlass17.par210.value,config.plugins.setupGlass17.par211.value)
		typeScr = typeScr.replace("</screen>", isOk + "</screen>")
	tmp = typeScr
	if config.plugins.setupGlass17.par137.value != "AutoColors" or config.plugins.setupGlass17.par136.value != "AutoColors" or config.plugins.setupGlass17.par135.value != "AutoColors" or config.plugins.setupGlass17.par128.value != "AutoColors" or config.plugins.setupGlass17.par129.value != "AutoColors" or config.plugins.setupGlass17.par130.value != "AutoColors":
		typeScr = tmp.split("\n")
		tmp = ""
		buff = ""
		isOk = False
		isOk2 = False
		isOk3 = False
		isOk4 = False
		for i in typeScr:
			if 'render="g17dateFormat"' in i and config.plugins.setupGlass17.par128.value != "AutoColors":
				tmp += setFcolor(i,config.plugins.setupGlass17.par128.value)
			elif '="global.CurrentTime' in i and not isOk:
				isOk = True
				buff = i
			elif '="session.CurrentService' in i and not isOk2:
				isOk2 = True
				buff = i
			elif '="session.Event_Now"' in i and not '="g17Poster"' in i and not isOk3:
				isOk3 = True
				buff = i
			elif '="session.Event_Next"' in i and not isOk4:
				isOk4 = True
				buff = i
			elif 'g17ClockToText' in i and isOk:
				if config.plugins.setupGlass17.par130.value != "AutoColors" and ('>Format::%S<' in i or '>Format:%S<' in i):
					tmp += setFcolor(buff,config.plugins.setupGlass17.par130.value) + i + "\n"
					isOk = False
				elif config.plugins.setupGlass17.par129.value != "AutoColors":
					tmp += setFcolor(buff,config.plugins.setupGlass17.par129.value) + i + "\n"
					isOk = False
				else:
					tmp += buff + "\n" + i + "\n"
					isOk = False
			elif ('"ServiceName">Name<' in i or '"g17ServiceNum">Number' in i) and isOk2:
				if config.plugins.setupGlass17.par135.value != "AutoColors":
					tmp += setFcolor(buff,config.plugins.setupGlass17.par135.value) + i + "\n"
					isOk2 = False
				else:
					tmp += buff + "\n" + i + "\n"
					isOk2 = False
			elif ('g17EventTime' in i or '="EventName' in i) and (isOk3 or isOk4):
				if config.plugins.setupGlass17.par136.value != "AutoColors" and isOk3:
					tmp += setFcolor(buff,config.plugins.setupGlass17.par136.value) + i + "\n"
					isOk3 = False
				elif config.plugins.setupGlass17.par137.value != "AutoColors" and isOk4:
					tmp += setFcolor(buff,config.plugins.setupGlass17.par137.value) + i + "\n"
					isOk4 = False
				else:
					tmp += buff + "\n" + i + "\n"
					isOk4 = False
					isOk3 = False
			else:
				tmp += ({True:buff + "\n", False:""}[isOk or isOk2 or isOk3 or isOk4]) + i + "\n"
				isOk = False
				isOk2 = False
				isOk3 = False
				isOk4 = False
	if config.plugins.setupGlass17.par183.value != "0":
		tt = int(config.plugins.setupGlass17.par183.value)
		typeScr = tmp.split("\n")
		tmp = ""
		for i in typeScr:
			if not '<screen' in i and ' position="' in i: 
				tmp += calcY(tt,i,' position="') + "\n"
			else:
				tmp += i + "\n"
	if ENA_SLIDER[0] or ENA_SLIDER[1]:
		typeScr = tmp.split("\n")
		tmp = ""
		tt = '<widget source="session.Event_Now" render="Progress"'
		for i in typeScr:
			if tt in i:
				isOk2 = 'pixmap="' in i and not config.plugins.setupGlass17.par222.value
				if not 'pixmap="' in i or isOk2:
					if isOk2:
						config.plugins.setupGlass17.par16.value = False
						isOk = i.split('pixmap="')
						isOk2 = isOk[1].split(' ')
						isOk2[0] = ''
						isOk = re.sub(r"\s+", " ", isOk[0] + ' '.join(isOk2))
						isOk2 = ((isOk.split('size="')[1]).split(',')[1]).strip()						
						isOk2 = (isOk.split('"')[0]).strip()
						if isOk2.isdigit():
							isOk2 = isOk2/2 - 3
						else:
							isOk2 = 5
						isOk = calcY(5,isOk,'size="',True)
						isOk = calcY(isOk2,isOk,'position="')
						i = isOk.replace('transparent="1"','transparent="0"')
					if ENA_SLIDER[0]:
						if config.plugins.setupGlass17.par214.value != "AutoColors":		
							isOk = config.plugins.setupGlass17.par214.value		
						else:		
							isOk = "white"				
						i = setFcolor(i,isOk)
					if ENA_SLIDER[1]:
						if config.plugins.setupGlass17.par215.value != "AutoColors":		
							isOk = config.plugins.setupGlass17.par215.value		
						else:		
							isOk = "#1546AF"
						i = setFcolor(i,isOk,True)
			tmp += i + "\n"
	if config.plugins.setupGlass17.par223.value:
		typeScr = tmp.split("\n")
		tmp = ""
		for i in typeScr:
			if ('<eLabel ' in i and 'text="' in i and ('"-"' in i or ':' in i)) or ('<ePixmap ' in i and ('slider/sig' in i or 'icons/bar_back' in i)):
				if '<eLabel ' in i:
					isOk = i.replace('<eLabel ','<widget source="session.FrontendStatus" render="FixedLabel" ')
				else:
					isOk = i.replace('<ePixmap ','<widget source="session.FrontendStatus" render="Pixmap" ')
				isOk = isOk.replace('/>','>\n')
				if 'SNR' in i.upper() or 'Q' in i or '"-"' in i:
					isOk2 = 'SnrNum'
				elif 'BER' in i.upper():
					isOk2 = 'BerNum'
				else:
					isOk2 = 'AgcNum'
				i = isOk + '<convert type="g17ExtraSource">%s</convert>\n<convert type="ValueRange">1,65536</convert>\n<convert type="ConditionalShowHide" />\n</widget>' % isOk2
			tmp += i + "\n"
	# TEST165: InfoPanel mirrors the three independent native Radio top labels.
	# All share y/height/valign; only the clock uses the larger font.
	tmp = setSideECM(tmp)
	from Plugins.Extensions.setupGlass17.warderRadioLayers import prepare_radio_layers
	tmp = prepare_radio_layers(tmp)
	warder_radio_top = """
		<widget source="global.CurrentTime" render="WarderRadioInfoTop" position="62,27" size="610,58" font="Prive4;30" foregroundColor="#FFE16A" halign="left" valign="center" noWrap="1" transparent="1" zPosition="20" />
		<widget source="global.CurrentTime" render="WarderRadioInfoTop" position="790,27" size="340,58" font="Prive4;38" foregroundColor="#FFE16A" halign="center" valign="center" noWrap="1" transparent="1" zPosition="20" />
		<widget source="global.CurrentTime" render="WarderRadioInfoTop" position="1170,27" size="630,58" font="Prive4;30" foregroundColor="#FFE16A" halign="right" valign="center" noWrap="1" transparent="1" zPosition="20" />
	"""
	return tmp.replace("</screen>", warder_radio_top + "</screen>")

def calcY(xs,dd,d,o=None):
	a = dd.split(d)
	b = a[1].split('"')
	c = b[0].split(',')
	if len(c) == 2:
		c[1] = c[1].strip()
		if c[1].isdigit():
			if o:
				c[1] = str(xs)
			else:
				c[1] = str(int(int(c[1])+xs))
	b[0] = c[0] + ',' + c[1]
	return a[0]+ d + '"'.join(b)
##########################################################################################################################
def parseEcmInfoLine(line,what=":"):
	if line.__contains__(what):
		line = line.split(what)[1]
		line = line.replace("\n", "")
		return " ".join(line.strip().split())
	else:
		return ""
##########################################################################################################################
def isIP(ip):
	ret = 0
	x = ip.strip().split(".")
	if len(x) == 4:
		for i in x:
			if i.isdigit():
				tt = int(i)
				if tt >= 0 and tt <= 255: 
					ret += 1
	return ret == 4

def internet(val=None):
	try:
		chck = socket(AF_INET, SOCK_STREAM)
		chck.settimeout(0.5)	
		if val is None:
			val = config.plugins.setupGlass17.par80.value
		return not bool(chck.connect_ex((val, 80)))
	except: pass
	return False
##########################################################################################################################    		
def chckScroll20():
	ena = False
	path = PYTHONPATH + "skin.py"
	if fileExists(path):
		try:
			r = open(path,"r")
			for line in r.readlines():	
				if "ValuePixmapBottomHeight" in line:	
					ena = True
					break
			r.close()          
		except: pass          	
	if ena:
		allLines = ""
		try:
			r = open(SKINXML,"r")
			for line in r.readlines():
				if "<!--windowstylescrollbar id=\"4\">" in line or "</windowstylescrollbar-->" in line:
					line = line.replace("!--", "").replace("--", "")
				allLines = allLines + line
			r.close()
			_atomicWriteText(SKINXML, allLines)
		except: pass
	return ena		
##########################################################################################################################
def setONOFF():
	ena = False         	
	if ENA_ONOFF:
		allLines = ""
		try:
			r = open(SKINXML,"r")
			for line in r.readlines():
				if 'switchpixmap' in line or 'config onPixmap=' in line:
					if ('!--' in line or '--' in line) and config.plugins.setupGlass17.par190.value:
						line = line.replace("!--", "").replace("--", "")
						ena = True
					elif not ('!--' in line or '--' in line) and not config.plugins.setupGlass17.par190.value:
						line = line.replace("<sw", "<!--sw").replace("</switchpixmap>", "</switchpixmap-->").replace("<config", "<!--config").replace("/>", "/-->")
						ena = True
				allLines += line
			r.close()
			_atomicWriteText(SKINXML, allLines)
		except: pass
	return ena
##########################################################################################################################
WARDER_ASSET_MANIFEST_URL = "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/warder-modernization-work/assets/warder/downloads.json"

def getWarderAssets():
	"""Load the Warder download catalog over HTTPS without reusing a stale cache entry.

	Returns (error_message, assets_dict). No certificate verification is disabled.
	"""
	try:
		sep = "&" if "?" in WARDER_ASSET_MANIFEST_URL else "?"
		url = "%s%scb=%d" % (WARDER_ASSET_MANIFEST_URL, sep, int(time1.time()))
		req = Request(url, headers={"User-Agent": "FullHDGlass17-Warder-Evolution/1.0.2", "Accept": "application/json", "Cache-Control": "no-cache, no-store, max-age=0", "Pragma": "no-cache"})
		with urlopen(req, timeout=15) as response:
			if str(response.geturl()) != url:
				raise ValueError("unsafe asset manifest redirect")
			data = json.loads(response.read().decode("utf-8-sig"))
		assets = data.get("assets", {})
		if not isinstance(assets, dict):
			raise ValueError("invalid assets catalog")
		assets = dict(assets)
		assets["__auxiliary_hybrid__"] = data.get("auxiliary_hybrid")
		return "", assets
	except Exception as err:
		return _("Sorry, download server is unavailable, check your internet connection !!!") + " " + str(err), {}

##########################################################################################################################
def menusel(t):
	a = ({"Icons":"1","List":"2","with PIG":"3","List and Icon":"7","Icons Bar":"8","Icons Right":"9","simply PIG":"10","PIG2":"11","PIG4":"13","Li2":"14","Li3":"16"}[t])
	if a == "16" and ISP38 and isATV:
		a = "15"
	return a
##########################################################################################################################
def listDir(what):
	f = None
	try:
		f = listdir(what)
	except: pass
	return f
	
def checkScreen(numScr):
	if numScr == 1:
		return True
	isOk = 0
	ispath = True
	path = '%s/extraScreens17/%s' % (config.plugins.setupGlass17.par39.value, numScr)
	pathOK = False
	num = 0
	numOK = 0
	try:
		if os.path.exists(path):
			pathOK = True
			f = listDir(path)
		from Screens.G17screens import g17_extraScreen	
		tmp = g17_extraScreen.get(str(numScr))
		tmp = tmp.split("\n")
		for line in tmp:
			if line.__contains__('<screen name="ExtraInfo17"') or line.__contains__('</screen>'):
				isOk += 1
			if line.__contains__(('extraScreens17/%s/' % numScr)):
				num += 1
				ispath = False
				if pathOK and f:
					for x in f:
						if x in line:
							numOK += 1
							break
		if num == numOK:
			ispath = True
	except: ispath = False
	return isOk == 2 and ispath
##########################################################################################################################
def checkIcons(num):
	global allIcons
	tst = 0
	path = config.plugins.setupGlass17.par39.value
	for x in allIcons:
		if fileExists(path + "/more_icons/i_type-" + str(num) + "/" + x + ".png"):
			tst += 1
	return tst == len(allIcons)
##########################################################################################################################					
def chnlSelChck():
	if fileExists(CHANSEL_FILE) and fileExists(CHANSEL_FILE.replace(".py","-ori17.py")):
		f = open(CHANSEL_FILE.replace(".py","-ori17.py"), "r").read()
		if f.find("def zap(self, nref=None, root=None") != -1:
			f = open(CHANSEL_FILE, "r").read()
			if f.find("def zap(self, nref=None, root=None") == -1:
				if not chnlSelPatch(False):
					setCFGoff()
					return 2
	enaMenuPy = 0
	if fileExists(CHANSEL_FILE):
		r = open(CHANSEL_FILE, "r")
		ena = False
		enaVti = False
		for line in r.readlines():
			if ena:
				if line.__contains__("				if old is None or ref == old:"):
					enaMenuPy += 1
				elif line.__contains__("				if ref == old:"):
					enaMenuPy += 10
				elif line.__contains__("if ref is None or ref != nref or forced:"):
					enaMenuPy += 1
				elif line.__contains__("self.session.nav.playService(lastservice) #revert"):
					enaMenuPy += 1
			if line.__contains__("if not root or not (root.flags & eServiceReference.isGroup):"):
				ena = True
			if line.__contains__("if config.usage.zap_pip.value and"):
				enaVti = True
		r.close()
	if (not enaVti and enaMenuPy == 3) or (enaVti and enaMenuPy == 4):
		return 1
	elif enaMenuPy > 9 or (enaVti and enaMenuPy == 3):
		if chnlSelPatch(False):
			if not chnlSelPatch():
				setCFGoff()
				return 2
			else:
				return 3			
		else:
			setCFGoff()
			return 2
	return 0
##########################################################################################################################
def chnlSelPatch(direct=True):
	# Warder Evolution safety rule: never patch image-owned ChannelSelection.py
	# on modern OpenATV. Preserve the legacy setting for old configurations,
	# but disable it instead of modifying core Enigma2 Python at runtime.
	if isATV:
		setCFGoff(62)
		return False
	if not direct and fileExists(CHANSEL_FILE) and fileExists(CHANSEL_FILE.replace(".py","-ori17.py")):
		shutil.copy2(CHANSEL_FILE.replace(".py","-ori17.py"), CHANSEL_FILE)
		return True
	elif not direct:
		return False	
	if not fileExists(CHANSEL_FILE): 
		return False
	txCH = chnlSelChck()
	if txCH == 1 or txCH == 3:
		return True
	elif txCH == 2:
		return False
	shutil.copy2(CHANSEL_FILE, CHANSEL_FILE.replace(".py","-ori17.py"))
	if not fileExists(CHANSEL_FILE) or not fileExists(CHANSEL_FILE.replace(".py","-ori17.py")):
		try:
			os.remove(CHANSEL_FILE.replace(".py","-ori2.py"))
		except OSError:
			pass
		return False
	r = open(CHANSEL_FILE, "r")
	ena = False
	ena2 = False
	breakRead = False
	allLines = ""
	secondWrite = 0
	ena3 = False
	for line in r.readlines():
		if line.__contains__("config.merlin"):
			breakRead = True
			break
		if ena and line.__contains__("				self.zap()"):
			line = line.replace("				self.zap()","				old = self.session.nav.getCurrentlyPlayingServiceReference()\n				self.session.nav.playService(ref)\n				if old is None or ref == old:\n					self.zap(forced=True)")
		elif ena and line.__contains__("				self.asciiOff()"):
			line = line.replace("				self.asciiOff()","					self.asciiOff()")
		elif ena and line.__contains__("				self.close(ref)"):
			line = line.replace("				self.close(ref)","					self.close(ref)")
		elif ena and line.__contains__("	def zap(self):"):
			line = line.replace("	def zap(self):","	def zap(self, forced=False):")
		elif ena and line.__contains__("	def zap(self, nref=None, root=None):"):
			line = line.replace("	def zap(self, nref=None, root=None):","	def zap(self, nref=None, root=None, forced=False):")
		elif ena and line.__contains__("		if ref is None or ref != nref:"):
			line = line.replace("		if ref is None or ref != nref:","		if ref is None or ref != nref or forced:")
			secondWrite += 1
			if not ena3: 
				ena = False
			elif ena3 and secondWrite == 2: 
				ena = False
		elif ena2 and line.__contains__("		self.close(None)"):
			line = line.replace("		self.close(None)","		lastservice=eServiceReference(self.lastservice.value)\n		if lastservice.valid():\n			self.session.nav.playService(lastservice) #revert\n		self.close(None)")
			ena2 = False
		if line.__contains__("if not root or not (root.flags & eServiceReference.isGroup):"):
			ena = True
		elif line.__contains__("		elif self.revertMode == MODE_RADIO:"):
			ena2 = True
		elif line.__contains__("if config.usage.zap_pip.value and"):
			ena3 = True
		allLines = allLines + line
	r.close()
	if breakRead:
		return False
	if not _atomicWriteText(CHANSEL_FILE, allLines):
		return False
	ena = chnlSelChck()
	if ena == 0:
		shutil.copy2(CHANSEL_FILE.replace(".py","-ori17.py"), CHANSEL_FILE)
		try:
			os.remove(CHANSEL_FILE.replace(".py","-ori17.py"))
		except OSError:
			pass
	elif ena == 1:
		return True
	return False
##########################################################################################################################
def writeStyleCfg(scrNum, num):
	state = False
	try:
		allLines = ""
		found = False
		f = open(SCREENSPATH + "g17Screens.cfg","r")
		for x in f.readlines():
			if x.replace("\n", "").startswith(str(scrNum)+"-"):
				allLines += str(scrNum)+"-"+str(num)+"\n"
				found = True
			else:	
				allLines += x
		if not found:
			allLines += str(scrNum)+"-"+str(num)+"\n"
		f.close()
		state = _atomicWriteText(SCREENSPATH + "g17Screens.cfg", allLines)
	except: pass
	return state
##########################################################################################################################
def checkStyle(num):
	allstyles = ['b_b','b_bl','b_br','b_l','b_r','b_tl','b_tr','b_t']
	tst = 0
	for x in allstyles:
		fileName = SKINPATH + "style/" + str(num) + "/" + x + ".png"
		if fileExists(fileName):
			tst += 1
	if tst == 8:
		return True
	else:
		return False
##########################################################################################################################			
def checkStyleFull(scrNum,cfg=False):
	def setdefStyle(scr, cfg):
		msg = "?"
		if checkStyle(1):	
			if writeStyleCfg(scr, "1"):
				if cfg:
					config.plugins.setupGlass17.par44.value = 1
					config.plugins.setupGlass17.par44.save()
				msg = "1"
		return msg
	style = -1
	try:
		f = open(SCREENSPATH + "g17Screens.cfg","r")
		for x in f.readlines():
			if x.replace("\n", "").startswith(str(scrNum)+"-"):
				x = x.strip().split("-")
				style = int(x[1])
				break	
		f.close()
	except: pass
	msg2 = "?"
	color = "#006cbcf0"
	if style != -1 and style < MAXICONS:
		if checkStyle(style):		
			msg2 = str(style)
			if cfg:
				config.plugins.setupGlass17.par44.value = style 
				config.plugins.setupGlass17.par44.save()
		else:
			msg2 = setdefStyle(scrNum, cfg)
		color = readcolorStyle(msg2)
	else:
		msg2 = setdefStyle(scrNum, cfg)
	if cfg:
		config.plugins.setupGlass17.par45.value = color 
		config.plugins.setupGlass17.par45.save()
	return msg2, color
##########################################################################################################################
def readcolorStyle(num):
	color = "#006cbcf0"
	try:
		f = open("%sstyle/%s/title_color.cfg" % (SKINPATH, num),"r").readline()
		f = f.replace("\n", "").strip().split()[0] 
		if len(f) == 9:
			color = int(f.replace("#", "0x"), 16)
			color = f
	except: pass
	return color
##########################################################################################################################
def setMenuPyo(what="new17"):
	# Modern OpenATV owns Screens/Menu.py. Do not swap image Python modules at runtime.
	if isATV:
		return False
	whatOld = "orig17"
	if what == "orig17":
		whatOld = "new17"
	path = SCREENSPATH + "Menu"
	ena = False
	for x in ['.py','.pyo','.pyc']: 
		whatNew = path + "-" + what + x
		if fileExists(whatNew):
			ena = True
			break
	if ena:
		for x in ['.py','.pyo','.pyc']:
			f = path + x
			h16 = path + "-new16" + x
			h18 = path + "-new18" + x
			if fileExists(f):
				if "orig" in whatOld and (not fileExists(h16) or (fileExists(h16) and os.path.getsize(h16) != os.path.getsize(f))) and (not fileExists(h18) or (fileExists(h18) and os.path.getsize(h18) != os.path.getsize(f))):
					shutil.copy2(f, "%s-%s%s" % (path, whatOld, x))
				try:
					os.remove(f)
				except OSError:
					pass
			if fileExists(path + "-" + what + x):
				shutil.copy2("%s-%s%s" % (path, what, x), f)
	return True
##########################################################################################################################
def chckPath(path):
	# A blank/corrupt legacy picon base path must fail safely instead of
	# indexing an empty string and crashing setupGlass17.
	path = (path or "").strip()
	if not path or path == "/":
		return False
	if path.endswith("/"):
		path = path[:-1]
	allpicons = ['poster','picon_BQT','picWeaInf','animIconWeather','piconProv','piconSat','piconCam','menuIconsBig','picon_50x30','picon','picon_400x240','piconOled','g17_setup_pict','more_icons','extraScreens17','menuIcons','weatherIcons','ZZPicon']	
	msg = True
	if not os.path.exists(path):
		tmp = path.strip().split("/")
		p = ""
		for x in range(0,len(tmp)):
			if tmp[x] != "":
				p += "/" + tmp[x]
				if not os.path.exists(p):
					try:
						os.mkdir(p)
					except OSError:
						return False
	for x in allpicons:
		if not os.path.exists(path+"/"+x):
			try:
				os.mkdir(path+"/"+x)
			except OSError:
				pass
			if not os.path.exists(path+"/"+x):
				msg = False
	return msg
##########################################################################################################################
def _atomicWriteText(path, data):
	"""Replace a text file atomically, preserving its mode when possible."""
	directory = os.path.dirname(path) or "."
	tmp = os.path.join(directory, ".%s.warder-tmp" % os.path.basename(path))
	mode = None
	try:
		if os.path.exists(path):
			mode = os.stat(path).st_mode & 0o7777
		with open(tmp, "w") as handle:
			handle.write(data)
			handle.flush()
			os.fsync(handle.fileno())
		if mode is not None:
			os.chmod(tmp, mode)
		os.replace(tmp, path)
		return True
	except OSError:
		try:
			os.remove(tmp)
		except OSError:
			pass
		return False

##########################################################################################################################
def windowStyle(what, color):
	allLines = ""
	allstyles = ['b_b','b_bl','b_br','b_l','b_r','b_tl','b_tr','b_t']
	ena = False
	r = open(SKINXML,"r")
	for line in r.readlines():
		if line.__contains__("<windowstyle type=\"skinned\" id=\"0\">"):
			ena = True
		if ena:
			if line.__contains__("<color name=\"WindowTitleForeground"):
				line = "    <color name=\"WindowTitleForeground\" color=\""+color+"\" />\n"
				ena = False
		allLines = allLines + line
	r.close()
	if not _atomicWriteText(SKINXML, allLines):
		return False
	for x in allstyles:
		shutil.copy2(os.path.join(SKINPATH, "style", what, x + ".png"), os.path.join(SKINPATH, "general", x + ".png"))
	return True
##########################################################################################################################			
def standbyOledOnOff():
	allLines = ""
	r = open(USERXML,"r")
	for line in r.readlines():
		if line.__contains__("<screen name=\"StandbySummary"):
			if line.__contains__("position=\"0,"):
				line = line.replace("position=\"0,", "position=\"200,")
			else:
				line = line.replace("position=\"200,", "position=\"0,")
		allLines = allLines + line
	r.close()
	_atomicWriteText(USERXML, allLines)
##########################################################################################################################
def getServiceInfoValue(info, what, ref=None):
	v = ref and info.getInfo(ref, what) or info.getInfo(what)
	if v != iServiceInformation.resIsString:
		return "N/A"
	return ref and info.getInfoString(ref, what) or info.getInfoString(what)
##########################################################################################################################    		
def changeSkinXml(what, new="1", old="1", oled=False):
	allLines = ""
	ena1 = False
	f = ({True:USERXML, False:SKINXML}[oled])
	try:
		r = open(f,"r")
		found = False
		for line in r.readlines():
			if oled:
				if line.__contains__("<screen name=\""+what+"\""):
					line = line.replace(what, what+"-"+old)
				elif line.__contains__("<screen name=\""+what+"-"+new+"\""):
					line = line.replace(what+"-"+new, what)
				allLines += line
			else:
				if line.__contains__("<screen name=\""+what+"\"") or (not found and line.__contains__("</skin>")):
					ena1 = True				
					ena = False
					ena2 = False
					if isATV and line.__contains__('<screen name="ChannelSelection"'):
						ena2 = True
					s = open(SKINALL,"r")
					for i in s.readlines():
						if i.__contains__("<screen name=\""+what+"-"+new+"\""):
							ena = True
							i = i.replace(what+"-"+new, what)
						if ena:
							if ena2 and i.__contains__('<widget name="key_'):
								i = i.replace('<widget name="key_','<widget render="Label" source="key_')
							allLines += i
							if i.__contains__("</screen>"):
								ena = False
								found = True
								ena2 = False								
								break
					s.close()
				else:
					if not ena1 and line != "\n":
 							allLines += line                       
					if ena1 and line.__contains__("</screen>"):                        
 							ena1 = False
		r.close()
		if allLines.find("</skin>") == -1:
			allLines += "\n</skin>\n"		
		_atomicWriteText(f, allLines)
	except: pass
	return True
##########################################################################################################################    		
def changePIGres():
	allLines = ""
	ena = False
	direct = True
	if config.plugins.setupGlass17.par68.value == "0":
		direct = False
	try:
		r = open(SKINXML,"r")
		for line in r.readlines():
			if ena and line.__contains__('session.VideoPicture'):
				if direct:
					line = line.replace('position="157,166"', 'position="66,120"').replace('size="697,435"', 'size="882,528"')
					line = line.replace('position="157,156"', 'position="66,109"').replace('position="1051,166"', 'position="966,120"')
					line = line.replace('position="138,181"', 'position="52,135"')
				else:
					line = line.replace('position="66,120"', 'position="157,166"').replace('size="882,528"', 'size="697,435"')
					line = line.replace('position="66,109"', 'position="157,156"').replace('position="966,120"', 'position="1051,166"')
					line = line.replace('position="52,135"', 'position="138,181"')
			allLines = allLines + line
			if line.__contains__('hd_glass17/menu/pig_frame-all-fs8.png'):
				ena = True
			else:
				ena = False
		r.close()
		_atomicWriteText(SKINXML, allLines)
	except: pass
	return "p"
##########################################################################################################################
def changeScreenXml(what, new="1", old="1"):
	o = False
	if what == "menu":
		tmp = ["menu_mainmenu", "menu_information", "menu_setup", "menu_scan", "menu_system", "menu_harddisk","menu_shutdown", "Menu"]
	elif what == "oled":
		o = True
		tmp = ["InfoBarSummary","StandbySummary"]
	for x in tmp:
		xxx = changeSkinXml(x, new, old, o)
	if what == "menu" and new in ("12","13"): 
		tmp = changePIGres()
	return True
##########################################################################################################################  
def setTypeIcos(num):
	global allIcons
	for x in allIcons:
		fileName = config.plugins.setupGlass17.par39.value + "/more_icons/i_type-" + str(num) + "/" + x + ".png"
		if fileExists(fileName):
			destination = SKINPATH + "icons/" + x + ".png"
			try:
				if os.path.lexists(destination):
					os.unlink(destination)
				shutil.copy2(fileName, destination)
			except OSError:
				pass
	return True
##########################################################################################################################
def setTypePicon():
	what = ({"Black":"", "White":"w"}[config.plugins.setupGlass17.par41.value])
	for x in ("marker","bouquet","next","picon_default","buttons/nopicon","piconWdef","icons/75"):
		try:
			shutil.copy2("%s%s-%sdef.png" % (SKINPATH, x, what), "%s%s.png" % (SKINPATH, x))
		except OSError:
			pass
##########################################################################################################################
def ShowHideViaKey():
	if keyManage.TunerTest() and keyManage.dialogKey is not None:
		if config.plugins.setupGlass17.par9.value:
			config.plugins.setupGlass17.par9.value = False
			keyManage.dialogKey.hide()
			if config.plugins.setupGlass17.par73.value:
				keyManage.stopTimer()
		else:
			config.plugins.setupGlass17.par9.value = True
			keyManage.dialogKey.show()
			if config.plugins.setupGlass17.par73.value:
				keyManage.startTimer()
##########################################################################################################################
class thumbList(MenuList):
		def __init__(self, list, enableWrapAround = False):
			MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
			self.l.setFont(0, gFont('Prive3', 30))
			self.l.setFont(1, gFont('Prive3', 25))
			self.l.setFont(2, gFont('Prive3', 33))
			self.l.setItemHeight(37)
class thumbList2(MenuList):
		def __init__(self, list, enableWrapAround = False):
			MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
			self.l.setFont(0, gFont('Prive3', 30))
			self.l.setFont(1, gFont('Prive3', 22))
			self.l.setFont(2, gFont('Prive3', 36))
			self.l.setFont(3, gFont('Prive3', 28))
			self.l.setItemHeight(97)						
##########################################################################################################################
def setEncodingUser(direction=True):
	# encoding.conf belongs to the image on OpenATV; keep the legacy option inert.
	if isATV:
		setCFGoff(59)
		return False
	state = False
	if direction:
		if fileExists(ENC_U):      		
			if not fileExists(ENC_O):
				shutil.copy2(ENC_C, ENC_O)
			try:
				if os.path.lexists(ENC_C):
					os.unlink(ENC_C)
				shutil.copy2(ENC_U, ENC_C)
			except OSError:
				return False
			state = True
	else:
		if fileExists(ENC_O):      		
			try:
				if os.path.lexists(ENC_C):
					os.unlink(ENC_C)
				shutil.copy2(ENC_O, ENC_C)
			except OSError:
				return False
			state = True
	return state
##########################################################################################################################
def setCFGoff(v=62):
	if v == 59:
		config.plugins.setupGlass17.par59.value = False					
		config.plugins.setupGlass17.par59.save()
	else:
		config.plugins.setupGlass17.par62.value = False					
		config.plugins.setupGlass17.par62.save()
	configfile.save()

def setOledXml(what, d=USERXML):
	try:
		if os.path.lexists(d):
			os.unlink(d)
		shutil.copy2(what, d)
		return True
	except OSError:
		return False

def chckUserHdg():
	ena = False
	if os.path.exists(USERXML):
		try:
			c = open(USERXML, "r").read()
			ena = not (c.find("name=\"InfoBarSummary-") != -1 and c.find("g17ClockToText\">") != -1)
			if ena:
				ena = setOledXml(USERXML, USERORI)						
		except: pass	
	return ena	

def setOledMore(msg=""):
	x = setOledXml(USERHDG)
	if config.plugins.setupGlass17.par15.value != "1":		
		msg += _("OLED type") + "\n"
		x = changeScreenXml("oled", config.plugins.setupGlass17.par15.value)
	if config.plugins.setupGlass17.par40.value:	
		msg += _("Set OLED off in Standby") + "\n"
		standbyOledOnOff()
	return msg

def getTemp(dev):
	tmp1 = 0
	commands = []
	for smartctl in ("/usr/sbin/smartctl", "/sbin/smartctl", "/usr/bin/smartctl"):
		if os.path.isfile(smartctl):
			commands.append(("smartctl", [smartctl, "-a", dev]))
			break
	if os.path.isfile("/usr/bin/hdd_temp_hdg17"):
		commands.append(("hddtemp", ["/usr/bin/hdd_temp_hdg17", "-q", "-n", dev]))
	commands.append(("hddtemp", ["hddtemp", "-n", "-q", dev]))
	if config.plugins.setupGlass17.par21.value:
		if os.path.isfile("/usr/bin/hdd_temp_hdg17"):
			commands.append(("hddtemp", ["/usr/bin/hdd_temp_hdg17", "-q", "-n", "-w", dev]))
		commands.append(("hddtemp", ["hddtemp", "-q", "-n", "-w", dev]))
	for kind, command in commands:
		try:
			output = subprocess.check_output(command, universal_newlines=True, stderr=subprocess.STDOUT)
			if kind == "smartctl":
				for line in output.splitlines():
					if "Temperature" not in line:
						continue
					values = re.findall(r"(?<![\w.-])-?\d+(?![\w.-])", line)
					for value in reversed(values):
						candidate = int(value)
						if 1 <= candidate <= 125:
							tmp1 = candidate
							break
					if tmp1:
						break
			else:
				match = re.search(r"-?\d+", output.strip())
				if match:
					candidate = int(match.group(0))
					if 1 <= candidate <= 125:
						tmp1 = candidate
		except (OSError, subprocess.CalledProcessError, ValueError):
			pass
		if tmp1:
			break
	return tmp1

def chckVolMute():
	if config.plugins.setupGlass17.par51.value != 1200 or config.plugins.setupGlass17.par52.value != 120:
		allLines = ""
		newData = 'position="%s,%s"' % (str(config.plugins.setupGlass17.par51.value),str(config.plugins.setupGlass17.par52.value))
		try:
			r = open(SKINXML,"r")
			for line in r.readlines():
				if line.__contains__('<screen name="Volume') or  line.__contains__('<screen name="Mute'):
					line = line.replace('position="1200,120"',newData)
				allLines += line
			r.close()
			_atomicWriteText(SKINXML, allLines)
			return True
		except: pass
	return False

def cChannelsel(c1="#cdcdcd",c2="#6cbcf0",c3="#6cbcf0",c4="#dddddd"):
	try:
		allLines = ""
		what = 'colorServiceDescription="'+config.plugins.setupGlass17.par109.value+'"'+' colorServiceDescriptionSelected="'+config.plugins.setupGlass17.par110.value+'"'+' foregroundColorSelected="'+config.plugins.setupGlass17.par111.value+'"'+' foregroundColor="'+config.plugins.setupGlass17.par117.value+'"' 
		r = open(SKINXML,"r")
		ena = False
		for line in r.readlines():
			if line.__contains__('<screen name="ChannelSelection"'):
				ena = True
			if ena and line.__contains__('<widget name="list"'):
				line = line.replace('colorServiceDescription="'+c1+'"'+' colorServiceDescriptionSelected="'+c2+'"'+' foregroundColorSelected="'+c3+'"'+' foregroundColor="'+c4+'"', what)
				if ENA_P_CH and not 'progressBarWidth="90"' in line:
					line = line.replace('picServiceEventProgressbar="bar_ch-fs8.png"','picServiceEventProgressbar="bar_ch-fs8.png" progressBarWidth="90"')				
				ena = False
			allLines += line
		r.close()
		_atomicWriteText(SKINXML, allLines)
	except: pass
	return "c"
		
def changeChF():
	try:
		allLines = ""
		r = open(SKINXML,"r")
		ena = ena2 = False
		buffLine = ""
		for line in r.readlines():
			if line.__contains__('<screen name="ChannelSelection"'):
				ena = True
			if line.__contains__('</screen>'):
				ena = False
			if ena:
				if line.__contains__('<widget name="list"'):
					vv = config.plugins.setupGlass17.par147.value
					if vv == "1" and (config.plugins.setupGlass17.par145.value != "0" or config.plugins.setupGlass17.par146.value != "0"):
						vv = str(max(int(config.plugins.setupGlass17.par145.value),int(config.plugins.setupGlass17.par146.value))+9)
						line = calc(line,' serviceItemHeight="',vv)
					if not vv in ("0","1"):
						line = calc(line,' serviceItemHeight="',vv)
					if config.plugins.setupGlass17.par145.value != "0":
						line = calc(line,' serviceNameFont="Prive4;',config.plugins.setupGlass17.par145.value)
					if config.plugins.setupGlass17.par146.value != "0":
						line = calc(line,' serviceInfoFont="Prive4;',config.plugins.setupGlass17.par146.value)
					allLines += line
				elif ena2:
					if line.__contains__('g17ServiceNameEvent">ExtendedDescription</convert>'):
						allLines += calc(buffLine,' font="Prive4;',config.plugins.setupGlass17.par148.value) + line
					else:
						allLines += buffLine + line
					ena2 = False
				else:
					if line.__contains__('source="ServiceEvent'):
						if line.__contains__('render="g17MetrixHDRunningText'):
							allLines += calc(line,' font="Prive4;',config.plugins.setupGlass17.par148.value)
						else:
							buffLine = line
							ena2 = True
					else:
						allLines += line
			else:
				allLines += line
		r.close()
		_atomicWriteText(SKINXML, allLines)
	except: pass
	return "o"
   	
def setFontEventEpgsel(val):
	allLines = ""
	ena3 = ena = ena2 = ena1 = ena4 = ena5 = ena6 = ena7 = False
	val1 = val
	if val == "0":
		val1 = "34"	
	if os.path.isfile(SHAREPATH + "PLi-FullHD/skin.xml") or os.path.isfile(PYTHONPATH + "Plugins/SystemPlugins/OBH/__pycache__/") or os.path.isfile(PYTHONPATH + "Plugins/Satdreamgr/__init__.pyo"):
		ena1 = True
	try:                               
		r = open(SKINXML,"r")
		for line in r.readlines():
			if (ENA_ELPLI or ENA_P_CH) and line.__contains__('<widget name="timerlist"'):
				if not line.__contains__('setServiceNameFont="Prive4;34"'):
					line = line.replace('name="timerlist"','name="timerlist" setServiceNameFont="Prive4;34"')			
				if not line.__contains__('setEventNameFont="Prive4;32"'):
					line = line.replace('name="timerlist"','name="timerlist" setEventNameFont="Prive4;32"')
				if not line.__contains__('setFont="Prive4;30"'):
					line = line.replace('name="timerlist"','name="timerlist" setFont="Prive4;30"')
				if not line.__contains__('satPosLeft="320"'):
					line = line.replace('name="timerlist"','name="timerlist" satPosLeft="320"')
				if not line.__contains__('iconMargin="10"'):
					line = line.replace('name="timerlist"','name="timerlist" iconMargin="10"')
				if not line.__contains__('rowSplit="52"'):
					line = line.replace('name="timerlist"','name="timerlist" rowSplit="52"')
			if ENA_BH:
				if line.__contains__('<widget name="timerlist"'):   
					if not line.__contains__('setServiceNameFont="Regular;28"'):
						line = line.replace('itemHeight="105"','itemHeight="105" setServiceNameFont="Regular;28" setFont="Regular;28"')	
				if line.__contains__('name="MovieSelection"'):
					ena2 = True
				elif ena2 and line.__contains__('<widget name="list"') and not line.__contains__('columnsOriginal="'):
					line = line.replace('font="Prive4;34" itemHeight="75"','font="Regular;28" columnsOriginal="400,420" columnsCompactDescription="300,420,170" compactColumn="180,420" itemHeights="113,68,34" fontSizesOriginal="30,26,24" fontSizesCompact="28,24" fontSizesMinimal="28,24"')
			if ENA_D == 'debpkg':
				if line.__contains__('name="MovieSelection"'):
					ena6 = True
				elif ena6 and line.__contains__('<widget name="list"'):
					line = line.replace('font="Prive4;34" itemHeight="75"','itemHeight="75"')
			if ena1:
				if line.__contains__('name="MovieSelection"'):
					ena2 = True
				elif ena2 and line.__contains__('<widget name="list"') and not line.__contains__('columnsOriginal="'):
					line = line.replace('font="Prive4;34" itemHeight="75"','columnsOriginal="400,420" columnsCompactDescription="300,420,170" compactColumn="420" itemHeights="100,75,45" fontSizesOriginal="32,26,24" fontSizesCompact="32,28" fontSizesMinimal="32,24"')
				elif ena2 and line.__contains__('name="key_red"'):
					line = line.replace('name="key_red"','render="Label" source="key_red"')
				elif ena2 and line.__contains__('name="key_green"'):
					line = line.replace('name="key_green"','render="Label" source="key_green"')
				elif ena2 and line.__contains__('name="key_yellow"'):
					line = line.replace('name="key_yellow"','render="Label" source="key_yellow"')
				elif ena2 and line.__contains__('name="key_blue"'):
					line = line.replace('name="key_blue"','render="Label" source="key_blue"')
				if line.__contains__('name="EPGSelectionMulti"'):
					ena4 = True
				elif ena4 and line.__contains__('<widget name="list"') and not line.__contains__('setColGap="20"'):
					line = line.replace('<widget name="list"','<widget name="list" setColGap="20" setTimeWidth="135" setEventItemFont="Prive3;33" setEventTimeFont="Prive3;30"')
			if line.__contains__('</screen>'):
				ena3 = False
				ena2 = False
				ena = False
				ena4 = False
				ena5 = False
				ena6 = False
				ena7 = False
			if line.__contains__('<screen name="EventView"') or (line.__contains__('<screen name="EPGSelection"') and val != "0"):    
				ena3 = True
			if ENA_ELPLI and line.__contains__('<screen name="EPGSelection"'):
				ena = True
			if ENA_PLI2 and (line.__contains__('<screen name="TimerEditList"') or line.__contains__('<screen name="TimerLog"') or line.__contains__('<screen name="EPGSelection"') or line.__contains__('<screen name="EventView"') or line.__contains__('<screen name="EPGSelectionMulti"')):
				ena5 = True
			if ISP38 and isATV and (line.__contains__('<screen name="EPGSelection"') or line.__contains__('<screen name="EventView"')):
				ena7 = True
			if (ena5 or ena7) and line.__contains__('<widget name="key_'):
				line = line.replace('<widget name="key_','<widget render="Label" source="key_')
			if ena3 and (line.__contains__('<widget name="epg_description"') or line.__contains__(' source="Event"')):
				line = calc(line,' font="Prive4;',val1)
			if ena and line.__contains__('name="list"') and not line.__contains__('setEventItemFont="'):
				line = line.replace('name="list"','name="list" setEventItemFont="Prive4;30"')
			allLines += line
		r.close()
		_atomicWriteText(SKINXML, allLines)
	except: pass
	return "f"
	
def setFontListEpg(val):
	allLines = ""
	try:
		r = open(SKINXML,"r")
		for line in r.readlines():
			if line.__contains__('<parameter name="EPGlistFont1"'):
				allLines += calc(line,' value="Prive4;',val)
			elif line.__contains__('<parameter name="EPGlistFont2"'):    
				allLines += calc(line,' value="Prive4;',str(int(val)-3))
			elif line.__contains__('<alias name="EPGList0"') or line.__contains__('<alias name="EPGList1"'): 
				allLines += calc(line,' size="',val)
			else:
				allLines += line
		r.close()
		_atomicWriteText(SKINXML, allLines)
	except: pass
	return "el"

def lbs():
	allLines = ""
	ena = False
	ena2 = False
	newBig = None
	newMed = None
	newBig2 = None
	newMed2 = None
	try:
		r = open(SKINXML,"r")
		for line in r.readlines():
			if ena:
				if line.__contains__('type="Bigger"'):
					a = config.plugins.setupGlass17.par153.value
					allLines += calc(line,' size="',({True:"36", False:a}[a == "0"]))
				elif line.__contains__('type="Big"'):    
					a = config.plugins.setupGlass17.par154.value
					allLines += calc(line,' size="',({True:"33", False:a}[a == "0"]))
					if int(a) > 33 or a == "0":
						newBig = ({True:"45", False:str(int(a)+7)}[a == "0"])					
						newBig2 = ({True:"40", False:str(int(a)+3)}[a == "0"])
				elif line.__contains__('type="Medium"'): 
					a = config.plugins.setupGlass17.par155.value
					allLines += calc(line,' size="',({True:"30", False:a}[a == "0"]))
					if int(a) > 30 or a == "0":
						newMed = ({True:"45", False:str(int(a)+7)}[a == "0"])	
						newMed2 = ({True:"36", False:str(int(a)+3)}[a == "0"])
				elif line.__contains__('type="Small"'): 
					a = config.plugins.setupGlass17.par156.value
					allLines += calc(line,' size="',({True:"28", False:a}[a == "0"]))
				elif line.__contains__('type="Smaller"'): 
					a = config.plugins.setupGlass17.par157.value
					allLines += calc(line,' size="',({True:"26", False:a}[a == "0"]))
				else:
					allLines += line
			elif ena2:
				if newBig is not None and (line.__contains__('type="ServiceInfoList"') or line.__contains__('type="SelectionList"') or line.__contains__('type="ParentalControlList"') or line.__contains__('type="ChoiceList"') or line.__contains__('type="HelpMenuList"')): 
					a = calc(line,' itemHeight="',newBig)
					if ' textHeight="' in a:
						allLines += calc(a,' textHeight="',newBig2)
					else:
						allLines += a
				elif newMed is not None and (line.__contains__('type="MediaplayerPlayList"') or line.__contains__('type="FileList"') or line.__contains__('type="HelpMenuList"')): 
					a = calc(line,' itemHeight="',newMed)
					if ' textHeight="' in a:
						allLines += calc(a,' textHeight="',newMed2)
					else:
						allLines += a
				else:
					allLines += line
			else:
				allLines += line
			if line.__contains__('</borderset>'):
				ena = True
			elif line.__contains__('</windowstyle>'):
				ena = False
			elif line.__contains__('<components>'):
				ena2 = True
			elif line.__contains__('</components>'):
				ena2 = False
		r.close()
		_atomicWriteText(SKINXML, allLines)
	except: pass
	return _("Listbox font size") + "\n"

def chckFifo():
	# Modern OpenATV owns Screens/ServiceScan.py; never rewrite image Python.
	if isATV:
		config.plugins.setupGlass17.par67.value = False
		config.plugins.setupGlass17.par67.save()
		configfile.save()
		return False
	f = SCREENSPATH + "ServiceScan.py"
	if os.path.isfile(f):
		allLines = ""
		a = config.plugins.setupGlass17.par67.value
		ena = False
		try:
			r = open(f,"r")
			for line in r.readlines():
				if line.__contains__('servicelist') and line.__contains__('FIFOList') and line.__contains__('len'):
					if (a and not "122" in line) or (not a and not "10" in line):
						ena = True
						if line.__contains__('len ='):
							tt = calc(line,'len =',({True:"122", False:"10"}[a]),')')
							if not "\n" in tt:
								tt += "\n"
							allLines += tt
						elif line.__contains__('len='):
							tt = calc(line,'len=',({True:"122", False:"10"}[a]),')')
							if not "\n" in tt:
								tt += "\n"
							allLines += tt
						else:
							allLines += line
					else:
						allLines += line
				else:
					allLines += line
			r.close()
			if ena:
				_atomicWriteText(f, allLines)
		except: pass
	return ena

def chckPigFont(s=0):
	x = ""
	if config.plugins.setupGlass17.par68.value != "0":			
		x += changePIGres()			
	if s != 1:
		x += cChannelsel()
		if config.plugins.setupGlass17.par148.value != "0" or config.plugins.setupGlass17.par145.value != "0" or config.plugins.setupGlass17.par146.value != "0" or config.plugins.setupGlass17.par147.value != "0":
			x += changeChF()
	if s != 0:
		x += setFontEventEpgsel(config.plugins.setupGlass17.par53.value)
	return x

def chMT():
	x = "2"
	if config.plugins.setupGlass17.par47.value:
		x = "1"
	try:
		shutil.copy2("%smute-%s.png" % (SKINPATH, x), "%smute.png" % SKINPATH)
	except OSError:
		pass
	return _("Mute picture transparency") + "\n"
##########################################################################################################################
class AutoStartChck17():
	def __init__(self):
		self.cmd = ""
		self.start_timerExec = eTimer()
		try:
			self.start_timerExec_conn = self.start_timerExec.timeout.connect(self.rstnow)
		except AttributeError:
			self.start_timerExec.timeout.get().append(self.rstnow)
		self.start_timerChck = eTimer()
		try:
			self.start_timerChck_conn = self.start_timerChck.timeout.connect(self.runchck)
		except AttributeError:
			self.start_timerChck.timeout.get().append(self.runchck)
		
	def startHdgchck(self, session):
		self.session = session				
		self.start_timerChck.start(15000, True)

	def runchck(self):
		self.start_timerChck.stop()
		def chckSkytec():
			tmpx = False
			try:
				r = open("/etc/image-version", "r")
				for line in r.readlines():
					if line.__contains__("kleio") or line.__contains__("SKYTEC"):
						tmpx = True
						break
			except: pass
			return tmpx     		
		def chckPlBrowser(what='source="pluginlist'):
			tmpx = False
			try:
				for x in ["skin_default.xml","skin.xml","PLi-HD/skin_plugins.xml","PLi-FullHD/skin_plugins.xml"]:
					if not tmpx and os.path.isfile(SHAREPATH + x):
						r = open(SHAREPATH + x, "r").read()
						if r.find(what) != -1:
							tmpx = True
							break
			except: pass
			return tmpx 
		msg = ""
		ver = '1.0.0'
		if XCPU != "mipsel":
			# Select architecture helpers without deleting package-owned variants.
			try:
				shutil.copy2("/usr/bin/btrGen17-%s" % XCPU, "/usr/bin/btrGen17")
				shutil.copy2("/usr/bin/hdd_temp_hdg17-%s" % XCPU, "/usr/bin/hdd_temp_hdg17")
				msg += _("Set binaries") + "\n"
			except OSError:
				pass
		ver, x = readHWtype()
		isOk = ver != "Dream Multimedia"
		# Seed the generated FullHDGlass17 overlay only on first use.
		# Existing USERHDG is user state (and a package conffile) and must survive
		# GUI restarts, package upgrades and hardware detection.
		if not os.path.exists(USERHDG):
			if (os.path.exists(PYTHONPATH+'Plugins/PLi') or isATV) and not isOk:
				template = "/etc/enigma2/skin_user-17%s.xml" % ({False:'2', True:'3'}[IS800SE or "dm820" in x])
			elif isOk:
				template = "/etc/enigma2/skin_user-172.xml"
			else:
				template = None
			if template and os.path.isfile(template):
				try:
					shutil.copy2(template, USERHDG)
				except OSError:
					pass
		# Keep packaged architecture helpers and overlay templates installed.
		# They are package-owned files and may be needed again after hardware/image
		# changes; deleting them at runtime also breaks package-manager ownership.
		if (isOk and ver != "Unknown") or (not isOk and ("dm920" in x or "dm900" in x or x == "one" or x == "two")):
			if ver == "AZbox":
				ver = "Zbox"
			if "DUO2" in x.upper():
				ver = "Duo"
			if "4k" in x:
				if "timo" in x:			
					ver = "Ultimo"			
					if ISVTI:
						x = changeSkinXml("g17SetupSummary")			
				elif "solo" in x:			
					ver = "Solo"	
				elif "duo" in x:			
					if "se" in x:
						ver = "e"
					else:
						ver = "4kDuo"
			if not isOk:
				if "dm920" in x:
					ver = "920"
				elif "dm900" in x:
					ver = "0"
				elif x == "one":
					ver = "o"
				elif x == "two":
					ver = "t"
			try:
				shutil.copy2("%smenu/box-%s.png" % (SKINPATH, ver[0]), "%smenu/box.png" % SKINPATH)
			except OSError:
				pass
		for x in ["A", "V", "Z", "C", "D", "U", "S", "9", "4", "0", "o", "t", "e"]:  
			try:
				os.remove("%smenu/box-%s.png" % (SKINPATH, x))
			except OSError:
				pass
		isOk, color = checkStyleFull(config.plugins.setupGlass17.par6.value, False)
		x = str(config.plugins.setupGlass17.par44.value)
		if isOk != x:
			try:
				if checkStyle(int(x)):	
					if writeStyleCfg(config.plugins.setupGlass17.par6.value, x):
						isOk = x
					else:
						config.plugins.setupGlass17.par44.value = 1
						config.plugins.setupGlass17.par44.save()
						configfile.save()
			except: pass
		if color != config.plugins.setupGlass17.par45.value:
			x = 0
			try:
				color = config.plugins.setupGlass17.par45.value.strip()
				if len(color) == 9:
					x = int(color.replace("#","0x"), 16)
			except: pass
			if x == 0:
				config.plugins.setupGlass17.par45.value = "#006cbcf0"
				config.plugins.setupGlass17.par45.save()
				configfile.save()
			else:
				try:
					f = open("%sstyle/%s/title_color.cfg" % (SKINPATH, isOk), "w")
					f.write(color)
					f.close()
				except: pass									
		if (isOk != "1" and isOk != "?") or color != "#006cbcf0":
			x = windowStyle(isOk, color)
			msg += _("Style:")+str(config.plugins.setupGlass17.par44.value)
			msg += ", " + _("Title color:")+str(config.plugins.setupGlass17.par45.value) + "\n"
			tmp = True
		if config.plugins.setupGlass17.par41.value != "Black":		
			msg += _("Picon default, marker, next ...") + ": " + _("White") + "\n"
			setTypePicon()
		if config.plugins.setupGlass17.par1.value != 1:
			if checkIcons(config.plugins.setupGlass17.par1.value):
				x = setTypeIcos(config.plugins.setupGlass17.par1.value)
				msg += _("Icons type") + ": " + str(config.plugins.setupGlass17.par1.value) + "\n"
			else:
				config.plugins.setupGlass17.par1.value = 1                                              
				config.plugins.setupGlass17.par1.save()
				configfile.save()
		if config.plugins.setupGlass17.par7.value != "List":			
			if not config.plugins.setupGlass17.par7.value == "Icons" and not config.plugins.setupGlass17.par7.value == "Icons Right" and not config.plugins.setupGlass17.par7.value == "Icons Bar":
				msg += _("Menu type") + "\n"
				x = changeScreenXml("menu", menusel(config.plugins.setupGlass17.par7.value))
			elif chckPMS():
				if setMenuPyo():
					msg += _("Menu type") + "\n"
					x = changeScreenXml("menu", menusel(config.plugins.setupGlass17.par7.value))
				else:
					config.plugins.setupGlass17.par7.value = "List"
					config.plugins.setupGlass17.par7.save()
					configfile.save()
		if config.plugins.setupGlass17.par4.value:	
			x = changeSkinXml("InfoBar","3")
			msg += _("Permanent Extra Infobar") + "\n"
		else:
			# Reapply the configured variant after upgrades that preserve skin.xml.
			if config.plugins.setupGlass17.par14.value != "1":
				msg += _("Standard Infobar type") + "\n"
			x = changeSkinXml("InfoBar",config.plugins.setupGlass17.par14.value)
		x = chckUserHdg()
		if config.plugins.setupGlass17.par15.value != "0":       
			msg = setOledMore(msg)
		if config.plugins.setupGlass17.par18.value != "1":		
			msg += _("Volume type") + "\n"
			x = changeSkinXml("Volume", config.plugins.setupGlass17.par18.value)
			x = changeSkinXml("Mute")
		if chckVolMute():
			msg += _("Set Volume and Mute positions") + "\n"
		if isATV or config.plugins.setupGlass17.par19.value != "35":		
			msg += _("Channel selection type") + "\n"
			x = changeSkinXml("ChannelSelection", config.plugins.setupGlass17.par19.value)
		if config.plugins.setupGlass17.par224.value != "1":		
			msg += _("Movie selection type") + "\n"
			x = changeSkinXml("MovieSelection", config.plugins.setupGlass17.par224.value)
		if config.plugins.setupGlass17.par54.value != "7":		
			msg += _("EPG selection type") + "\n"
			x = changeSkinXml("EPGSelection", config.plugins.setupGlass17.par54.value)
		if config.plugins.setupGlass17.par229.value != "1":		
			msg += _("EventView type") + "\n"
			x = changeSkinXml("EventView", config.plugins.setupGlass17.par229.value)
		if ISVTI:
			for i in ("TaskListScreen","VTIPasswdScreen","VTISubMenu","VTIStatusListMenu","VTIMainMenu","AudioZap","PictureInPicture","AnimationSetupScreen"):
				x = changeSkinXml(i)
			x = changeSkinXml("SplitScreen", config.plugins.setupGlass17.par208.value)
		x = chckPigFont(2)
		if x != "":		
			if "p" in x: 
				msg += _("PIG type") + "\n"            
			if "f" in x:
				msg += _("Extendend description font size") + "\n"
			if "c" in x:
				msg += _("Channel selection type")+" ("+_("color") + ")\n"
			if "o" in x:
				msg += _("Channel selection font size") + "\n"
		if config.plugins.setupGlass17.par46.value != "0":
			x = setFontListEpg(config.plugins.setupGlass17.par46.value)
			msg += _("EPG list font size")                      
		if chckPlBrowser('"posGoto"') and chckPlBrowser('"turnTime"'): 
			x = "2"
			if chckPlBrowser('name="Tuner"'):
				x = "3"			
			x = changeSkinXml("Dish",x)
			msg += _("Dish screen") + "\n"
		if isATV:
			for i in ("PositionerSetup","SleepTimerEdit","PluginBrowserList"):
				x = changeSkinXml(i)	
			x = changeSkinXml("MessageBox", "2")
		if os.path.isfile(SHAREPATH + "PLi-FullHD/skin.xml") or os.path.isfile(PYTHONPATH + "Plugins/SystemPlugins/OBH/__pycache__/") or os.path.isfile(PYTHONPATH + "Plugins/Satdreamgr/__init__.pyo"):
			for i in ("Config","AdapterSetup","HarddiskSelection","MenuSort","ParentalControlSetup","Troubleshoot","CommitInfo","MemoryInfo","StreamingClientsInfo","PositionerSetup","HotkeySetup","HotkeySetupSelect"):
				x = changeSkinXml(i)
			x = changeSkinXml("About","2")
		if chckPlBrowser('subs_notselected":'): 		
			x = changeSkinXml("AudioSelection")
			msg += _("AudioSelection") + "\n"
		if os.path.exists("/usr/lib/python2.7") or ISP38:
			if not fileExists('/etc/bhversion') and not os.path.exists("/etc/bpversion") and not os.path.exists(SHAREPATH + "PLi-HD") and not ISVTI and not chckSkytec():			
				ttt = "2"
				if chckVersion():
					ttt = "3"
					x = changeSkinXml("About")
					x = changeSkinXml("PluginBrowser", ttt)
				elif isATV and ISP38:
					x = changeSkinXml("PluginBrowser", "4")
				if chckPlBrowser():
					msg += _("Set PluginBrowser - OE 2.0") + "\n"
					x = changeSkinXml("PluginBrowser", ttt)
			if chckVersion("openbh"):
				x = changeSkinXml("PluginBrowser", "3")
				x = changeSkinXml("MessageBox", "1")
				x = changeSkinXml("MessageBox-template", "1")
		if config.plugins.setupGlass17.par59.value and not os.path.exists('/etc/dpkg'):
			x = setEncodingUser()
			msg += _("Set user encoding.conf") + "\n" 
		else:
			setCFGoff(59)
		if config.plugins.setupGlass17.par62.value:
			if E2OK:
				x = chnlSelChck()
				if x == 0:
					if chnlSelPatch():
						msg += _("ChannelSelection 2xOK") + "\n" 
					else:
						setCFGoff()
				elif x == 3:
					msg += _("ChannelSelection 2xOK") + "\n"
			else:
				setCFGoff()
		if chckScroll20():
			msg += _("Enable windowstylescrollbar") + "\n" 
		if setONOFF():
			msg += _("On/Off icons") + "\n"
		try:
			for ii in ["skin_default.xml","skin.xml","skin_default/skin.xml"]:
				if os.path.isfile(SHAREPATH + ii):
					x = open(SHAREPATH + ii, "r").read()
					if x.find("self.autoResize()") != -1:
						x = changeSkinXml("ChoiceBox")
						break
		except: pass
		if ENA_PLI2: 
			x = changeSkinXml("TimerEntry")
		x = PYTHONPATH + "Plugins/Extensions/MultiQuickButton/MultiQuickButton.py"
		if ENA_D == 'debpkg' and os.path.isfile(x): 
			x = open(x, "r").read()
			if x.find("key_3") == -1:
				x = changeSkinXml("MultiQuickButton")
		# Upgrade compatibility only: undo a legacy FullHDGlass spinner symlink
		# if an older installation left it active. Never replace the image spinner.
		msg += spinnerOnOff()
		if not config.plugins.setupGlass17.par47.value:
			msg += chMT()
		if config.plugins.setupGlass17.par157.value != "0" or config.plugins.setupGlass17.par156.value != "0" or config.plugins.setupGlass17.par155.value != "0" or config.plugins.setupGlass17.par154.value != "0" or config.plugins.setupGlass17.par153.value != "0":
			msg += lbs()
		if EFIFO and config.plugins.setupGlass17.par67.value:
			if chckFifo():
				msg += _("Service scan long list") + "\n"
		if config.plugins.setupGlass17.par227.value != "5":
			msg += _('Extended Number ZAP Picon Size') + "\n"
			if config.plugins.setupGlass17.par227.value == "0":
				x = changeSkinXml("NumberZapExt", chckPiconSize())
			else:
				x = changeSkinXml("NumberZapExt", config.plugins.setupGlass17.par227.value)
		if msg != "":
			try:
				self.session.open(MessageBox, _("GUI will now be restarted to activate restored options:") + "\n" + msg, MessageBox.TYPE_INFO, 5)				
			except: pass
			self.start_timerExec.start(4000, True)
		try:
			os.remove(SHAREPATH + "hd_glass17/icons/about1.png")
		except OSError:
			pass

	def rstnow(self):
		if XCPU != "sh4":
			try:
				quitMainloop(3)
			except: 
				subprocess.call(RSTCMD)
		else:
			subprocess.call(RSTCMD)  

	def updateChck(self, session):
		self.session = session
		self.session.open(MessageBox, _("GUI will now be restarted, updated files founded !!!"), MessageBox.TYPE_INFO, 5)
		self.start_timerExec.start(4000, True)
  
autoStartChck17 = AutoStartChck17()  		
##########################################################################################################################
class KeyManage():
	def __init__(self):
		self.dialogKey = None
		self.dialog = None

	def initKeyMng(self, session):
		self.session = session
		if config.plugins.setupGlass17.par12.value != "n":
			if config.plugins.setupGlass17.par12.value == "g":
				if ENA_Z:
					self.dialogKey = self.session.instantiateDialog(SpecialScreen, zPosition=3000)
					self.dialogKey.shown = False
				else:
					self.dialogKey = session.instantiateDialog(SpecialScreen)
			elif "w" in config.plugins.setupGlass17.par12.value:
				from Plugins.Extensions.setupGlass17.weather import WeatherScreen
				if ENA_Z:
					self.dialogKey = self.session.instantiateDialog(WeatherScreen, config.plugins.setupGlass17.par171.value, zPosition=3000)
					self.dialogKey.shown = False
				else:
					self.dialogKey = session.instantiateDialog(WeatherScreen, config.plugins.setupGlass17.par171.value)
			elif config.plugins.setupGlass17.par12.value == "i":
				from Plugins.Extensions.setupGlass17.infoEcm_by_duri import InfoEcmScreen
				if ENA_Z:
					self.dialogKey = self.session.instantiateDialog(InfoEcmScreen, zPosition=3000)
					self.dialogKey.shown = False
				else:
					self.dialogKey = session.instantiateDialog(InfoEcmScreen)
			elif config.plugins.setupGlass17.par12.value == "a":
				from Plugins.Extensions.setupGlass17.Netatmo import NetatmoScreen
				if ENA_Z:
					self.dialogKey = self.session.instantiateDialog(NetatmoScreen, zPosition=3000)
					self.dialogKey.shown = False
				else:
					self.dialogKey = session.instantiateDialog(NetatmoScreen)
		if config.plugins.setupGlass17.par64.value:
			from Plugins.Extensions.setupGlass17.screenSaver import ScreenSaverScreen
			if ENA_Z:
				self.dialog = self.session.instantiateDialog(ScreenSaverScreen, zPosition=-1)
				self.dialog.shown = False
			else:
				self.dialog = session.instantiateDialog(ScreenSaverScreen)
			self.hideME()
		self.specialinfoTimer = None

	def stopTimer(self):
		if config.plugins.setupGlass17.par73.value and self.specialinfoTimer is not None: 
			if self.specialinfoTimer.isActive(): 
				self.specialinfoTimer.stop()
			self.specialinfoTimer = None
			
	def startTimer(self):  
		if config.plugins.setupGlass17.par73.value and self.specialinfoTimer is None:  
			self.specialinfoTimer = eTimer()
			try:
				self.specialinfoTimer_conn = self.specialinfoTimer.timeout.connect(ShowHideViaKey)
			except AttributeError:
				self.specialinfoTimer.timeout.get().append(ShowHideViaKey)
			self.specialinfoTimer.start(20000, True)
  			
	def TunerTest(self):
		service = self.session.nav.getCurrentService()
		if service is not None:
			frontendInfo = service.frontendInfo()
			if frontendInfo is not None:
				frontendData = frontendInfo and frontendInfo.getAll(True)
				if frontendData is not None:
					isSatTuner = str(frontendData.get("tuner_type", "None"))
					if isSatTuner in ["DVB-S","DVB-C","DVB-T","DVB-S2","DVB-S2X","0","1","2","4","8","16"]:
						return True
		return False
		
	def showME(self):
		self.dialog.show()

	def hideME(self):
		self.dialog.hide()
		
keyManage = KeyManage()
##########################################################################################################################
class SpecialScreen(Screen):

	skin = """<screen name="SpecialScreen" position="1155,195" size="825,412" zPosition="8" title="ECM and TP Status" backgroundColor="background" >                                           
<widget name="ecm_items" font="Prive3;24" position="15,15" zPosition="2" size="150,532" valign="top" halign="left" foregroundColor="yellow" backgroundColor="background" transparent="1" />
<widget name="ecm_Values" font="Prive3;24" position="100,15" zPosition="3" size="337,532" valign="top" halign="left"  backgroundColor="background" transparent="1" />
<widget name="tp_items" font="Prive3;24" position="440,15" zPosition="2" size="170,480" valign="top" halign="left" foregroundColor="yellow" backgroundColor="background" transparent="1" />
<widget name="tp_Values" font="Prive3;24" position="605,15" zPosition="3" size="232,480" valign="top" halign="left"  backgroundColor="background" transparent="1" />                         
</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skin = SpecialScreen.skin
		self.c = CLRDATA
		self.e = ECM_LABELS
		if not config.plugins.setupGlass17.par50.value:
			self.c += CLR
			self.e += "\nCW0:\nCW1:"
		self['ecm_items'] = Label(self.e)
		self['ecm_Values'] = Label(self.c)
		self['tp_items'] = Label("Video PID:\nAudio PID:\nPCR PID:\nPMT PID:\nTXT PID:\nSID:\nTSID:\nONID:\nVideo Format:\nVideo Size:\nAudio Type:\nAudio Tracks:\nSubtitles:")
		self['tp_Values'] = Label(CLRTP)
		self.__firstInit = True
		self.__sleep = False
		self.ecmTimer = eTimer()
		try:
			self.ecmTimer_conn = self.ecmTimer.timeout.connect(self.__RefreshMe)
		except AttributeError:
			self.ecmTimer.timeout.get().append(self.__RefreshMe)
		if config.plugins.setupGlass17.par78.value == "g":
			self["actions"] = ActionMap(["ColorActions", "SetupActions", "DirectionActions"],
			{
            "green": self.exit,
            "red": self.exit,
            "ok": self.exit,
            "cancel": self.exit,
            "yellow": self.exit,
            "blue": self.exit
			}, -2)	
		else:	
			self._SpecialScreen__event_tracker = ServiceEventTracker(screen=self, eventmap={iPlayableService.evStopped: self._SpecialScreen__SetDef, iPlayableService.evUpdatedInfo: self._SpecialScreen__Wakeup, iPlayableService.evTunedIn: self._SpecialScreen__Wakeup})
			self.onHide.append(self.__goStandby)
		self.onLayoutFinish.append(self.firstRun)	
		self.onShow.append(self.__goWakeup)
			
	def exit(self):
		self.ecmTimer.stop()
		self.ecmTimer_conn = None
		self.ecmTimer = None
		self.close()
		
	def firstRun(self):
		if self.__firstInit and self.instance:
			self.setTitle(_("ECM and TP Status"))
			self.instance.move(ePoint(config.plugins.setupGlass17.par10.value, config.plugins.setupGlass17.par11.value))
			self.__firstInit = False

	def __SetDef(self):
		self.ecmTimer.stop()
		self['ecm_items'].setText(self.e)
		self['ecm_Values'].setText(self.c)
		self['tp_Values'].setText(CLRTP)

	def __goStandby(self):
		self.ecmTimer.stop()
		self.__sleep = True
    		
	def __goWakeup(self):
		self.__sleep = False
		self.__Wakeup()

	def __Wakeup(self):
		if not self.ecmTimer.isActive() and not self.__sleep:
			self.ecmTimer.start(300, True)

	def __RefreshMe(self):
		self.ecmTimer.stop()
		v = config.plugins.setupGlass17.par38.value
		if not config.plugins.setupGlass17.par50.value:
			v += config.plugins.setupGlass17.par194.value
		if config.plugins.setupGlass17.par195.value == "Prov.:":
			self['ecm_items'].setText(self.e.replace("Prov.:","CHID:"))
		elif config.plugins.setupGlass17.par195.value == "PrvID:":
			self['ecm_items'].setText(self.e.replace("PrvID:","CHID:"))
		else:
			self['ecm_items'].setText(self.e)
		self['ecm_Values'].setText(v)
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if info:
			aa = ".............."
			serviceinfo = service.info()
			d = []
			vpid = serviceinfo.getInfo(iServiceInformation.sVideoPID)
			d.append("0x%0.4X (%0.4dd)" % (vpid, vpid))
			apid = serviceinfo.getInfo(iServiceInformation.sAudioPID)
			d.append("0x%0.4X (%0.4dd)" % (apid, apid))
			ppid = serviceinfo.getInfo(iServiceInformation.sPCRPID)
			d.append("0x%0.4X (%0.4dd)" % (ppid, ppid))
			pmtpid = serviceinfo.getInfo(iServiceInformation.sPMTPID)
			d.append("0x%0.4X (%0.4dd)" % (pmtpid, pmtpid))
			txtpid = serviceinfo.getInfo(iServiceInformation.sTXTPID)
			d.append("0x%0.4X (%0.4dd)" % (txtpid, txtpid))
			sid = serviceinfo.getInfo(iServiceInformation.sSID)
			d.append("0x%0.4X (%0.4dd)" % (sid, sid))
			tsid = serviceinfo.getInfo(iServiceInformation.sTSID)
			d.append("0x%0.4X (%0.4dd)" % (tsid, tsid))
			onid = serviceinfo.getInfo(iServiceInformation.sONID)
			d.append("0x%0.4X (%0.4dd)" % (onid, onid))
			d.append("%s x %s" % (serviceinfo.getInfo(iServiceInformation.sVideoWidth),serviceinfo.getInfo(iServiceInformation.sVideoHeight)))
			for x in range(0, len(d)):
				if "-0001" in d[x] or "-1" in d[x]:
					d[x] = aa
			ac = iswide = aa
			if d[8] != aa:
				if serviceinfo.getInfo(iServiceInformation.sAspect) in (3, 4, 7, 8, 0xB, 0xC, 0xF, 0x10):
					iswide = "16:9"
				else:
					iswide = "4:3"
			num = 0
			audio = service.audioTracks()
			if audio:                                
				num = audio.getNumberOfTracks()
				if not config.plugins.setupGlass17.par42.value:
					idx = 0
					while idx < num:
						i = audio.getTrackInfo(idx)
						for x in (i.getDescription(), i.getLanguage()):
							xx = x.upper()
							if "AC3" in xx or "DTS" in xx or "DOLBY" in xx:
								ac = "AC3"
								break
						if EACC and ac == aa:
							try:
								if i.getType() in (iAt.atAC3, iAt.atDDP, iAt.atDTS, iAt.atDTSHD):
									ac = "AC3"
									break
							except: pass
						idx += 1
				else:
					try:
						i = audio.getTrackInfo(audio.getCurrentTrack())					
						x = (i.getDescription()).upper()
						idx = (i.getLanguage()).upper()
						if "5.1" in x or "5.1" in idx:
							ac = "Dolby Digital 5.1"
						elif "2.0" in x or "2.0" in idx:
							ac = "Dolby Digital 2.0"
						elif "MPEG" in x or "MPEG" in idx:
							ac = "MPEG"
						elif "DTS" in x or "DTS" in idx:
							ac = "DTS"
						elif "AAC" in x or "AAC" in idx:
							ac = "AAC"
						elif "DOLBY" in x or "AC3" in x or "DOLBY" in idx or "AC3" in idx:
							ac = "AC3"
					except: pass
					if EACC and ac == aa:
						try:
							idx = i.getType()
							if idx in (iAt.atDTS, iAt.atDTSHD):
								ac = "DTS"				
							elif idx == iAt.atMPEG:
								ac = "MPEG"
							elif idx in (iAt.atAAC, iAt.atAACHE):
								ac = "AAC"
							elif idx in (iAt.atDDP, iAt.atAC3):
								ac = "AC3"
						except: pass
			isSubtitles = _("no")
			tmp = None
			try:
				subservices = service and service.subtitleTracks()
				tmp = subservices.getNumberOfSubtitleTracks()
			except:
				subservices = service and service.subtitle()
				tmp = subservices and subservices.getSubtitleList()
				if tmp:
					tmp = len(tmp)
			if tmp and tmp > 0:
				isSubtitles = _("yes")
			self['tp_Values'].setText(d[0] + "\n" + d[1] + "\n" + d[2] + "\n" + d[3] + "\n" + d[4] + "\n" + d[5] + "\n" + d[6] + "\n" + d[7] + "\n" + iswide + "\n" + d[8] + "\n" + ac + "\n" + str(num) + "\n" + isSubtitles)   		 
			del d
		if not self.__sleep:
			self.ecmTimer.start(int(config.plugins.setupGlass17.par74.value)*1000, True)
##########################################################################################################################
# Active ExtraInfo17 instance for live weather refresh after city change.
G17_EXTRAINFO_INSTANCE = None

class ExtraInfo17(Screen):
				
	def __init__(self, session):
		global G17_EXTRAINFO_INSTANCE
		Screen.__init__(self, session)
		G17_EXTRAINFO_INSTANCE = self
		self.skin = fromCfg()
		self.session = session								
		self.allCaids = {
				"06" : "ird", "01" : "sec", "18" : "nag", "55" : "gfn", "22" : "cdc", "4B64" : "tvk", "4347" : "cro",
				"05" : "via", "0B" : "con", "17" : "ver", "0E" : "pwu", "07" : "dig", "4B63" : "red", "4AF4" : "mdc",
				"0D" : "crw", "4A70" : "drc", "09" : "nds", "A1" : "ros", "4AD0" : "xcr", "4AD1" : "xcr","1702" : "bet",
				"4AE0" : "dre", "4AE1" : "dre", "44A0" : "dre", "5581" : "bul", "26" : "bis", "4AEA" : "crg", "1EC0" : "crg", "4B24" : "crg","1722" : "bet",
				"4ABF" : "dgc", "4AEE" : "bul", "4AFC" : "pnc", "2710" : "exs", "1010" : "tan", "FF" : "ccw", "1762" : "bet",
				"56" : "ver","4AB0" : "skp"
				}
		for x in range(0,8):
			self["D%s_Demm" % x] = Pixmap()
			self["D%s_Demm" % x].hide()
		for x in ["subserv","txt","multi_audio","subtit","hbb","HDD_state","Dnetstate","Decm","Dtype","Dcam","tuner"]:
			self[x] = Pixmap()
			self[x].hide()
		for x in ["wide","dolby","hd_sd"]:
			self[x] = MultiPixmap()
			self[x].hide()
		self["picSat"] = Pixmap()
		self["picProv"] = Pixmap()
		self["g17picon"] = Pixmap()
		self["slider_back"] = Pixmap()
		self["Prov_temp_rpm"] = ColorLabel("")
		self["TP_info"] = ColorLabel(NO_TUN)
		self["TP_type"] = ColorLabel(_("No data"))
		self["Video_size"] = ColorLabel("--- x ---")
		self["piconCam"] = Pixmap()
		self["piconEcm"] = Pixmap()
		self['ecmLineInfo'] = ColorLabel(_("No info from Cam"))
		self['active_caidPid'] = Label()
		self['caidPids'] = Label()
		self['caidPids_back'] = Pixmap()
		self['caidPids_end'] = Pixmap()
		self['ecmValues'] = ColorLabel()
		self['ecmlabels'] = ColorLabel(ECM_LABELS)    		
		self["back_enhanced"] = Pixmap()
		self["bitrate_info"] = ColorLabel(_("Bitrate Stopped"))
		self.bitNotActive = True
		self.state = None
		self.enaIcoTun = True
		self.allCaidPid = ""		
		self.tstprov = ""
		self.tstsat = ""
		self.pngname = ""
		self.tstca = ""
		self.typecam = ""
		self.pngnamesat = ""
		self.pngnameWea = SKINPATH+"piconWdef.png"		
		self.typeCAviaCam = ""
		self.pngnamePic = ""
		self.sname = ""
		self.caidsLive = ""
		self.iscalcstart = True
		self.isBit = False
		self.enaTuned = False
		self.sid = self.vpid = "N/A"
		self.pidsX = 0
		self.pidsY = 0
		self.numBit = 0
		self.is_prov = 9
		self.cAud = -9
		self.uhdtype = "x"
		self.uhdTimer = eTimer()
		try:
			self.uhdTimer_conn = self.uhdTimer.timeout.connect(self.__uhdTypeSW)
		except AttributeError:
			self.uhdTimer.timeout.get().append(self.__uhdTypeSW)
		self.runChkTimer = eTimer()
		try:
			self.runChkTimer_conn = self.runChkTimer.timeout.connect(self.__updCamECM)
		except AttributeError:
			self.runChkTimer.timeout.get().append(self.__updCamECM)
		self.emm_timer = eTimer()
		try:
			self.emm_timer_conn = self.emm_timer.timeout.connect(self.__updateEMM)
		except AttributeError:
			self.emm_timer.timeout.get().append(self.__updateEMM)
		self.ecmCaidTimer = eTimer()
		try:
			self.ecmCaidTimer_conn = self.ecmCaidTimer.timeout.connect(self.ecmCaidSwitch)
		except AttributeError:
			self.ecmCaidTimer.timeout.get().append(self.ecmCaidSwitch)
		self.provRPMTimer = eTimer()
		try:
			self.provRPMTimer_conn = self.provRPMTimer.timeout.connect(self.provRPMTimerSwitch)
		except AttributeError:
			self.provRPMTimer.timeout.get().append(self.provRPMTimerSwitch)
		self.runBitTimer = eTimer()
		try:
			self.runBitTimer_conn = self.runBitTimer.timeout.connect(self.__startBitrate)
		except AttributeError:
			self.runBitTimer.timeout.get().append(self.__startBitrate)
		self.hddTimer = eTimer()
		try:
			self.hddTimer_conn = self.hddTimer.timeout.connect(self.__hddState)
		except AttributeError:
			self.hddTimer.timeout.get().append(self.__hddState)
		self.hbboff = True
		self.lastIco = ""
		self.lastIcoSwitch = 0
		self.runHBBTimer = eTimer()
		try:
			self.runHBBTimer_conn = self.runHBBTimer.timeout.connect(self.checkHBB)
		except AttributeError:
			self.runHBBTimer.timeout.get().append(self.checkHBB)
		if not ENAEBTR and not ENA_Z:
			self.container = eConsoleAppContainer()
			self.container.dataAvail.append(self.dataAvail)
			if XCPU == "arm":
				self.restartBtrTimer = eTimer()
				self.restartBtrTimer.timeout.get().append(self.restartBtrStop)
		self.enaProvSat = False
		self.__isOn = False
		self.timerpics = None
		if self.skin.find("picProvSat") != -1:
			self["picProvSat"] = Pixmap()
			self.timerpics = eTimer()
			self["weaTxt"] = Label('--'+DG)
			if config.plugins.setupGlass17.par8.value == "3" and config.plugins.setupGlass17.par169.value:
				try:
					self.timerpics_conn = self.timerpics.timeout.connect(self.animTimerEvent)
				except AttributeError:
					self.timerpics.callback.append(self.animTimerEvent)
			else:
				self["weaTxt"].hide()
				try:
					self.timerpics_conn = self.timerpics.timeout.connect(self.timerpicsEvent)
				except AttributeError:
					self.timerpics.callback.append(self.timerpicsEvent)
			self.enaProvSat = True
		self.enaWeainf = config.plugins.setupGlass17.par8.value in ("3","4","5","6") and self.enaProvSat
		if (config.plugins.setupGlass17.par58.value and ECL) or self.enaWeainf:
			try:
				os.remove(XML_FILE)
			except OSError:
				pass
			self.wConsole = wConsole()
			self.refreshValue = 900
			self.count = 0
			self.clrMemTimer = eTimer()
			try:
				self.clrMemTimer_conn = self.clrMemTimer.timeout.connect(self.clearMem)
			except AttributeError:
				self.clrMemTimer.timeout.get().append(self.clearMem)			
		self.caidLineTxt = _("No info about Caids")
		self.ecmLineTxt = _("No info from Cam")
		self.widthDynIco = 48
		self.posX_DynIco = 0
		self.posY_DynIco = 1080
		self.width_D_icons = 28
		self.posY_DynIco_CA = 0
		self.x_dyn_pos_CA = 1920
		self.forceUpd = True
		self.noReplace = True
		self.rEMM = 0
		self.dataV = 0
		self.dataA = 0
		self.piconSize = "picon"
		self.picProvSatSize = ""
		self.pics = []
		if config.plugins.setupGlass17.par31.value == "si":
			config.plugins.setupGlass17.par5.value = "0"
			config.plugins.setupGlass17.par5.save()
			configfile.save()
		self.__evStart()
		if ENAVFT:
			try:
				self.__event_tracker00 = ServiceEventTracker(screen=self, eventmap={iPlayableService.evVideoTypeReady: self.__evUpdatedVideoType})
			except: pass
		try:
			self.__event_tracker0 = ServiceEventTracker(screen=self, eventmap={iPlayableService.evHBBTVInfo: self.checkHBB})
		except: pass
		try:
			self.__event_tracker1 = ServiceEventTracker(screen=self, eventmap={iPlayableService.evStopped: self.__stopBitrate, iPlayableService.evStart: self.__evStart, iPlayableService.evUpdatedInfo: self.__evUpdatedInfo, iPlayableService.evTunedIn: self.__evTunedIn, iPlayableService.evUpdatedEventInfo: self.__evUpdatedInfo, iPlayableService.evVideoSizeChanged: self.__evUpdatedInfo})
		except: pass
		try:
			self.__event_tracker2 = ServiceEventTracker(screen=self, eventmap={iPlayableService.evVideoGammaChanged: self.__evUpdatedInfo})
		except: pass
		self.enaBit = fromCfgB()
		self.onLayoutFinish.append(self.startloadpixmap)
		self.onShow.append(self.startEcmCaidInfo)
		self.onShow.append(self.setOn)
		self.onHide.append(self.stopEcmCaidInfo)

	def setOn(self):
		self.__isOn = True
		if self.timerpics and self.chckWeaInafAnim():
			if not self.timerpics.isActive():
				self.timerpics.start(config.plugins.setupGlass17.par170.value)
    		
	def startloadpixmap(self):
		if self.iscalcstart:
			try:
				self['caidPids_back'].instance.setScale(0)
			except: pass
			try:
				for x in range(0,8):
					self["D%s_Demm" % x].instance.setScale(1)
				for x in ["subserv","txt","multi_audio","subtit","hbb","HDD_state","Dnetstate","Decm","Dtype","Dcam","tuner","wide","dolby","hd_sd"]:
					self[x].instance.setScale(1)
			except: pass
			if self.enaProvSat:
				try:
					self.posX_PSW = self["picProvSat"].instance.position().x()
					self.posY_PSW = self["picProvSat"].instance.position().y()
					self["picProvSat"].instance.setScale(1)
					if self["picProvSat"].instance.size().width() == 220:
						self.picProvSatSize = ""
				except: pass			
				if self.chckWeaInafAnim():
					self.updpicProvSat(self.pngnameWea)
			try:
				self.pidsX = self['caidPids_back'].instance.position().x()
				self.pidsY = self['caidPids_back'].instance.position().y()
				self.widthDynIco = self["wide"].instance.size().width()
				self.posX_DynIco = self["wide"].instance.position().x()
				self.posY_DynIco = self["wide"].instance.position().y()
				self.piconSize = piconSize("%s,%s" % (self["g17picon"].instance.size().width(),self["g17picon"].instance.size().height()))
				if ENA_POPEN and config.plugins.setupGlass17.par23.value:
					self.posX_DynIco -= self["HDD_state"].instance.size().width()
				self.width_D_icons = self["D0_Demm"].instance.size().width()
				self.posY_DynIco_CA = self["D0_Demm"].instance.position().y()
				self.x_dyn_pos_CA = self["D0_Demm"].instance.position().x()
				self.enaIcoTun = self["tuner"].instance.size().width() != 0
			except: pass
			if (config.plugins.setupGlass17.par58.value and ECL) or self.enaWeainf:
				# r12 behaviour: weather is populated as soon as the Infobar layout is ready.
				# Do not leave N/A visible behind the old 30-second startup timer.
				if self.enaWeainf:
					self.refreshWeatherNow()
				else:
					self.clrMemTimer.startLongTimer(30)
			self.cpu_count = 0
			self.maxDynX = self.posX_DynIco - (7*self.widthDynIco)
			self.x_dyn_pos = self.posX_DynIco - 30
			self.prev_info = self.getCpuInfo()
			self.curr_info = self.getCpuInfo()
			self.iscalcstart = False
			config.plugins.setupGlass17.par43.value = True
			self.showEnhancedInfo()
			self['active_caidPid'].hide()
			self['caidPids'].hide()
			self['caidPids_back'].hide()
			self['caidPids_end'].hide()
			self['ecmlabels'].colorX(config.plugins.setupGlass17.par118.value)
			self['ecmValues'].colorX(config.plugins.setupGlass17.par119.value)
			self['TP_info'].colorX(config.plugins.setupGlass17.par122.value)
			self['TP_type'].colorX(config.plugins.setupGlass17.par121.value)
			self['Video_size'].colorX(config.plugins.setupGlass17.par123.value)
			for x in ("g17picon","picSat","picProv","piconCam","piconEcm"):
				try:
					self[x].instance.setScale(1)
				except: pass
			if ENA_ANIM and config.plugins.setupGlass17.par161.value:
				if config.plugins.setupGlass17.par162.value != "None":
					try:
						self['g17picon'].instance.setShowHideAnimation(config.plugins.setupGlass17.par162.value)
					except: pass             
				if config.plugins.setupGlass17.par164.value != "None":
					try:
						self['ecmLineInfo'].instance.setShowHideAnimation(config.plugins.setupGlass17.par164.value)
					except: pass 
				if self.enaProvSat and not config.plugins.setupGlass17.par169.value and config.plugins.setupGlass17.par8.value != "3" and config.plugins.setupGlass17.par163.value != "None":
					try:
						self['picProvSat'].instance.setShowHideAnimation(config.plugins.setupGlass17.par163.value)
					except: pass
				if config.plugins.setupGlass17.par167.value != "None":
					try:
						self['TP_info'].instance.setShowHideAnimation(config.plugins.setupGlass17.par167.value)
						self['TP_type'].instance.setShowHideAnimation(config.plugins.setupGlass17.par167.value)
					except: pass
                                        
	def __evStart(self):
		self.noReplace = True
		try:
			from enigma import eEnv
			self.noReplace = not os.path.isfile(eEnv.resolve('$sysconfdir/enigma2/serviceapp_replaceservicemp3'))
		except: pass
		if self.emm_timer.isActive():
			self.emm_timer.stop()
		if self.runChkTimer.isActive():
			self.runChkTimer.stop()
		if self.runBitTimer.isActive():
			self.runBitTimer.stop()
		if self.runHBBTimer.isActive():
			self.runHBBTimer.stop()
		if self.uhdTimer.isActive():
			self.uhdTimer.stop()
		self.uhdtype = "x"
		self.showEnhancedInfo()		
		self.typeCAviaCam = ""
		self["Video_size"].setText("--- x ---")
		self.caidLineTxt = _("No info about Caids")
		self.ecmLineTxt = _("No info from Cam")
		self.ecmLineShowFnc()
		self["TP_type"].setText(_("No data"))
		self["TP_info"].setText(NO_TUN)
		for x in range(0,8):
			try:
				self["D%s_Demm" % x].hide()
			except: pass
		for x in ["Decm","Dtype","Dcam"]:
			try:
				self[x].hide()
			except: pass
		self.netStateMove(self.x_dyn_pos_CA)
		self.chckSS()
            		
	def __uhdTypeSW(self):
		self.uhdTimer.stop()
		if "3" in self.uhdtype:
			try:
				self["hd_sd"].setPixmapNum(int(self.uhdtype[1]))
				self.uhdtype = self.uhdtype[1]+self.uhdtype[0]
			except: pass
			self.uhdTimer.start(2000)
		
	def showPicon(self, sname):
		playing = self.session.nav.getCurrentlyPlayingServiceReference()
		native_dab = is_native_dab(playing)
		if native_dab:
			sname = playing.toString()
		if self.sname == sname:
			return		
		self.sname = sname
		pngname = ""
		self.path = self.piconSize
		if native_dab:
			from Components.Renderer.Picon import getPiconName
			pngname = getPiconName(sname) or ""
		if sname != "" and not native_dab:
			tmp = self.alternative(sname).split(':', 10)[:10]
			sname = '_'.join(tmp)
			pngname = self.findPicon(sname)
			if pngname == "" and len(sname) > 11:
				if sname.startswith('4097'):
					tmp = sname.split('_')
					tmp[0] = '1'
					sname = '_'.join(tmp)
					pngname = self.findPicon(sname)
				if pngname == "":
					pngname = self.findPicon(sname[:-10]+"0000_0_0_0")
					if pngname == "":
						for i in ("1","19","16"):
							if i != tmp[2]:
								tmp[2] = i
								sname = '_'.join(tmp)
								pngname = self.findPicon(sname)
								if pngname == "":
									pngname = self.findPicon(sname[:-10]+"0000_0_0_0")
									if pngname != "":
										break
								else:
									break
		if pngname == "":
			pngname = self.findPicon("picon_default")
			if pngname == "":
				sname = "picon_default.png"
				if self.path == "ZZPicon":
					sname = "ZZpicon_default.png"
				if "220" in self.path:
					sname = "picon220_default.png"
				pngname = setDefPicon(sname)
		if self.pngnamePic != pngname:
			self.pngnamePic = pngname
			try:
				self["g17picon"].instance.setPixmapFromFile(self.pngnamePic)				
			except: pass

	def alternative(self, serviceName):
		def alternativeChannels(service):
			tmp = eServiceCenter.getInstance().list(eServiceReference(service))
			return tmp and tmp.getContent("S", True)
		if serviceName.startswith('1:134:'):
			channels = alternativeChannels(serviceName)
			if channels:
				return channels[0]
		return serviceName

	def stopEcmCaidInfo(self):
		self.__isOn = False
		if self.ecmCaidTimer.isActive():
			self.ecmCaidTimer.stop()
		if self.provRPMTimer.isActive():
			self.provRPMTimer.stop()
		if self.hddTimer.isActive():
			self.hddTimer.stop()
		if config.plugins.setupGlass17.par57.value != "2": 
 			self["Dnetstate"].instance.setPixmapFromFile(SKINPATH + "icons/unk.png")
             			
	def startEcmCaidInfo(self, hddTmr=1):               
		if config.plugins.setupGlass17.par17.value == "1" and not self.ecmCaidTimer.isActive() and (self.ecmLineTxt != _("Free To Air") and self.ecmLineTxt != "....."):
			self.is_ecm = False
			self.ecmCaidSwitch()
		if hddTmr == 1:
			a, b, c, d = self.readPTCH()
			if a and not b and not c and not d:
				self["Prov_temp_rpm"].setText(self.tstprov)
				self["Prov_temp_rpm"].color5(config.plugins.setupGlass17.par20.value)
			else:
				if b:
					self.is_prov = 1
				elif c:
					self.is_prov = 2
				elif d:
					self.is_prov = 3
				else:
					self.is_prov = 9
					self["Prov_temp_rpm"].setText("")
				self.provRPMTimer.start(400) 
			self.testNet = False
			self.hddTimer.start(100)
    			
	def readPTCH(self):
		a, b, c, d = config.plugins.setupGlass17.par81.value, config.plugins.setupGlass17.par82.value, config.plugins.setupGlass17.par83.value, config.plugins.setupGlass17.par84.value
		if not ENA_POPEN:
			d = False
		return a, b, c, d

	def readPower(self, dev):
		where = "no_hdd"
		hpdArm = ""
		if os.path.exists("/sbin/hdparm"):
			hpdArm = "/sbin/hdparm"
		elif os.path.exists("/usr/sbin/hdparm"):
			hpdArm = "/usr/sbin/hdparm"
		if hpdArm != "":
			try:
				output = subprocess.check_output([hpdArm, "-C", dev], universal_newlines=True, stderr=subprocess.STDOUT)
				for f in output.splitlines():
					if f.find("active") != -1 or f.find("idle") != -1:
						where = "active"
					elif f.find("standby") != -1:
						where = "standby"
			except (OSError, subprocess.CalledProcessError):
				pass
		if config.plugins.setupGlass17.par182.value == "SSD":
			return where+"_s"
		else:
			return where

	def __hddState(self):
		self.hddTimer.stop()
		def readRoute():
			state = "unk"
			try:
				f = open("/proc/net/route","r")
				for line in f:
					tt = line.split()
					if tt[3] == "0003":
						if tt[0] == "eth0":
							state = "eth"
							break
						elif tt[0] == "wlan0":
							state = "wifi"
							break
						elif tt[0] == "ppp0":
							state = "3g"
							break
				f.close()
			except: pass
			return state
		def readNetState():
			state = "error"
			if config.plugins.setupGlass17.par57.value == "3":			
				if internet():
					state = readRoute()
			else:
				state = readRoute()
			return state			
		if not self.testNet:
			self.testNet = True
			self.hddTimer.start(1500)
			return
		if ENA_POPEN and config.plugins.setupGlass17.par23.value and config.plugins.setupGlass17.par140.value != "None":      
			self["HDD_state"].instance.setPixmapFromFile(SKINPATH + "icons/"+self.readPower(config.plugins.setupGlass17.par140.value)+".png")           
			self["HDD_state"].show()
		else:
			self["HDD_state"].hide()		
		if config.plugins.setupGlass17.par57.value != "2": 
			self["Dnetstate"].instance.setPixmapFromFile(SKINPATH + "icons/"+readNetState()+".png")           
			self["Dnetstate"].show()   
		else:
			self["Dnetstate"].hide()
		self.hddTimer.start(4000)
                              			
	def provRPMTimerSwitch(self):
		self.provRPMTimer.stop()
		a, b, c, d = self.readPTCH()
		if self.is_prov == 1:
			tempRPM, tempDB = self.getTempRPM()
			self["Prov_temp_rpm"].setText(tempRPM)
			aa = config.plugins.setupGlass17.par20.value
			if tempDB == -1:
				self["Prov_temp_rpm"].color6(aa)
			elif tempDB > 45:
				self["Prov_temp_rpm"].color4(aa)
			elif tempDB > 35:
				self["Prov_temp_rpm"].color3(aa)
			else:
				self["Prov_temp_rpm"].color2(aa)
			if c:
				self.is_prov = 2
			elif d:
				self.is_prov = 3
			elif a:
				self.is_prov = 0
		elif self.is_prov == 2:
			tempRPM, tempDB = self.getCpuMem()
			self["Prov_temp_rpm"].setText(tempRPM)
			aa = config.plugins.setupGlass17.par20.value
			if tempDB == -1:
				self["Prov_temp_rpm"].color6(aa)
			elif tempDB > 75:
				self["Prov_temp_rpm"].color4(aa)
			elif tempDB > 50:
				self["Prov_temp_rpm"].color3(aa)
			elif tempDB > 25:
				self["Prov_temp_rpm"].color7(aa)
			else:
				self["Prov_temp_rpm"].color2(aa)
			if d:
				self.is_prov = 3
			elif a:
				self.is_prov = 0
			elif b:
				self.is_prov = 1
		elif self.is_prov == 3:
			tempDB = getTemp(config.plugins.setupGlass17.par140.value)
			aa = config.plugins.setupGlass17.par20.value
			if tempDB == 0:
				tempDB = "--"
				self["Prov_temp_rpm"].color6(aa)
			elif tempDB > 55:
				self["Prov_temp_rpm"].color4(aa)
			elif tempDB > 45:
				self["Prov_temp_rpm"].color3(aa)
			elif tempDB > 35:
				self["Prov_temp_rpm"].color7(aa)
			else:
				self["Prov_temp_rpm"].color2(aa)
			self["Prov_temp_rpm"].setText("Temp. %s: %s%sC" % (config.plugins.setupGlass17.par182.value,tempDB,DG))
			if a:
				self.is_prov = 0
			elif b:
				self.is_prov = 1
			elif c:
				self.is_prov = 2
		elif self.is_prov == 0:
			self["Prov_temp_rpm"].setText(self.tstprov)
			self["Prov_temp_rpm"].color5(config.plugins.setupGlass17.par20.value)
			if b:
				self.is_prov = 1
			elif c:
				self.is_prov = 2
			elif d:
				self.is_prov = 3
		if self.is_prov != 9:
			self.provRPMTimer.start(3000)
		
	def getCpuMem(self):
		def setUnits(value):
			if value >= 1024*1024:
				return '%.1f%s' % (float(value)/(1024*1024),'GB')
			elif value >= 1024:
				return '%.1f%s' % (float(value)/1024,'MB')
			else:
				return '%.1f%s' % (float(value),'kB')
		try:
			tmp = open('/proc/meminfo').readlines()
			free = tmp[1].strip().split(":")[1]
			free = free.strip().split(" ")[0]
			total = tmp[0].strip().split(":")[1] 
			total = total.strip().split(" ")[0]
			tmp = "Mem: "+ setUnits(int(free)) +"/"+ setUnits(int(total))
		except:
			tmp = "Mem: --/--"		
		self.prev_info, self.curr_info = self.curr_info, self.getCpuInfo()
		zataz = 0
		count = 0
		for i in range(len(self.curr_info)):
			try:
				count += 1				
				zataz += 100 * (self.curr_info[i][2] - self.prev_info[i][2]) // (self.curr_info[i][1] - self.prev_info[i][1])
			except ZeroDivisionError: pass
		if count > 0 and zataz > 0:
			zataz = int(zataz/count)
		if zataz == 0 or count == 0:
			tmp += ', Cpu: --'
		elif zataz > 100:
			zataz = 100    			
			tmp += ", Cpu: " + str(zataz) + "%"	
		else:			
			tmp += ", Cpu: " + str(zataz) + "%"								
		return tmp, int(zataz)

	def getCpuInfo(self):
		res = []
		try:
			fd = open("/proc/stat", "r")
			for l in fd:
				if l.find("cpu") == 0:
					total = busy = 0
					tmp = l.split()
					for i in range(1, len(tmp)):
						tmp[i] = int(tmp[i])
						total += tmp[i]

					busy = total - tmp[4] - tmp[5]
					res.append([tmp[0], total, busy])
			fd.close()
		except: pass
		return res
    		
	def getTempRPM(self):
		temp = -1
		rpm = 0
		ret = ""
		try:
			allsensors = sensors.getSensorsList(sensors.TYPE_TEMPERATURE)
			numtemp = len(allsensors)
			for num in range(numtemp):
				idx = allsensors[num]
				isMax = sensors.getSensorValue(idx)
				if isMax > temp:
					temp = isMax
		except: pass
		if temp > 0:
			ret = "Temp.: " + str(temp) + DG
		elif fileExists('/sys/devices/virtual/thermal/thermal_zone0/temp'):
			try:
				idx = open('/sys/devices/virtual/thermal/thermal_zone0/temp').read()[:2]
				ret = "CPU Temp.: " + idx.replace('\n', '') + DG
			except: pass
		try:
			allsensors = sensors.getSensorsList(sensors.TYPE_FAN_RPM)
			numtemp = len(allsensors)
			for num in range(numtemp):
				idx = allsensors[num]
				isMax = sensors.getSensorValue(idx)
				if isMax > rpm:
					rpm = isMax
		except: pass
		if rpm > 0:
			ret += "RPM: " + str(rpm)
			if temp > 0:
				ret = ret.replace("RPM:",", RPM:")
		if ret == "":
			return "Temp.: N/A, RPM: N/A", temp 
		else:
			return ret, temp 
            			
	def ecmCaidSwitch(self):
		self.ecmCaidTimer.stop()
		aa = config.plugins.setupGlass17.par116.value
		if self.is_ecm:
			self["ecmLineInfo"].setText(self.caidLineTxt)
			self["ecmLineInfo"].color3(aa)
			self.is_ecm = False
		else:
			self["ecmLineInfo"].setText(self.ecmLineTxt)
			self["ecmLineInfo"].color1(aa)
			self.is_ecm = True                               
		if config.plugins.setupGlass17.par17.value == "1" and self.ecmLineTxt != _("Free To Air") and self.ecmLineTxt != ".....":
			self.ecmCaidTimer.start(2400)
		else:
			self["ecmLineInfo"].setText(self.ecmLineTxt)
			self["ecmLineInfo"].color2(aa)
			
	def ecmLineShowFnc(self):                            
		aa = config.plugins.setupGlass17.par116.value
		if self.ecmLineTxt != _("Free To Air") and self.ecmLineTxt != ".....":
			if config.plugins.setupGlass17.par17.value == "0":
				self["ecmLineInfo"].setText(self.ecmLineTxt)
				self["ecmLineInfo"].color1(aa)
			elif config.plugins.setupGlass17.par17.value == "2":
				self["ecmLineInfo"].setText(self.caidLineTxt)
				self["ecmLineInfo"].color3(aa)
			elif config.plugins.setupGlass17.par17.value == "3":
				self["ecmLineInfo"].setText("SID: %s" % self.sid)
				self["ecmLineInfo"].color6(aa)
			elif config.plugins.setupGlass17.par17.value == "4":
				self["ecmLineInfo"].setText(self.caidLineTxt + ",VPID: %s" % self.vpid)
				self["ecmLineInfo"].color6(aa)
		else:
			self["ecmLineInfo"].setText(self.ecmLineTxt)
			self["ecmLineInfo"].color2(aa)
      			
	def __startBitrate(self):
		self.runBitTimer.stop()
		if not self.bitNotActive:
 			return
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		ena = True
		if info:
			vpid = apid = dvbnamespace = tsid = onid = -1
			serviceinfo = service.info()
			vpid = serviceinfo.getInfo(iServiceInformation.sVideoPID)
			apid = serviceinfo.getInfo(iServiceInformation.sAudioPID)
			if ENAEBTR:
				ref = self.session.nav.getCurrentlyPlayingServiceReference()
				if not ref.getPath():
					tsid = ref.getData(2)
					onid = ref.getData(3)
					dvbnamespace = ref.getData(4)
				if vpid > 0:
					if not ENAEBTR2:
						try:
							self.videoBitrate = eBitrateCalculator(vpid, ref.toString(), 1000, 1024*1024)
							self.videoBitrate.callback = self.getVideoBitrateData
							ena = False
						except:
							try:
								self.videoBitrate = eBitrateCalculator(vpid, ref.toString(), 1000, 1024*1024)
								self.videoBitrate.callback.append(self.getVideoBitrateData)
								ena = False
							except: pass
					else:
						try:
							self.videoBitrate = eBitrateCalculator(vpid, dvbnamespace, tsid, onid, 1000, 1024*1024)
							self.videoBitrate.callback.append(self.getVideoBitrateData)
							ena = False
						except: pass
				if apid > 0:
					if not ENAEBTR2:
						try:
							self.audioBitrate = eBitrateCalculator(apid, ref.toString(), 1000, 64*1024)
							self.audioBitrate.callback = self.getAudioBitrateData
							ena = False
						except:
							try:
								self.audioBitrate = eBitrateCalculator(apid, ref.toString(), 1000, 64*1024)
								self.audioBitrate.callback.append(self.getAudioBitrateData)
								ena = False
							except: pass
					else:
						try:
							self.audioBitrate = eBitrateCalculator(apid, dvbnamespace, tsid, onid, 1000, 64*1024)
							self.audioBitrate.callback.append(self.getAudioBitrateData)
							ena = False
						except: pass
			elif not ENA_Z and (fileExists("/usr/bin/btrGen17")) and not self.isBit:
				demux = 2
				a = ""
				try:
					stream = service.stream()
					if stream:
						streamdata = stream.getStreamingData()
						if streamdata:
							if 'demux' in streamdata:
								demux = streamdata["demux"]
							if XCPU == "arm":
								a = "0 "
								if 'adapter' in streamdata:
									a = str(streamdata["adapter"]) + " "
				except:
					pass
				cmd = ["/usr/bin/btrGen17"]
				if XCPU == "arm":
					cmd.append(str(streamdata.get("adapter", 0)))
				cmd.extend([str(demux), str(vpid), str(apid)])
				self["bitrate_info"].setText(_("Starting Bitrate"))
				self["bitrate_info"].color2(config.plugins.setupGlass17.par115.value)
				self.container.execute(*cmd)
				if XCPU == "arm":
					if self.restartBtrTimer.isActive():
						self.restartBtrTimer.stop()
					self.restartBtrTimer.startLongTimer(720)
				self.isBit = True
				ena = False
		self.bitNotActive = ena
		if ena:				
			self["bitrate_info"].setText(_("Bitrate")+_(" failed"))
			self["bitrate_info"].color4(config.plugins.setupGlass17.par115.value)				
				
	def getVideoBitrateData(self,value, status):
		if status:
			self.dataV = value
			self.updBtrData()
		else:
			self.videoBitrate = None

	def getAudioBitrateData(self,value, status): 
		if status:
			self.dataA = value
			self.updBtrData(False)
		else:
			self.audioBitrate = None

	def updBtrData(self, isVid=True):
		self["bitrate_info"].setText(("Btr: V: " + str(self.dataV) + " kb/s, A: " + str(self.dataA) + " kb/s"))
		if isVid:
			try:
				aa = config.plugins.setupGlass17.par115.value
				if int(self.dataV) < 2000: 
					self["bitrate_info"].color4(aa)
				elif int(self.dataV) < 4000: 
					self["bitrate_info"].color3(aa)
				elif int(self.dataV) < 8000: 
					self["bitrate_info"].color1(aa)
				else: 
					self["bitrate_info"].color2(aa)
			except: pass
			
	def dataAvail(self, str):
		try:
			if ISP38:
				str = str.decode("ascii")
			cmddata = str.split(" ")
			tmp = cmddata[3].split("\n")
			tmp1 = cmddata[6]
			if int(tmp[0]) > int(config.plugins.setupGlass17.par35.value):
				self.stopBitrateNow(_("Btr: too high - stopped"))
			elif config.plugins.setupGlass17.par25.value:
				aa = config.plugins.setupGlass17.par115.value
				if self.numBit == 0:
					self["bitrate_info"].setText(("Act: V: " + tmp[0] + " kb/s, A: " + tmp1[:-1] + " kb/s"))
					self["bitrate_info"].color1(aa)
				elif self.numBit == 2:
					self["bitrate_info"].setText(("Avg: V: " + cmddata[2] + " kb/s, A: " + cmddata[5] + " kb/s"))
					self["bitrate_info"].color3(aa)
				elif self.numBit == 4:
					self["bitrate_info"].setText(("Min: V: " + cmddata[0] + " kb/s, A: " + tmp[1] + " kb/s"))
					self["bitrate_info"].color4(aa)
				elif self.numBit == 6:
					self["bitrate_info"].setText(("Max: V: " + cmddata[1] + " kb/s, A: " + cmddata[4] + " kb/s"))
					self["bitrate_info"].color2(aa)
					self.numBit = -2
				self.numBit += 1
			else:
				self.dataV = tmp[0]
				self.dataA = tmp1[:-1]
				self.updBtrData()
		except: pass

	def __stopBitrate(self):
		self.bitNotActive = True
		self.hbboff = True
		self.lastIco = ""
		self.lastIcoSwitch = 0
		config.plugins.setupGlass17.par38.value = CLRDATA
		config.plugins.setupGlass17.par194.value = CLR
		config.plugins.setupGlass17.par178.value = "x"
		self.rEMM = 0
		self.dataV = 0
		self.dataA = 0
		if ENAEBTR:
			self.videoBitrate = None
			self.audioBitrate = None
			self["bitrate_info"].setText(_("Bitrate stopped"))
			self["bitrate_info"].color1(config.plugins.setupGlass17.par115.value)
		elif not ENAEBTR and self.isBit and fileExists("/usr/bin/btrGen17"):
			self.stopBitrateNow()
		self.allCaidPid = ""
		self['active_caidPid'].hide()
		self['caidPids'].hide()
		self['caidPids_back'].hide()
		self['caidPids_end'].hide()
		try:
			os.remove("/tmp/ecm.info")
		except OSError:
			pass

	def refreshWeatherNow(self):
		"""Refresh active Infobar weather immediately for the configured city."""
		if not self.enaWeainf:
			return
		try:
			if self.clrMemTimer.isActive():
				self.clrMemTimer.stop()
			# Run now. The city-keyed cache makes startup instant when last-known
			# data exists, while a changed city can never inherit another city's data.
			self.clearMem()
		except:
			pass

	def clearMem(self):
		self.clrMemTimer.stop()
		if (config.plugins.setupGlass17.par58.value and ECL) and self.refreshValue == 900:
			try:
				if hasattr(os, "sync"):
					os.sync()
				with open("/proc/sys/vm/drop_caches", "w") as cache_control:
					cache_control.write("3\n")
			except OSError:
				pass
		self.refreshValue = 900
		if self.enaWeainf:
			txt = '--'+DG
			png = ""
			self.count += 1
			if netChck():
				self.units = chckUnit()
				try:
					city_ref = config.plugins.setupGlass17.par13.value
					if not str(city_ref).startswith("om|"):
						city_ref = config.plugins.setupGlass17.par13.getText()
					data = openMeteo(city_ref, self.units, 1)
					cur = data.get("current", {})
					code = cur.get("weather_code")
					if code is not None:
						png = wmoPicon(code, not bool(cur.get("is_day", 1)))
					if cur.get("temperature_2m") is not None:
						txt = temperature_fix(str(int(round(float(cur.get("temperature_2m"))))), False)
					self.refreshValue = max(60, int(config.plugins.setupGlass17.par87.value) * 60)
				except Exception as e:
					Writelog("Classic Open-Meteo: %s" % e)
					if self.count < 5:
						self.refreshValue = 30
					if self.count > 10:
						self.count = 0
			if self.chckWeaInafAnim():
				if self.timerpics.isActive():
					self.timerpics.stop()
				f = None
				if png != "":
					path = config.plugins.setupGlass17.par39.value + "/animIconWeather/" + png
					try:
						f = len(os.listdir(path))
					except: pass
				self.pics = []
				self.slideXX = 0
				if f:
					for i in range(0,f):
						self.pics.append(LoadPixmap(path+"/"+str(i)+".png"))					
				else:
					self['picProvSat'].instance.resize(eSize(150,90))
					self['picProvSat'].instance.move(ePoint(self.posX_PSW,self.posY_PSW))
					self.updpicProvSat(self.pngnameWea)
				if len(self.pics) != 0:
					self['picProvSat'].instance.resize(eSize(90,90))
					self['picProvSat'].instance.move(ePoint(self.posX_PSW+30,self.posY_PSW))
					self.timerpics.start(config.plugins.setupGlass17.par170.value)
			else:
				if png != "":
					self.path = "picWeaInf"
					png = self.findPicon(png)                     
				if png != "":
					self.pngnameWea = png
				else:
					self.pngnameWea = SKINPATH+"piconWdef.png"
				self.updpicProvSat(self.pngnameWea)
			self["weaTxt"].setText(txt)
		self.clrMemTimer.startLongTimer(self.refreshValue)

	def dwnW(self,req):
		if not isinstance(req, str) or not req.startswith("https://"):
			return
		self.wConsole.ePopen(["wget", "-T", "2", req, "-O", XML_FILE])
		
	def animTimerEvent(self):
		self.timerpics.stop()
		a = len(self.pics)
		if a != 0:
			if self.slideXX == a:
				self.slideXX = 0
			self['picProvSat'].instance.setPixmap(self.pics[self.slideXX])	
			self.slideXX += 1
			if self.__isOn:
				self.timerpics.start(config.plugins.setupGlass17.par170.value)

	def stopBitrateNow(self, tmp=_("Bitrate stopped")):
		self.isBit = False
		self.bitNotActive = True
		self.container.kill()
		self["bitrate_info"].setText(tmp)
		self["bitrate_info"].color4(config.plugins.setupGlass17.par115.value)
      				
	def restartBtrStop(self):
		self.restartBtrTimer.stop()
		if self.isBit:
			self.stopBitrateNow()
			self.__startBitrate()
		
	def __evTunedIn(self):
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if info:
			self.enaTuned = True
			self.runChkTimer.start(750)
			self.emm_timer.start(700)
			if ENAHBB:
				self.runHBBTimer.start(4000, True)
			if self.enaBit and self.bitNotActive and config.plugins.setupGlass17.par2.value:
				t = 8000
				if ENAEBTR:
					t = 5000
				self.runBitTimer.start(t)
				self["bitrate_info"].setText(_("Preparing Bitrate"))
				self["bitrate_info"].color3(config.plugins.setupGlass17.par115.value)
			self.chckSS()

	def chckSS(self, state=False):
		if config.plugins.setupGlass17.par64.value:	
			if not state:
				service = self.session.nav.getCurrentService()
				info = service and service.info()
				if info:	
					ref = eServiceReference(info.getInfoString(iServiceInformation.sServiceref))
					if isinstance(ref, eServiceReference):
						isRadioService = ref.getData(0) in (2, 10)
						if isRadioService and keyManage.TunerTest():
							state = True
			if self.state != state and keyManage.dialog is not None:
				self.state = state
				if state:
					keyManage.showME()
				else:
					keyManage.hideME()
						
	def __updateEMM(self):
		self.emm_timer.stop()
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if info is not None:
			if self.enaTuned:
				self.setTunerInfo(service)
				self.enaTuned = False
			self.caidsLive = info.getInfoObject(iServiceInformation.sCAIDs)
			self.showDyn_EMM_ECM()
			self.forceUpd = True
			try:
				caidpids = info.getInfoObject(iServiceInformation.sCAIDPIDs)
				if len(caidpids) != 0:
					self.allCaidPid = ""
					h_size = 0
					no_error = True
					for x in range(0, len(caidpids)):
						c = "%0.4X" % int(caidpids[x][0])
						p = "%0.4X" % int(caidpids[x][1])
						tt = "%s : %s\n" % (c,p)
						if "-0001" in tt or "-1" in tt:
							no_error = False
							break
						if not tt in self.allCaidPid:
							self.allCaidPid += tt
							h_size += 1
					if no_error:
						h_size = h_size*26 + 66
						if config.plugins.setupGlass17.par26.value:
							self['caidPids'].setText(self.allCaidPid)
							self['caidPids'].instance.resize(eSize(195,h_size - 62))
							self['caidPids'].show()
							self['caidPids_back'].instance.resize(eSize(255,h_size))
							self['caidPids_back'].show()
							self['caidPids_end'].move(ePoint(self.pidsX, h_size + self.pidsY))
							self['caidPids_end'].show()
					else:
						self.emm_timer.start(2000)
			except: pass
			if not self.emm_timer.isActive() and self.ecmLineTxt != _("Free To Air") and self.CaidsChck() == _("Error reading CaIds !!!") and self.rEMM < 4:
				if self.chckEcmInfo():
					self.rEMM += 1
				self.emm_timer.start(2000)			
        			
	def chckEcmInfo(self):
		if os.path.isfile('/tmp/ecm.info'):
			try:
				if os.path.getsize('/tmp/ecm.info') > 10:
					f = open('/tmp/ecm.info', "r").read()
					if f.find("fta") == -1 and f.find("Signature OK") == -1 and f.find("system: BISS") == -1:
						return True
			except: pass
		return False
		
	def __updCamECM(self):
		self.runChkTimer.stop()
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if info:
			serviceinfo = service.info()
			if serviceinfo.getInfo(iServiceInformation.sIsCrypted) or self.chckEcmInfo():
				self.readEcm()
				self.startEcmCaidInfo(0)
			else:			
				self.actFta()
			if config.plugins.setupGlass17.par42.value:
				info = service.audioTracks()
				if info:
					a = info.getCurrentTrack()
					if a != self.cAud:
						self.cAud = a				
						self.__evUpdatedInfo()
			self.runChkTimer.start(int(config.plugins.setupGlass17.par74.value)*1000, True)
		
	def actFta(self, ena=True, service=None):
		self.ecmLineTxt = ({True:_("Free To Air"), False:"....."}[ena])
		if service is None:
			self.ecmLineShowFnc()
		self['ecmValues'].setText(CLRDATA)
		self['ecmlabels'].setText(ECM_LABELS)
		self.picCamShow()
		if ena:
			self.netStateMove(self.x_dyn_pos_CA - self.width_D_icons)

	def picCamShow(self, ca="Fta", ena=True):
		if config.plugins.setupGlass17.par5.value != "0":
			x = "%s/piconCam/%s-fs8.png" % (config.plugins.setupGlass17.par39.value, ca)
			if not fileExists(x):
				x = "%sicons/missing-fs8.png" % SKINPATH
			if ena:
				self["piconCam"].instance.setPixmapFromFile(x)
			self["piconEcm"].instance.setPixmapFromFile(x)

	def readEcm(self):
		def chckIdx(what):
			if "X" in what:
				idx = what.index("X")
				what = what[idx+1:]
			return what
		def cutMe(c):
			c = c.replace("\n","")
			if len(c) > 21:
				if c[-1] == ")": 
					c = "%s..)" % c[:21]
				else:
					c = "%s.." % c[:21]
			return c + "\n"
		def setEcmTime(t):
			t = t.strip()
			if not "." in t:
				if len(t) == 4:
					t =  "%s.%s" % (t[0], t[1:])
				elif t.isdigit():
					t =  "0.%003d" % int(t)
			return t + "\n"
		def setCaid(t):
			if t in FCAID:
				return t
			else:
				return t[:2]
		def convCaid(caid):
			if caid.startswith("18"):
				coding = "Nagravision"
			elif caid in ["1702\n","1722\n","1762\n"]:
				coding = "Betacrypt"
			elif caid.startswith("01"):
				coding = "Seca"
			elif caid.startswith("06"):
				coding = "Irdeto"
			elif caid.startswith("07"):
				coding = "DigiCipher"
			elif caid.startswith("22"):
				coding = "Codicrypt"
			elif caid.startswith("A1"):
				coding = "Rosscrypt"
			elif caid.startswith("05"):
				coding="Viaccess"
			elif caid.startswith("0B"):
				coding="Conax"
			elif caid.startswith("0D"):
				coding="Cryptoworks"
			elif caid in ["4AE1\n","4AE0\n","44A0\n"]:
				coding="DRE-crypt"
			elif caid == "4ABF\n":
				coding="DGCrypt"
			elif caid == "4AEE\n":
				coding="Bulcrypt"
			elif caid in ["4AD1\n","4AD0\n"]:
				coding="XCrypt"
			elif caid == "4AFC\n":
				coding="Panaccess"
			elif caid == "4A70\n":
				coding="Dreamcrypt"
			elif caid in ["4AEA\n","4B24\n","1EC0\n"]:
				coding="CryptoGuard"
			elif caid == "4B63\n":
				coding="RedCrypter"
			elif caid == "4B64\n":
				coding="TVkey"
			elif caid == "4AF4\n":
				coding="MDC"
			elif caid == "4347\n":
				coding="CryptOn"
			elif caid.startswith("09"):
				coding="Videoguard"
			elif caid.startswith("55"):
				if caid == "5581\n":
					coding="Bulcrypt"
				else:
					coding="Griffin"
			elif caid.startswith("26"):
				coding="Biss"
			elif caid.startswith("56") or caid.startswith("17"):
				coding="Verimatrix"
			elif caid == "2710\n":
				coding="Exset"
			elif caid.startswith("0E"):
				coding="PowerVU"
			elif caid == "1010\n":
				coding="Tandberg"
			elif caid == "4AB0\n":
				coding="Sky-Pilot"
			elif caid == "FFFF\n":
				coding="Constant-CW"
			else:
				coding="Unknown"
			return coding
		def fixCW(t):
			t = t.strip()
			if t[2] != " ":
				b = ""
				for i in range(0,len(t),2):
					b += t[i:i+2] + " "
				return (b.strip())[:24]
			else:
				return t
		try:
			tmp = open('/tmp/ecm.info', 'r')
			content = tmp.read()
			tmp.close
		except:
			content = ""
		lines = content.split("\n")
		caid=provider=pid=using=prot=adress=hops=share=ecmTime=coding=typecam=provid=cw0=cw1=chid="..............\n"
		config.plugins.setupGlass17.par195.value = ""
		typeCAviaCam2 = ""
		isEmu = ""
		oscVersion = "\n"
		doscam = ""
		if content != "":
			typcm = False
			dyntmpcaid = "xxx"
			for line in lines:
				if "chid:" in line.lower():
					if ", chid:" in line:
						chid = line.split("chid:")[1]
						if "," in chid:
							chid = chid.split(",")[0]
					else:
						chid = line.split(":")[1] 
					chid = chckIdx(chid.upper()) + "\n"
				if line.startswith("protocol:"):
					prot = parseEcmInfoLine(line) + "\n"
					if "constcw" in prot:
						isEmu = "emu" 
						typeCAviaCam2 = "emu"
				elif line.startswith("CW0:") or line.startswith("cw0:"):
					cw0 = fixCW(line.split(":")[1])+"\n" 
				elif line.startswith("CW1") or line.startswith("cw1:"):
					cw1 = fixCW(line.split(":")[1])+"\n"
				if line.startswith("Service:"):
					typecam = "Wicardd\n"
				elif line.startswith("=====") and typecam == "..............\n":
					typecam = "Mgcamd\n"
					typcm = True
				elif typecam == "..............\n":
					typecam = "CCcam\n"
				elif typecam == "CCcam\n" and line.startswith("reader:"):
					typecam = "OScam\n"
				elif typecam == "CCcam\n" and line.startswith("FROM:"):
					typecam = "Camd3\n"
				if line.startswith("caid:") or line.startswith("====") or line.startswith("CAID ") or line.startswith("CAID:"):
					if line.startswith("===="):
						caid = str(parseEcmInfoLine(line,"CaID")).upper()
						caid = chckIdx(caid)
						caid = caid[:4]+"\n"
					elif line.startswith("CAID "):
						caid = str(line.split(' ')[1].split())
						caid = caid[2:-2]
						caid = chckIdx(caid.upper())
						caid = caid[:4]+"\n"
					else:
						caid = str(parseEcmInfoLine(line)).upper()
						caid = chckIdx(caid)
						if len(caid) == 3:
							caid = "0%s" % caid
						caid = caid + "\n"
					dyntmpcaid = setCaid(caid[:-1])
					coding = convCaid(caid)
				if line.startswith("provid:") or line.startswith("CAID ") or line.startswith("SysID"):
					if line.startswith("CAID "):
						provid = str(line.split(' ')[5].split())
						provid = provid[2:-2]
						provid = chckIdx(provid.upper())
						provid += "\n"
					elif line.startswith("SysID"):
						provid = str(line.split(' ')[1].split())
						provid = provid[2:-2]
						provid = provid.upper() + "\n"
					else:
						provid = parseEcmInfoLine(line)
						provid = provid.upper()
						provid = provid[2:] + "\n"
				elif line.startswith("provider:") or line.startswith("prov: ") or line.startswith("Provider:"):
					provider = parseEcmInfoLine(line) + "\n"
					if provider.__contains__("key:"):
						idx = provider.index("key:")
						provider = provider[:idx] + "\n"
					if provider.__contains__(","):
						idx = provider.index(",")
						provider = provider[:idx] + "\n"
					if provider.__contains__("0X") or provider.__contains__("0x"):
						provider = chckIdx(provider.upper())
					provider = cutMe(provider)
				if line.startswith("pid:") or line.startswith("====") or line.startswith("CAID "):
					if line.startswith("===="):
						pid = str(line.split(' ')[7].split())
						pid = pid.replace(",","")
						pid = pid[2:-2]
					elif line.startswith("CAID "):
						pid = str(line.split(' ')[3].split())
						pid = pid[2:-3]
					else:
						pid = parseEcmInfoLine(line)
					pid = chckIdx(pid.upper())
					if len(pid) == 2:
						pid = "00%s" % pid
					if len(pid) == 3:
						pid = "0%s" % pid
					pid += "\n"
				if line.startswith("using:") or line.startswith("source:") or line.startswith("reader:") or line.startswith("decode:"):
					if line.startswith("source:"):
						using = str(line.split(' ')[1].split())
						using = using[2:-2] + "\n"
					elif line.startswith("decode:"):
						if typcm:
							typecam = "Mgcamd\n"
						else:
							typecam = "Gbox\n"
						if line.__contains__("slot") or line.__contains__("Local"):
							using = "Cardreader\n"
						elif line.__contains__("Internal"):
							using = "Emu\n"
							typecam = "Gbox\n"
						elif line.__contains__("com"):
							using = parseEcmInfoLine(line) + "\n"
						else:
							using = "Network\n"
					else:
						using = parseEcmInfoLine(line) + "\n"
						if using == "sci\n":
							using = "Cardreader\n"
					using = cutMe(using)
					if line.__contains__("emu") or line.__contains__("Internal"):
						isEmu = "emu" 
						typeCAviaCam2 = "emu"
				if line.startswith("address:") or line.startswith("source:") or line.startswith("from:") or line.startswith("FROM:") or line.startswith("decode:"):
					if line.startswith("source: net"):
						idex = line.index("(")
						adress = line[idex:]
						adress = adress.replace("\n", "")
						adress = str(adress.split(' ')[2].split())
						adress = adress[2:-3] + "\n"
					elif line.startswith("source: emu") or line.startswith("decode:"):
						adress = "..............\n"
						if line.startswith("decode:") and not using.__contains__("com"): 
							adress = parseEcmInfoLine(line) + "\n"
					else:
						adress = parseEcmInfoLine(line) + "\n"
						if adress == "/dev/sci0\n":
							if IS800SE:
								adress = "Upper slot \n"
							else:
								adress = "Lower slot \n"
						elif adress == "/dev/sci1\n":
							if IS800SE:
								adress = "Lower slot \n"
							else:
								adress = "Upper slot \n"
						elif adress.__contains__("local"):
							adress = "Local slot\n"
						elif coding == "Unknown":
							adress = "..............\n"
					adress = cutMe(adress)
					if isEmu == "":
						if (using.__contains__("com") and typecam == "Gbox\n") or adress.__contains__("127.0.0.1") or adress.__contains__("slot") or adress.__contains__("local") or (line.startswith("decode:") and (line.__contains__("slot") or line.__contains__("Local"))):
							typeCAviaCam2 = "crd"
						elif line.__contains__("emu"):
							typeCAviaCam2 = "emu"
						elif (adress != "..............\n" and using != "unsupported CAs\n") or (line.startswith("decode:") and line.__contains__("Network")):
							typeCAviaCam2 = "net"
					else:
						typeCAviaCam2 = "emu"					
				elif line.startswith("hops:"):
					hops = parseEcmInfoLine(line) + "\n"
				elif line.startswith("prov:") and "dist:" in line and "," in line:
					l = ""
					for ii in line.split(","):
						if "prov:" in ii:
							provid = chckIdx((parseEcmInfoLine(ii)).upper()) + "\n"
						if "dist:" in ii:
							hops = parseEcmInfoLine(ii)
						if "slot:" in ii:
							l += ", Slot: " + parseEcmInfoLine(ii)
						if "level:" in ii:
							l += ", Level: " + parseEcmInfoLine(ii)
					if not "\n" in hops:
						hops += l + "\n"
				if line.startswith("share:") or line.startswith("source:"):
					if line.startswith("source: net"):
						idex = line.index("(")
						share = line[idex:]
						share = share.replace("\n", "")
						share = share.split(' ')[0].strip()
						share = share[3:-2] + "\n"
					elif line.startswith("source: emu"):
						share = "..............\n"
					else:
						share = parseEcmInfoLine(line) + "\n"
					share = cutMe(share)
				elif line.startswith("response:") or line.startswith("ecm time:") or line.startswith("Time:(") or line.startswith("Time: (") or line.startswith("1") or line.startswith("2") or line.startswith("3") or line.startswith("4") or line.startswith("5") or line.startswith("6") or line.startswith("7") or line.startswith("8") or line.startswith("9"):
					if line.startswith("ecm time:") or line.startswith("response:"):
						ecmTime = parseEcmInfoLine(line)
					elif line.startswith("Time:(") or line.startswith("Time: ("):
						ecmTime = (line.split('(')[1]).strip()
						if " " in ecmTime:
							ecmTime = (ecmTime.split(' ')[0]).strip()
						if ")" in ecmTime:
							ecmTime = (ecmTime.split(')')[0]).strip()
					else:
						ecmTime = line.split(' ')[0].strip()
				elif line.startswith("response time:"):
					ecmTime = line.strip().split("e:")[1]				
					if "(" in ecmTime:
						adress = cutMe((ecmTime.strip().split("(")[1]).replace(")","").replace("\n",""))				
						typeCAviaCam2 = "net"
						using = cutMe(((ecmTime.strip().split("(")[0]).strip().split("decoded by")[1])[1:])
					else:            
						using = cutMe((ecmTime.strip().split("decoded by")[1])[1:])            						
						if "funcard" in using.lower() or "goldcard" in using.lower():
							typeCAviaCam2 = "emu"
						elif "upper" in using.lower() or "lower" in using.lower():
							typeCAviaCam2 = "crd"
					ecmTime = ecmTime.strip().split("ms")[0]
				if line.startswith("Signature OK") and typecam == "CCcam\n":
					typecam = "Mgcamd\n"
				if (line.startswith("Time:(") or line.startswith("Time: (")) and typecam == "Mgcamd\n":
					typecam = "Mbox\n"
			if typecam != "OScam\n":
				try:
					ax = typecam
					try:
						process_lines = subprocess.check_output(["ps", "-ef"], universal_newlines=True).splitlines()
					except (OSError, subprocess.CalledProcessError):
						process_lines = subprocess.check_output(["ps"], universal_newlines=True).splitlines()
					for f in process_lines:
						f = f.upper()
						if f.find("OSCAM") != -1:
							typecam = "OScam\n"
							break
						elif f.find("GCAM") != -1 and f.find("MGCAMD") == -1:
							typecam = "Gcam\n"
							break
						elif f.find("NCAM") != -1:
							typecam = "Ncam\n"
							break
				except: pass
			if typecam == "Gbox\n" and using == "Network\n":
				try:
					f = open("/tmp/share.info","r")
					for l in f.readlines():
						l = l.replace("\n", "").strip().split(" ") 
						if len(l) == 10:
							if provider[:-1] == parseEcmInfoLine(l[9]) and l[5].startswith(caid[:-1]): 
								adress = l[3] + "\n"
								adress = cutMe(adress)
								hops = "%s, %s, %s\n" % (l[6], l[7], l[8]) 
								share = "%s, %s\n" % (l[5], l[9])
								break
					f.close()
				except: pass
			elif (typecam in ("OScam\n","Ncam\n","Gcam\n")) and (os.path.isfile(GCM) or os.path.isfile(NCM) or os.path.isfile("/tmp/oscam.version") or os.path.isfile("/tmp/.oscam/oscam.version") or os.path.isfile(DSC)):
				oscfile = "/tmp/.oscam/oscam.version"
				if os.path.isfile("/tmp/oscam.version"):
					oscfile = "/tmp/oscam.version"
				ax = 0 
				for xi in (DSC,NCM,oscfile,GCM):
					if os.path.isfile(xi):
						l = os.stat(xi).st_mtime 
						if l > ax:
							ax = l					
							oscfile = xi
				if "ncam" in oscfile:
					typecam = "Ncam\n"
				elif "gcam" in oscfile:
					typecam = "Gcam\n"
				try:
					f = open(oscfile,"r")
					for l in f.readlines(): 
						if l.startswith("Version:"):
							if "Rev." in l:
								if "ymod" in l:
									oscVersion = " (ymod" + (l.replace("\n","").split("ymod")[1]).split(" ")[0] + ")\n"
								else:
									idx = l.index("Rev.") 
									oscVersion = " (" + l[idx+4:].replace("\n","").strip() + ")\n"
							elif "-r" in l:
								idx = l.index("-r") 
								oscVersion = " (" + l[idx+2:].replace("\n","").strip() + ")\n"
							if "(0)" in oscVersion:
								idx = l.index("ymodv")
								oscVersion = " (" + l[idx+5:].replace("\n","").replace("Rev. 0","").strip() + ")\n"
							elif "emu" in oscVersion:     
								oscVersion = oscVersion.replace("-r16-GS","")
							elif "DOSC" in l:
								idx = l.index("DOSC") 
								oscVersion = " (" + l[idx+7:].replace("\n","").strip() + ")\n"							
								doscam = "D"
							if not "(" in oscVersion:
								oscVersion = " (" + (l.split("Version:")[1]).replace("ncam-","").replace("gcam-","").replace("\n","").strip() + ")\n"
							break
					f.close()
					if "(" in oscVersion and "-" in oscVersion and "." in oscVersion:
						oscVersion = oscVersion.replace("(","").replace(")","")          					
					oscVersion = (cutMe("xxxxxxx"+oscVersion)).replace("xxxxxxx","")
				except: pass
			elif typecam == "CCcam\n" and ecmTime == "..............\n" and adress == "..............\n":
				typecam = "Scam\n"
			if provider == "Unknown\n":
				provider = "..............\n"
			tmpline = ""
			if ecmTime != "..............\n":
				ecmTime = setEcmTime(ecmTime)
			if using == "unsupported CAs\n":
				tmpline = _("Unsuported CA found, no correct ECM info !!!")
			else:
				if typecam != "..............\n":
					tmpline = "CAM: " + typecam[:-1]
				if caid != "..............\n":
					tmpline = tmpline + ", CAID: " + caid[:-1]
				if config.plugins.setupGlass17.par3.value:
					if adress != "..............\n":
						tmpline = tmpline + ", Source: " + adress[:-1]
					if using != "..............\n" and adress == "..............\n":
						tmpline = tmpline + ", Source: " + using[:-1]
					if using != "..............\n" and typecam == "OScam\n":
						tmpline = tmpline + ", Using: " + using[:-1]
				else:
					adress = "..............\n"
				if provid != "..............\n" and typecam == "Gbox\n":
					tmpline = tmpline + ", ProvId: " + provid[:-1]
				if provider != "..............\n" and typecam == "Gbox\n":
					tmpline = tmpline + ", Provider: " + provider[:-1]
				if pid != "..............\n" and config.plugins.setupGlass17.par196.value:
					tmpline = tmpline + ", PID: " + pid[:-1]
				if chid != "..............\n" and config.plugins.setupGlass17.par197.value:
					tmpline += ", CHID: " + chid[:-1]
				if hops != "..............\n":
					tmpline = tmpline + ", Hops: " + hops[:-1]
				if ecmTime != "..............\n":
					tmpline = tmpline + ", Time: " + ecmTime[:-1]
			if not config.plugins.setupGlass17.par193.value or caid[:-1] + " : " + pid[:-1] in self.allCaidPid:
				self.caidLineTxt = self.CaidsChck((caid[:-1]))
				self.ecmLineTxt = tmpline
				self.ecmLineShowFnc() 						
				typecam = doscam+typecam
				provider, provid = self.chid(provider, provid, chid)
				config.plugins.setupGlass17.par38.value = (typecam.replace("Mgc","MGc").replace("\n",oscVersion)+caid+provider+provid+pid+using+prot+adress+hops+share+ecmTime+coding)
				if config.plugins.setupGlass17.par50.value:
					config.plugins.setupGlass17.par38.value += "\n"+cw0+cw1
				config.plugins.setupGlass17.par194.value = "\n"+cw0+cw1
				self['ecmValues'].setText(config.plugins.setupGlass17.par38.value)
				config.plugins.setupGlass17.par178.value = typeCAviaCam2
				if self.typecam != typecam or self.forceUpd:
					self.typecam = typecam
					if config.plugins.setupGlass17.par5.value == "1":
						oscVersion = config.plugins.setupGlass17.par39.value + "/piconCam/" + typecam[:-1] + "-fs8.png"
						if not os.path.isfile(oscVersion):
							oscVersion = SKINPATH+"icons/missing-fs8.png"
						self["piconCam"].instance.setPixmapFromFile(oscVersion)
					if typecam != "..............\n":
						self["Dcam"].instance.setPixmapFromFile((SKINPATH + "icons/" + typecam[:-1] + "-fs8.png"))
					else:
						self["Dcam"].hide()
				if ((self.tstca != coding or self.typeCAviaCam != typeCAviaCam2) and (using != "unsupported CAs\n")) or self.forceUpd:
					self.forceUpd = False
					self.tstca = coding 
					self.picCamShow(coding, False)
					self.typeCAviaCam = typeCAviaCam2
					self.showDyn_EMM_ECM(dyntmpcaid, typeCAviaCam2, "True")
				if config.plugins.setupGlass17.par26.value:
					try:
						share = caid[:-1] + " : " + pid[:-1]
						if share in self.allCaidPid:
							self['caidPids'].setText(("\n"+self.allCaidPid.replace((share+"\n"),"")))
							self['active_caidPid'].setText(share)
							self['active_caidPid'].show()
					except: pass
			return
		ena = _("No info from Cam")
		caid = "xxx"
		ci = "xxx"
		if ENACI and config.plugins.setupGlass17.par192.value:
			try:
				num = eDVBCIInterfaces.getInstance().getNumOfSlots()
				if num > 0 and len(self.caidsLive) > 0:
					for x in range(num):
						ca = eDVBCIInterfaces.getInstance().readCICaIds(x)
						if ca:
							for i in self.caidsLive:
								if i in ca and int(i) > 0:
									caid = "%0.4X" % i
									adress = "Slot: %s" % (x+1)
									ena = "%s, CAID: %s" % (adress,caid)
									using = eDVBCI_UI.getInstance().getAppName(x)
									if using and using != "":
										ena += ", CI: %s" % using
									else:
										using = ".............."
									ci = "ci" + str(x+1)
									break
			except: pass
		self.ecmLineTxt = ena
		self.caidLineTxt = self.CaidsChck()
		self.ecmLineShowFnc()
		self.tstca = "" 
		self.typecam = ""
		self.typeCAviaCam = ""
		config.plugins.setupGlass17.par178.value = "x"
		if caid == "xxx" or ci == "xxx":
			config.plugins.setupGlass17.par38.value = CLRDATA
			config.plugins.setupGlass17.par194.value = CLR	
			self.picCamShow("Unknown")
			self['ecmValues'].setText(config.plugins.setupGlass17.par38.value)
			self['ecmlabels'].setText(ECM_LABELS)
		else:
			caid += "\n"
			coding = convCaid(caid)
			provider, provid = self.chid(provider, provid, chid)
			config.plugins.setupGlass17.par38.value = "CAM\n"+caid+provider+provid+pid+using+"\n"+prot+adress+"\n"+hops+share+ecmTime+coding
			if config.plugins.setupGlass17.par50.value:
				config.plugins.setupGlass17.par38.value += "\n"+cw0+cw1
			config.plugins.setupGlass17.par194.value = "\n"+cw0+cw1
			self['ecmValues'].setText(config.plugins.setupGlass17.par38.value)
			self.picCamShow(coding,False)
			oscVersion = config.plugins.setupGlass17.par39.value + "/piconCam/CAM-fs8.png"
			if not os.path.isfile(oscVersion):
				oscVersion = SKINPATH+"icons/missing-fs8.png"
			self["piconCam"].instance.setPixmapFromFile(oscVersion)
			caid = setCaid(caid[:-1])
		self.showDyn_EMM_ECM(caid,ci)
		if config.plugins.setupGlass17.par26.value:
			try:
				self['caidPids'].setText(self.allCaidPid)
				self['active_caidPid'].hide()
			except: pass
      				
	def chid(self, a, b, c):
		if c != "..............\n":
			if a == "..............\n":
				a = c
				config.plugins.setupGlass17.par195.value = "Prov.:"
				self['ecmlabels'].setText(ECM_LABELS.replace("Prov.:","CHID:"))
			elif b == "..............\n":
				b = c
				config.plugins.setupGlass17.par195.value = "PrvID:"
				self['ecmlabels'].setText(ECM_LABELS.replace("PrvID:","CHID:"))
			else:
				self['ecmlabels'].setText(ECM_LABELS)
		else:
			self['ecmlabels'].setText(ECM_LABELS)
		return a, b

	def CaidsChck(self, ecm="xxx"):
		txt = _("Error reading CaIds !!!")
		if self.caidsLive is not None:
			num_caid = len(self.caidsLive)
			if num_caid > 0:
				a = "%0.4X" % self.caidsLive[0]
				if num_caid == 1 and a == "0000":
					return txt
				if ecm == "xxx":
					txt = _("Available:")
				else:
					txt = _("Used:") + " " + ecm + ", "				
					if num_caid > 1:
						txt += _("Remaining:") + " "
				for caid in self.caidsLive:
					caid = "%0.4X" % caid
					if caid != ecm:
						txt += caid + ", "		
		if txt != _("Error reading CaIds !!!"):
			txt += "Sid: %s" % self.sid
		return txt

	def checkHBB(self):
		self.runHBBTimer.stop()
		if self.lastIcoSwitch == 0:
			if ENAHBB and self.hbboff:
				try:
					apps = eHbbtv.getInstance().getApplicationIdsAndName()
					if len(apps) != 0:
						self.hbboff = False
				except: pass
			if self.hbboff:
				try:
					service = self.session.nav.getCurrentService()
					info = service and service.info()
					if info.getInfoString(iServiceInformation.sHBBTVUrl) != "":
						self.hbboff = False
				except: pass        		
			if not self.hbboff:
				self.__evUpdatedInfo(False)		
		else:
			try:
				if self.lastIcoSwitch == 1:   
					self["hbb"].show()
					self[self.lastIco].hide()
					self.lastIcoSwitch = 2
				else:     
					self["hbb"].hide()
					self[self.lastIco].show()
					self.lastIcoSwitch = 1
			except: pass  
			self.runHBBTimer.start(2000, True)
                          		
	def __evUpdatedVideoType(self):
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if info is not None:
			self.setTunerInfo(service)

	def __evUpdatedInfo(self, noforced=True):
		def chckIPbit(a):
			if "-" in a or ":0" in a:
				return ""
			return a
		if noforced:
			service = self.session.nav.getCurrentService()
			info = service and service.info()
			if info is not None:
				enaIp = False
				refer = eServiceReference(info.getInfoString(iServiceInformation.sServiceref))
				if refer is not None:
					refer = refer.toString()
					if refer.startswith("-1:"):
						refer = self.session.nav.getCurrentlyPlayingServiceReference()
						if refer is not None:
							refer = refer.toString()
					playing = self.session.nav.getCurrentlyPlayingServiceReference()
					native_dab = is_native_dab(playing)
					if native_dab:
						refer = playing.toString()
						self.setTunerInfo(service)
					self.showPicon(refer)
					enaIp = not native_dab and (refer.startswith("4097:0") or "3a//" in refer or "http" in refer)
					if enaIp:
						self.setTunerInfo(service, chckIPTVprov(refer))
						self.actFta(False, service)
				tmp = self.getServiceInfoString(info, iServiceInformation.sVideoWidth)
				tpid = enaIp and self.noReplace and not refer.startswith("5001:") and not refer.startswith("5002:") and config.plugins.setupGlass17.par225.value
				if tmp and str(tmp).isdigit():
					vpid = ""
					if config.plugins.setupGlass17.par120.value:
						try:
							apid = open("/proc/stb/vmpeg/0/progressive", "r").read()
							if apid.find("0") != -1:
								vpid = "i"
							elif apid.find("1") != -1:
								vpid = "p"
						except: pass
						if vpid == "":
							try:
								vpid = ({False:'i', True:'p'}[info.getInfo(iServiceInformation.sProgressive) == 1])
							except: pass
					apid = "%sx%s%s" % (tmp,self.getServiceInfoString(info, iServiceInformation.sVideoHeight),vpid)
					if vpid == "":
						apid = apid.replace("x"," x ")
					self["Video_size"].setText(apid)
					if enaIp:
						self.chckSS()
				elif tpid or (not enaIp and (refer.startswith("1:0:2") or refer.startswith("1:0:10"))):
					self["Video_size"].setText(_("Radio"))
					if tpid:
						self.chckSS(True)
				self.sid = "%0.4X" % info.getInfo(iServiceInformation.sSID)
				if self.sid == "-0001":
					self.sid = "N/A"
				serviceinfo = service.info()
				vpid = serviceinfo.getInfo(iServiceInformation.sVideoPID)
				apid = serviceinfo.getInfo(iServiceInformation.sAudioPID)
				if not config.plugins.setupGlass17.par2.value and not enaIp:
					self["bitrate_info"].setText("")
				elif enaIp and config.plugins.setupGlass17.par2.value:
					try:
						if (vpid > 0 or apid > 0) and self.bitNotActive:
							self.__startBitrate()
						else:				        
							b = chckIPbit("A:%s  " % str(int(info.getInfo(iServiceInformation.sTagBitrate))/1000))
							d = chckIPbit("H:%s  " % str(int(info.getInfo(iServiceInformation.sTagMaximumBitrate))/1000))
							c = chckIPbit("L:%s  " % str(int(info.getInfo(iServiceInformation.sTagMinimumBitrate))/1000))
							b = "%s%s%skb/s" % (b,c,d)
							if b == "kb/s":
								b = ""
							self["bitrate_info"].setText(b)
							self["bitrate_info"].color1(config.plugins.setupGlass17.par115.value)				
					except: pass				
				self.vpid = "%0.4X" % vpid
				if self.vpid == "-0001":
					self.vpid = "N/A"
				self.x_dyn_pos = self.posX_DynIco - 30
				if self.enaIcoTun and config.plugins.setupGlass17.par187.value:
					feinfo = service and service.frontendInfo()
					if feinfo is not None:
						frontendData = feinfo and feinfo.getAll(True)
						if frontendData is not None:
							num = -1
							tpid = ""
							if ENA_I_T:
								num = frontendData.get("input_number", -1)
								if num is not None and num > -1:
									tpid = getTunerDesc(num)
							if tpid == "":
								num = frontendData.get("tuner_number")
								if num in range(0,20):
									try:
										tpid = (nimmanager.getNimDescription(num).split(":")[0]).strip()
										if tpid[-1].isdigit():
											tpid = tpid[-2:]
										else:
											tpid = tpid[-1]									
									except: pass
							if tpid != "":
								tpid = "%sicons/icon_%sw.png" % (SKINPATH, tpid.lower())
								if os.path.isfile(tpid):
									try:
										self["tuner"].instance.setPixmapFromFile(tpid)
										self.x_dyn_pos += 30
										self["tuner"].move(ePoint(self.x_dyn_pos, self.posY_DynIco))
										self["tuner"].show()
										self.x_dyn_pos -=  self.widthDynIco
									except: self["tuner"].hide()
								else:
									self["tuner"].hide()
							else:
								self["tuner"].hide()
						else:
							self["tuner"].hide()
					else:
						self["tuner"].hide()
				else:
					self["tuner"].hide()
				if tmp != "N/A":
					try:					
						self.uhdtype = "x"
						num = int(tmp)
						if num < 721:
							num = 0
						elif num < 1281:
							num = 1
						elif num < 1921:
							num = 2
						elif num < 3841:
							num = 3								
							self.uhdtype = "34"	
						else:
							num = 3								
							self.uhdtype = "35"
						self["hd_sd"].setPixmapNum(num)
						self["hd_sd"].move(ePoint(self.x_dyn_pos, self.posY_DynIco))
						self["hd_sd"].show()
						self.x_dyn_pos -=  self.widthDynIco
						if "3" in self.uhdtype and not self.uhdTimer.isActive():
							self.uhdTimer.start(2000)						
					except: self["hd_sd"].hide()
				else:
					self["hd_sd"].hide()
				tpid = info.getInfo(iServiceInformation.sTXTPID)
				if tpid != -1:
					self["txt"].move(ePoint(self.x_dyn_pos, self.posY_DynIco))
					self["txt"].show()
					self.x_dyn_pos -=  self.widthDynIco
				else:
					self["txt"].hide()
				tmp = -1
				audio = service.audioTracks()
				n = 0
				if audio:
					n = audio.getNumberOfTracks()
					if not config.plugins.setupGlass17.par42.value:
						idx = 0
						while idx < n:
							i = audio.getTrackInfo(idx)
							for x in (i.getDescription(), i.getLanguage()):
								xx = x.upper()
								if "AC3" in xx or "DTS" in xx or "DOLBY" in xx:
									tmp = 0
									break
							if EACC and tmp != 0:
								try:
									if i.getType() in (iAt.atAC3, iAt.atDDP, iAt.atDTS, iAt.atDTSHD):
										tmp = 0
										break
								except: pass
							idx += 1
					else:
						try:
							i = audio.getTrackInfo(audio.getCurrentTrack())					
							x = (i.getDescription()).upper()
							idx = (i.getLanguage()).upper()
							if "5.1" in x or "5.1" in idx:
								tmp = 1
							elif "2.0" in x or "2.0" in idx:
								tmp = 2
							elif "DTS" in x or "DTS" in idx:
								tmp = 4
							elif "AAC" in x or "AAC" in idx:
								tmp = 5
							elif "DOLBY" in x or "AC3" in x or "DOLBY" in idx or "AC3" in idx:
								tmp = 0
							elif "MPEG" in x or "MPEG" in idx:
								tmp = 3
						except: pass
						if EACC and tmp == -1:
							try:
								idx = i.getType()
								if idx in (iAt.atDTS, iAt.atDTSHD):
									tmp = 4				
								elif idx == iAt.atMPEG:
									tmp = 3
								elif idx in (iAt.atAAC, iAt.atAACHE):
									tmp = 5
								elif idx in (iAt.atDDP, iAt.atAC3):
									tmp = 0
							except: pass
				if tmp != -1:
					self["dolby"].setPixmapNum(tmp)
					self["dolby"].move(ePoint(self.x_dyn_pos, self.posY_DynIco))
					self["dolby"].show()
					self.x_dyn_pos -=  self.widthDynIco
				else:
					self["dolby"].hide()
				if n > 1:
					self["multi_audio"].move(ePoint(self.x_dyn_pos, self.posY_DynIco))
					self["multi_audio"].show()
					self.x_dyn_pos -=  self.widthDynIco
				else:
					self["multi_audio"].hide()
				tmp = 0
				if "3" in self.uhdtype:
					try:
						idx = (info.getInfoString(iServiceInformation.sEotf)).upper()
						if "HDR" in idx: 
							tmp = 2
						elif "HLG" in idx: 
							tmp = 3
					except: pass
					if tmp == 0:
						try:
							idx = info.getInfo(iServiceInformation.sGamma)
							if idx in (1,2): 
								tmp = 2
							elif idx == 3: 
								tmp = 3
						except: pass
				try:
					if tmp != 0:
						self["wide"].setPixmapNum(tmp)
						self["wide"].move(ePoint(self.x_dyn_pos, self.posY_DynIco))
						self["wide"].show()
						self.x_dyn_pos -=  self.widthDynIco
						self.lastIco = "wide"
				except: pass
				if tmp == 0:
					tmp = self.getServiceInfoString(info, iServiceInformation.sAspect)
					if tmp != "N/A":
						if (info.getInfo(iServiceInformation.sAspect) in (3, 4, 7, 8, 0xB, 0xC, 0xF, 0x10)):
							self["wide"].setPixmapNum(1)
						else:
							self["wide"].setPixmapNum(0)
						self["wide"].move(ePoint(self.x_dyn_pos, self.posY_DynIco))
						self["wide"].show()
						self.x_dyn_pos -=  self.widthDynIco
						self.lastIco = "wide"
					else:
						self["wide"].hide()
				tmp = None
				try:
					subservices = service and service.subtitleTracks()
					tmp = subservices.getNumberOfSubtitleTracks()
				except:
					try:
						subservices = service and service.subtitle()
						tmp = subservices and subservices.getSubtitleList()
						if tmp:
							tmp = len(tmp)
					except: pass
				if tmp and tmp > 0:
					self["subtit"].move(ePoint(self.x_dyn_pos, self.posY_DynIco))
					self["subtit"].show()
					self.x_dyn_pos -=  self.widthDynIco
					self.lastIco = "subtit"
				else:
					self["subtit"].hide()
				subservices = service.subServices()
				if subservices and subservices.getNumberOfSubservices() > 0:
					self["subserv"].move(ePoint(self.x_dyn_pos, self.posY_DynIco))
					self["subserv"].show()
					self.x_dyn_pos -=  self.widthDynIco
					self.lastIco = "subserv"
				else:
					self["subserv"].hide()
		if not self.hbboff:
			if self.lastIcoSwitch == 0:
				if self.x_dyn_pos == self.maxDynX:
					self.x_dyn_pos += self.widthDynIco
					self.lastIcoSwitch = 1		
					self.runHBBTimer.start(2000, True)
				self["hbb"].move(ePoint(self.x_dyn_pos, self.posY_DynIco))
				if self.lastIcoSwitch == 0:
					self["hbb"].show()
		else:
			self["hbb"].hide()    		
		
	def getServiceInfoString(self, info, what, convert = lambda x: "%d" % x):
		v = info.getInfo(what)
		if v == -1:
			return "N/A"
		if v == -2:
			return info.getInfoString(what)
		return convert(v)
		
	def setTunerInfo(self, service, ip=None):
		playing = self.session.nav.getCurrentlyPlayingServiceReference()
		if is_native_dab(playing):
			info = service and service.info()
			provider = getServiceInfoValue(info, iServiceInformation.sProvider) if info else ""
			self["TP_info"].setText(provider or "DAB")
			self["TP_type"].setText("DAB")
			self.tstprov = provider
			self.tstsat = "DAB"
			self.path = "piconProv" + self.picProvSatSize
			self.pngname = self.findPicon(fixNameOf(provider)) if provider else ""
			self.path = "piconSat" + self.picProvSatSize
			self.pngnamesat = self.findPicon("DAB")
			if not self.pngname:
				self.pngname = SKINPATH + "icons/missing-fs8.png"
			if not self.pngnamesat:
				self.pngnamesat = SKINPATH + "icons/missing-fs8.png"
			self.chckSatProv()
			return
		def chckVtype(i):
			x = ""
			if ENAVFT: 
				try:
					x = { CT_MPEG2 : "MPEG2", CT_H264 : "H.264", CT_MPEG1 : "MPEG1", CT_MPEG4_PART2 : "MPEG4", 
						CT_VC1 : "VC1", CT_VC1_SIMPLE_MAIN : "WMV3", CT_H265 : "HEVC", CT_DIVX311 : "DIVX3", CT_DIVX4 : "DIVX4", CT_SPARK : "SPARK", CT_VP6 : "VP6", CT_VP8 : "VP8", 
						CT_VP9 : "VP9", CT_H263 : "H.263", CT_MJPEG : "MJPEG", CT_REAL : "RV", CT_AVS : "AVS", CT_UNKNOWN : "" }[i]
				except: pass
			else:
				try:
					from Components.Converter.PliExtraInfo import codec_data
					x = codec_data.get(i, "")
					if "/" in x:
						x = ""
				except: pass 
				if x == "":
					try:
						x = ('MPEG2', 'MPEG4', 'MPEG1', 'MPEG4-II', 'VC1', 'VC1-SM', 'HEVC', '')[i]
					except: pass   
			if x == "":
				try:
					mpg = open("/proc/stb/vmpeg/0/codec", "r").read()
					if mpg.find("MPEG2") != -1:
						x = "MPEG2"
					elif mpg.find("MPEG4") != -1:
						x = "MPEG4"
						if mpg.find("H.264") != -1:
							x = "MPEG4(H.264)"
						if mpg.find("H.265") != -1:
							x = "MPEG4(H.265)"
						if mpg.find("HEVC") != -1:
							x = "MPEG4(HEVC)"
					elif mpg.find("H.264") != -1:
						x = "H.264"
					elif mpg.find("MPEG1") != -1:
						x = "MPEG1"
					elif mpg.find("H.265") != -1:
						x = "H.265"
					elif mpg.find("HEVC") != -1:
						x = "HEVC"
				except: pass
			return x									
		def convCH(what):
			fqT = ""
			try:
				fqT = int(((int(round(float(what.replace(" MHz","")))) - 474) / 8) + 21)
				if fqT < 21 or fqT > 69:
					fqT = ""
				else:
					fqT = "(CH %d) " % fqT						
			except: pass
			return fqT
		def cleanInfo(what):
			if "Auto" in what or "None" in what or _("Auto") in what or _("None") in what:
 				return ""
			return what
		def findPP(what):
			pngname = self.findPicon(what)
			if pngname == "":
				sname = "picon_default"
				pngname = self.findPicon(sname)
				if pngname == "":
					if "220" in self.path:
						sname = "picon220sp_default"	
					pngname = setDefPicon(sname+".png")
			if pngname != "":
				self.pngnamesat = pngname
		pngname = ""
		ref = None
		info = service and service.info()
		if ip:
			provname = ip
			self.tstsat = "IPTV"
			self.path = "piconSat" +	self.picProvSatSize
			findPP(self.tstsat)
		else:
			provname = getServiceInfoValue(info, iServiceInformation.sProvider, ref)
		if self.tstprov != provname:
			self.tstprov = provname 
			a, b, c, d = self.readPTCH()
			if a and not b and not c and not d:
				self["Prov_temp_rpm"].setText(self.tstprov)
			sname = fixNameOf(provname)
			self.path = "piconProv" +	self.picProvSatSize
			if ip is None and info is not None:
				try:
					refer = eServiceReference(info.getInfoString(iServiceInformation.sServiceref))
					if refer is not None:
						refer = refer.toString()
						if refer.startswith("-1:"):
							refer = self.session.nav.getCurrentlyPlayingServiceReference()
							if refer is not None:
								refer = refer.toString()
					if refer is not None and refer != "":
						refer = refer.split(':', 10)[:10]
						refer = '_'.join(refer)
						refer = ((refer[:-10]).split('_')[6]).upper()
						pngname = self.findPicon(refer + "x" + sname)
				except: pass
			if pngname == "":
				pngname = self.findPicon(sname)
			if pngname == "":
				sname = "picon_default"
				pngname = self.findPicon(sname)
				if pngname == "":
					if "220" in self.path:
						sname = "picon220sp_default"	
					pngname = setDefPicon(sname+".png")
			if self.pngname != pngname:
				self.pngname = pngname
		tunerinfo = tptype = orb = ""
		feinfo = service and service.frontendInfo()
		if feinfo is not None and not ip:
			frontendData = feinfo and feinfo.getAll({"F" : False,"T" : True}[config.plugins.setupGlass17.par168.value])
			if frontendData is not None:
				dataTP = { }
				try:
					dataTP = ConvertToHumanReadable(frontendData)
					if len(dataTP) == 0 and len(frontendData) == 0 and info and service:
						sname = info.getInfoObject(iServiceInformation.sTransponderData)
						if sname:
							frontendData = sname
							dataTP = ConvertToHumanReadable(sname)
				except: pass
				tunerType = str(frontendData.get("tuner_type","None"))
				if ENA_TT and tunerType != "None":
					try:
						tunerType = {iDVBFrontend.feSatellite : "0",iDVBFrontend.feCable : "1",iDVBFrontend.feTerrestrial : "2",iDVBFrontend.feSatellite2 : "0",iDVBFrontend.feTerrestrial2 : "2"}[int(tunerType)]
					except: 
						try:
							tunerType = {iDVBFrontend.feSatellite : "0",iDVBFrontend.feCable : "1",iDVBFrontend.feTerrestrial : "2"}[int(tunerType)]
						except: pass
				if config.plugins.setupGlass17.par168.value == "F": 
					fq = 1.0 * frontendData.get("frequency", 0) / 1000
					if (fq > 9999 and fq < 99999 and (tunerType == "1" or "DVB-C" in tunerType)) or fq > 99999:
						fq = 1.0 * fq / 1000
					if "." in str(fq):
						fq = str(fq).split(".")
						if len(fq[1]) > 2:
							fq[1] = fq[1][:2]
						fq = ".".join(fq)
					frequency = str(fq) + " MHz"
				else:
					fq = int(round(1.0 * frontendData.get("frequency", 0) / 1000))
					if (fq > 9999 and fq < 99999 and (tunerType == "1" or "DVB-C" in tunerType)) or fq > 99999:
						fq = int(round(1.0 * fq / 1000))
					frequency = str(fq) + " MHz"
				symbolrate = str(int(frontendData.get("symbol_rate", 0) / 1000))
				pol = fec = system = modulation = "N/A"
				if tunerType in ["DVB-S","DVB-S2","0"]:
					config.plugins.setupGlass17.par70.value = False
					numSat = frontendData.get("orbital_position", 0)
					if numSat > 1800:
						orbPic = str((3600 - numSat)) + "W"
						numSat = str((float(3600 - numSat))/10.0)
						orb = numSat + DG + "W"
						numSat += "W"
					else:
						orbPic = str(numSat) + "E"
						numSat = str((float(numSat))/10.0)
						orb = numSat + DG + "E"
						numSat += "E"
					if not config.plugins.setupGlass17.par48.value:
						global allSat
						if numSat in allSat:
							orb = allSat.get(numSat)
						else:
							orb = "Sat on position: %s" % orb
					pngname = ""
					try:
						pol = {
									eDVBFrontendParametersSatellite.Polarisation_Horizontal : "H",
									eDVBFrontendParametersSatellite.Polarisation_Vertical : "V",
									eDVBFrontendParametersSatellite.Polarisation_CircularLeft : "CL",
									eDVBFrontendParametersSatellite.Polarisation_CircularRight : "CR"
								}[frontendData.get("polarization", eDVBFrontendParametersSatellite.Polarisation_Horizontal)]		
					except: pass
					fec = dataTP.get("fec_inner","Auto")
					system = dataTP.get("system","DVB-S")
					modulation = dataTP.get("modulation","Auto")
					tunerinfo = frequency + "  " + pol + "  " + cleanInfo(fec + "  ") + symbolrate + "  "
					tptype = system + "  " + modulation
					if self.tstsat != orbPic:
						self.tstsat = orbPic
						self.path = "piconSat" +	self.picProvSatSize
						findPP(self.tstsat)
					self["TP_type"].setText(tptype)	
				elif tunerType == "1" or "DVB-C" in tunerType:
					config.plugins.setupGlass17.par70.value = True
					fec = dataTP.get("fec_inner","Auto")
					modulation = dataTP.get("modulation","Auto")
					tunerinfo = frequency + "  " + cleanInfo(fec + "  ") + symbolrate + "  "
					tptype = "DVB-C"+ "  " + modulation
					self["TP_type"].setText(tptype)
					if self.tstsat != "picon_cable":
						self.tstsat = "picon_cable"
						self.path = "piconSat" +	self.picProvSatSize
						findPP(self.tstsat)
				elif tunerType == "2" or "DVB-T" in tunerType:
					config.plugins.setupGlass17.par70.value = True
					tptype = "DVB-T"
					try:
						tptype = {
									eDVBFrontendParametersTerrestrial.System_DVB_T : "DVB-T",
									eDVBFrontendParametersTerrestrial.System_DVB_T2 : "DVB-T2"
								}[frontendData.get("system", eDVBFrontendParametersTerrestrial.System_DVB_T)]
					except: pass
					pol = dataTP.get("constellation","Auto")
					if "fec_inner" in dataTP: 
						fec = dataTP.get("fec_inner","Auto")
					else:
						fec = dataTP.get("code_rate_hp","Auto") + ":" + dataTP.get("code_rate_lp","Auto")
					system = dataTP.get("bandwidth","x")
					if system != "x":
						system = cleanInfo(system +"  ")
					else:
						system = ""
					modulation = dataTP.get("guard_interval","Auto")
					pls = dataTP.get("transmission_mode","Auto")
					tunerinfo = frequency + "  " + convCH(frequency) + system + cleanInfo(fec + "  ") + cleanInfo("GI:" + modulation + "  ") + cleanInfo("TM:" + pls + "  ")	
					if self.tstsat != "picon_trs":
						self.tstsat = "picon_trs"
						self.path = "piconSat" +	self.picProvSatSize
						findPP(self.tstsat)
					tptype += "  " + pol
					self["TP_type"].setText(tptype)
				else:
					tunerinfo = (frequency + "  " + symbolrate + "  ")	
					self["TP_type"].setText(_("No data"))
					if self.tstsat != "picon_default":
						self.tstsat = "picon_default"
						self.path = "piconSat" +	self.picProvSatSize
						findPP(self.tstsat)
				self.chckSatProv()
				pls = ''
				if config.plugins.setupGlass17.par48.value:
					i = info.getInfo(iServiceInformation.sVideoType)
					x = chckVtype(i)
					if x != "":
						tunerinfo += x + "  " 
					if config.plugins.setupGlass17.par168.value == "F":
						frontendData = feinfo and feinfo.getAll(True)
					if "pls_mode" in frontendData or "is_id" in frontendData or "pls_code" in frontendData:
						i = str(frontendData.get('is_id', 0))
						c = str(frontendData.get('pls_code', 0))
						m = str(frontendData.get('pls_mode', None))
						if not(m == 'None' or i == '-1' or i == '255' or i == '0' and c == '1'):
							if m.isdigit():
								try:
									m = {
										eDVBFrontendParametersSatellite.PLS_Root : "Root",
										eDVBFrontendParametersSatellite.PLS_Gold : "Gold",
										eDVBFrontendParametersSatellite.PLS_Combo : "Combo",
										eDVBFrontendParametersSatellite.PLS_Unknown : "U"}[frontendData["pls_mode"]]
								except: pass
							pls = ' MS:%s %s %s ' % (i,c.replace('262143', ''),m.replace('U', ''))
					if "t2mi_plp_id" in frontendData:
						if frontendData.get('t2mi_plp_id') > -1:
							pls += 'T2-MI:%s %s' % (frontendData.get('t2mi_plp_id', 0), frontendData.get('t2mi_pid', 0))
				try:
					orb = orb.replace("E)",DG+"E)").replace("W)",DG+"W)")
				except: pass
				self["TP_info"].setText(tunerinfo+orb+pls)
				return
		self.chckSatProv()
		if ip:
			b = ""
			x = chckVtype(info.getInfo(iServiceInformation.sVideoType))
			try:				        
				if x != "":
					b = x
				else:
					b = str(service.info().getInfoString(iServiceInformation.sTagVideoCodec))
			except: pass
			if info is not None:
				idIP = None
				try:
					refer = eServiceReference(info.getInfoString(iServiceInformation.sServiceref))
					if refer is not None:
						refer = refer.toString()
						if refer.startswith("-1:"):
							refer = self.session.nav.getCurrentlyPlayingServiceReference()
							if refer is not None:
								refer = refer.toString()
					if refer is not None and refer != "":
						if "/" in refer:
							refer = refer.split('/')
							for x in refer:
								if x.isdigit():
									idIP = x
									break
				except: pass
			if idIP:
				self["TP_info"].setText(_("Streaming service")+"  IPTV  " + b + " ID: " + idIP)
			else:
				self["TP_info"].setText(_("Streaming service")+"  IPTV  " + b)
			self["TP_type"].setText(_("IP stream"))
		else:
			self["TP_info"].setText(NO_TUN)
			self["TP_type"].setText(_("No data"))
			
	def chckSatProv(self):
		if self.pngnamesat != "" and self.pngname != "":
			config.plugins.setupGlass17.par36.value = self.pngname
			config.plugins.setupGlass17.par37.value = self.pngnamesat
			if self.enaProvSat and not self.chckWeaInafAnim():
				self.aSw = config.plugins.setupGlass17.par8.value
				if self.aSw in ("0","4","5","6"):
					if self.aSw in ("0","4","5"):
						self.maxSlide = 2
						self.steps = 4
					else:
						self.maxSlide = 3
						self.steps = 8
					self.slide = self.maxSlide
					self.timerpics.start(100, True)
				elif self.aSw == "1":
					self.updpicProvSat(self.pngnamesat)
					self["weaTxt"].hide()
				elif self.aSw == "2":
					self.updpicProvSat(self.pngname)
					self["weaTxt"].hide()
				elif self.aSw == "3" and not config.plugins.setupGlass17.par169.value:
					self.updpicProvSat(self.pngnameWea)
					self["weaTxt"].show()
			if config.plugins.setupGlass17.par5.value != "0":
				self["picSat"].instance.setPixmapFromFile(self.pngnamesat)
				self["picProv"].instance.setPixmapFromFile(self.pngname)

	def chckWeaInafAnim(self):
		return config.plugins.setupGlass17.par8.value == "3" and config.plugins.setupGlass17.par169.value

	def timerpicsEvent(self):
		self.timerpics.stop()
		if self.steps != 0:
			if (((self.aSw == "0" and self.slide == 2) or (self.aSw == "5" and self.slide == 1))and self.maxSlide == 2) or (self.slide == 2 and self.maxSlide == 3):
				self.updpicProvSat(self.pngname)
				self["weaTxt"].hide()
			elif (((self.aSw == "5" and self.slide == 2) or (self.aSw == "4" and self.slide == 1))and self.maxSlide == 2) or (self.slide == 3 and self.maxSlide == 3):
				self.updpicProvSat(self.pngnameWea)
				self["weaTxt"].show()
			elif (((self.aSw == "4" and self.slide == 2) or (self.aSw == "0" and self.slide == 1))and self.maxSlide == 2) or (self.slide == 1 and self.maxSlide == 3):
				self.updpicProvSat(self.pngnamesat)
				self["weaTxt"].hide()
			self.steps -= 1
			self.slide -= 1
			if self.slide == 0:
				self.slide = self.maxSlide		
			self.timerpics.start(2000, True)
		elif self.aSw in ("4","5","6"):
			self.updpicProvSat(self.pngnameWea)
			self["weaTxt"].show()
		else:
			self.updpicProvSat(self.pngname)
			self["weaTxt"].hide()

	def updpicProvSat(self, w):
		self["picProvSat"].instance.setPixmapFromFile(w)
			
	def findPicon(self, piconName):
		pngname = "%s/%s/%s.png" % (config.plugins.setupGlass17.par39.value, self.path, piconName)
		if fileExists(pngname):
			return pngname
		elif self.path in ("ZZPicon","picon_400x240","picon_220x132"):
			if self.path == "picon_220x132":
				pngname = "%s/picon_400x240/%s.png" % (config.plugins.setupGlass17.par39.value, piconName)
				if fileExists(pngname):
					return pngname
			elif self.path == "picon_400x240":
				pngname = "%s/picon_220x132/%s.png" % (config.plugins.setupGlass17.par39.value, piconName)
				if fileExists(pngname):
					return pngname
			pngname = "%s/picon/%s.png" % (config.plugins.setupGlass17.par39.value, piconName)
			if fileExists(pngname):
				return pngname
		elif "piconSat" in self.path or "piconProv" in self.path:
			path = self.path.replace("_220x132","")
			pngname = "%s/%s/%s.png" % (config.plugins.setupGlass17.par39.value, path, piconName)
			if fileExists(pngname):
				return pngname
			elif path == "piconSat" and (piconName.endswith("E") or piconName.endswith("W")):
				pngname = "%s/%s/picon_sat.png" % (config.plugins.setupGlass17.par39.value, self.path)
				if fileExists(pngname):				
					return pngname
				else:
					pngname = "%s/piconSat/picon_sat.png" % config.plugins.setupGlass17.par39.value
					if fileExists(pngname):				
						return pngname
		return ""       
	
	def showDyn_EMM_ECM(self, ecm="xxx", typeECM="xxx", typeCam=False):
		caRequiredstatus = {}
		for x in list(self.allCaids.keys()):
			tmp = self.allCaids.get(x)
			caRequiredstatus[tmp] = True
		for x in range(0,8):
			try:
				self["D%s_Demm" % x].hide()
			except: pass
		x_dyn_pos_CA = self.x_dyn_pos_CA
		ena = False
		if ecm in self.allCaids or ecm in ("26","FF"):
			ecm = self.allCaids.get(ecm)
			ena = True
		num = 0
		if self.caidsLive:
			if len(self.caidsLive) > 0:
				for x in self.caidsLive:
					x = "%0.4X" % x
					if x not in FCAID: 
						x = x[:2]
					tmp = self.allCaids.get(x,"xx")
					if tmp != ecm:
						if caRequiredstatus.get(tmp) or (tmp == "xx" and config.plugins.setupGlass17.par191.value): 
							try:
								aa = "D%s_Demm" % num
								ss = SKINPATH + "icons/" + tmp + "emm-fs8.png"
								if os.path.isfile(ss):
									self[aa].instance.setPixmapFromFile(ss)
								else:
									self[aa].instance.setPixmapFromFile(SKINPATH + "icons/unk-ca.png")
								self[aa].move(ePoint(x_dyn_pos_CA, self.posY_DynIco_CA))
								self[aa].show()
								x_dyn_pos_CA -= self.width_D_icons
								caRequiredstatus[tmp] = False  
								num += 1
							except: pass
		else:
			if not _("Error reading CaIds !!!") in self.caidLineTxt:
				typeECM = "fta"
		if ena and typeECM != "fta":
			try:
				self["Decm"].instance.setPixmapFromFile((SKINPATH + "icons/" + ecm + "ecm-fs8.png"))
				self["Decm"].move(ePoint(x_dyn_pos_CA, self.posY_DynIco_CA))
				self["Decm"].show()
				x_dyn_pos_CA -= self.width_D_icons
			except: pass
		else:
			try:
				self["Decm"].hide()
			except: pass
		if config.plugins.setupGlass17.par103.value and typeECM != "xxx" and typeECM != "" or typeECM == "fta":
			try:
				self["Dtype"].instance.setPixmapFromFile(SKINPATH + "icons/" + typeECM + "new-fs8.png")
				self["Dtype"].move(ePoint(x_dyn_pos_CA, self.posY_DynIco_CA))
				self["Dtype"].show()
				x_dyn_pos_CA -= self.width_D_icons
			except: pass
		else:
			try:
				self["Dtype"].hide()
			except: pass		
		if config.plugins.setupGlass17.par102.value and typeECM != "xxx" and typeECM != "fta" and typeCam:
			try:
				self["Dcam"].move(ePoint(x_dyn_pos_CA, self.posY_DynIco_CA))
				self["Dcam"].show()
				x_dyn_pos_CA -= self.width_D_icons
			except: pass
		else:
			try:
				self["Dcam"].hide()
			except: pass
		self.netStateMove(x_dyn_pos_CA)         						

	def netStateMove(self, x=-100):
		if config.plugins.setupGlass17.par57.value != "2":
			try:
				self["Dnetstate"].move(ePoint(x, self.posY_DynIco_CA))
				self["Dnetstate"].show()
			except:
				pass 
		else:
			try:
				self["Dnetstate"].hide()
			except:
				pass
        				
	def showEnhancedInfo(self):
		if not config.plugins.setupGlass17.par43.value:
			return
		config.plugins.setupGlass17.par43.value = False
		if config.plugins.setupGlass17.par16.value:
			self["slider_back"].show()
		else:
			self["slider_back"].hide()
		if config.plugins.setupGlass17.par5.value == "1":
			self["picSat"].show()
			self["picProv"].show()
			self['ecmValues'].show()
			self['ecmlabels'].show()    		
			self["back_enhanced"].show()
			self["piconEcm"].show()
			self["piconCam"].show()
		else:
			self["piconEcm"].hide()
			self["piconCam"].hide()
			self["picSat"].hide()
			self["picProv"].hide()
			self['ecmValues'].hide()
			self['ecmlabels'].hide()    		
			self["back_enhanced"].hide()
      		
##########################################################################################################################
	
class setupGlass17ScreenSetup(Screen, ConfigListScreen):

	skin = """
<screen name="setupGlass17" position="0,0" size="1920,1080" title="FullHDGlass" backgroundColor="#ff000000" flags="wfNoBorder">
<widget position="0,0" size="1920,164" source="global.CurrentTime" render="WarderSettingsHeader" zPosition="-3" /><widget name="description" position="60,174" size="1800,46" noWrap="1" backgroundColor="#00071627" zPosition="1" valign="center" halign="left" font="Regular;24" transparent="0" foregroundColor="#00b5d4ec" />
<widget source="session.VideoPicture" render="WarderSettingsPig" position="60,242" zPosition="1" size="737,415" backgroundColor="transparent" />
<widget name="config" font="Prive3;34" position="60,242" size="1790,320" zPosition="4" foregroundColorSelected="#00ffffff" itemHeight="40" transparent="1" backgroundColor="#ff000000" scrollbarMode="showOnDemand" foregroundColor="#00ffffff" backgroundColorSelected="#002a70ad" scrollbarBackgroundColor="#00102136" scrollbarForegroundColor="#003ee8ff" />
<widget name="list" position="860,238" size="990,720" zPosition="4" scrollbarMode="showOnDemand" backgroundColor="#ff000000" foregroundColor="#00ffffff" transparent="1" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" scrollbarBackgroundColor="#00102136" scrollbarForegroundColor="#003ee8ff" />
<widget name="white" position="60,574" font="Prive3;34" size="1790,2" backgroundColor="#003ee8ff" zPosition="4" transparent="0" foregroundColor="#00ffffff" />
<widget name="key_red" position="60,980" zPosition="3" size="500,60" noWrap="1" valign="center" halign="center" font="Regular;28" transparent="0" backgroundColor="#00071627" foregroundColor="#00ff526a" />
<widget name="key_green" position="1360,980" zPosition="3" size="500,60" noWrap="1" valign="center" halign="center" font="Regular;28" transparent="0" backgroundColor="#00071627" foregroundColor="#0039ff59" />
<widget source="Canvas" render="WarderSettingsCanvas" position="735,890" zPosition="6" size="450,45" backgroundColor="#00102136" transparent="1" alphatest="on" />
<widget name="help_pict" position="445,592" size="1029,350" zPosition="4" alphatest="blend" />
<widget name="help_txt" position="579,592" size="780,350" backgroundColor="#ff000000" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#00b5d4ec" />
<widget name="helpPiconFrame" position="865,705" pixmap="hd_glass17/frame_hd.png" size="189,123" zPosition="8" alphatest="on" />
<widget name="helpPicon" position="885,721" size="150,90" zPosition="9" alphatest="on" />
<widget name="helpTxtAnim" position="579,592" size="780,350" backgroundColor="#ff000000" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#00b5d4ec" />
<eLabel position="60,974" size="500,2" backgroundColor="#00ff526a" zPosition="1" /><eLabel position="1360,974" size="500,2" backgroundColor="#0039ff59" zPosition="1" /><widget position="50,232" size="760,728" name="warder_menu_panel_0" backgroundColor="#00102136" transparent="0" zPosition="0" /><widget position="50,232" size="760,2" name="warder_menu_panel_1" backgroundColor="#003ee8ff" transparent="0" zPosition="1" /><widget position="50,958" size="760,2" name="warder_menu_panel_2" backgroundColor="#003ee8ff" transparent="0" zPosition="1" /><widget position="50,232" size="2,728" name="warder_menu_panel_3" backgroundColor="#003ee8ff" transparent="0" zPosition="1" /><widget position="808,232" size="2,728" name="warder_menu_panel_4" backgroundColor="#003ee8ff" transparent="0" zPosition="1" /><widget position="850,232" size="1010,728" name="warder_menu_panel_5" backgroundColor="#00102136" transparent="0" zPosition="0" /><widget position="850,232" size="1010,2" name="warder_menu_panel_6" backgroundColor="#003ee8ff" transparent="0" zPosition="1" /><widget position="850,958" size="1010,2" name="warder_menu_panel_7" backgroundColor="#003ee8ff" transparent="0" zPosition="1" /><widget position="850,232" size="2,728" name="warder_menu_panel_8" backgroundColor="#003ee8ff" transparent="0" zPosition="1" /><widget position="1858,232" size="2,728" name="warder_menu_panel_9" backgroundColor="#003ee8ff" transparent="0" zPosition="1" /><widget position="50,232" size="1810,728" name="warder_settings_panel_0" backgroundColor="#1a102136" transparent="0" zPosition="-1" /><widget position="50,232" size="1810,2" name="warder_settings_panel_1" backgroundColor="#003ee8ff" transparent="0" zPosition="3" /><widget position="50,958" size="1810,2" name="warder_settings_panel_2" backgroundColor="#003ee8ff" transparent="0" zPosition="3" /><widget position="50,232" size="2,728" name="warder_settings_panel_3" backgroundColor="#003ee8ff" transparent="0" zPosition="3" /><widget position="1858,232" size="2,728" name="warder_settings_panel_4" backgroundColor="#003ee8ff" transparent="0" zPosition="3" /><widget position="1120,25" size="250,36" font="Regular;25" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%A</convert></widget><widget position="1020,70" size="350,36" font="Regular;24" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%d. %B %Y</convert></widget><widget position="1398,32" size="190,85" font="Regular;62" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Default</convert></widget><widget position="1590,58" size="66,54" font="Regular;38" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="left" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format::%S</convert></widget><eLabel position="1680,25" size="210,36" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="Version:" /><eLabel position="1680,70" size="210,36" font="Regular;24" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="1.0.35" /><eLabel position="1392,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><eLabel position="1664,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><eLabel position="0,164" size="1920,68" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,232" size="50,728" backgroundColor="#00071627" zPosition="-2" /><eLabel position="1860,232" size="60,728" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,960" size="1920,120" backgroundColor="#00071627" zPosition="-2" /></screen>
"""
  	
	def __init__(self, session):
		Screen.__init__(self, session)
		from .warderPreviewAssets import ensure_assets
		ensure_assets(config.plugins.setupGlass17.par39.value)
		if os.path.exists('/etc/dpkg'):
			self.skin = setupGlass17ScreenSetup.skin.replace('<widget name="config" font="Prive3;34"','<widget name="config"')
		else:
			self.skin = setupGlass17ScreenSetup.skin
		for prefix, count in (("warder_menu_panel_", 10), ("warder_settings_panel_", 5)):
		    for index in range(count):
		        self[prefix + str(index)] = Label("")
		        self[prefix + str(index)].hide()
		self.list = [ ]
		ConfigListScreen.__init__(self, self.list, session, on_change = self.doMyHelpWindow)
		self.canvas = CanvasSource()
		self["Canvas"] = self.canvas
		self.mainlist = []
		self['list'] = thumbList(self.mainlist)
		self["help_pict"] = Pixmap()
		self["helpPicon"] = Pixmap()
		self["helpPicon"].hide()
		self["helpPiconFrame"] = Pixmap()
		self["helpPiconFrame"].hide()
		self["help_txt"] = Label("")
		self["white"] = Label("")
		self["white"].hide()		
		self["helpTxtAnim"] = Label("")
		self["description"] = Label("")
		self["selected_item"] = StaticText("")
		self["key_green"] = Label(_("Save"))
		self["key_red"] = Label(_("Cancel"))
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green": self.save,
			"ok": self.ActivateselectedFnc,
			"yellow": self.doNothing,
			"blue": self.doNothing,
			"red": self.isExit,
			"cancel": self.isExit
		}, -2)			
		self.eeTanimLast = "0"
		self.vip = ""
		self.pwdV = None
		self.isShow = True
		self.isMainMenu = True
		self.mainMenuIdx = 0
		self.d = []
		self.d.append(config.plugins.setupGlass17.par50.getValue())
		self.d.append(None) # retired weather provider slot kept for snapshot index compatibility
		self.d.append(config.plugins.setupGlass17.par78.getValue())
		self.d.append(config.plugins.setupGlass17.par12.getValue())
		self.d.append(config.plugins.setupGlass17.par15.getValue())
		self.d.append(config.plugins.setupGlass17.par7.getValue())
		self.d.append(config.plugins.setupGlass17.par4.getValue())
		self.d.append(config.plugins.setupGlass17.par1.getValue())
		self.d.append(config.plugins.setupGlass17.par6.getValue())
		self.d.append(config.plugins.setupGlass17.par31.getValue())
		self.d.append(config.plugins.setupGlass17.par33.getValue())
		self.d.append(config.plugins.setupGlass17.par14.getValue())
		self.d.append(config.plugins.setupGlass17.par18.getValue())
		self.d.append(config.plugins.setupGlass17.par19.getValue())
		self.d.append(config.plugins.setupGlass17.par34.getValue())
		self.d.append(config.plugins.setupGlass17.par23.getValue())
		self.d.append(config.plugins.setupGlass17.par41.getValue())
		self.d.append(config.plugins.setupGlass17.par40.getValue())
		self.d.append(config.plugins.setupGlass17.par44.getValue())
		self.d.append(config.plugins.setupGlass17.par45.getValue())
		self.d.append(config.plugins.setupGlass17.par46.getValue())
		self.d.append(config.plugins.setupGlass17.par47.getValue())
		self.d.append(config.plugins.setupGlass17.par48.getValue())
		self.d.append(config.plugins.setupGlass17.par49.getValue())
		self.d.append(config.plugins.setupGlass17.par51.getValue())
		self.d.append(config.plugins.setupGlass17.par52.getValue())
		self.d.append(config.plugins.setupGlass17.par53.getValue())
		self.d.append(config.plugins.setupGlass17.par54.getValue())
		self.d.append(config.plugins.setupGlass17.par56.getValue())
		self.d.append(config.plugins.setupGlass17.par58.getValue())
		self.d.append(config.plugins.setupGlass17.par59.getValue())
		self.d.append(config.plugins.setupGlass17.par55.getValue())
		self.d.append(config.plugins.setupGlass17.par62.getValue())
		self.d.append(config.plugins.setupGlass17.par65.getValue())
		self.d.append(config.plugins.setupGlass17.par64.getValue())
		self.d.append(config.plugins.setupGlass17.par66.getValue())
		self.d.append(config.plugins.setupGlass17.par67.getValue())
		self.d.append(config.plugins.setupGlass17.par68.getValue())
		self.d.append(config.plugins.setupGlass17.par71.getValue())
		self.d.append(config.plugins.setupGlass17.par80.getValue())
		self.d.append(config.plugins.setupGlass17.par72.getValue())
		self.d.append(config.plugins.setupGlass17.par90.getValue())
		self.d.append(config.plugins.setupGlass17.par92.getValue())
		self.d.append(config.plugins.setupGlass17.par93.getValue())
		self.d.append(config.plugins.setupGlass17.par94.getValue())
		self.d.append(config.plugins.setupGlass17.par109.getValue())
		self.d.append(config.plugins.setupGlass17.par110.getValue())
		self.d.append(config.plugins.setupGlass17.par111.getValue())
		self.d.append(config.plugins.setupGlass17.par117.getValue())
		self.d.append(config.plugins.setupGlass17.par114.getValue())
		self.d.append(config.plugins.setupGlass17.par118.getValue())
		self.d.append(config.plugins.setupGlass17.par119.getValue())
		self.d.append(config.plugins.setupGlass17.par121.getValue())
		self.d.append(config.plugins.setupGlass17.par122.getValue())
		self.d.append(config.plugins.setupGlass17.par123.getValue())
		self.d.append(config.plugins.setupGlass17.par125.getValue())
		self.d.append(config.plugins.setupGlass17.par126.getValue())
		self.d.append(config.plugins.setupGlass17.par128.getValue())
		self.d.append(config.plugins.setupGlass17.par129.getValue())
		self.d.append(config.plugins.setupGlass17.par130.getValue())
		self.d.append(config.plugins.setupGlass17.par135.getValue())
		self.d.append(config.plugins.setupGlass17.par136.getValue())
		self.d.append(config.plugins.setupGlass17.par137.getValue())
		self.d.append(config.plugins.setupGlass17.par22.getValue())
		self.d.append(config.plugins.setupGlass17.par124.getValue())
		self.d.append(config.plugins.setupGlass17.par141.getValue())
		self.d.append(config.plugins.setupGlass17.par145.getValue())
		self.d.append(config.plugins.setupGlass17.par146.getValue())
		self.d.append(config.plugins.setupGlass17.par147.getValue())
		self.d.append(config.plugins.setupGlass17.par148.getValue())
		self.d.append(config.plugins.setupGlass17.par153.getValue())
		self.d.append(config.plugins.setupGlass17.par154.getValue())
		self.d.append(config.plugins.setupGlass17.par155.getValue())
		self.d.append(config.plugins.setupGlass17.par156.getValue())
		self.d.append(config.plugins.setupGlass17.par157.getValue())
		self.d.append(config.plugins.setupGlass17.par8.getValue())
		self.d.append(config.plugins.setupGlass17.par161.getValue())
		self.d.append(config.plugins.setupGlass17.par162.getValue())
		self.d.append(config.plugins.setupGlass17.par163.getValue())
		self.d.append(config.plugins.setupGlass17.par164.getValue())
		self.d.append(config.plugins.setupGlass17.par165.getValue())
		self.d.append(config.plugins.setupGlass17.par166.getValue())
		self.d.append(config.plugins.setupGlass17.par167.getValue())
		self.d.append(config.plugins.setupGlass17.par169.getValue())
		self.d.append(config.plugins.setupGlass17.par171.getValue())
		self.d.append(config.plugins.setupGlass17.par172.getValue())
		self.d.append(config.plugins.setupGlass17.par174.getValue())
		self.d.append(config.plugins.setupGlass17.par175.getValue())
		self.d.append(config.plugins.setupGlass17.par180.getValue())
		self.d.append(config.plugins.setupGlass17.par183.getValue())
		self.d.append(config.plugins.setupGlass17.par143.getValue())
		self.d.append(config.plugins.setupGlass17.par189.getValue())
		self.d.append(config.plugins.setupGlass17.par190.getValue())
		self.d.append(config.plugins.setupGlass17.par198.getValue())
		self.d.append(config.plugins.setupGlass17.par200.getValue())
		self.d.append(config.plugins.setupGlass17.par201.getValue())
		self.d.append(config.plugins.setupGlass17.par202.getValue())
		self.d.append(config.plugins.setupGlass17.par203.getValue())
		self.d.append(config.plugins.setupGlass17.par207.getValue())
		self.d.append(config.plugins.setupGlass17.par208.getValue())
		self.d.append(config.plugins.setupGlass17.par209.getValue())
		self.d.append(config.plugins.setupGlass17.par210.getValue())
		self.d.append(config.plugins.setupGlass17.par211.getValue())
		self.d.append(config.plugins.setupGlass17.par213.getValue())
		self.d.append(config.plugins.setupGlass17.par214.getValue())
		self.d.append(config.plugins.setupGlass17.par215.getValue())
		self.d.append(config.plugins.setupGlass17.par222.getValue())
		self.d.append(config.plugins.setupGlass17.par223.getValue())
		self.d.append(config.plugins.setupGlass17.par224.getValue())
		self.d.append(config.plugins.setupGlass17.par226.getValue())
		self.d.append(config.plugins.setupGlass17.par227.getValue())                                       	                                                                                                                                        
		self.d.append(config.plugins.setupGlass17.par229.getValue())
		self.showDonate = False
		self.stateDonate = False
		self.isTunerLabel = False
		self.rst = False
		self._weatherCityAtOpen = config.plugins.setupGlass17.par13.value
		self.firststart = True
		self.start_rst = eTimer()
		try:
			self.start_rst_conn = self.start_rst.timeout.connect(self.saving)
		except AttributeError:
			self.start_rst.timeout.get().append(self.saving)
		self.delayTimer = eTimer()
		try:
			self.delayTimer_conn = self.delayTimer.timeout.connect(self._warderAutoUpdateCheck)
		except AttributeError:
			self.delayTimer.timeout.get().append(self._warderAutoUpdateCheck)
		if ENA_ANIM:
			self.animTimer = eTimer()
			try:
				self.animTimer_conn = self.animTimer.timeout.connect(self.showNext)
			except AttributeError:
				self.animTimer.timeout.get().append(self.showNext)
		try:
			self._changedEntry()
		except: pass
		self.onLayoutFinish.append(self.chckTunerLabel)
		self.onLayoutFinish.append(self._warderStartAutoUpdateCheck)
		self.onShow.append(self.doMyHelpWindow)
			
	def chckSetup(self):
		t = self["config"].getCurrent()[1]
		if t in (config.plugins.setupGlass17.par229, config.plugins.setupGlass17.par226, config.plugins.setupGlass17.par222, config.plugins.setupGlass17.par209, config.plugins.setupGlass17.par104, config.plugins.setupGlass17.par143, config.plugins.setupGlass17.par180, config.plugins.setupGlass17.par171, config.plugins.setupGlass17.par172, config.plugins.setupGlass17.par169, config.plugins.setupGlass17.par161, config.plugins.setupGlass17.par8, config.plugins.setupGlass17.par56, config.plugins.setupGlass17.par125, config.plugins.setupGlass17.par15, config.plugins.setupGlass17.par22, config.plugins.setupGlass17.par95, config.plugins.setupGlass17.par93, config.plugins.setupGlass17.par94, config.plugins.setupGlass17.par31, config.plugins.setupGlass17.par78, config.plugins.setupGlass17.par12, config.plugins.setupGlass17.par76, config.plugins.setupGlass17.par66, config.plugins.setupGlass17.par7, config.plugins.setupGlass17.par27, config.plugins.setupGlass17.par2, config.plugins.setupGlass17.par57):
			self.runSetup()
		elif t in (config.plugins.setupGlass17.par14, config.plugins.setupGlass17.par4):
			self.chckTunerLabel()
      		
	def keyLeft(self):
		if not self.isMainMenu:
			ConfigListScreen.keyLeft(self)
			self.chckSetup()
		else:
			self['list'].pageUp()

	def keyRight(self):
		if not self.isMainMenu:
			ConfigListScreen.keyRight(self)
			self.chckSetup()
		else:
			self['list'].pageDown()

	def keyUp(self):
		if self.isMainMenu:
			if len(self.mainlist) - self['list'].getSelectedIndex() == 1:
				self['list'].instance.moveSelectionTo(0)
			else:
				self['list'].down()
		else:
			self["config"].itemUp()
		
	def keyDown(self):
		if self.isMainMenu:
			if self['list'].getSelectedIndex() == 0:
				self['list'].instance.moveSelectionTo(len(self.mainlist)-1)
			else:
				self['list'].up()
		else:
			self["config"].itemDown()

	def isExit(self):
		if self.isMainMenu:
			self.exit()
		else:
			self["config"].instance.moveSelectionTo(0)
			self.isMainMenu = True
			self.runSetup()
			self.doMyHelpWindow()
			
	def _warderSetPanelMode(self):
	    for prefix, count, visible in (("warder_menu_panel_", 10, self.isMainMenu), ("warder_settings_panel_", 5, not self.isMainMenu)):
	        for index in range(count):
	            panel = self[prefix + str(index)]
	            if visible:
	                panel.show()
	            else:
	                panel.hide()
	    if self.isMainMenu:
	        self["help_txt"].instance.resize(eSize(737, 248))
	    else:
	        self["help_txt"].instance.resize(eSize(780, 350))
	    for renderer in getattr(self, "renderer", ()):
	        if type(renderer).__name__ in ("Pig", "WarderSettingsPig") and renderer.instance is not None:
	            if self.isMainMenu:
	                renderer.onShow()
	                renderer.instance.show()
	            else:
	                renderer.onHide()
	                renderer.instance.hide()

	def runSetup(self):
		self._warderSetPanelMode()
		xxx = chckEnaWea()
		if self.isMainMenu:
			self.mainlist = []
			All = {
				0:[_("Download menu"),''],							
				1:[_("Changelog"),''],
				2:[_("Update"),''],					
				3:[_("Restore config"),''],
				4:[_("Reset all settings of FHDG 17").replace("FHDG 17", "FullHDGlass"),''],
				5:[_("ECM"),''],
				6:[_("EXTRA INFOBAR"),''],
				7:[_("INFOBAR"),({False:'x',True:''}[not config.plugins.setupGlass17.par4.value])],
				8:[_("INFOBAR")+"/"+_("EXTRA INFOBAR"),''],
				9:[_("POSTER"),({False:'x',True:''}[config.plugins.setupGlass17.par198.value])],
				10:[_("HDD/SSD"),''],
				11:[_("NETWORK"),''],
				12:[_("MENU"),''],
				13:[_("CHANNEL SELECTION"),''],
				14:[_("EPG SELECTION"),''],
				15:[_("EVENT VIEW"),''],
				16:[_("SPECIAL INFO"),''],
				17:[_("USER INFO"),''],			
				18:[_("NETATMO"),({False:'x',True:''}[config.plugins.setupGlass17.par12.value == "a" or config.plugins.setupGlass17.par31.value == "a" or config.plugins.setupGlass17.par78.value == "a"])],
				19:[_("OLED"),({False:'',True:'x'}['dm5' in HardwareInfo().get_device_name() or HardwareInfo().get_device_name() == "one"])],
				20:[_("TUNER"),({False:'x',True:''}[self.isTunerLabel])],
				21:[_("ENHANCED WEATHER"),({False:'x',True:''}[config.plugins.setupGlass17.par78.value == "e"])],
				22:[_("WEATHER"),({False:'x',True:''}[xxx])],
				23:[_("WEATHER")+"/"+_("ENHANCED WEATHER"),({False:'x',True:''}[xxx or config.plugins.setupGlass17.par78.value == "e"])],
				24:[_("PATHS"),''],
 				25:[_("VOLUME"),''],
 				26:[_("LISTBOX FONT SIZE"),({False:'x',True:''}[ENA_LS])],
 				27:[_("ANIMATIONS"),({False:'x',True:''}[ENA_ANIM])],
				28:[_("OTHER"),'']
				}
			for x in All:
				if All[x][1] == '':
					item = [x]                        
					item.append(MultiContentEntryText(pos=(40, 2), size=(960, 38), font=2, backcolor_sel=int('0x2a70ad',16), color_sel=int('0xffffff',16), text=All[x][0]))
					item.append(MultiContentEntryPixmapAlphaTest(pos=(0, 9), size=(21, 21), png=LoadPixmap("%sbuttons/led_%s.png" % (SKINPATH, ({False:'green',True:'blue'}[x in range(0,5)])))))
					self.mainlist.append(item)
			del item
			self["config"].hide()
			self["white"].hide()
			self["help_txt"].instance.move(ePoint(60,692))
			self["key_red"].setText(_("Cancel"))
			self['list'].l.setList(self.mainlist)  
			self['list'].l.setItemHeight(40)
			self['list'].instance.moveSelectionTo(self.mainMenuIdx)
			self["list"].show()    		
		else:
			self.list = []
			sepCC = '--- '+_("Color(s)")+':'
			S0 = '%s:'
			C1 = '  %s:'          		
			tt = self['list'].getCurrent()[0]
			if tt == 5:        
				self.list.append(getConfigListEntry(S0 % _("ECM line type"), config.plugins.setupGlass17.par17))                     
				self.list.append(getConfigListEntry(S0 % (_("ECM refresh time")+" (s)"), config.plugins.setupGlass17.par74))      
				self.list.append(getConfigListEntry(S0 % _("Enable show address in ECM info"), config.plugins.setupGlass17.par3))        
				self.list.append(getConfigListEntry(S0 % _("ECM info from current displayed channel only"), config.plugins.setupGlass17.par193))
				self.list.append(getConfigListEntry(S0 % _("Display CW0/1 in Side bar"), config.plugins.setupGlass17.par50))
				self.list.append(getConfigListEntry(S0 % _("Show PID in ECM line"), config.plugins.setupGlass17.par196))
				self.list.append(getConfigListEntry(S0 % _("Show CHID in ECM line"), config.plugins.setupGlass17.par197))
				self.list.append(getConfigListEntry(sepCC)) 
				self.list.append(getConfigListEntry(C1 % _("ECM line"), config.plugins.setupGlass17.par116)) 
				self.list.append(getConfigListEntry(C1 % _("ECM Labels"), config.plugins.setupGlass17.par118))
				self.list.append(getConfigListEntry(C1 % _("ECM Values"), config.plugins.setupGlass17.par119))
			elif tt == 6:
				x = S0 % _("Type")
				self.list.append(getConfigListEntry(x[:-1], config.plugins.setupGlass17.par218))
				x = S0 % _("Icons type")
				self.list.append(getConfigListEntry(x[:-1], config.plugins.setupGlass17.par219))
				self.list.append(getConfigListEntry(S0 % _("Permanent Extra Infobar"), config.plugins.setupGlass17.par4))
				self.list.append(getConfigListEntry(S0 % _("Enable Enhanced Infobar"), config.plugins.setupGlass17.par5))
				self.list.append(getConfigListEntry(S0 % _("Vertical Offset"), config.plugins.setupGlass17.par183))
				self.list.append(getConfigListEntry(S0 % _("Date format"), config.plugins.setupGlass17.par127))
				if ENA_POSTER:
					self.list.append(getConfigListEntry(S0 % _("Poster"), config.plugins.setupGlass17.par198))
				self.list.append(getConfigListEntry(S0 % _("Second picon type"), config.plugins.setupGlass17.par8))                      		                         
				if config.plugins.setupGlass17.par8.value == "3":
					self.list.append(getConfigListEntry(S0 % (_("Animated Weather Icons")), config.plugins.setupGlass17.par169))
					if config.plugins.setupGlass17.par169.value:
						self.list.append(getConfigListEntry(S0 % (_("Animation speed (ms)")), config.plugins.setupGlass17.par170))
				self.list.append(getConfigListEntry(S0 % _("Enable icon")+" Dcam", config.plugins.setupGlass17.par102))
				self.list.append(getConfigListEntry(S0 % _("Enable icon")+" Dtype", config.plugins.setupGlass17.par103))    
				self.list.append(getConfigListEntry(S0 % _("Enable icon")+" Tuner", config.plugins.setupGlass17.par187))
				self.list.append(getConfigListEntry(S0 % _("Enable icon of Unknown CAID"), config.plugins.setupGlass17.par191))
				self.list.append(getConfigListEntry(S0 % _("Audio type of current track"), config.plugins.setupGlass17.par42))
				self.list.append(getConfigListEntry(S0 % _("Progressive/Interlace detection"), config.plugins.setupGlass17.par120))
				self.list.append(getConfigListEntry(S0 % _("Tuner info"), config.plugins.setupGlass17.par168))
				self.list.append(getConfigListEntry(S0 % _("Hide SNR/AGC (Q/S) if value is 0"), config.plugins.setupGlass17.par223))
				self.list.append(getConfigListEntry(S0 % _("CI info"), config.plugins.setupGlass17.par192))
				isBitrate = fromCfgB()
				if isBitrate:
					self.list.append(getConfigListEntry(S0 % _("Bitrate"), config.plugins.setupGlass17.par2))                         			
					if config.plugins.setupGlass17.par2.value:
						if not chckBtr():
							self.list.append(getConfigListEntry(S0 % _("Enable full bitrate info"), config.plugins.setupGlass17.par25))             
							self.list.append(getConfigListEntry(S0 % (_("Bitrate auto stop limit")+(" (kb/s)")), config.plugins.setupGlass17.par35))         
						else:
							self.list.append(getConfigListEntry(S0 % _("Enable eBitrateCalculator"), config.plugins.setupGlass17.par189))
				self.list.append(getConfigListEntry(S0 % _("Show Satellite position in TP info"), config.plugins.setupGlass17.par48))      	
				self.list.append(getConfigListEntry(S0 % _("Provider"), config.plugins.setupGlass17.par81))    
				self.list.append(getConfigListEntry(S0 % _("Temp/RPM"), config.plugins.setupGlass17.par82))    
				self.list.append(getConfigListEntry(S0 % _("CPU/Mem"), config.plugins.setupGlass17.par83))    
				if ENA_POPEN:
					self.list.append(getConfigListEntry(S0 % _("Temp. HDD/SSD"), config.plugins.setupGlass17.par84))
				isSlider = fromCfgB(False)
				if not isSlider:
					self.list.append(getConfigListEntry(S0 % _("Progress bar pixmap"), config.plugins.setupGlass17.par222))
					if config.plugins.setupGlass17.par222.value:
						self.list.append(getConfigListEntry(S0 % _("Progress bar background pixmap"), config.plugins.setupGlass17.par16))     
				self.list.append(getConfigListEntry(sepCC))
				if isBitrate and config.plugins.setupGlass17.par2.value:
					self.list.append(getConfigListEntry(C1 % _("Bitrate"), config.plugins.setupGlass17.par115))
				self.list.append(getConfigListEntry(C1 % _("CPU/Mem, RPM/Temp, Provider"), config.plugins.setupGlass17.par20))
				self.list.append(getConfigListEntry(C1 % _("TP type"), config.plugins.setupGlass17.par121))
				self.list.append(getConfigListEntry(C1 % _("TP info"), config.plugins.setupGlass17.par122))                   	
				self.list.append(getConfigListEntry(C1 % _("Video resolution"), config.plugins.setupGlass17.par123))
				self.list.append(getConfigListEntry(C1 % _("Date"), config.plugins.setupGlass17.par128))                		
				self.list.append(getConfigListEntry(C1 % _("Time"), config.plugins.setupGlass17.par129))
				self.list.append(getConfigListEntry(C1 % _("Seconds"), config.plugins.setupGlass17.par130))
				self.list.append(getConfigListEntry(C1 % _("Channel name"), config.plugins.setupGlass17.par135))                		
				self.list.append(getConfigListEntry(C1 % _("Event now"), config.plugins.setupGlass17.par136))
				self.list.append(getConfigListEntry(C1 % _("Event next"), config.plugins.setupGlass17.par137))
				if isSlider or (not isSlider and not config.plugins.setupGlass17.par222.value):
					if ENA_SLIDER[0]:
						self.list.append(getConfigListEntry(C1 % _("Progress bar foreground"), config.plugins.setupGlass17.par214))
					if ENA_SLIDER[1]:
						self.list.append(getConfigListEntry(C1 % _("Progress bar background"), config.plugins.setupGlass17.par215))
			elif tt == 7:
				self.list.append(getConfigListEntry(S0 % _("Type"), config.plugins.setupGlass17.par14))
				self.list.append(getConfigListEntry(S0 % _("Date format"), config.plugins.setupGlass17.par134))
			elif tt == 8:		        	
				self.list.append(getConfigListEntry(S0 % _("Enable typewriting"), config.plugins.setupGlass17.par30)) 
				self.list.append(getConfigListEntry(S0 % _("Ignore infobar timeout"), config.plugins.setupGlass17.par55))             
				if os.path.exists("/proc/stb/video/alpha"):
					self.list.append(getConfigListEntry(S0 % _("Enable fade"), config.plugins.setupGlass17.par27))                           
					if config.plugins.setupGlass17.par27.value:
						self.list.append(getConfigListEntry(S0 % _("Speed of fade"), config.plugins.setupGlass17.par28))                         
						self.list.append(getConfigListEntry(S0 % _("Enable fade in"), config.plugins.setupGlass17.par29))                                     	
				self.list.append(getConfigListEntry(S0 % _("Show recording icon"), config.plugins.setupGlass17.par114))    	
				self.list.append(getConfigListEntry(S0 % _("Channel name type"), config.plugins.setupGlass17.par79))                   
			elif tt == 9:
				x = S0 % _("Set Position")
				self.list.append(getConfigListEntry(x[:-1], config.plugins.setupGlass17.par199))
				self.list.append(getConfigListEntry(S0 % _("Size"), config.plugins.setupGlass17.par202))
				self.list.append(getConfigListEntry(S0 % _("Provider"), config.plugins.setupGlass17.par204))
				self.list.append(getConfigListEntry(S0 % _("Search delay (s)"), config.plugins.setupGlass17.par205))
				x = S0 % _("Erase poster cache")
				self.list.append(getConfigListEntry(x[:-1], config.plugins.setupGlass17.par206))  
				self.list.append(getConfigListEntry(S0 % _("Removing current Poster"), config.plugins.setupGlass17.par207))
			elif tt == 10:					
				self.list.append(getConfigListEntry(S0 % _("HDD/SSD"), config.plugins.setupGlass17.par22)) 
				if ENA_POPEN and config.plugins.setupGlass17.par22.value != "None":
					self.list.append(getConfigListEntry(S0 % _('Movieplayer infobar HDD/SSD state'), config.plugins.setupGlass17.par160))
					self.list.append(getConfigListEntry(S0 % _("Enable HDD/SSD power state check"), config.plugins.setupGlass17.par23))         
					self.list.append(getConfigListEntry(S0 % _("Wake up HDD/SSD if needed"), config.plugins.setupGlass17.par21))         
			elif tt == 11:	
				self.list.append(getConfigListEntry(S0 % _("Enable control of network status"), config.plugins.setupGlass17.par57))     
				if config.plugins.setupGlass17.par57.value == "3":
					self.list.append(getConfigListEntry(S0 %_ ("IP Address"), config.plugins.setupGlass17.par80))
				x = S0 % (_("Network speed") + "  -  " + _("Set Position"))
				self.list.append(getConfigListEntry(S0 % _("Network speed"), config.plugins.setupGlass17.par209))
				if config.plugins.setupGlass17.par209.value != "0":
					self.list.append(getConfigListEntry(x[:-1], config.plugins.setupGlass17.par212))
					self.list.append(getConfigListEntry(S0 % _("Type"), config.plugins.setupGlass17.par226))
					if config.plugins.setupGlass17.par226.value != "2":
						self.list.append(getConfigListEntry(sepCC)) 
						self.list.append(getConfigListEntry(C1 % _("Network speed"), config.plugins.setupGlass17.par213))   
			elif tt == 12:	
				self.list.append(getConfigListEntry(S0 % _("Type"), config.plugins.setupGlass17.par7))                              
				if config.plugins.setupGlass17.par7.value in ("Icons","Icons Right","Icons Bar","List and Icon"):
					x = S0 % _("Menu Icons")
					self.list.append(getConfigListEntry(x[:-1], config.plugins.setupGlass17.par221))
				self.list.append(getConfigListEntry(S0 % _("Date format"), config.plugins.setupGlass17.par133))
				if config.plugins.setupGlass17.par7.value in ("Icons","Icons Right","Icons Bar"):
					if config.plugins.setupGlass17.par7.value != "Icons Bar":
						self.list.append(getConfigListEntry(S0 % _("Enable empty icons in Menu type - Icons"), config.plugins.setupGlass17.par60))           
					self.list.append(getConfigListEntry(S0 % _("Enable Animation (Menu: Icons/Icons Bar)"), config.plugins.setupGlass17.par63)) 
			elif tt == 13:	
				self.list.append(getConfigListEntry(S0 % _("Type"), config.plugins.setupGlass17.par19))               
				self.list.append(getConfigListEntry(S0 % _("Date format"), config.plugins.setupGlass17.par132))
				self.list.append(getConfigListEntry(S0 % _("Display remaining time in extra EPG"), config.plugins.setupGlass17.par142))
				self.list.append(getConfigListEntry(S0 % _("Picon default, marker, next ..."), config.plugins.setupGlass17.par41))       
				if E2OK:
					self.list.append(getConfigListEntry(S0 % _("ChannelSelection 2xOK"), config.plugins.setupGlass17.par62))      	      
				self.list.append(getConfigListEntry(S0 % _("Text rolling type"), config.plugins.setupGlass17.par76))      
				if config.plugins.setupGlass17.par76.value != "None":
					self.list.append(getConfigListEntry(S0 % _("Text rolling start delay"), config.plugins.setupGlass17.par77))      		
				self.list.append(getConfigListEntry(S0 % _("Service name font size"), config.plugins.setupGlass17.par145))
				self.list.append(getConfigListEntry(S0 % _("Service info font size"), config.plugins.setupGlass17.par146))
				self.list.append(getConfigListEntry(S0 % _("Line height"), config.plugins.setupGlass17.par147))
				self.list.append(getConfigListEntry(S0 % _("Extendend description font size"), config.plugins.setupGlass17.par148))
				self.list.append(getConfigListEntry(sepCC))
				self.list.append(getConfigListEntry(C1 % _("EPG Description"), config.plugins.setupGlass17.par109))
				self.list.append(getConfigListEntry(C1 % _("EPG Description - selected"), config.plugins.setupGlass17.par110))
				self.list.append(getConfigListEntry(C1 % _("Channel name"), config.plugins.setupGlass17.par117))
				self.list.append(getConfigListEntry(C1 % _("Channel name - selected"), config.plugins.setupGlass17.par111))		
			elif tt == 14:                                                         
				self.list.append(getConfigListEntry(S0 % _("Type"), config.plugins.setupGlass17.par54))
				self.list.append(getConfigListEntry(S0 % _("Extendend description font size"), config.plugins.setupGlass17.par53))
				if ENA_ELFS:
					self.list.append(getConfigListEntry(S0 % _("EPG list font size"), config.plugins.setupGlass17.par46))
			elif tt == 15:
				self.list.append(getConfigListEntry(S0 % _("Type"), config.plugins.setupGlass17.par229))
				if config.plugins.setupGlass17.par229.value == "2":
					self.list.append(getConfigListEntry(S0 % _("Provider"), config.plugins.setupGlass17.par204))
					self.list.append(getConfigListEntry(S0 % _("Search delay (s)"), config.plugins.setupGlass17.par205))
					x = S0 % _("Erase poster cache")
					self.list.append(getConfigListEntry(x[:-1], config.plugins.setupGlass17.par206))
			elif tt == 16: 						
				self.list.append(getConfigListEntry(S0 % _("Type"), config.plugins.setupGlass17.par12))
				if config.plugins.setupGlass17.par12.value in ("g","i"):
					x = S0 % _("Set Position")
					self.list.append(getConfigListEntry(x[:-1], config.plugins.setupGlass17.par217))                   
				if config.plugins.setupGlass17.par12.value != "n":
					self.list.append(getConfigListEntry(S0 % _("Enable Special info timeout"), config.plugins.setupGlass17.par73))      
				self.list.append(getConfigListEntry(S0 % (_("Type") + " ("+_("extensions")+")"), config.plugins.setupGlass17.par78))    
				if config.plugins.setupGlass17.par78.value != "n":
					self.list.append(getConfigListEntry(S0 % _("Special info in main menu"), config.plugins.setupGlass17.par85))    	
			elif tt == 17:	
				self.list.append(getConfigListEntry(S0 % _("Type"), config.plugins.setupGlass17.par31))                        
				if config.plugins.setupGlass17.par31.value != "n":
					self.list.append(getConfigListEntry(S0 % _("Enable Permanent User info"), config.plugins.setupGlass17.par32))            
					if config.plugins.setupGlass17.par31.value in ("e","esi","e2"):
						self.list.append(getConfigListEntry(S0 % _("User info act./next switching"), config.plugins.setupGlass17.par33))                      
			elif tt == 18:	
				self.list.append(getConfigListEntry(S0 % _("Station"), config.plugins.setupGlass17.par180)) 
				if config.plugins.setupGlass17.par180.value == "a":                             
					self.list.append(getConfigListEntry(S0 % _("Stations switch time"), config.plugins.setupGlass17.par181)) 
			elif tt == 19:	
				self.list.append(getConfigListEntry(S0 % _("Type"), config.plugins.setupGlass17.par15)) 
				if config.plugins.setupGlass17.par15.value != "0":                             
					self.list.append(getConfigListEntry(S0 % _("Enable OLED off in standby"), config.plugins.setupGlass17.par40)) 
			elif tt == 20:
				self.list.append(getConfigListEntry(S0 % _("Number of tuners"), config.plugins.setupGlass17.par104))
				if config.plugins.setupGlass17.par104.value != "99":
					self.list.append(getConfigListEntry(S0 % _("Hide tuner in standby or missing tuner"), config.plugins.setupGlass17.par139))
					self.list.append(getConfigListEntry(sepCC))
					self.list.append(getConfigListEntry(C1 % _("Active"), config.plugins.setupGlass17.par105))
					self.list.append(getConfigListEntry(C1 % _("Active in the background"), config.plugins.setupGlass17.par106))
					self.list.append(getConfigListEntry(C1 % _("Standby mode"), config.plugins.setupGlass17.par107))
					self.list.append(getConfigListEntry(C1 % _("Missing"), config.plugins.setupGlass17.par108))
					self.list.append(getConfigListEntry(C1 % _("Recording"), config.plugins.setupGlass17.par112))
					self.list.append(getConfigListEntry(C1 % _("Recording and live"), config.plugins.setupGlass17.par113))
			elif tt == 21:	
				self.list.append(getConfigListEntry(S0 % _("Date format"), config.plugins.setupGlass17.par185))
				#self.list.append(getConfigListEntry(S0 % _("Temperature unit"), config.plugins.setupGlass17.par151))
				self.list.append(getConfigListEntry(S0 % (_("Animated Weather Icons")), config.plugins.setupGlass17.par66))
				if config.plugins.setupGlass17.par66.value:
					self.list.append(getConfigListEntry(S0 % (_("Animation speed (ms)")), config.plugins.setupGlass17.par159))
				self.list.append(getConfigListEntry(sepCC))
				self.list.append(getConfigListEntry(C1 % _("UV index"), config.plugins.setupGlass17.par176))
				self.list.append(getConfigListEntry(C1 % _("Wind speed"), config.plugins.setupGlass17.par177))
			elif tt == 22:                                 						
				if config.plugins.setupGlass17.par12.value == "w" or config.plugins.setupGlass17.par78.value == "w":
					self.list.append(getConfigListEntry(S0 % ("("+_("SPECIAL INFO")+") " + _("Type")), config.plugins.setupGlass17.par171))
				if config.plugins.setupGlass17.par31.value == "w":
					self.list.append(getConfigListEntry(S0 % ("("+_("USER INFO")+") " + _("Type")), config.plugins.setupGlass17.par172))
				if not (((config.plugins.setupGlass17.par12.value == "w" or config.plugins.setupGlass17.par78.value == "w") and config.plugins.setupGlass17.par171.value in ("2","4")) or (config.plugins.setupGlass17.par31.value == "w" and config.plugins.setupGlass17.par172.value == "2")):
					self.list.append(getConfigListEntry(S0 % _("Weather Title"), config.plugins.setupGlass17.par173))
				self.list.append(getConfigListEntry(S0 % _("Date format"), config.plugins.setupGlass17.par186))
				self.list.append(getConfigListEntry(S0 % _("Weather location"), config.plugins.setupGlass17.par13))                     
				self.list.append(getConfigListEntry(S0 % _("Temperature unit"), config.plugins.setupGlass17.par86))                      
				self.list.append(getConfigListEntry(S0 % ("("+_('Error')+") "+_("Reconnect time")+" (s)"), config.plugins.setupGlass17.par91))		
				self.list.append(getConfigListEntry(S0 % _("Animated Weather Icons"), config.plugins.setupGlass17.par56))
				if config.plugins.setupGlass17.par56.value:
					self.list.append(getConfigListEntry(S0 % _("Animation speed (ms)"), config.plugins.setupGlass17.par158))
				self.list.append(getConfigListEntry(S0 % _("Display nighttime icons"), config.plugins.setupGlass17.par24))
				self.list.append(getConfigListEntry(S0 % _("Enable next city in Weather"), config.plugins.setupGlass17.par71))
				# r10: provider/API-key UI is obsolete; Open-Meteo is the built-in provider.
				self.list.append(getConfigListEntry(S0 % _("Forecast for more days"), config.plugins.setupGlass17.par143))
				if config.plugins.setupGlass17.par143.value:
					self.list.append(getConfigListEntry(S0 % _("More days switch time"), config.plugins.setupGlass17.par184))
				else:
					self.list.append(getConfigListEntry(S0 % _("Show yesterday"), config.plugins.setupGlass17.par92))
				if ENAFINDER:
					x = S0 % _("Find a city")
					self.list.append(getConfigListEntry(x[:-1], config.plugins.setupGlass17.par90))
			elif tt == 23: 
				x = S0 % _("Weather Icons")
				self.list.append(getConfigListEntry(x[:-1], config.plugins.setupGlass17.par220))
				self.list.append(getConfigListEntry(S0 % (_("Reconnect time")+" (min)"), config.plugins.setupGlass17.par87))
				self.list.append(getConfigListEntry(sepCC))
				self.list.append(getConfigListEntry(C1 % _("Date"), config.plugins.setupGlass17.par174))
				self.list.append(getConfigListEntry(C1 % _("State"), config.plugins.setupGlass17.par175))
				self.list.append(getConfigListEntry(C1 % _("Warm"), config.plugins.setupGlass17.par93))
				self.list.append(getConfigListEntry(C1 % _("Cold"), config.plugins.setupGlass17.par94))
				if config.plugins.setupGlass17.par93.value != "AutoColors" or config.plugins.setupGlass17.par94.value != "AutoColors":
					self.list.append(getConfigListEntry(C1 % _("Fair"), config.plugins.setupGlass17.par95))
					if config.plugins.setupGlass17.par95.value != "None":
						if config.plugins.setupGlass17.par93.value != "AutoColors": 
							self.list.append(getConfigListEntry(S0 % (_("Warm")+" ("+_("temperature")+") - "+DG+"C"), config.plugins.setupGlass17.par96))
							self.list.append(getConfigListEntry(S0 % (_("Warm")+" ("+_("temperature")+") - "+DG+"F"), config.plugins.setupGlass17.par149))
						if config.plugins.setupGlass17.par94.value != "AutoColors": 
							self.list.append(getConfigListEntry(S0 % (_("Cold")+" ("+_("temperature")+") - "+DG+"C"), config.plugins.setupGlass17.par97)) 
							self.list.append(getConfigListEntry(S0 % (_("Cold")+" ("+_("temperature")+") - "+DG+"F"), config.plugins.setupGlass17.par150))
			elif tt == 24:
				self.list.append(getConfigListEntry(S0 % _("Picons/Icons path"), config.plugins.setupGlass17.par125))
				if config.plugins.setupGlass17.par125.value == "0":
					self.list.append(getConfigListEntry(S0 % _("User defined path"), config.plugins.setupGlass17.par124))
				self.list.append(getConfigListEntry(S0 % _("FHDG Configuration file"), config.plugins.setupGlass17.par144))
				if not config.plugins.setupGlass17.par48.value:
					self.list.append(getConfigListEntry(S0 % _("Path to satellites.xml"), config.plugins.setupGlass17.par141))		
			elif tt == 25:
				self.list.append(getConfigListEntry(S0 % _("Type"), config.plugins.setupGlass17.par18))
				self.list.append(getConfigListEntry(S0 % _("Mute picture transparency"), config.plugins.setupGlass17.par47))
				x = S0 % _("Set Position")
				self.list.append(getConfigListEntry(x[:-1], config.plugins.setupGlass17.par216))
			elif tt == 26:
				self.list.append(getConfigListEntry(S0 % _("Bigger"), config.plugins.setupGlass17.par153))
				self.list.append(getConfigListEntry(S0 % _("Big"), config.plugins.setupGlass17.par154))
				self.list.append(getConfigListEntry(S0 % _("Medium"), config.plugins.setupGlass17.par155))
				self.list.append(getConfigListEntry(S0 % _("Small"), config.plugins.setupGlass17.par156))
				self.list.append(getConfigListEntry(S0 % _("Smaller"), config.plugins.setupGlass17.par157))
			elif tt == 27:
				self.list.append(getConfigListEntry(S0 % _("Enable Animations"), config.plugins.setupGlass17.par161))
				if config.plugins.setupGlass17.par161.value:
					self.list.append(getConfigListEntry(S0 % _("(Infobar) Picon"), config.plugins.setupGlass17.par162))
					if config.plugins.setupGlass17.par8.value != "3":
						self.list.append(getConfigListEntry(S0 % _("(Infobar) Second Picon"), config.plugins.setupGlass17.par163))
					self.list.append(getConfigListEntry(S0 % _("(Infobar) Poster"), config.plugins.setupGlass17.par203))
					self.list.append(getConfigListEntry(S0 % _("(Infobar) ECM line"), config.plugins.setupGlass17.par164))
					self.list.append(getConfigListEntry(S0 % _("(Infobar) TP info/type"), config.plugins.setupGlass17.par167))
					self.list.append(getConfigListEntry(S0 % _("(Menu) Big Icons/Icons"), config.plugins.setupGlass17.par165))
					self.list.append(getConfigListEntry(S0 % _("(Channel selection) picon/Prov/Sat"), config.plugins.setupGlass17.par166))
			elif tt == 28:   
				if not os.path.isdir(PYTHONPATH+"Plugins/Extensions/EnhancedMovieCenter"):
					self.list.append(getConfigListEntry(S0 % _("Movie selection type"), config.plugins.setupGlass17.par224))
				if ISVTI:
					self.list.append(getConfigListEntry(S0 % _("VTi SplitScreen"), config.plugins.setupGlass17.par208))
				self.list.append(getConfigListEntry(S0 % _("Reference separating char"), config.plugins.setupGlass17.par179))
				if EFIFO:
					self.list.append(getConfigListEntry(S0 % _("Service scan long list"), config.plugins.setupGlass17.par67))
				self.list.append(getConfigListEntry(S0 % _("Date format"), config.plugins.setupGlass17.par131))
				self.list.append(getConfigListEntry(S0 % _("Ignore leading 0 in time"), config.plugins.setupGlass17.par138))
				self.list.append(getConfigListEntry(S0 % _("Ignore leading 0 in date"), config.plugins.setupGlass17.par188))
				self.list.append(getConfigListEntry(S0 % _("Calculation of channel numbers"), config.plugins.setupGlass17.par126))
				self.list.append(getConfigListEntry(S0 % _("Enable CAID PIDs"), config.plugins.setupGlass17.par26))                                                            
				self.list.append(getConfigListEntry(S0 % _("Neutrino keymap"), config.plugins.setupGlass17.par34))                        
				self.list.append(getConfigListEntry(S0 % _("Localization of the skin"), config.plugins.setupGlass17.par49))            
				if ECL:
					self.list.append(getConfigListEntry(S0 % _("Enable Clear memory"), config.plugins.setupGlass17.par58))      
				if not isATV and not os.path.exists('/etc/dpkg'):
					self.list.append(getConfigListEntry(S0 % _("Enable user encoding.conf"), config.plugins.setupGlass17.par59))          
				if ENA_ONOFF:
					self.list.append(getConfigListEntry(S0 % _("On/Off icons"), config.plugins.setupGlass17.par190))
				self.list.append(getConfigListEntry(S0 % _("RadioScreenSaver"), config.plugins.setupGlass17.par64))      
				self.list.append(getConfigListEntry(S0 % _("IPTV Radio Detection"), config.plugins.setupGlass17.par225))
				self.list.append(getConfigListEntry(S0 % _("PIG type"), config.plugins.setupGlass17.par68))     	
				self.list.append(getConfigListEntry(S0 % _("Update"), config.plugins.setupGlass17.par75))      	                    
				if os.path.isdir(PYTHONPATH+"Plugins/SystemPlugins/NumberZapExt") or os.path.isdir(PYTHONPATH+"Plugins/Extensions/NumberZapExt"):
					self.list.append(getConfigListEntry(S0 % _('Extended Number ZAP Picon Size'), config.plugins.setupGlass17.par227))
			self["config"].list = self.list
			self["config"].setList(self.list)	
			self["list"].hide()
			self["white"].show()
			self["help_txt"].instance.move(ePoint(579,592))
			self["config"].show() 
			self["key_red"].setText(_("Exit"))
                     		
	def reloadCities(self,a=None):
		ch_help = getCitiesCode()
		config.plugins.setupGlass17.par13 = ConfigSelection(default=ch_help[0][0], choices = ch_help)
		ch_help = readAPIkey()
		self.runSetup()

	def openWeatherCityChoice(self):
		choices = []
		for value, name in getCitiesCode():
			if value != "None":
				choices.append((name, value))
		if not choices:
			return
		self.session.openWithCallback(self.weatherCityChoiceSelected, ChoiceBox, title=_("Weather location"), list=choices)

	def weatherCityChoiceSelected(self, answer):
		if answer is None:
			return
		try:
			config.plugins.setupGlass17.par13.value = answer[1]
			self["config"].invalidateCurrent()
		except:
			pass

	def ActivateselectedFnc(self):
		if self.isMainMenu:
			t = self['list'].getCurrent()[0]
			self.mainMenuIdx = self['list'].getSelectedIndex()
			if t == 0:
				self.downMenu()
			elif t == 1:
				self.showHistory()
			elif t == 2:
				self.updatechckact(True)
			elif t == 3:
				self.session.openWithCallback(self.restoreCfgFromFile, dirBrowser, config.plugins.setupGlass17.par144.value, True)
			elif t == 4:
				self.restoreTofactory()
			else:
				self.isMainMenu = False
				self.runSetup()
		else:
			t = self["config"].getCurrent()[1]
			if t == config.plugins.setupGlass17.par124:
				self.session.openWithCallback(self.dirSelected, dirBrowser, config.plugins.setupGlass17.par124.value)
			elif t == config.plugins.setupGlass17.par144:
				self.session.openWithCallback(self.dirConf, dirBrowser, config.plugins.setupGlass17.par144.value)
			elif t == config.plugins.setupGlass17.par141:
				self.session.openWithCallback(self.satxmlConf, dirBrowser, config.plugins.setupGlass17.par141.value)
			elif t == config.plugins.setupGlass17.par13:
				self.openWeatherCityChoice()
			elif t == config.plugins.setupGlass17.par90:
				self.session.openWithCallback(self.reloadCities, cityFinder)
			elif t == config.plugins.setupGlass17.par199:
				self.session.open(SelectPosition, "poster")
			elif t == config.plugins.setupGlass17.par212:
				self.session.open(SelectPosition, "netspeed")
			elif t == config.plugins.setupGlass17.par216:
				self.session.open(SelectPosition, "volMute")
			elif t == config.plugins.setupGlass17.par217:
				self.session.open(SelectPosition)
			elif t == config.plugins.setupGlass17.par218:
				self.session.openWithCallback(self.chckTunerLabel, selectScreenShowed)
			elif t == config.plugins.setupGlass17.par219:
				self.session.openWithCallback(self.showInfo, selectIconsDisplayed)
			elif t == config.plugins.setupGlass17.par220:
				self.session.openWithCallback(self.showInfo, selectIconsDisplayed, 2)
			elif t == config.plugins.setupGlass17.par221:
				self.session.openWithCallback(self.showInfo, selectIconsDisplayed, 1)
			elif t == config.plugins.setupGlass17.par206:
				restartbox = self.session.openWithCallback(self.eraseAnswerNow, MessageBox, _("Erase poster cache"), MessageBox.TYPE_YESNO)
				restartbox.setTitle(_("now?"))
			elif t in (config.plugins.setupGlass17.par203,config.plugins.setupGlass17.par167,config.plugins.setupGlass17.par166,config.plugins.setupGlass17.par165,config.plugins.setupGlass17.par162,config.plugins.setupGlass17.par163,config.plugins.setupGlass17.par164):
				self.doMyHelpWindow()
			else:
				self.isExit()
      			
	def eraseAnswerNow(self, answer):
		if answer:
			poster_dir = os.path.join(config.plugins.setupGlass17.par39.value, "poster")
			for name in listDir(poster_dir) or []:
				candidate = os.path.join(poster_dir, name)
				try:
					if os.path.isfile(candidate) or os.path.islink(candidate):
						os.unlink(candidate)
				except OSError:
					pass
			self.session.open(MessageBox, _("Erase finished successfully!"), MessageBox.TYPE_INFO, 6)

	def doNothing(self):
		pass
			
	def sampleColor(self, c):
		self.canvas.warder_sample_visible = c is not None and not self.isMainMenu
		if c is None:
			if self.isShow:
				self.isShow = False
				self.canvas.fill(0, 0, 450, 45, 0)
				self.canvas.flush()		
		else:
			c = int(c[1:], 0x10)
			self.canvas.fill(0, 0, 450, 45, 0)
			self.canvas.fill(405, 0, 45, 45, c)
			self.canvas.fill(0, 0, 45, 45, c)
			self.canvas.writeText(52, 0, 345, 45, c, 0, gFont("Regular", 37), _("Color Sample"),RT_HALIGN_CENTER)
			self.canvas.flush()
			self.isShow = True
		
	def doMyHelpWindow(self):
		if self.isMainMenu:
			if ENA_ANIM:
				self["helpPicon"].hide()
				self["helpPiconFrame"].hide()
				self["helpTxtAnim"].hide()
			self["help_pict"].hide()
			self["selected_item"].setText("")
			self.sampleColor(None)
			t = helpTxt.get("ok-1","")
			if t != "": 
				self["help_txt"].setText(t)				
			else:
 				self["help_txt"].setText(helpTxt.get("00",""))				
			return
		if len(self.list) == 0:
			return
		def TF(a):
			return ({True:"1", False:"0"}[a])
		self.sampleColor(None)
		t = self["config"].getCurrent()[1]
		filename = "00" 
		ed = False
		if t in (config.plugins.setupGlass17.par215, config.plugins.setupGlass17.par214, config.plugins.setupGlass17.par213, config.plugins.setupGlass17.par177, config.plugins.setupGlass17.par176, config.plugins.setupGlass17.par175, config.plugins.setupGlass17.par174, config.plugins.setupGlass17.par137, config.plugins.setupGlass17.par136, config.plugins.setupGlass17.par135, config.plugins.setupGlass17.par130, config.plugins.setupGlass17.par129, config.plugins.setupGlass17.par128, config.plugins.setupGlass17.par123, config.plugins.setupGlass17.par121, config.plugins.setupGlass17.par122, config.plugins.setupGlass17.par20, config.plugins.setupGlass17.par115, config.plugins.setupGlass17.par116, config.plugins.setupGlass17.par118, config.plugins.setupGlass17.par119):
			ed = True
			t = t.value
			if t != "AutoColors":
				self.sampleColor(t)
				filename = "1-0"
			else:
				filename = "1-1"
		elif t in (config.plugins.setupGlass17.par221,config.plugins.setupGlass17.par220,config.plugins.setupGlass17.par219,config.plugins.setupGlass17.par218,config.plugins.setupGlass17.par217,config.plugins.setupGlass17.par216,config.plugins.setupGlass17.par212,config.plugins.setupGlass17.par90,config.plugins.setupGlass17.par199,config.plugins.setupGlass17.par206):
			filename = "ok-1"
		elif t == config.plugins.setupGlass17.par17:   
			filename = "4-"+config.plugins.setupGlass17.par17.value
		elif t == config.plugins.setupGlass17.par74:
			filename = "54-0"
		elif t == config.plugins.setupGlass17.par3:
			filename = "3-"+TF(config.plugins.setupGlass17.par3.value)
		elif t == config.plugins.setupGlass17.par4:
			filename = "5-"+TF(config.plugins.setupGlass17.par4.value)			
		elif t == config.plugins.setupGlass17.par14:
			filename = "800-"+config.plugins.setupGlass17.par14.value
		elif t == config.plugins.setupGlass17.par42:
			filename = "420-"+TF(config.plugins.setupGlass17.par42.value)
		elif t == config.plugins.setupGlass17.par16:
			filename = "9-"+TF(config.plugins.setupGlass17.par16.value)
		elif t == config.plugins.setupGlass17.par28:
			filename = "13-0"      
		elif t == config.plugins.setupGlass17.par27:
			filename = "14-"+TF(config.plugins.setupGlass17.par27.value)      
		elif t == config.plugins.setupGlass17.par29:
			filename = "15-"+TF(config.plugins.setupGlass17.par29.value)      
		elif t == config.plugins.setupGlass17.par8:
			filename = "16-"+config.plugins.setupGlass17.par8.value      			
		elif t == config.plugins.setupGlass17.par2:
			filename = "22-"+TF(config.plugins.setupGlass17.par2.value)
		elif t == config.plugins.setupGlass17.par25:
			filename = "11-"+TF(config.plugins.setupGlass17.par25.value)
		elif t == config.plugins.setupGlass17.par5:
			filename = "12-"+config.plugins.setupGlass17.par5.value
		elif t == config.plugins.setupGlass17.par35:
			filename = "27-0" 
		elif t == config.plugins.setupGlass17.par48:
			filename = "34-"+TF(config.plugins.setupGlass17.par48.value)			
		elif t == config.plugins.setupGlass17.par55:
			filename = "39-"+config.plugins.setupGlass17.par55.value			
		elif t == config.plugins.setupGlass17.par81:
			filename = "60-"+TF(config.plugins.setupGlass17.par81.value)
		elif t == config.plugins.setupGlass17.par82:
			filename = "61-"+TF(config.plugins.setupGlass17.par82.value)
		elif t == config.plugins.setupGlass17.par83:
			filename = "62-"+TF(config.plugins.setupGlass17.par83.value)
		elif t == config.plugins.setupGlass17.par84:
			filename = "63-"+TF(config.plugins.setupGlass17.par84.value)			
		elif t == config.plugins.setupGlass17.par79:
			filename = "59-"+str(config.plugins.setupGlass17.par79.value)
		elif t == config.plugins.setupGlass17.par23:
			filename = "28-"+TF(config.plugins.setupGlass17.par23.value)      
		elif t == config.plugins.setupGlass17.par21:
			filename = "1007-"+({True:"71", False:"70"}[config.plugins.setupGlass17.par21.value])      
		elif t == config.plugins.setupGlass17.par57:
			filename = "41-"+config.plugins.setupGlass17.par57.value      
		elif t == config.plugins.setupGlass17.par80:
			filename = "42-2" 
		elif t == config.plugins.setupGlass17.par60:
			filename = "44-"+TF(config.plugins.setupGlass17.par60.value)                      			
		elif t == config.plugins.setupGlass17.par63:
			filename = "46-"+TF(config.plugins.setupGlass17.par63.value) 
		elif t == config.plugins.setupGlass17.par19:
			filename = ("6-"+config.plugins.setupGlass17.par19.value).replace("a","").replace("v","")
		elif t == config.plugins.setupGlass17.par41:
			filename = "31-"+({"Black":"0", "White":"1"}[config.plugins.setupGlass17.par41.value])
		elif t == config.plugins.setupGlass17.par62:
			filename = "45-"+TF(config.plugins.setupGlass17.par62.value)
		elif t == config.plugins.setupGlass17.par76:
			filename = "56-"+({"Roll back":"1", "Autostop":"2", "None":"0"}[config.plugins.setupGlass17.par76.value])
		elif t == config.plugins.setupGlass17.par77:
			filename = "57-"+({True:"1", False:"0"}[config.plugins.setupGlass17.par77.value != "default"])	
		elif t == config.plugins.setupGlass17.par12:
			filename = "10-"+config.plugins.setupGlass17.par12.value
		elif t == config.plugins.setupGlass17.par85:
			filename = "64-"+TF(config.plugins.setupGlass17.par85.value)
		elif t == config.plugins.setupGlass17.par78:
			filename = "58-"+config.plugins.setupGlass17.par78.value
		elif t == config.plugins.setupGlass17.par73:
			filename = "53-"+TF(config.plugins.setupGlass17.par73.value)
		elif t == config.plugins.setupGlass17.par13:
			filename = "1017-"+({True:"1", False:"0"}[config.plugins.setupGlass17.par13.value != "None"])
		elif t == config.plugins.setupGlass17.par86:
			filename = "65-"+str(config.plugins.setupGlass17.par86.value)
		elif t == config.plugins.setupGlass17.par87:
			filename = "66-0"
		elif t == config.plugins.setupGlass17.par71:
			filename = "52-"+TF(config.plugins.setupGlass17.par71.value)
		elif t == config.plugins.setupGlass17.par31:
			filename = "18-"+config.plugins.setupGlass17.par31.value
		elif t == config.plugins.setupGlass17.par32:
			filename = "19-"+TF(config.plugins.setupGlass17.par32.value)
		elif t == config.plugins.setupGlass17.par33:
			filename = "20-"+TF(config.plugins.setupGlass17.par33.value)
		elif t == config.plugins.setupGlass17.par26:
			filename = "21-"+TF(config.plugins.setupGlass17.par26.value)
		elif t == config.plugins.setupGlass17.par18:
			filename = "24-"+str(int(config.plugins.setupGlass17.par18.value)-1)
		elif t == config.plugins.setupGlass17.par15:
			filename = "25-"+config.plugins.setupGlass17.par15.value
		elif t == config.plugins.setupGlass17.par7:
			filename = "26-"+menusel(config.plugins.setupGlass17.par7.value)
		elif t == config.plugins.setupGlass17.par40:
			filename = "30-"+TF(config.plugins.setupGlass17.par40.value)
		elif t == config.plugins.setupGlass17.par54:                             
			filename = "38-"+config.plugins.setupGlass17.par54.value
		elif t == config.plugins.setupGlass17.par34:
			filename = "29-"+TF(config.plugins.setupGlass17.par34.value)
		elif t == config.plugins.setupGlass17.par49:
			filename = "35-"+TF(config.plugins.setupGlass17.par49.value)
		elif t == config.plugins.setupGlass17.par53:
			filename = "37-0"
		elif t == config.plugins.setupGlass17.par58:
			filename = "42-"+TF(config.plugins.setupGlass17.par58.value)
		elif t == config.plugins.setupGlass17.par59:
			filename = "43-"+TF(config.plugins.setupGlass17.par59.value)
		elif t == config.plugins.setupGlass17.par64:
			filename = "47-"+TF(config.plugins.setupGlass17.par64.value)
		elif t == config.plugins.setupGlass17.par68:
			filename = "51-"+config.plugins.setupGlass17.par68.value			
		elif t == config.plugins.setupGlass17.par75:
			filename = "55-"+TF(config.plugins.setupGlass17.par75.value)						
		elif t == config.plugins.setupGlass17.par30:
			filename = "23-"+TF(config.plugins.setupGlass17.par30.value)
		elif t == config.plugins.setupGlass17.par91:
			filename = "91-"+({True:"1", False:"0"}[config.plugins.setupGlass17.par91.value != "0"])
		elif t == config.plugins.setupGlass17.par92:
			filename = "92-"+TF(config.plugins.setupGlass17.par92.value)
		elif t == config.plugins.setupGlass17.par94:
			t = config.plugins.setupGlass17.par94.value
			ed = True
			if t != "AutoColors":
				self.sampleColor(t)
				filename = "94-1"
			else:
				filename = "94-0"
		elif t == config.plugins.setupGlass17.par93:
			t = config.plugins.setupGlass17.par93.value
			ed = True
			if t != "AutoColors":
				self.sampleColor(t)
				filename = "93-1"
			else:
				filename = "93-0"
		elif t == config.plugins.setupGlass17.par95:
			t = config.plugins.setupGlass17.par95.value
			ed = True
			if t != "None":
				self.sampleColor(t)
				filename = "95-1"
			else:
				filename = "95-0"
		elif t == config.plugins.setupGlass17.par96:
			filename = "96-0"
		elif t == config.plugins.setupGlass17.par97:
			filename = "97-0"
		elif t == config.plugins.setupGlass17.par102:
			filename = "102-"+TF(config.plugins.setupGlass17.par102.value)
		elif t == config.plugins.setupGlass17.par103:
			filename = "103-"+TF(config.plugins.setupGlass17.par103.value)
		elif t == config.plugins.setupGlass17.par187:
			filename = "187-"+TF(config.plugins.setupGlass17.par187.value)
		elif t == config.plugins.setupGlass17.par104:
			if config.plugins.setupGlass17.par104 == "99":
				filename = _("disabled")
			else:
				filename = "104-0"
		elif t == config.plugins.setupGlass17.par105:
			filename = "105-0"
			t = config.plugins.setupGlass17.par105.value
			ed = True
			if t != "AutoColors":
				self.sampleColor(t)
		elif t == config.plugins.setupGlass17.par106:
			filename = "106-0"
			t = config.plugins.setupGlass17.par106.value
			ed = True
			if t != "AutoColors":
				self.sampleColor(t)
		elif t == config.plugins.setupGlass17.par107:
			filename = "107-0"
			t = config.plugins.setupGlass17.par107.value
			ed = True
			if t != "AutoColors":
				self.sampleColor(t)
		elif t == config.plugins.setupGlass17.par108:
			filename = "108-0"
			t = config.plugins.setupGlass17.par108.value
			ed = True
			if t != "AutoColors":
				self.sampleColor(t)
		elif t == config.plugins.setupGlass17.par109:
			ed = True
			filename = "109-0"
			self.sampleColor(config.plugins.setupGlass17.par109.value)
		elif t == config.plugins.setupGlass17.par110:
			ed = True
			filename = "110-0"
			self.sampleColor(config.plugins.setupGlass17.par110.value)
		elif t == config.plugins.setupGlass17.par111:
			ed = True
			filename = "111-0"
			self.sampleColor(config.plugins.setupGlass17.par111.value)
		elif t == config.plugins.setupGlass17.par117:
			ed = True
			filename = "117-0"
			self.sampleColor(config.plugins.setupGlass17.par117.value)
		elif t == config.plugins.setupGlass17.par112:
			ed = True
			filename = "112-0"
			t = config.plugins.setupGlass17.par112.value
			if t != "AutoColors":
				self.sampleColor(t)
		elif t == config.plugins.setupGlass17.par113:
			ed = True
			filename = "113-0"
			t = config.plugins.setupGlass17.par113.value
			if t != "AutoColors":
				self.sampleColor(t)
		elif t == config.plugins.setupGlass17.par114:
			filename = "114-"+TF(config.plugins.setupGlass17.par114.value)
		elif t == config.plugins.setupGlass17.par120:
			filename = "120-"+TF(config.plugins.setupGlass17.par120.value)
		elif t == config.plugins.setupGlass17.par22:
			filename = "22-1-0"
		elif t == config.plugins.setupGlass17.par124:
			filename = "124-0"
		elif t == config.plugins.setupGlass17.par125:
			filename = "39-1-0"
			setPathFiles(False)
		elif t == config.plugins.setupGlass17.par126:
			filename = "126-" + config.plugins.setupGlass17.par126.value
		elif t == config.plugins.setupGlass17.par127:
			filename = "127-"+({True:"1", False:"0"}[config.plugins.setupGlass17.par127.value != "D"])
			ff = "0"
		elif t == config.plugins.setupGlass17.par131:
			filename = "127-"+({True:"1", False:"0"}[config.plugins.setupGlass17.par131.value != "D"])
			ff = "1"
		elif t == config.plugins.setupGlass17.par132:
			filename = "127-"+({True:"1", False:"0"}[config.plugins.setupGlass17.par132.value != "D"])
			ff = "2"
		elif t == config.plugins.setupGlass17.par133:
			filename = "127-"+({True:"1", False:"0"}[config.plugins.setupGlass17.par133.value != "D"])
			ff = "3"
		elif t == config.plugins.setupGlass17.par134:
			filename = "127-"+({True:"1", False:"0"}[config.plugins.setupGlass17.par134.value != "D"])
			ff = "4"
		elif t == config.plugins.setupGlass17.par185:
			filename = "127-1"
			ff = "5"
		elif t == config.plugins.setupGlass17.par186:
			filename = "127-1"
			ff = "6"
		elif t == config.plugins.setupGlass17.par138:
			filename = "138-"+TF(config.plugins.setupGlass17.par138.value)
		elif t == config.plugins.setupGlass17.par139:
			filename = "139-"+TF(config.plugins.setupGlass17.par139.value)
		elif t == config.plugins.setupGlass17.par142:
			filename = "142-"+TF(config.plugins.setupGlass17.par142.value)
		elif t == config.plugins.setupGlass17.par143:
			filename = "143n-"+TF(config.plugins.setupGlass17.par143.value)
		elif t == config.plugins.setupGlass17.par184:
			filename = "181-x"
		elif t == config.plugins.setupGlass17.par144:
			filename = "144-0"
		elif t == config.plugins.setupGlass17.par141:
			filename = "141-0"
		elif t == config.plugins.setupGlass17.par145:
			filename = "117-0"
		elif t == config.plugins.setupGlass17.par146:
			filename = "109-0"
		elif t == config.plugins.setupGlass17.par147:
			filename = "147-0"
		elif t == config.plugins.setupGlass17.par148:
			filename = "148-0"
		elif t == config.plugins.setupGlass17.par46:
			filename = "460-0"
		elif t == config.plugins.setupGlass17.par149:
			filename = "149-0"
		elif t == config.plugins.setupGlass17.par150: 
			filename = "150-0"
		elif t == config.plugins.setupGlass17.par151:
			filename = ({True:"65-"+str(config.plugins.setupGlass17.par151.value), False:"151-0"}[config.plugins.setupGlass17.par151.value != "0"])
		elif t == config.plugins.setupGlass17.par47:
			filename = "047-"+TF(config.plugins.setupGlass17.par47.value)
		elif t == config.plugins.setupGlass17.par56:
			filename = "560-"+TF(config.plugins.setupGlass17.par56.value)
		elif t == config.plugins.setupGlass17.par66:
			filename = "560-"+TF(config.plugins.setupGlass17.par66.value)
		elif t == config.plugins.setupGlass17.par169:
			filename = "560-"+TF(config.plugins.setupGlass17.par169.value)
		elif t == config.plugins.setupGlass17.par24:
			filename = "024-"+TF(config.plugins.setupGlass17.par24.value)
		elif t in (config.plugins.setupGlass17.par153,config.plugins.setupGlass17.par154,config.plugins.setupGlass17.par155,config.plugins.setupGlass17.par156,config.plugins.setupGlass17.par157):
			filename = "lbs-1"
		elif t in (config.plugins.setupGlass17.par158,config.plugins.setupGlass17.par159,config.plugins.setupGlass17.par170):
			filename = "as-1"
		elif t == config.plugins.setupGlass17.par67:
			filename = "fifo-"+TF(config.plugins.setupGlass17.par67.value)
		elif t == config.plugins.setupGlass17.par160:
			filename = "160-"+TF(config.plugins.setupGlass17.par160.value) 
		elif t == config.plugins.setupGlass17.par161:
			filename = "161-"+TF(config.plugins.setupGlass17.par161.value)
		elif t == config.plugins.setupGlass17.par168:
			filename = "168-"+config.plugins.setupGlass17.par168.value
		elif t == config.plugins.setupGlass17.par171:
			filename = "171-"+config.plugins.setupGlass17.par171.value
		elif t == config.plugins.setupGlass17.par172:
			filename = "172-"+config.plugins.setupGlass17.par172.value
		elif t == config.plugins.setupGlass17.par173:
			filename = "173-"+config.plugins.setupGlass17.par173.value
		elif t == config.plugins.setupGlass17.par179:
			filename = "179-"+config.plugins.setupGlass17.par179.value
		elif t == config.plugins.setupGlass17.par180:
			filename = "180-"+config.plugins.setupGlass17.par180.value
		elif t == config.plugins.setupGlass17.par181:
			filename = "181-x"
		elif t == config.plugins.setupGlass17.par183:
			filename = "183-x"
		elif t == config.plugins.setupGlass17.par188:
			filename = "188-"+TF(config.plugins.setupGlass17.par188.value)
		elif t == config.plugins.setupGlass17.par189:
			filename = "189-"+TF(config.plugins.setupGlass17.par189.value)
		elif t == config.plugins.setupGlass17.par190:
			filename = "190-"+TF(config.plugins.setupGlass17.par190.value)
		elif t == config.plugins.setupGlass17.par191:
			filename = "191-"+TF(config.plugins.setupGlass17.par191.value)
		elif t == config.plugins.setupGlass17.par192:
			filename = "192-"+TF(config.plugins.setupGlass17.par192.value)
		elif t == config.plugins.setupGlass17.par193:
			filename = "193-"+TF(config.plugins.setupGlass17.par193.value)
		elif t == config.plugins.setupGlass17.par50:
			filename = "50x-"+TF(config.plugins.setupGlass17.par50.value)
		elif t == config.plugins.setupGlass17.par196:
			filename = "196-"+TF(config.plugins.setupGlass17.par196.value)
		elif t == config.plugins.setupGlass17.par197:
			filename = "197-"+TF(config.plugins.setupGlass17.par197.value)
		elif t == config.plugins.setupGlass17.par198:
			filename = "198-"+TF(config.plugins.setupGlass17.par198.value)
		elif t == config.plugins.setupGlass17.par202:
			filename = "202"
		elif t == config.plugins.setupGlass17.par204:
			filename = "204-"+config.plugins.setupGlass17.par204.value
		elif t == config.plugins.setupGlass17.par205:
			filename = "205"
		elif t == config.plugins.setupGlass17.par207:
			filename = "207-"+TF(config.plugins.setupGlass17.par207.value)
		elif t == config.plugins.setupGlass17.par208:
			filename = "208-"+config.plugins.setupGlass17.par208.value
		elif t == config.plugins.setupGlass17.par209:
			filename = "209-"+config.plugins.setupGlass17.par209.value
		elif t == config.plugins.setupGlass17.par222:
			filename = "222-"+TF(config.plugins.setupGlass17.par222.value)
		elif t == config.plugins.setupGlass17.par223:
			filename = "223-"+TF(config.plugins.setupGlass17.par223.value)
		elif t == config.plugins.setupGlass17.par224:
			filename = "224-"+config.plugins.setupGlass17.par224.value
		elif t == config.plugins.setupGlass17.par225:
			filename = "225-"+TF(config.plugins.setupGlass17.par225.value)
		elif t == config.plugins.setupGlass17.par226:
			filename = "226-"+config.plugins.setupGlass17.par226.value
		elif t == config.plugins.setupGlass17.par227:
			if config.plugins.setupGlass17.par227.value == "0":
				filename = "227-0"
			else:
				filename = "227-" + config.plugins.setupGlass17.par227.value
		elif t == config.plugins.setupGlass17.par229:                             
			filename = "229-"+config.plugins.setupGlass17.par229.value
		if t in (config.plugins.setupGlass17.par203,config.plugins.setupGlass17.par167,config.plugins.setupGlass17.par166,config.plugins.setupGlass17.par165,config.plugins.setupGlass17.par162,config.plugins.setupGlass17.par163,config.plugins.setupGlass17.par164):
			self["selected_item"].setText("")
			self["help_pict"].hide()
			self["help_txt"].setText("")
			self.eeTanim = None
			if t in (config.plugins.setupGlass17.par167,config.plugins.setupGlass17.par164):
				self.eeTanim = t.getText()
				if self.eeTanimLast == self.eeTanim:
					self.eeTanim = self.eeTanim.upper()
				self.eeTanimLast = self.eeTanim
				self.showAnimTxt(t)
			else:
				self.showAnim(t.value)
		else:
			if ENA_ANIM:
				self["helpPicon"].hide()
				self["helpPiconFrame"].hide()
				self["helpTxtAnim"].hide()
			if filename in helpTxt:
				if filename == "127-1": 
					self["selected_item"].setText(datetime.now().strftime(({"6":config.plugins.setupGlass17.par186.value, "5":config.plugins.setupGlass17.par185.value, "4":config.plugins.setupGlass17.par134.value, "3":config.plugins.setupGlass17.par133.value, "2":config.plugins.setupGlass17.par132.value, "1":config.plugins.setupGlass17.par131.value, "0":config.plugins.setupGlass17.par127.value}[ff])))
				else:
					self["selected_item"].setText("")
				self["help_pict"].hide()
				self["help_txt"].setText(helpTxt.get(filename))
			else:
				filename = config.plugins.setupGlass17.par39.value+"/g17_setup_pict/"+filename+".png"
				if filename:  # All disk access and preparation are delegated to the preview worker.
					if ed:
						self["selected_item"].setText("")
					else:
						self["selected_item"].setText("")
					self["help_txt"].setText("")
					self._warderLoadHelpPicture(filename)
					self["help_pict"].show()
				else:
					self["selected_item"].setText("")
					self["help_pict"].hide()
					self["help_txt"].setText(helpTxt.get("00",""))

	def _warderLoadHelpPicture(self, filename):
	    from .warderHelpPreview import PreviewLoader
	    if not hasattr(self, "_warderHelpLoader"):
	        self._warderHelpLoader = PreviewLoader(self["help_pict"].instance.setPixmapFromFile)
	        self.onClose.append(self._warderHelpLoader.close)
	    self._warderHelpLoader.request(filename)

	def readVersion(self):
		version = "x.xx"
		if os.path.isfile(PLUGINPATH + 'version') is True:
			myfile = open(PLUGINPATH + 'version', 'r')
			version = myfile.readline().strip()
		return version

	def chckTunerLabel(self):
		self.isTunerLabel = False
		if not config.plugins.setupGlass17.par4.value and config.plugins.setupGlass17.par14.value in ("1","4"):
			self.isTunerLabel = True
		else:
			from Screens.G17screens import g17_extraScreen	
			tmp = g17_extraScreen.get(str(config.plugins.setupGlass17.par6.value))
			tmp = tmp.split("\n")
			for i in tmp:
				if "g17TunersLabel" in i:
					self.isTunerLabel = True
					break
		self.showInfo()

	def showInfo(self):
		self.runSetup()
		version = self.readVersion()
		self.textShowInfo = ui_text("Selected settings") + " – " + (_("Extra Screen") + ": " + str(config.plugins.setupGlass17.par6.value) + ", " + _("Icons type") + ": " + str(config.plugins.setupGlass17.par1.value) + ", " + _("Menu Icons") + ": " + str(config.plugins.setupGlass17.par69.value) + ", " + _("Weather Icons") + ": " + str(config.plugins.setupGlass17.par72.value) + ", " + _("HDD/SSD") + ": " + str(config.plugins.setupGlass17.par140.value))
		self.vip = ""
		self.pwdV = None
		if os.path.isfile('/etc/vip17') and os.path.isfile('/usr/bin/unrar_bin'):
			try:
				self.pwdV = open('/etc/vip17', 'r').readline().strip()
			except: pass
			if self.pwdV is not None:
				self.vip = "-vip"
				self.textShowInfo = self.textShowInfo.replace(_("Version:"),_("Version:")+" VIP")
		self["description"].setText(self.textShowInfo)
		if self.firststart:
			self["config"].onSelectionChanged.append(self.doMyHelpWindow)
			self.firststart = False			
			try:
				self["help_pict"].instance.setScale(1)
			except: pass
			if ENA_ANIM:
				try:
					self["helpPicon"].instance.setScale(1)
				except: pass
				
	def showAnimTxt(self,aa):
		self.animTimer.stop()
		if ENA_ANIM and aa.value != "None":
			self["helpPiconFrame"].hide()
			self['helpPicon'].hide()
			try:
				self['helpTxtAnim'].instance.setShowHideAnimation(aa.value)
			except: pass
			self["helpTxtAnim"].show()
			self.animTimer.start(1000)

	def showAnim(self,aa):
		self.animTimer.stop()
		if ENA_ANIM and aa != "None":
			self["helpTxtAnim"].hide()
			try:
				self['helpPicon'].instance.setShowHideAnimation(aa)
			except: pass
			self["helpPiconFrame"].show()
			try:
				self['helpPicon'].show()
				self["helpPicon"].instance.setPixmapFromFile(SKINPATH+"piconWdef.png")
			except: pass
			self.animTimer.start(1000)

	def showNext(self):
		self.animTimer.stop()
		if self.eeTanim:
			try:
				self["helpTxtAnim"].setText(self.eeTanim)
			except: pass
		else:
			try:
				self["helpPicon"].instance.setPixmapFromFile(SKINPATH+"picon_default.png")
			except: pass
      				
	def inetchck(self):
		ret = internet("37.9.170.194")
		if not ret:
			ret = internet()
		return ret

	def _warderVersionTuple(self, value):
		"""Compare Warder versions with TEST prereleases below the matching stable."""
		try:
			value = str(value).strip().lstrip("vV")
			match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-test(\d+))?$", value, re.IGNORECASE)
			if not match:
				return (0, 0, 0, 0, 0)
			major, minor, patch = (int(match.group(i)) for i in (1, 2, 3))
			test_no = match.group(4)
			if test_no is None:
				return (major, minor, patch, 1, 0)
			return (major, minor, patch, 0, int(test_no))
		except (TypeError, ValueError):
			return (0, 0, 0, 0, 0)

	def _warderFetchJson(self, url):
		official_manifests = (
			"https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/update.json",
			"https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/update-production.json",
			"https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/warder-modernization-work/update-test.json",
		)
		if str(url) not in official_manifests:
			raise ValueError("unsafe manifest URL")
		prepared = getattr(self, "_warderPreparedManifest", None)
		if prepared is not None:
			del self._warderPreparedManifest
			if prepared[0] == url:
				return prepared[1]
		sep = "&" if "?" in url else "?"
		url = "%s%scb=%d" % (url, sep, int(time1.time()))
		req = Request(url, headers={"User-Agent": "FullHDGlass17-Warder-Evolution/%s" % self.readVersion(), "Accept": "application/json", "Cache-Control": "no-cache, no-store, max-age=0", "Pragma": "no-cache"})
		with urlopen(req, timeout=12) as response:
			final_url = str(response.geturl()).split("?", 1)[0]
			if final_url not in official_manifests:
				raise ValueError("unsafe manifest redirect")
			return json.loads(response.read().decode("utf-8"))

	def _warderDownload(self, url, target):
		official_package_prefixes = (
			"https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/packages/",
			"https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/warder-modernization-work/packages/test/",
		)
		if not any(str(url).startswith(x) for x in official_package_prefixes):
			raise ValueError("unsafe package URL")
		req = Request(url, headers={"User-Agent": "FullHDGlass17-Warder-Evolution/%s" % self.readVersion()})
		sha = hashlib.sha256()
		with urlopen(req, timeout=30) as response, open(target, "wb") as out:
			if not any(str(response.geturl()).startswith(x) for x in official_package_prefixes):
				raise ValueError("unsafe package redirect")
			while True:
				chunk = response.read(128 * 1024)
				if not chunk:
					break
				out.write(chunk)
				sha.update(chunk)
		return sha.hexdigest().lower()

	def _warderStartAutoUpdateCheck(self):
	    """Start the silent one-shot check only after the setup screen layout exists."""
	    self.delayTimer.stop()
	    if not getattr(self, '_warderAutoTimerCloseHook', False):
	        self.onClose.append(self.delayTimer.stop)
	        self._warderAutoTimerCloseHook = True
	    self.delayTimer.start(3000, True)

	def _warderAutoUpdateCheck(self):
	    """Run the startup network check outside the GUI event loop."""
	    from .warderAutoUpdate import AutoCheck
	    previous = getattr(self, "_warderAutoCheck", None)
	    if previous is not None:
	        previous.close()
	    self._warderAutoCheck = AutoCheck(self)
	    self.onClose.append(self._warderAutoCheck.close)

	def updatechckact(self, ena=False, automatic=False):
		"""Check the official Warder Evolution GitHub update manifest.
	
		The legacy rotating donation banner is intentionally disabled. The setup
		header remains dedicated to normal skin/version information.
		"""
		if not automatic:
			pending = getattr(self, "_warderAutoCheck", None)
			if pending is not None:
				pending.close()
		self.delayTimer.stop()
		self.showDonate = False
		self.stateDonate = False
		if not automatic and not config.plugins.setupGlass17.par75.value and not ena:
			return
	
		manifest_url = "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/update-production.json"
		if "-test" in self.readVersion():
			manifest_url = "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/warder-modernization-work/update-test.json"
		try:
			manifest = self._warderFetchJson(manifest_url)
			new_version = str(manifest.get("version", "")).strip()
			package_url = str(manifest.get("package_url", "")).strip()
			sha256 = str(manifest.get("sha256", "")).strip().lower()
			changelog = str(manifest.get("changelog", "")).strip()
			if not new_version:
				raise ValueError("missing version")
			official_prefixes = (
				"https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/packages/",
				"https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/warder-modernization-work/packages/test/",
			)
			if package_url and not any(package_url.startswith(x) for x in official_prefixes):
				raise ValueError("unsafe package URL")
			if package_url and not re.match(r"^[0-9a-f]{64}$", sha256):
				raise ValueError("missing or invalid SHA256")
		except Exception as err:
			if ena:
				self.session.open(MessageBox, _("Error reading version info!") + "\n\n" + str(err), MessageBox.TYPE_ERROR, 8)
			return
	
		current = self.readVersion()
		if self._warderVersionTuple(new_version) <= self._warderVersionTuple(current):
			if ena:
				self.session.open(MessageBox, update_text("current", "FullHDGlass Warder Evolution", current=current, language=config.osd.language.value), MessageBox.TYPE_INFO, 6)
			return
	
		if not package_url:
			if ena:
				self.session.open(MessageBox, _("New version:") + " " + new_version + "\n\n" + _("Download is not available yet."), MessageBox.TYPE_INFO, 8)
			return
	
		self.warderUpdate = {
			"version": new_version,
			"url": package_url,
			"sha256": sha256,
			"changelog": changelog,
		}
		msg = update_text("offer", "FullHDGlass Warder Evolution", current=current, new=new_version, notes=changelog, language=config.osd.language.value)
		box = self.session.openWithCallback(self.updCont, MessageBox, msg, MessageBox.TYPE_YESNO)
		box.setTitle("FullHDGlass - Warder Evolution")

	def updCont(self, answer):
		if not answer:
			return
		info = getattr(self, "warderUpdate", {})
		url = info.get("url", "")
		version = info.get("version", "")
		expected_sha = info.get("sha256", "").lower()
		official_prefixes = (
			"https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/packages/",
			"https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/warder-modernization-work/packages/test/",
		)
		if not url or not version or not any(url.startswith(x) for x in official_prefixes) or not re.match(r"^[0-9a-f]{64}$", expected_sha):
			self.session.open(MessageBox, _("Error while downloading file!") + "\n\n" + _("Invalid update metadata."), MessageBox.TYPE_ERROR, 6)
			return
		filename = os.path.basename(url.split("?", 1)[0]) or ("fullhdglass17-warder-evolution_%s_all.ipk" % version)
		if not (filename.endswith(".ipk") or filename.endswith(".deb")):
			filename = "fullhdglass17-warder-evolution_%s_all.ipk" % version
		self.fileName = filename
		self.warderProgressBox = self.session.open(MessageBox, update_text("progress", "FullHDGlass Warder Evolution", language=config.osd.language.value), MessageBox.TYPE_INFO, timeout=0, enable_input=False)
		self.warderProgressBox.setTitle("FullHDGlass - Warder Evolution")
		target = "/tmp/" + filename
		try:
			if os.path.exists(target):
				os.remove(target)
			actual_sha = self._warderDownload(url, target)
			if actual_sha != expected_sha:
				try:
					os.remove(target)
				except Exception:
					pass
				self.session.open(MessageBox, _("Downloaded package checksum does not match!") + "\n\nSHA256: " + actual_sha, MessageBox.TYPE_ERROR, 10)
				return
		except Exception as err:
			self.session.open(MessageBox, _("Error while downloading file!") + "\n\n" + str(err), MessageBox.TYPE_ERROR, 8)
			return

		if filename.endswith(".deb"):
			cmd = ["dpkg", "-i", "--force-overwrite", target]
		else:
			cmd = ["opkg", "--force-reinstall", "--force-overwrite", "install", target]

		# Package-manager argv must be passed unchanged. subprocess.Popen avoids
		# Enigma2 eConsoleAppContainer argv[0] differences between images.
		self.warderInstallOutput = []
		try:
			self.warderInstallProcess = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		except Exception as err:
			self._warderInstallCleanup()
			self.session.open(MessageBox, _("Error while updating to new version!!!") + "\n\n" + str(err), MessageBox.TYPE_ERROR, 10)
			return
		self.warderInstallTimer = eTimer()
		try:
			self.warderInstallTimer_conn = self.warderInstallTimer.timeout.connect(self._warderInstallPoll)
		except AttributeError:
			self.warderInstallTimer.timeout.get().append(self._warderInstallPoll)
		self.warderInstallTimer.start(250, True)

	def _warderInstallPoll(self):
		process = getattr(self, "warderInstallProcess", None)
		if process is None:
			return
		exitCode = process.poll()
		if exitCode is None:
			self.warderInstallTimer.start(250, True)
			return
		try:
			out = process.communicate()[0]
			if isinstance(out, bytes):
				out = out.decode("utf-8", "replace")
			self.warderInstallOutput.append(str(out))
		except Exception:
			pass
		self.warderInstallProcess = None
		self._warderInstallFinished(exitCode)

	def _warderCloseProgress(self):
		box = getattr(self, "warderProgressBox", None)
		if box is not None:
			try:
				box.close()
			except Exception:
				pass
		self.warderProgressBox = None

	def _warderInstallCleanup(self):
		self._warderCloseProgress()
		try:
			os.remove("/tmp/" + self.fileName)
		except Exception:
			pass

	def _warderInstallFinished(self, exitCode):
		# Closing the modal progress MessageBox and opening the result dialog in the
		# same callback crashes newer OpenATV (the setup screen is not modal again
		# until the next GUI event-loop turn). Defer the result dialog explicitly.
		self._warderInstallCleanup()
		self.warderInstallExitCode = int(exitCode)
		self.warderInstallProcess = None
		self.warderResultTimer = eTimer()
		try:
			self.warderResultTimer_conn = self.warderResultTimer.timeout.connect(self._warderShowInstallResult)
		except AttributeError:
			self.warderResultTimer.timeout.get().append(self._warderShowInstallResult)
		self.warderResultTimer.start(250, True)

	def _warderShowInstallResult(self):
		target_version = getattr(self, "warderUpdate", {}).get("version", "")
		installed = self.readVersion()
		exitCode = getattr(self, "warderInstallExitCode", -1)
		if exitCode == 0 and target_version and self._warderVersionTuple(installed) >= self._warderVersionTuple(target_version):
			self.warderRestartBox = self.session.open(MessageBox, update_text("success", "FullHDGlass Warder Evolution", new=installed, language=config.osd.language.value), MessageBox.TYPE_INFO, 3, enable_input=False)
			self.warderRestartTimer = eTimer()
			try:
				self.warderRestartTimer_conn = self.warderRestartTimer.timeout.connect(self.sDr)
			except AttributeError:
				self.warderRestartTimer.timeout.get().append(self.sDr)
			self.warderRestartTimer.start(3000, True)
		else:
			out = "".join(getattr(self, "warderInstallOutput", []))
			if len(out) > 5000:
				out = out[-5000:]
			msg = _("Error while updating to new version!!!") + " " + target_version
			if out.strip():
				msg += "\n\n" + out.strip()
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, 15)

	def rstAnswer(self, answer):
		if answer:
			self.sDr()

	def dirSelected(self, answer):
		if answer is not None:
			config.plugins.setupGlass17.par124.value = answer
			setPathFiles()
      			
	def dirConf(self, answer):
		if answer is not None:
			config.plugins.setupGlass17.par144.value = answer

	def satxmlConf(self, answer):
		if answer is not None:
			if os.path.isfile(answer+"satellites.xml"):
				config.plugins.setupGlass17.par141.value = answer
			else:
				self.session.open(MessageBox, _("The file satellites.xml do not exists in selected dir"), MessageBox.TYPE_ERROR, 5)

	def save(self):
		msg = _("GUI will now be restarted to activate changes in:") + "\n"
		msgScr = ""
		tmp = False
		if self.d[39] != config.plugins.setupGlass17.par80.value:
			if not isIP(config.plugins.setupGlass17.par80.value):
				self.session.open(MessageBox, _("IP Address")+": " + str(config.plugins.setupGlass17.par80.value) + ER_F, MessageBox.TYPE_ERROR, 5)
				return
		if self.d[17] != config.plugins.setupGlass17.par40.value:
			xxx = _("Set OLED off in Standby")
			if self.d[4] != "0":	
				msg += xxx + "\n"
				standbyOledOnOff()
			else:
				self.session.open(MessageBox, xxx + ER_F, MessageBox.TYPE_ERROR, 5)
				return
		if self.d[32] != config.plugins.setupGlass17.par62.value:
			if E2OK:
				xxx = chnlSelPatch(config.plugins.setupGlass17.par62.value)
				if not xxx:
					self.session.open(MessageBox, _("ChannelSelection 2xOK") + ER_F, MessageBox.TYPE_ERROR, 5)
					return			
				msg += _("ChannelSelection 2xOK") + "\n"
			else:
				setCFGoff()
		if config.plugins.setupGlass17.par125.value != self.d[55] or config.plugins.setupGlass17.par124.value != self.d[64]:
			xxx = ({True:config.plugins.setupGlass17.par124.value[:-1],False:config.plugins.setupGlass17.par125.value}[config.plugins.setupGlass17.par125.value == "0"])
			if not chckPath(xxx+"/hdg17_files"):
				self.session.open(MessageBox, _("Sorry, cannot create dir on path:") + " " + xxx + " !!!", MessageBox.TYPE_ERROR, 5)
				return
			setPathFiles()
		if self.d[5] != config.plugins.setupGlass17.par7.value:
			if ((config.plugins.setupGlass17.par7.value == "Icons" or self.d[5] == "Icons") and (config.plugins.setupGlass17.par7.value == "Icons Bar" or self.d[5] == "Icons Bar")) \
			or ((config.plugins.setupGlass17.par7.value == "Icons" or self.d[5] == "Icons") and (config.plugins.setupGlass17.par7.value == "Icons Right" or self.d[5] == "Icons Right")) \
			or ((config.plugins.setupGlass17.par7.value == "Icons Right" or self.d[5] == "Icons Right") and (config.plugins.setupGlass17.par7.value == "Icons Bar" or self.d[5] == "Icons Bar")):
				msg += _("Menu type") + "\n"
			elif config.plugins.setupGlass17.par7.value == "Icons" or self.d[5] == "Icons" or config.plugins.setupGlass17.par7.value == "Icons Right" or self.d[5] == "Icons Right" or config.plugins.setupGlass17.par7.value == "Icons Bar" or self.d[5] == "Icons Bar":
				ttmp = "orig17"
				if config.plugins.setupGlass17.par7.value == "Icons" or config.plugins.setupGlass17.par7.value == "Icons Right" or config.plugins.setupGlass17.par7.value == "Icons Bar": 
					ttmp = "new17"
				if setMenuPyo(ttmp):
					msg += _("Menu type") + "\n"
					xxx = changeScreenXml("menu", menusel(config.plugins.setupGlass17.par7.value))
				else:
					msg = _("Menu type") + ": " + str(config.plugins.setupGlass17.par7.value) + ER_F
					self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, 5)
					return
			else:
				msg += _("Menu type") + "\n"
				xxx = changeScreenXml("menu", menusel(config.plugins.setupGlass17.par7.value))
		if config.plugins.setupGlass17.par27.value and not os.path.exists(("/proc/stb/video/alpha")):
			msg = _("Fade cannot be used, alhpa file missing!!!")
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, 5)
			return
		if config.plugins.setupGlass17.par23.value and XCPU == "sh4":
			msg = _("HDD/SSD power state check is not available for SH4")
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, 5)
			return
		if self.d[29] != config.plugins.setupGlass17.par58.value:
			if not ECL:
				config.plugins.setupGlass17.par58.value = False
			else:
				msg += _("Set Clear memory") + "\n"
		if self.d[30] != config.plugins.setupGlass17.par59.value:
			if config.plugins.setupGlass17.par59.value:
				x = setEncodingUser()
				msg += _("Set user encoding.conf") + "\n" 
			else:
				x = setEncodingUser(False)
				msg += _("Set original encoding.conf") + "\n"
			if not x:
				self.session.open(MessageBox, (msg.replace("\n","").replace(_("GUI will now be restarted to activate changes in:"),"") + ER_F), MessageBox.TYPE_ERROR, 5)
				return
		if self.d[8] != config.plugins.setupGlass17.par6.value:
			isOk = checkScreen(config.plugins.setupGlass17.par6.value)
			if not isOk:
				msg = (_("Extra Screen") + ": " + str(config.plugins.setupGlass17.par6.value) + " " + _("is incorrect, please, select existing/correct screen !!!"))
				self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, 5)
				return
			tmp = True
			msgScr = _("Extra Screen") + ": " + str(config.plugins.setupGlass17.par6.value)
			self.d[8] = config.plugins.setupGlass17.par6.value					
			config.plugins.setupGlass17.par6.save()
			if config.plugins.setupGlass17.par227.value == "0":
				x = changeSkinXml("NumberZapExt", chckPiconSize())
		if self.d[7] != config.plugins.setupGlass17.par1.value:
			if not checkIcons(config.plugins.setupGlass17.par1.value):
				msg = (_("Icons type") + ": " + str(config.plugins.setupGlass17.par1.value) + " " + _("is incorrect, please, select correct icons !!!"))
				self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, 5)
				return
			self.d[7] = config.plugins.setupGlass17.par1.value
			msg += _("Icons type") + ": " + str(config.plugins.setupGlass17.par1.value) + "\n"	
			config.plugins.setupGlass17.par1.save()
			x = setTypeIcos(self.d[7])
		if self.d[18] != config.plugins.setupGlass17.par44.value or self.d[19] != config.plugins.setupGlass17.par45.value:
			isOk, color = checkStyleFull(config.plugins.setupGlass17.par6.value, True)
			if isOk != "?":
				x = windowStyle(isOk, color)
				if msgScr == "":
					msg += _("Extra Screen") + ": " + str(config.plugins.setupGlass17.par6.value) + ", "
				msg += _("Style:") + " " + str(config.plugins.setupGlass17.par44.value) + ", " + _("Title color:") + " " + str(config.plugins.setupGlass17.par45.value) + "\n"
			else:
				msg = (_("Style:") + " " + str(config.plugins.setupGlass17.par44.value) + " " + _("is incorrect, style will not be changed!!!") + "\n\n" + _("Save again to apply all setup changes without style change"))
				self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, 5)				
				self.d[18] = config.plugins.setupGlass17.par44.value
				self.d[19] = config.plugins.setupGlass17.par45.value
				return
		if self.d[16] != config.plugins.setupGlass17.par41.value:		
			msg += _("Picon default, marker, next ...") + ": " + config.plugins.setupGlass17.par41.value + "\n"
			setTypePicon()
		if (self.d[38] != config.plugins.setupGlass17.par71.value) and ("w" in config.plugins.setupGlass17.par12.value or "w" in config.plugins.setupGlass17.par31.value):
			msg += _("Enable next city in Weather") + "\n"
		if self.d[6] != config.plugins.setupGlass17.par4.value:
			msg += _("Permanent Extra Infobar") + "\n"
			if config.plugins.setupGlass17.par4.value:
				x = changeSkinXml("InfoBar","3")
			else:
				x = changeSkinXml("InfoBar",config.plugins.setupGlass17.par14.value)
				msg += _("Standard Infobar type") + "\n"
		elif not config.plugins.setupGlass17.par4.value and self.d[11] != config.plugins.setupGlass17.par14.value:	
			msg += _("Standard Infobar type") + "\n"
			x = changeSkinXml("InfoBar",config.plugins.setupGlass17.par14.value)
		if self.d[3] != config.plugins.setupGlass17.par12.value:
			msg += _("Special Info type") + "\n"
		if self.d[9] != config.plugins.setupGlass17.par31.value:
			msg += _("User info type") + "\n"
		if self.d[15] != config.plugins.setupGlass17.par23.value:
			msg += _("HDD/SSD state") + "\n"
		if self.d[14] != config.plugins.setupGlass17.par34.value:
			msg += _("Neutrino keymap") + "\n"
		if self.d[23] != config.plugins.setupGlass17.par49.value:
			msg += _("Localization of the skin") + "\n"
		if self.d[10] != config.plugins.setupGlass17.par33.value:
			msg += _("User info act./next switching") + "\n"
		xxx = False
		if self.d[12] != config.plugins.setupGlass17.par18.value:
			msg += _("Volume type") + "\n"
			xxx = True
		if self.d[24] != config.plugins.setupGlass17.par51.value or self.d[25] != config.plugins.setupGlass17.par52.value:
			msg += _("Set Volume and Mute positions") + "\n"
			xxx = True
		if xxx:
			xxx = changeSkinXml("Volume", config.plugins.setupGlass17.par18.value)
			xxx = changeSkinXml("Mute")
			xxx = chckVolMute()
		if self.d[13] != config.plugins.setupGlass17.par19.value:
			msg += _("Channel selection type") + "\n"
			xxx = changeSkinXml("ChannelSelection", config.plugins.setupGlass17.par19.value)
			x = chckPigFont()
		else:
			eee = True
			if self.d[66] != config.plugins.setupGlass17.par145.value or self.d[67] != config.plugins.setupGlass17.par146.value or self.d[68] != config.plugins.setupGlass17.par147.value or self.d[69] != config.plugins.setupGlass17.par148.value:
				if (config.plugins.setupGlass17.par145.value == "0" and self.d[66] != "0") or (config.plugins.setupGlass17.par146.value == "0" and self.d[67] != "0") or (config.plugins.setupGlass17.par147.value == "0" and self.d[68] != "0") or (config.plugins.setupGlass17.par148.value == "0" and self.d[69] != "0"):
					eee = False
					xxx = changeSkinXml("ChannelSelection", config.plugins.setupGlass17.par19.value)
					x = chckPigFont()
				else:
					x = changeChF()
				msg += _("Channel selection font size") + "\n"
			if eee and (self.d[45] != config.plugins.setupGlass17.par109.value or self.d[46] != config.plugins.setupGlass17.par110.value or self.d[47] != config.plugins.setupGlass17.par111.value or self.d[48] != config.plugins.setupGlass17.par117.value):
				x = cChannelsel(self.d[45],self.d[46],self.d[47],self.d[48])
				msg += _("Channel selection type")+" ("+_("color") + ")\n"
		if self.d[4] != config.plugins.setupGlass17.par15.value:
			if config.plugins.setupGlass17.par15.value == "0":
				xxx = setOledXml(USERORI)
			elif self.d[4] == "0":
				xxx = chckUserHdg()
				xxx = setOledMore()
			else:
				xxx = changeScreenXml("oled", config.plugins.setupGlass17.par15.value, self.d[4])
			msg += _("OLED type") + "\n"
		if self.d[37] != config.plugins.setupGlass17.par68.value:						
			msg += _("PIG type") + "\n"            
			xxx = changePIGres()			
		if self.d[22] != config.plugins.setupGlass17.par48.value:
			msg += _("Show Satellite position in TP info") + "\n"			
		if self.d[34] != config.plugins.setupGlass17.par64.value:
			msg += _("RadioScreenSaver") + "\n"		
		if config.plugins.setupGlass17.par54.value != self.d[27]:		
			msg += _("EPG selection type") + "\n"
			x = changeSkinXml("EPGSelection", config.plugins.setupGlass17.par54.value)
			x = chckPigFont(1)
		elif self.d[26] != config.plugins.setupGlass17.par53.value:
			if config.plugins.setupGlass17.par53.value == "0":
				x = changeSkinXml("EPGSelection", config.plugins.setupGlass17.par54.value)
				x = chckPigFont(1)
			else:			
				x = setFontEventEpgsel(config.plugins.setupGlass17.par53.value)
			msg += _("Extendend description font size") + "\n"
		if config.plugins.setupGlass17.par46.value != self.d[20]:
			if config.plugins.setupGlass17.par46.value == "0":
				x = setFontListEpg("32")
			else:
				x = setFontListEpg(config.plugins.setupGlass17.par46.value)
			msg += _("EPG list font size") + "\n"
		if config.plugins.setupGlass17.par55.value != self.d[31] and self.d[31] == "2":
			config.usage.infobar_timeout.value = config.plugins.setupGlass17.par61.value
		if self.d[2] != config.plugins.setupGlass17.par78.value and (self.d[2] == "n" or config.plugins.setupGlass17.par78.value == "n"):
			msg += _("Special Info type") + " ("+_("extensions")+")" + "\n"
		if self.d[42] != config.plugins.setupGlass17.par92.value:
			msg += _("Show yesterday") + "\n"
		if self.d[43] != config.plugins.setupGlass17.par93.value:
			msg += _("Warm")+" ("+_("color") + ")\n"
		if self.d[44] != config.plugins.setupGlass17.par94.value:
			msg += _("Cold")+" ("+_("color") + ")\n"
		if self.d[49] != config.plugins.setupGlass17.par114.value:
			msg += _("Show recording icon") + "\n"
		if self.d[50] != config.plugins.setupGlass17.par118.value:
			msg += _("ECM Labels")+" ("+_("color") + ")\n"
		if self.d[51] != config.plugins.setupGlass17.par119.value:
			msg += _("ECM Values")+" ("+_("color") + ")\n"
		if self.d[52] != config.plugins.setupGlass17.par121.value:
			msg += _("TP type")+" ("+_("color") + ")\n"
		if self.d[53] != config.plugins.setupGlass17.par122.value:
			msg += _("TP info")+" ("+_("color") + ")\n"
		if self.d[54] != config.plugins.setupGlass17.par123.value:
			msg += _("Video resolution")+" ("+_("color") + ")\n"
		if self.d[56] != config.plugins.setupGlass17.par126.value:
			msg += _("Calculation of channel numbers") + "\n"
		if self.d[57] != config.plugins.setupGlass17.par128.value:
			msg += _("Date") +" ("+_("color") + ")\n"
		if self.d[58] != config.plugins.setupGlass17.par129.value:
			msg += _("Time") +" ("+_("color") + ")\n"
		if self.d[59] != config.plugins.setupGlass17.par130.value:
			msg += _("Seconds") +" ("+_("color") + ")\n"
		if self.d[60] != config.plugins.setupGlass17.par135.value:
			msg += _("Channel name") +" ("+_("color") + ")\n"
		if self.d[61] != config.plugins.setupGlass17.par136.value:
			msg += _("Event now") +" ("+_("color") + ")\n"
		if self.d[62] != config.plugins.setupGlass17.par137.value:
			msg += _("Event next") +" ("+_("color") + ")\n"
		if self.d[63] != config.plugins.setupGlass17.par22.value:
			config.plugins.setupGlass17.par140.value = autoHdd()	
			config.plugins.setupGlass17.par182.value = autoTypeHdd()
		if self.d[65] != config.plugins.setupGlass17.par141.value:
			msg += _("Path to satellites.xml") + "\n"
		if self.d[28] != config.plugins.setupGlass17.par56.value:
			msg += _("Animated Weather Icons") + "\n"
		if self.d[35] != config.plugins.setupGlass17.par66.value:
			msg += _("Animated Weather Icons") + "\n" 
		if self.d[83] != config.plugins.setupGlass17.par169.value:
			msg += _("Animated Weather Icons") + "\n" 
		if self.d[21] != config.plugins.setupGlass17.par47.value:
			msg += chMT()
		if self.d[74] != config.plugins.setupGlass17.par157.value or self.d[73] != config.plugins.setupGlass17.par156.value or self.d[72] != config.plugins.setupGlass17.par155.value or self.d[71] != config.plugins.setupGlass17.par154.value or self.d[70] != config.plugins.setupGlass17.par153.value:
			msg += lbs()
		if self.d[36] != config.plugins.setupGlass17.par67.value:
			x = chckFifo()
			msg += _("Service scan long list") + "\n"
		if (config.plugins.setupGlass17.par8.value != "3" and self.d[75] == "3") or (config.plugins.setupGlass17.par8.value == "3" and self.d[75] != "3") or (config.plugins.setupGlass17.par8.value in ("0","1","2") and self.d[75] in ("4","5","6")) or (self.d[75] in ("0","1","2") and config.plugins.setupGlass17.par8.value in ("4","5","6")):
			msg += _("Second picon type") + "\n"			
		if config.plugins.setupGlass17.par203.value != self.d[97] or config.plugins.setupGlass17.par165.value != self.d[80] or self.d[81] != config.plugins.setupGlass17.par166.value or config.plugins.setupGlass17.par161.value != self.d[76] or self.d[77] != config.plugins.setupGlass17.par162.value or self.d[78] != config.plugins.setupGlass17.par163.value or self.d[79] != config.plugins.setupGlass17.par164.value or self.d[82] != config.plugins.setupGlass17.par167.value:
			msg += _("Animation") + "\n"
		if self.d[84] != config.plugins.setupGlass17.par171.value:
			msg += "("+_("SPECIAL INFO")+") " + _("Type") + "\n" 
		if self.d[85] != config.plugins.setupGlass17.par172.value:
			msg += "("+_("USER INFO")+") " + _("Type") + "\n"
		if self.d[86] != config.plugins.setupGlass17.par174.value:
			msg += "("+_("WEATHER")+") " + _("Date") +" ("+_("color") + ")\n"
		if self.d[87] != config.plugins.setupGlass17.par175.value:
			msg += "("+_("WEATHER")+") " + _("State") +" ("+_("color") + ")\n"
		if self.d[88] != config.plugins.setupGlass17.par180.value:
			msg += _("NETATMO") + "\n"
		if self.d[89] != config.plugins.setupGlass17.par183.value:
			msg += _("Vertical Offset") + "\n"
		if self.d[90] != config.plugins.setupGlass17.par143.value:
			msg += _("10 days forecast") + "\n"
		if self.d[91] != config.plugins.setupGlass17.par189.value:
			msg += _("Enable eBitrateCalculator") + "\n"
		if self.d[92] != config.plugins.setupGlass17.par190.value:
			if setONOFF():
				msg += _("On/Off icons") + "\n"
		if self.d[0] != config.plugins.setupGlass17.par50.value:
			msg += _("Display CW0/1 in Side bar") + "\n"
		if self.d[93] != config.plugins.setupGlass17.par198.value:
			msg += _("Poster") + "\n"
		if self.d[94] != config.plugins.setupGlass17.par200.value or self.d[95] != config.plugins.setupGlass17.par201.value:
			msg += _("Poster") + "/" + _("Set Position") + "\n"
		if self.d[96] != config.plugins.setupGlass17.par202.value:
			msg += _("Poster") + "/" + _("Size") + "\n"
		if self.d[98] != config.plugins.setupGlass17.par207.value:
			msg += _("Poster") + "/" + _("Removing current Poster") + "\n"
		if self.d[99] != config.plugins.setupGlass17.par208.value:
			x = changeSkinXml("SplitScreen", config.plugins.setupGlass17.par208.value)
			msg += _("VTi SplitScreen") + "\n"
		if (self.d[100] == "0" and config.plugins.setupGlass17.par209.value != "0") or (self.d[100] != "0" and config.plugins.setupGlass17.par209.value == "0"):
			msg += _("Network speed") + "\n"
		if self.d[101] != config.plugins.setupGlass17.par210.value or self.d[102] != config.plugins.setupGlass17.par211.value:
			msg += _("Network speed") + "/" + _("Set Position") + "\n"
		if self.d[103] != config.plugins.setupGlass17.par213.value:
			msg += _("Network speed")+" ("+_("color") + ")\n"
		if self.d[104] != config.plugins.setupGlass17.par214.value:
			msg += _("Progress bar foreground")+" ("+_("color") + ")\n"
		if self.d[105] != config.plugins.setupGlass17.par215.value:
			msg += _("Progress bar background")+" ("+_("color") + ")\n"
		if self.d[106] != config.plugins.setupGlass17.par222.value:
			msg += _("Progress bar pixmap") + "\n"
		if self.d[107] != config.plugins.setupGlass17.par223.value:
			msg += _("Hide SNR/AGC (Q/S) if value is 0") + "\n"
		if self.d[108] != config.plugins.setupGlass17.par224.value:		
			msg += _("Movie selection type") + "\n"
			x = changeSkinXml("MovieSelection", config.plugins.setupGlass17.par224.value)
			x = chckPigFont(1)
		if self.d[109] != config.plugins.setupGlass17.par226.value:
			msg += _("Network speed")+" ("+_("Type") + ")\n"
		if self.d[110] != config.plugins.setupGlass17.par227.value:
			msg += _('Extended Number ZAP Picon Size') + "\n"
			if config.plugins.setupGlass17.par227.value == "0":
				x = changeSkinXml("NumberZapExt", chckPiconSize())
			else:
				x = changeSkinXml("NumberZapExt", config.plugins.setupGlass17.par227.value)
		if config.plugins.setupGlass17.par229.value != self.d[111]:		
			msg += _("EventView type") + "\n"
			x = changeSkinXml("EventView", config.plugins.setupGlass17.par229.value)
			x = chckPigFont(1)
		if msg != _("GUI will now be restarted to activate changes in:") + "\n":                                                                                            
			try:
				self.session.open(MessageBox, str(msg+msgScr), MessageBox.TYPE_INFO, 8)
			except: pass
			self.rstGUI()
		else:
			if tmp:
				msg = _("Do you want restart GUI to activate the screen:") + " " + str(config.plugins.setupGlass17.par6.value) + " " + _("now?")
				restartbox = self.session.openWithCallback(self.typeAnswer, MessageBox, msg, MessageBox.TYPE_YESNO)
				restartbox.setTitle(_("Restart GUI now?"))
			else:
				self.saving()

	def typeAnswer(self, answer):
		if answer:
			self.rst = True
		self.saving()

	def rstGUI(self):
		self.rst = True				
		self.start_rst.start(8000, True)

	def saving(self):
		allLines = ""
		try:
			a = config.plugins.setupGlass17.dict()
			for x in range(1, len(ALL_CFG)+1):
				if ALL_CFG[x-1] != "":
					for i in a.items():
						idx = int(str(i[0]).replace("par",""))
						if idx == x:
							cfg = i[1].getValue()
							allLines += "%s: %s\n" % (ALL_CFG[x-1], cfg)
							i[1].save()
							break
			if allLines != "":
				_atomicWriteText(config.plugins.setupGlass17.par144.value+"hdg17.conf", allLines)
		except: pass
		configfile.save()
		if self._weatherCityAtOpen != config.plugins.setupGlass17.par13.value:
			_refreshLiveWeather()
			self._weatherCityAtOpen = config.plugins.setupGlass17.par13.value
		config.plugins.setupGlass17.par43.value = True
		if self.rst:
			self.sDr()
		elif self.destroyTimers():
			self.close()    

	def sDr(self):
		if XCPU != "sh4":
			try:
				self.session.open(TryQuitMainloop, 3)
			except: 
				subprocess.call(RSTCMD)
		else:
			subprocess.call(RSTCMD)

	def isNum(self, txt):
		try:
			tt = int(txt)
			return True
		except ValueError:
			return False

	def restoreTofactory(self):
		restartbox = self.session.openWithCallback(self.restoreTofactoryAnswerNow, MessageBox, _("Reset all settings of FHDG 17").replace("FHDG 17", "FullHDGlass"), MessageBox.TYPE_YESNO, default = False)
		restartbox.setTitle(_("now?"))

	def restoreTofactoryAnswerNow(self,a):
		if a:
			self.restoreCfgFromFile(PLUGINPATH+"defaults")

	def restoreCfgFromFile(self,cfile):
		if cfile is None:
			return
		msg = _("Restore config") + ER_F
		if not os.path.isfile(cfile):
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, 5)
			return
		try:
			num = 0
			lenCfg = 0
			msg = _(" failed") + ": "
			a = config.plugins.setupGlass17.dict()
			f = open(cfile,"r")
			for i in f.readlines():
				tmp = i.strip().split(":")
				if len(tmp) == 2 and tmp[1] is not None and tmp[1] != "":
					for x in range(1, len(ALL_CFG)+1):
						if ALL_CFG[x-1] != "" and tmp[0] == ALL_CFG[x-1]:
							ena = True
							tmp[1] = tmp[1].replace("\n","")
							tmp[1] = str(tmp[1].strip())
							typeValue = tmp[1]								
							if x in [1,6,10,11,44,51,52,69,72,96,97,149,150,158,159,170,200,201,210,211] and not self.isNum(tmp[1]):
								ena = False
							elif x not in [5,8,14,15,17,18,19,24,28,35,46,50,53,54,55,57,68,74,77,79,86,87,90,91,104,125,126,141,145,146,147,148,153,154,155,156,157,171,172,181,183,184,205,208,209,224,226,227] and self.isNum(tmp[1]):
								typeValue = int(tmp[1])            
								if int(tmp[1]) < 1 or ("x-pos." in tmp[0] and 1920 < int(tmp[1])) or ("y-pos." in tmp[0] and 1080 < int(tmp[1])):
									ena = False
							elif "False" in tmp[1]:
								typeValue = False
							elif "True" in tmp[1]:
								typeValue = True
							elif x == 80:
								if not isIP(tmp[1]):
									ena = False
							for ii in a.items():
								idx = int(str(ii[0]).replace("par",""))
								if idx == x:
									cfg = ii[1].getValue()
									if (cfg is True or cfg is False) and not (typeValue is True or typeValue is False):
										ena = False								
									if ena:
										ii[1].setValue(typeValue)
										bb = ii[1].getValue()
										if str(bb) == str(typeValue) or str(bb) == str(tmp[1]):
											lenCfg += 1
										else:
											msg += "%s, " % tmp[0]
									else:
										msg += "%s, " % tmp[0]
									break
							num += 1
							break
			msg = msg[:-2]
			f.close()
		except: pass
		if num == lenCfg:
			msg = _("Config loaded successfully!") + " (%s)" % num
		self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, 5)		
		self.showInfo()    
    		
	def exit(self):
		def gotoRestart(msg):
			self.rst = True				
			try:
				self.start_rst_conn = None
				self.start_rst_conn = self.start_rst.timeout.connect(self.exitNow)
			except AttributeError:
				try:
					self.start_rst.timeout.get().remove(self.saving)
				except: pass
				self.start_rst.timeout.get().append(self.exitNow)
			self.start_rst.start(8000, True)
			self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, 8)
		if self.d[18] != config.plugins.setupGlass17.par44.value or self.d[19] != config.plugins.setupGlass17.par45.value:
			isOk, color = checkStyleFull(config.plugins.setupGlass17.par6.value, True)
			if isOk != "?":
				x = windowStyle(isOk, color)
				msg = _("GUI will now be restarted to activate changes in:") + "\n\n" + _("Style:") + " " + str(config.plugins.setupGlass17.par44.value) + ", " + _("Title color:") + " " + str(config.plugins.setupGlass17.par45.value) + "\n"
				gotoRestart(msg)
			else:
				self.exitNow()
		else:
			self.exitNow()
			
	def exitNow(self):
		try:
			a = config.plugins.setupGlass17.dict()
			for x in range(1, len(ALL_CFG)+1):
				if ALL_CFG[x-1] != "":
					for i in a.items():
						idx = int(str(i[0]).replace("par",""))
						if idx == x:
							i[1].cancel()
							break
		except: pass
		if self.rst:
			self.sDr()
		else:
			setPathFiles()
			if self.destroyTimers():
				self.close()   		

	def destroyTimers(self):
		del self.d
		self.start_rst.stop()
		self.start_rst = None
		self.start_rst_conn = None
		self.delayTimer.stop()
		self.delayTimer = None
		self.delayTimer_conn = None
		if ENA_ANIM:
			self.animTimer.stop()
			self.animTimer = None
			self.animTimer_conn = None
		return True

	def downMenu(self):       		
		self.session.open(downloadMenu) 

	def showHistory(self):                     
		self.session.open(historyScreen)
    
	def createSummary(self):
		return g17SetupSummary

	def getCurrentEntry(self):
		tmp = "FullHDGlass"
		if not self.isMainMenu:
			try:
				tmp = str(self["config"].getCurrent()[0])
			except: pass
		return tmp
		
	def getCurrentValue(self):
		tmp = _("Welcome in setup")
		if self.isMainMenu:
			try:
				sel = self["list"].getCurrent()		
				if sel:
					tmp = str(sel[1][7])
			except: pass
		else:
			try:
				tmp = str(self["config"].getCurrent()[1].getText())		
			except: pass
		return tmp
##########################################################################################################################
class g17SetupSummary(Screen):

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		self.tst = False
		if not IS800SE and not IS820:
			try:
				self["item"] = Label("")
				self["value"] = Label("")
				self.tst = True
			except: pass
		if not self.tst:
			try:
				self["item"] = StaticText("")
				self["value"] = StaticText("")
			except: pass	
		try:
			self.parent["config"].onSelectionChanged.append(self.selectionChanged)
			self.parent.onConfigEntryChanged.append(self.selectionChanged)
		except: pass
		try:
			self.parent['list'].onSelectionChanged.append(self.selectionChanged)
		except: pass
		self.onLayoutFinish.append(self.selectionChanged)

	def selectionChanged(self):
		try:
			self["item"].text = self.parent.getCurrentEntry()
			self["value"].text = self.parent.getCurrentValue()
		except: pass
##########################################################################################################################		
class downloadMenu(Screen):

	skin = """
<screen name="downloadMenu" position="center,center" size="1920,1080" title="" flags="wfNoBorder" backgroundColor="#ff000000">
	<widget position="0,0" size="1920,164" source="global.CurrentTime" render="WarderSettingsHeader" zPosition="-3" /><eLabel position="40,197" size="1840,778" backgroundColor="#1a102136" zPosition="-1" /><eLabel position="1878,197" size="2,778" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="40,197" size="2,778" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="40,973" size="1840,2" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="40,197" size="1840,2" backgroundColor="#003ee8ff" zPosition="1" /><widget name="dwn" position="50,166" size="1820,30" zPosition="20" valign="center" halign="center" font="Regular;25" transparent="1" backgroundColor="#ff000000" foregroundColor="#00ffffff" />
  <widget name="list" position="50,207" size="1820,730" zPosition="2" scrollbarMode="showOnDemand" backgroundColor="#ff000000" foregroundColor="#00ffffff" transparent="1" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" scrollbarBackgroundColor="#00102136" scrollbarForegroundColor="#003ee8ff" />
	<widget name="key_red" position="20,1006" size="458,50" zPosition="2" valign="center" halign="center" font="Regular;28" transparent="0" foregroundColor="#00ff526a" backgroundColor="#00071627" noWrap="1" />
	<widget name="key_green" position="494,1006" size="458,50" zPosition="2" valign="center" halign="center" font="Regular;28" transparent="0" foregroundColor="#0039ff59" backgroundColor="#00071627" noWrap="1" />
	<widget name="key_yellow" position="968,1006" size="458,50" zPosition="2" valign="center" halign="center" font="Regular;28" transparent="0" foregroundColor="#00f5d54e" backgroundColor="#00071627" noWrap="1" />
	<widget name="key_blue" position="1442,1006" size="458,50" zPosition="2" valign="center" halign="center" font="Regular;28" transparent="0" foregroundColor="#0045b9ff" backgroundColor="#00071627" noWrap="1" />
   <eLabel position="20,1000" size="458,2" backgroundColor="#00ff526a" zPosition="1" /><eLabel position="494,1000" size="458,2" backgroundColor="#0039ff59" zPosition="1" /><eLabel position="968,1000" size="458,2" backgroundColor="#00f5d54e" zPosition="1" /><eLabel position="1442,1000" size="458,2" backgroundColor="#0045b9ff" zPosition="1" /><widget position="1120,25" size="250,36" font="Regular;25" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%A</convert></widget><widget position="1020,70" size="350,36" font="Regular;24" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%d. %B %Y</convert></widget><widget position="1398,32" size="190,85" font="Regular;62" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Default</convert></widget><widget position="1590,58" size="66,54" font="Regular;38" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="left" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format::%S</convert></widget><eLabel position="1680,25" size="210,36" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="Version:" /><eLabel position="1680,70" size="210,36" font="Regular;24" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="1.0.35" /><eLabel position="1392,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><eLabel position="1664,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><eLabel position="0,164" size="1920,33" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,197" size="40,778" backgroundColor="#00071627" zPosition="-2" /><eLabel position="1880,197" size="40,778" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,975" size="1920,105" backgroundColor="#00071627" zPosition="-2" /></screen>
"""

	def __init__(self,session):
		self.skin = downloadMenu.skin
		self.session = session
		Screen.__init__(self, session)
		self.list = []
		self["dwn"] = Label(_("Wait for the file downloads to complete"))
		self["dwn"].hide()
		self["key_green"] = Label(_("Select"))
		self["key_yellow"] = Label(_("Cleaning Picons"))
		self["key_red"] = Label(_("Exit"))
		self["key_blue"] = Label(_("Start Download"))
		self["key_blue"].hide()
		self["type_preview"] = Pixmap()
		self['list'] = thumbList2(self.list)	
		self.enaSelectsat = False
		self.clrSelectsat = False
		self.toDown = False
		self.firststart = True
		self.ena = True
		self.msg = ""
		self.warderChannelState = "idle"
		self.warderDABOnly = False
		self.warderDABPending = False
		self.warderDABWorker = None
		self.warderDABTimer = None
		self.warderDABTaskSnapshot = None
		self.onClose.append(self._warderDABCleanup)
		self.warderChannelQueue = None
		self.warderChannelJobs = []
		self.warderChannelInstalled = set()
		self.warderChannelAvailable = set()
		self.warderChannelPackageResults = []
		self.warderChannelCurrentJob = None
		self.warderPiconPrefs = warderPiconSync.default_preferences()
		self.warderPositionSelectionAttempted = False
		self.warderPiconRows = ("wp-pos", "wp-res", "wp-style", "wp-dest", "wp-mode")
		self.warderAuxRows = ("aux-prov", "aux-sat", "aux-cam", "aux-weather")
		self.warderAuxChoiceRow = None
		self.warderLargeSelectionPending = False
		self.warderCurrentActionRow = None
		self.warderOperationSucceeded = False
		self.warderOperationFailed = False
		self.warderFailedRows = set()
		self.warderLegacyChannelQueue = None
		self.warderLegacyChannelAvailable = set()
		self.warderLegacyChannelInstalled = set()
		self.warderLegacyChannelWanted = None
		self.warderLegacyPiconDestination = None
		self.warderLegacyChannelFailures = 0
		self.warderLegacyArchivesProcessed = 0
		sel = '***'+_('Select')+'***   '
		self.menuListAll = {
			0:['wp-pos',_('Satellite positions') + ': ' + _('No position selected'),'warder-picon-positions','','x'],
			1:['wp-res',_('Picon resolution') + ': ' + _('No resolution selected'),'warder-picon-resolution','','x'],
			2:['wp-style',_('Picon colour') + ': ' + _('No colour selected'),'warder-picon-style','','x'],
			3:['wp-dest',_('Picon location') + ': ' + self.warderPiconPrefs["destination"],'warder-picon-destination','','x'],
			4:['wp-mode',_('Update method') + ': ' + _('No update method selected'),'warder-picon-mode','','x'],
			5:['aux-prov',_('Provider logos'),'piconProv','','x'],
			6:['aux-sat',_('Satellite logos'),'piconSat','','x'],
			7:['aux-cam',_('CAM picons'),'piconCam','','x'],
			8:['aux-weather',_('Weather picons'),'piconWeather','','x'],
			9:['oa',sel+_('picon OLED'),8,'','x'],
			10:['h',_('Help'),'help','','x'],
			11:['i',_('Set of icons and prewievs'),'icon_sets_preview','','x'],
			12:['a',_('ExtraScreens graphics'),'extraScreens','','x'],
			13:['m',_('Menu icons'),'menuicons','','x'],
			14:['mb',_('Menu icons')+' ('+_('big')+')','menuiconsbig','','x'],
			15:['w',_('Weather icons'),'weatherIconsN','','x'],
			16:['wanim',_("Animated Weather Icons"),'animWeatherIcons','','x'],
			17:['7z',"7zip",({"aarch64":"7zip-aa","arm":"7zip-a","mipsel":"7zip-m"}.get(XCPU, '')),'','x']
			}	
		self.dwnTimer = eTimer()
		try:
			self.dwnTimer_conn = self.dwnTimer.timeout.connect(self.dwnLoop)
		except AttributeError:
			self.dwnTimer.timeout.get().append(self.dwnLoop)
		self["actions"] = ActionMap(['WizardActions', 'ColorActions'],
		{
			"blue": self.startDown,
			"green": self.doSelection,
			"red": self.exit,
			"yellow": self.cleanPicon,
			"back": self.exit,
			"ok": self.doSelection
		})    
		self.onLayoutFinish.append(self.createList)
		self['list'].onSelectionChanged.append(self.reactivate)	

	def destDir(self,a):
		return ({9:"picon",3:"picon_400x240",4:"picon_50x30",5:"picon",6:"picon_50x30",7:"picon",8:"piconOled"}[a])

	def exit(self):
		if not self.ena:
			return
		if self.dwnTimer is not None and self.dwnTimer.isActive():
			self.dwnTimer.stop()
		self.dwnTimer_conn = None
		self.dwnTimer = None
		self.close()

	def reactivate(self):
		self.toDown = warderPiconSync.has_executable_action(self.warderPiconPrefs)

		for x in self.menuListAll:
			if self.menuListAll[x][4] == "d":
				self.toDown = True
				break
		if self.toDown:
			self["key_blue"].show()
		else:
			self["key_blue"].hide()
				
	def startDown(self, destination_confirmed=False):
		if not self.ena or self.warderChannelState == "running":
			return
		prepared = bool(self.warderPiconPrefs.get("prepared"))
		if prepared and not warderPiconSync.valid_task_selection(self.warderPiconPrefs) and not warderRadio.selected(self.warderPiconPrefs):
			self.session.open(historyScreen, _("Result"), _("Select at least one satellite position."))
			return
		self.warderDABOnly = bool(warderRadio.selected(self.warderPiconPrefs) and not warderPiconSync.valid_task_selection(self.warderPiconPrefs))
		if prepared and ((warderRadio.selected(self.warderPiconPrefs) and not warderRadio.ready(self.warderPiconPrefs)) or (not self.warderDABOnly and not warderPiconSync.channel_preferences_ready(self.warderPiconPrefs))):
			self.session.open(historyScreen, _("Result"), _("Choose a resolution, colour, location and update method before downloading."))
			return
		if not self.toDown:
			return
		if prepared:
			destination = warderPiconSync.validate_destination(self.warderPiconPrefs.get("destination"))
			if not destination:
				self.session.open(historyScreen, _("Result"), _("Invalid picon destination"))
				return
			if os.path.islink(destination):
				self.session.open(historyScreen, _("Result"), _("Invalid picon destination"))
				return
			if not warderPiconSync.destination_storage_available(destination):
				self.session.open(historyScreen, _("Result"), _("Selected storage is not mounted"))
				return
			if not os.path.isdir(destination):
				if not destination_confirmed:
					message = _("Create picon directory?") + "\n" + destination
					self.session.openWithCallback(self.warderCreateDestinationAnswer, MessageBox, message, MessageBox.TYPE_YESNO, default=False)
					return
				try:
					os.makedirs(destination, exist_ok=True)
				except OSError:
					self.session.open(historyScreen, _("Result"), _("Cannot create picon destination"))
					return
			if not os.path.isdir(destination) or not os.access(destination, os.W_OK):
				self.session.open(historyScreen, _("Result"), _("Picon destination is not writable"))
				return
			resolution = self.warderPiconPrefs.get("resolution")
			style = self.warderPiconPrefs.get("style")
			try:
				if self.warderDABOnly:
					pass
				elif warderPiconSync.channel_delivery_backend(resolution, style) == "warder":
					queue = warderPiconSync.build_runtime_queue(self.warderPiconPrefs, publication=warderPiconSync.runtime_publication())
					if queue.get("state") == warderPiconSync.PUBLICATION_LOCKED:
						self.warderChannelState = "locked"
						legacy_pending = any(self.menuListAll[x][4] == "d" and self.menuListAll[x][0] not in self.warderPiconRows for x in self.menuListAll)
						legacy_pending = legacy_pending or self.warderLargeSelectionPending
						msg = _("Warder channel picon publication is currently unavailable.") + " "
						msg += _("Warder picons were skipped; other selected downloads will continue.")
						if not legacy_pending:
							self.warderChannelState = "idle"
							self.session.open(historyScreen, _("Result"), msg)
							return
						self.msg = "(" + _("Warder channel picons") + ") " + msg + "\n"
					self.warderChannelQueue = None
				else:
					archives = warderPiconSync.plan_legacy_channel_archives(
						self.warderPiconPrefs.get("package_selectors"), SATLIST, resolution, style)
					for selector_id, archive_id in archives:
						if not self._legacyPiconArchiveUrl(archive_id):
							raise ValueError(_("Preserved legacy archive is not available in Warder migration catalogue") + ": " + archive_id)
					self.warderLegacyChannelQueue = archives
					self.warderLegacyChannelAvailable = set()
					self.warderLegacyChannelInstalled = set()
					self.warderLegacyChannelFailures = 0
					self.warderLegacyArchivesProcessed = 0
					self.warderLegacyPiconDestination = destination
					if self.warderPiconPrefs.get("update_mode") in (warderPiconSync.UPDATE_MODE_SYNC_TV, warderPiconSync.UPDATE_MODE_SYNC_TV_RADIO):
						request = warderPiconSync.build_sync_request(
							selected_positions=list(self.warderPiconPrefs.get("positions", [])),
							style=style, resolution=resolution,
							include_radio=(self.warderPiconPrefs.get("update_mode") == warderPiconSync.UPDATE_MODE_SYNC_TV_RADIO))
						self.warderLegacyChannelWanted = warderPiconSync.wanted_picon_names(request)
					else:
						self.warderLegacyChannelWanted = None
			except Exception as err:
				message = str(err)
				if message == "no-satellite-position-selected":
					message = _("Select at least one satellite position.")
				elif message == "no-pinned-channel-archive-for-resolution-and-colour":
					message = _("No legacy picon archive is available for the selected positions and variant.")
				self.session.open(historyScreen, _("Result"), _("ERROR") + ": " + message)
				return
		self.warderDABPending = bool(prepared and warderRadio.selected(self.warderPiconPrefs))
		self.warderDABTaskSnapshot = dict(self.warderPiconPrefs) if self.warderDABPending else None
		needs_sevenzip = bool(self.warderLegacyChannelQueue) or any(self.menuListAll[x][0] == "oa" and self.menuListAll[x][4] == "d" for x in self.menuListAll)
		if needs_sevenzip and not find_sevenzip(SEVENZIP):
			tool_row = next((row for row in self.menuListAll.values() if row[0] == "7z" and row[2]), None)
			if tool_row is None:
				self.session.open(historyScreen, _("Result"), ui_text("7zip is not available for this receiver architecture."))
				return
			tool_row[4] = "d"
		self.warderOperationSucceeded = False
		self.warderOperationFailed = False
		self.warderFailedRows = set()
		self.instance.resize(eSize(1920,1080))
		self["dwn"].show()
		self.ena = False
		if self.warderChannelState != "locked":
			self.msg = ""
		self.dwnJob = ""
		self.dwnTimer.start(25, True)

	def warderCreateDestinationAnswer(self, answer=None):
		if answer:
			self.startDown(True)

	def _warderRefreshRowText(self):
		prefs = self.warderPiconPrefs
		positions = warderPiconSync.task_positions_for_display(prefs)
		position_text = _("No position selected")
		if positions:
			position_text = ", ".join(positions[:4])
			if len(positions) > 4:
				position_text += " ..."
			selectors = prefs.get("package_selectors", [])
			position_text += " (" + str(len(selectors)) + " " + _("FastScan tables selected") + ")"
		resolution = prefs.get("resolution")
		style = prefs.get("style")
		mode = prefs.get("update_mode")
		path = prefs.get("destination") or warderPiconSync.DEFAULT_DESTINATION
		preset = dict((value, label) for value, label in warderPiconSync.PICON_DESTINATIONS)
		location = _(preset[path]) if path in preset else _("User defined")
		mode_labels = dict((key, _(label)) for key, label in warderPiconSync.UPDATE_MODES)
		labels = {
			"wp-pos": _("Satellite positions") + ": " + position_text,
			"wp-res": _("Picon resolution") + ": " + (resolution.replace("x", " x ") if resolution else _("No resolution selected")),
			"wp-style": _("Picon colour") + ": " + (_(style.capitalize()) if style else _("No colour selected")),
			"wp-dest": _("Picon location") + ": " + location,
			"wp-mode": _("Update method") + ": " + (mode_labels.get(mode, _("No update method selected"))),
		}
		if warderRadio.selected(prefs):
			labels["wp-pos"] = _("Satellite positions") + ": " + warderRadio.label(prefs, _) + (", " + position_text if positions else "")
		for row_id, label in labels.items():
			for index in self.menuListAll:
				if self.menuListAll[index][0] == row_id:
					self.menuListAll[index][1] = label
					break
		return path

	def _warderDisplayPath(self, path):
		value = str(path or "")
		if len(value) <= 68:
			return value
		return value[:24] + "..." + value[-41:]

	def createList(self):
		warder_destination = self._warderRefreshRowText()
		self.list = []
		warder_help = {
			"wp-pos": _("Choose satellite positions for channel picon downloads and updates."),
			"wp-res": _("Choose 50 x 30, 220 x 132, 400 x 240 or 710 x 682 channel selection icons."),
			"wp-style": _("Choose a channel picon colour supported at the selected size."),
			"wp-dest": _("Download destination:") + " " + self._warderDisplayPath(warder_destination),
			"wp-mode": _("Choose how channel picons are synchronized or copied for selected positions."),
			"aux-prov": _("TV platform and service provider logos."),
			"aux-sat": _("Satellite logos and graphical identifiers."),
			"aux-cam": _("Choose black or white CAM picons."),
			"aux-weather": _("Choose black or white weather information picons."),
		}
		warder_icons = {
			"wp-pos": "down/p4.png",
			"wp-res": "down/ba5.png",
			"wp-style": "down/warder-colour.png",
			"wp-dest": "down/warder-location.png",
			"wp-mode": "down/warder-sync.png",
			"aux-prov": "down/p4p.png",
			"aux-sat": "down/p4s.png",
			"aux-cam": "down/bc.png",
			"aux-weather": "down/bw.png",
		}
		for x in self.menuListAll:
			row_id = self.menuListAll[x][0]
			item = [row_id]
			item.append(MultiContentEntryText(pos=(0, 0), size=(1820, 80), font=0, backcolor_sel=int('0x2a70ad',16), color_sel=int('0xffffff',16), text=" "))
			item.append(MultiContentEntryText(pos=(176, 3), size=(1630, 35), font=0, backcolor_sel=int('0x2a70ad',16), color_sel=int('0xffffff',16), color=int('0xffcc00', 16), text=self.menuListAll[x][1]))
			description = warder_help.get(row_id, helpTxt.get(row_id, ""))
			item.append(MultiContentEntryText(pos=(176, 42), size=(1630, 30), font=1, backcolor_sel=int('0x2a70ad',16), color_sel=int('0xffffff',16), color=int('0xb5d4ec', 16), text=description))
			icon_path = warder_icons.get(row_id, "down/%s.png" % row_id.replace("wanim","w"))
			item.append(MultiContentEntryPixmapAlphaTest(pos=(44, 3), size=(116, 74), flags=BT_SCALE | BT_KEEP_ASPECT_RATIO, png=LoadPixmap(PLUGINPATH + "images/download/" + os.path.basename(icon_path))))
			item.append(MultiContentEntryPixmapAlphaTest(pos=(4, 24), size=(30, 30), flags=BT_SCALE | BT_KEEP_ASPECT_RATIO, png=LoadPixmap(PLUGINPATH + "images/download/" + self.menuListAll[x][4] + ".png")))
			self.list.append(item)
		self['list'].l.setList(self.list)  
		self['list'].l.setItemHeight(80)
		if self.firststart:
			self.firststart = False	
			if not chckPath(config.plugins.setupGlass17.par39.value):
				self.session.openWithCallback(self.exit,MessageBox, _("Sorry, cannot create dir on path:") + " " + config.plugins.setupGlass17.par39.value + "!!!" , MessageBox.TYPE_ERROR, 30)
        		
	def getFreeSpace(self):
		ret = 0
		ret1 = 0
		try:
			stat = statvfs(self.zzz[:-1])
			ret = float(stat.f_bfree/1024 * stat.f_bsize/1024)
			stat = statvfs(config.plugins.setupGlass17.par39.value)
			ret1 = float(stat.f_bfree/1024 * stat.f_bsize/1024)
		except OSError:
			pass
		return ret,ret1

	def setWdir(self):
		if not os.path.exists(HDDTMP):
			try:
				os.makedirs(HDDTMP, exist_ok=True)
			except OSError:
				pass
		return ({False:"/tmp/",True:"%s/" % HDDTMP}['big' in self.type_download or 'ZZPicon' in self.type_download or '400' in self.type_download])

	def doSelection(self):
		if not self.ena:
			return
		tmp = self['list'].getSelectedIndex()
		if self.menuListAll[tmp][0] in self.warderPiconRows:
			self.openWarderPiconChoice(self.menuListAll[tmp][0])
			return
		if self.menuListAll[tmp][0] in self.warderAuxRows:
			self.openAuxPiconChoice(self.menuListAll[tmp][0])
			return
		if self.menuListAll[tmp][0] == '7z' and not self.menuListAll[tmp][2]:
			self.session.open(historyScreen, _("Result"), _("ERROR")+": 7zip helper download is not available for this CPU architecture")
			return
		if '***' in self.menuListAll[tmp][1]:
			self.session.openWithCallback(self.satSelcallback, satSelectorScr, self.menuListAll[tmp][2])
		else:
			self.menuListAll[tmp][4] = ({False:"x",True:"d"}[self.menuListAll[tmp][4] == 'x'])
			self.createList()
			self.reactivate()

	def _setWarderPiconPrepared(self, active_row=None):
		# A Warder picon update is one executable action.  Only the row the user
		# actually confirmed gets the green pending marker; the other preference
		# rows remain configuration, not five separate downloads.
		if active_row:
			for x in self.menuListAll:
				if self.menuListAll[x][0] == active_row:
					self.menuListAll[x][4] = "d"
					break
		self.createList()
		self.reactivate()

	def openWarderPiconChoice(self, row):
		if row == "wp-pos":
			selected = list(self.warderPiconPrefs.get("position_bindings", []))
			if self.warderPiconPrefs.get("include_dab"):selected.append(dict(warderRadio.DAB_BINDING))
			if self.warderPiconPrefs.get("include_iptv"):selected.append(dict(warderRadio.IPTV_BINDING))
			self.session.openWithCallback(self.warderPositionAnswer, warderPositionSelectorScr, selected)
			return
		choices = {}
		resolution = self.warderPiconPrefs.get("resolution", "220x132")
		style = self.warderPiconPrefs.get("style")
		if row == "wp-res":
			choices[row] = [(_(label), ("resolution", size)) for size, label in warderPiconSync.CHANNEL_RESOLUTION_CHOICES]
			choices[row].append((_("710 x 682 - Large icons for selected channel list types"), ("large-selection", "CHSPiconbig")))
		elif row == "wp-style":
			styles = warderPiconSync.STYLES if not resolution else tuple((value, label) for value, label in warderPiconSync.STYLES if warderPiconSync.channel_style_supported(resolution, value))
			choices[row] = [(_(label), ("style", value)) for value, label in styles]
		elif row == "wp-mode":
			choices[row] = [(_(label), ("update_mode", value)) for value, label in warderPiconSync.UPDATE_MODES]
		elif row == "wp-dest":
			choices[row] = [(_(label) + " - " + path, ("destination", path)) for path, label in warderPiconSync.PICON_DESTINATIONS]
			choices[row].append((_("User defined..."), ("custom-location", "")))
		self.warderChoiceRow = row
		self.session.openWithCallback(self.warderPiconChoiceAnswer, ChoiceBox, title=_("Select"), list=choices.get(row, []))

	def openAuxPiconChoice(self, row):
		kind = {"aux-prov": "piconProv", "aux-sat": "piconSat", "aux-cam": "piconCam", "aux-weather": "piconWeather"}.get(row)
		if kind in warderPiconSync.AUXILIARY_VARIANT_IDS:
			options = warderPiconSync.auxiliary_hybrid_variants(kind)
		else:
			variants = warderPiconSync.auxiliary_variants(warderPiconSync.AUXILIARY_ASSET_KEYS)
			options = variants.get(kind, ())
		choices = [(_(label), (asset, label)) for asset, label in options]
		self.session.openWithCallback(lambda *answer: self.warderAuxPiconAnswerFor(row, *answer), ChoiceBox, title=_("Select"), list=choices)

	def warderAuxPiconAnswerFor(self, row, *answer):
		if not answer:
			return
		answer = answer[0] if len(answer) == 1 else answer
		if answer is None or not isinstance(answer, (list, tuple)) or len(answer) < 2:
			return
		try:
			asset, label = answer[1]
		except (TypeError, ValueError):
			return
		if not isinstance(asset, str) or not isinstance(label, str):
			return
		kind = {"aux-prov": "piconProv", "aux-sat": "piconSat"}.get(row)
		if kind in warderPiconSync.AUXILIARY_VARIANT_IDS:
			allowed = set(("transparent", "black", "white"))
			if asset not in allowed:
				return
		elif asset not in warderPiconSync.AUXILIARY_ASSET_KEYS:
			return
		for index in self.menuListAll:
			if self.menuListAll[index][0] == row:
				self.menuListAll[index][2] = asset
				self.menuListAll[index][1] = _(self.menuListAll[index][1].split(":")[0]) + ": " + _(label)
				self.menuListAll[index][4] = "d"
				break
		self.createList()
		self.reactivate()

	def warderPositionAnswer(self, answer=None):
		# Enigma2 dialog close/back paths may call back without a value: Cancel.
		if answer is None or not isinstance(answer, (list, tuple)):
			return
		self.warderPositionSelectionAttempted = True
		include_dab = any(warderRadio.is_dab(item) for item in answer)
		include_iptv = any(warderRadio.is_iptv(item) for item in answer)
		native = [item for item in answer if not warderRadio.is_radio(item)]
		bindings = warderPiconSync.normalize_position_bindings(native)
		if len(bindings) != len(native):
			bindings = []
		self.warderPiconPrefs = warderPiconSync.set_task_position_bindings(self.warderPiconPrefs, bindings)
		self.warderPiconPrefs["include_dab"] = include_dab
		self.warderPiconPrefs["include_iptv"] = include_iptv
		positions = list(self.warderPiconPrefs.get("positions", []))
		if positions:
			preview = ", ".join(positions[:4])
			if len(positions) > 4:
				preview += " ..."
			label = _("Satellite positions") + ": " + preview + " (" + str(len(bindings)) + " " + _("FastScan tables selected") + ")"
		elif include_dab or include_iptv:
			label = _("Satellite positions") + ": " + warderRadio.label(self.warderPiconPrefs, _)
			self.warderPiconPrefs["prepared"] = True
		else:
			label = _("Satellite positions") + ": " + _("No position selected")
			self.warderPiconPrefs["prepared"] = False
			for index in self.menuListAll:
				if self.menuListAll[index][0] in self.warderPiconRows:
					self.menuListAll[index][4] = "x"
		for index in self.menuListAll:
			if self.menuListAll[index][0] == "wp-pos":
				self.menuListAll[index][1] = label
				break
		if positions or include_dab or include_iptv:
			self.warderPiconPrefs["prepared"] = True
			self._setWarderPiconPrepared("wp-pos")
		self.createList()
		self.reactivate()

	def warderPiconChoiceAnswer(self, answer=None):
		# ChoiceBox cancel and window-close paths can call back with no value.
		if answer is None or not isinstance(answer, (list, tuple)) or len(answer) < 2:
			return
		try:
			key, value = answer[1]
		except (TypeError, ValueError):
			return
		if key == "custom-location":
			current = self.warderPiconPrefs.get("destination") or warderPiconSync.DEFAULT_DESTINATION
			start_path = current if os.path.isdir(current) else "/"
			self.session.openWithCallback(self.warderCustomLocationAnswer, dirBrowser, start_path)
			return
		if key == "large-selection":
			self.warderLargeSelectionPending = True
			for index in self.menuListAll:
				if self.menuListAll[index][0] == "wp-res":
					self.menuListAll[index][4] = "d"
					break
			self.createList()
			self.reactivate()
			return
		if key not in ("resolution", "style", "update_mode", "destination"):
			return
		if key == "style" and self.warderPiconPrefs.get("resolution") and not warderPiconSync.channel_style_supported(self.warderPiconPrefs.get("resolution"), value):
			return
		if key == "destination":
			value = warderPiconSync.validate_destination(value)
			if not value:
				return
		self.warderPiconPrefs = warderPiconSync.set_preference(self.warderPiconPrefs, key, value)
		if key == "resolution" and self.warderPiconPrefs.get("style") and not warderPiconSync.channel_style_supported(value, self.warderPiconPrefs["style"]):
			self.warderPiconPrefs = warderPiconSync.set_preference(self.warderPiconPrefs, "style", None)
		self._setWarderPiconPrepared(self.warderChoiceRow)
		self.createList()
		self.reactivate()

	def warderCustomLocationAnswer(self, answer=None):
		if not answer:
			return
		path = os.path.normpath(str(answer))
		if not os.path.isabs(path) or not os.path.isdir(path) or os.path.islink(path):
			self.session.open(historyScreen, _("Result"), _("Select an existing directory."))
			return
		path = warderPiconSync.validate_destination(path)
		if not path:
			self.session.open(historyScreen, _("Result"), _("Invalid picon destination"))
			return
		self.warderPiconPrefs = warderPiconSync.set_preference(self.warderPiconPrefs, "destination", path)
		self._setWarderPiconPrepared("wp-dest")
		self.createList()
		self.reactivate()

	def satSelcallback(self, answer=None):
		if answer is None:
			return
		tmp = self['list'].getSelectedIndex()
		if answer:
			self.menuListAll[tmp][3] = answer
		else:
			self.menuListAll[tmp][3] = ''
		self.menuListAll[tmp][4] = ({False:"x",True:"d"}[self.menuListAll[tmp][3] != ''])
		self.createList()
		self.reactivate()

	def satSelcallback(self, answer):
		tmp = self['list'].getSelectedIndex()
		if answer:
			self.menuListAll[tmp][3] = answer
		else:
			self.menuListAll[tmp][3] = ''
		self.menuListAll[tmp][4] = ({False:"x",True:"d"}[self.menuListAll[tmp][3] != ''])
		self.createList()
		self.reactivate()

	def cleanPicon(self):
		if not self.ena:
			return
		self.session.openWithCallback(self.cleanAnswerNow, satSelectorScr)

	def cleanAnswerNow(self, answer=None):
		if answer:
			self.clrSelectsat = True
			self.answer = answer          				
			numPict = 0
			total = 0
			for ii in ['picon','piconOled','picon_50x30','picon_400x240','ZZPicon','picon_220x132']:	
				actDir = "%s/%s" % (config.plugins.setupGlass17.par39.value,ii)
				f = listDir(actDir)
				if f:
					for x in f:
						total += 1
						if self.chck(x):
							candidate = os.path.join(actDir, x)
							try:
								if os.path.isfile(candidate) or os.path.islink(candidate):
									os.unlink(candidate)
							except OSError:
								pass
							if not os.path.lexists(candidate):
								numPict += 1
			self.dwnLoop(_("SUCCESSFUL")+": "+_("Total:") + " " + str(total) + ", " + _("Deleted:") + " " + str(numPict))	
		
	def _warderLoadChannelManifest(self, url):
		"""Fetch a fresh approved catalogue for each new channel-download operation."""
		expected = warderPiconSync.runtime_publication().get("manifest_url")
		if not expected or url != expected:
			raise ValueError("Warder channel manifest is not enabled")
		req = Request(url, headers={"User-Agent": "FullHDGlass17-Warder-Evolution/channel-picons",
			"Accept": "application/json", "Cache-Control": "no-cache", "Pragma": "no-cache"})
		with urlopen(req, timeout=30) as response:
			if str(response.geturl()) != expected:
				raise ValueError("Warder channel manifest redirect rejected")
			data = response.read(4 * 1024 * 1024 + 1)
		if len(data) > 4 * 1024 * 1024:
			raise ValueError("Warder channel manifest too large")
		doc = json.loads(data.decode("utf-8"))
		errors = warderPiconSync.validate_publication_manifest(doc, url)
		if errors:
			raise ValueError("invalid Warder channel manifest: " + "; ".join(errors[:3]))
		return doc

	def _warderLoadAuxiliaryCandidateManifest(self, url):
		"""Fetch only the PiconHub manifest pinned by the auxiliary descriptor."""
		descriptor = warderPiconSync.AUXILIARY_PUBLICATION_SOURCES["piconhub-aux-candidate"]
		if url != descriptor.get("manifest_url"):
			raise ValueError("untrusted auxiliary candidate manifest")
		req = Request(url, headers={"User-Agent": "FullHDGlass17-Warder-Evolution/auxiliary-picons",
			"Accept": "application/json"})
		with urlopen(req, timeout=30) as response:
			if str(response.geturl()) != url:
				raise ValueError("unsafe auxiliary candidate manifest redirect")
			content_type = str(response.headers.get("Content-Type", "")).lower()
			if "text/html" in content_type:
				raise ValueError("auxiliary candidate manifest returned HTML")
			data = response.read(1024 * 1024 + 1)
		if len(data) > 1024 * 1024 or data.lstrip().lower().startswith((b"<html", b"<!doctype")):
			raise ValueError("invalid auxiliary candidate manifest response")
		document = json.loads(data.decode("utf-8"))
		errors = warderPiconSync.validate_auxiliary_candidate_manifest(document, url)
		if errors:
			raise ValueError("invalid auxiliary candidate manifest: " + "; ".join(errors[:3]))
		return document

	def _warderAuxiliaryDestination(self, name):
		"""Create only the requested auxiliary leaf under the configured picon root."""
		if name not in ("piconProv", "piconSat"):
			raise ValueError("invalid auxiliary destination")
		base = str(config.plugins.setupGlass17.par39.value)
		if not os.path.isdir(base) or os.path.islink(base):
			raise ValueError("unsafe auxiliary picon base directory")
		base = os.path.realpath(base)
		destination = os.path.join(base, name)
		if os.path.islink(destination):
			raise ValueError("auxiliary destination is a symbolic link")
		if not os.path.exists(destination):
			os.mkdir(destination)
		if not os.path.isdir(destination) or os.path.realpath(destination) != destination:
			raise ValueError("unsafe auxiliary destination")
		return destination

	def _warderFetchAuxiliaryArchive(self, asset, archive):
		"""Download and reassemble source-bound archive parts; verify SHA and ZIP."""
		source_id = asset.get("publication_source_id")
		parts = asset.get("parts", [])
		urls = [str(url) for url in parts] if isinstance(parts, list) and parts else [str(asset.get("url", ""))]
		if not urls or not all(warderPiconSync.trusted_auxiliary_url(url, source_id) for url in urls):
			raise ValueError("unsafe Warder auxiliary URL")
		expected_size = int(asset.get("size", 0))
		if expected_size < 1 or expected_size > 32 * 1024 * 1024:
			raise ValueError("invalid Warder auxiliary archive size")
		digest = hashlib.sha256()
		total = 0
		with open(archive, "wb") as output:
			for url in urls:
				req = Request(url, headers={"User-Agent": "FullHDGlass17-Warder-Evolution/auxiliary-picons"})
				with urlopen(req, timeout=45) as response:
					if not warderPiconSync.trusted_auxiliary_url(str(response.geturl()), source_id):
						raise ValueError("unsafe Warder auxiliary redirect")
					content_type = str(response.headers.get("Content-Type", "")).lower()
					if "text/html" in content_type:
						raise ValueError("Warder auxiliary archive returned HTML")
					while True:
						chunk = response.read(1024 * 128)
						if not chunk:
							break
						total += len(chunk)
						if total > expected_size:
							raise ValueError("oversized Warder auxiliary archive")
						output.write(chunk)
						digest.update(chunk)
		if total != expected_size:
			raise ValueError("Warder auxiliary archive size mismatch")
		if digest.hexdigest().lower() != str(asset.get("sha256", "")).lower():
			raise ValueError("Warder auxiliary archive SHA-256 mismatch")
		errors = warderPiconSync.validate_auxiliary_archive(archive, asset)
		if errors:
			raise ValueError("invalid Warder auxiliary archive: " + "; ".join(errors[:3]))

	def _warderRunCanalProviderBundle(self, style):
		"""Overlay the two Canal+ country logos into the selected provider style."""
		spec = warderPiconSync.CANAL_PROVIDER_BUNDLE_ASSETS.get(style)
		if not spec:
			raise ValueError("invalid provider logo style")
		asset_id, filename, expected_members = spec
		err, assets = getWarderAssets()
		if err:
			raise ValueError(err)
		asset = assets.get(asset_id)
		if not isinstance(asset, dict):
			raise ValueError("Canal+ provider bundle is not published")
		source = warderPiconSync.AUXILIARY_PUBLICATION_SOURCES["fullhd-provider-bundle"]
		expected_url = source["package_root"] + filename
		if (asset.get("filename") != filename or asset.get("root") != "piconProv_220x132"
				or int(asset.get("png_count", 0)) != len(expected_members)
				or asset.get("publication_source_id") != "fullhd-provider-bundle"
				or str(asset.get("url", "")) != expected_url):
			raise ValueError("Canal+ provider bundle catalog entry does not match its package")
		root = "piconProv_220x132"
		self._warderAuxiliaryDestination(root)
		archive = None
		stage = None
		previous_zzz = self.zzz
		try:
			fd, archive = tempfile.mkstemp(prefix="warder-canal-provider-", suffix=".zip", dir="/tmp")
			os.close(fd)
			self._warderFetchAuxiliaryArchive(asset, archive)
			stage = tempfile.mkdtemp(prefix="warder-canal-provider-stage-", dir="/tmp")
			self._safeExtractZip(archive, stage)
			stage_root = os.path.join(stage, root)
			if os.path.islink(stage_root) or not os.path.isdir(stage_root):
				raise ValueError("Canal+ provider bundle ZIP root missing after extraction")
			members = sorted(name for name in os.listdir(stage_root) if name.lower().endswith(".png"))
			if members != sorted(expected_members) or any(os.path.islink(os.path.join(stage_root, name)) for name in members):
				raise ValueError("Canal+ provider bundle must contain exactly the SK and CZ PNGs")
			self.zzz = stage + os.sep
			updated, attempted = self.cprmFiles(root)
			if attempted != len(expected_members) or updated != len(expected_members):
				raise ValueError("Canal+ SK/CZ provider logos could not be installed")
			base = os.path.realpath(str(config.plugins.setupGlass17.par39.value))
			for folder in ("piconProv", "piconProv_220x132"):
				directory = os.path.join(base, folder)
				if os.path.islink(directory) or not os.path.isdir(directory):
					continue
				for name in os.listdir(directory):
					if name.lower() != "skylink.png":
						continue
					path = os.path.join(directory, name)
					if not os.path.islink(path) and os.path.isfile(path):
						os.unlink(path)
		finally:
			self.zzz = previous_zzz
			if archive:
				try:
					os.unlink(archive)
				except OSError:
					pass
			if stage:
				try:
					shutil.rmtree(stage)
				except OSError:
					pass

	def _warderRunAuxiliaryComposite(self, row, variant_id):
	    from .warderCanonicalPicons import install
	    return install(self, row, variant_id, getWarderAssets, _)

	def _warderRemoveStaleChannelPicons(self, destination, positions, package_names):
		"""Remove only stale service PNGs for selected orbits after package success."""
		destination = warderPiconSync.validate_destination(destination)
		if not destination or os.path.islink(destination) or not os.path.isdir(destination):
			raise ValueError(_("Invalid picon destination"))
		try:
			names = os.listdir(destination)
		except OSError as err:
			raise ValueError(_("Cannot read picon destination") + ": " + str(err))
		stale = warderPiconSync.plan_stale_position_picons(names, positions, package_names)
		for name in stale:
			if name.startswith("4115_"):continue
			path = os.path.join(destination, name)
			if os.path.basename(path) != name or os.path.islink(path) or not os.path.isfile(path):
				continue
			try:
				os.unlink(path)
			except OSError as err:
				raise ValueError(_("Could not remove stale selected-position picon") + ": " + str(err))
		return len(stale)

	def _recordWarderOperationResult(self, text):
		if not text:
			return
		value = str(text)
		is_partial = _("PARTIAL SUCCESS") + ":" in value
		if (_("ERROR") + ":") in value or is_partial:
			self.warderOperationFailed = True
			if is_partial:
				self.warderOperationSucceeded = True
			row = getattr(self, "warderCurrentActionRow", None)
			if row:
				self.warderFailedRows.add(row)
				if row == "wp-res":
					self.warderLargeSelectionPending = True
				for index in self.menuListAll:
					if self.menuListAll[index][0] == row:
						self.menuListAll[index][4] = "d"
					break
		elif (_("SUCCESSFUL") + ":") in value:
			self.warderOperationSucceeded = True
		self.warderCurrentActionRow = None

	def resetWarderWorkingState(self):
		"""Clear only in-memory download choices after the entire run succeeds."""
		self.warderPiconPrefs = warderPiconSync.preferences_after_task(self.warderPiconPrefs, "success")
		self.warderDABOnly = False
		self.warderDABPending = False
		self.warderDABTaskSnapshot = None
		self.warderChannelTaskSnapshot = None
		self.warderPositionSelectionAttempted = False
		self.warderLargeSelectionPending = False
		self.warderAuxChoiceRow = None
		for index in self.menuListAll:
			row = self.menuListAll[index][0]
			if row in self.warderPiconRows:
				self.menuListAll[index][4] = "x"
			elif row in self.warderAuxRows:
				self.menuListAll[index][4] = "x"
				self.menuListAll[index][2] = {"aux-prov":"piconProv", "aux-sat":"piconSat", "aux-cam":"piconCam", "aux-weather":"piconWeather"}[row]
				self.menuListAll[index][1] = {
					"aux-prov": _("Provider logos"), "aux-sat": _("Satellite logos"),
					"aux-cam": _("CAM picons"), "aux-weather": _("Weather picons"),
				}[row]
		self.createList()
		self.reactivate()


	def _warderDABStart(self):
		self.dwnJob = warderRadio.label(self.warderDABTaskSnapshot or {}, _)
		self.type_download = "DAB"
		self.warderCurrentActionRow = "wp-pos"
		try:
			self.warderDABWorker = warderRadio.Worker(self.warderDABTaskSnapshot)
			self.warderDABTimer = eTimer()
			try:
				self.warderDABTimerConnection = self.warderDABTimer.timeout.connect(self._warderDABPoll)
			except AttributeError:
				self.warderDABTimer.timeout.get().append(self._warderDABPoll)
			self.warderDABTimer.start(150, False)
			self.warderDABWorker.start()
		except Exception as error:
			self.warderPiconPrefs = dict(self.warderDABTaskSnapshot or self.warderPiconPrefs)
			self.dwnLoop(_("ERROR") + ": " + self.dwnJob + ": " + str(error))

	def _warderDABPoll(self):
		worker = self.warderDABWorker
		if worker is None:return
		for kind,value in worker.drain():
			if kind == "event":
				if value[0] == "download":
					percent = int(100 * value[2] / max(1,value[3]))
					self["dwn"].setText(self.dwnJob + ": %d%%" % percent)
				elif value[0] == "stage":self["dwn"].setText(value[1])
			else:
				self.warderDABTimer.stop()
				self.warderDABWorker = None
				if kind == "done":
					count = value["added"] + value["changed"]
					self.dwnLoop(_("SUCCESSFUL") + ": " + warderPiconSync.success_summary(count, None, _))
				else:
					self.warderPiconPrefs = dict(self.warderDABTaskSnapshot or self.warderPiconPrefs)
					self.dwnLoop(_("ERROR") + ": " + self.dwnJob + ": " + str(value))
				return

	def _warderDABCleanup(self):
		if self.warderDABWorker is not None:self.warderDABWorker.cancel.set()
		if self.warderDABTimer is not None:self.warderDABTimer.stop()

	def _warderRunChannelQueue(self):
		self.warderChannelState = "running"
		queue = getattr(self, "warderChannelQueue", None)
		if queue is None:
			self.warderChannelTaskSnapshot = dict(self.warderPiconPrefs)
			queue = warderPiconSync.build_runtime_queue(self.warderPiconPrefs, publication=warderPiconSync.runtime_publication())
			if queue.get("state") != warderPiconSync.READY:
				raise ValueError("Warder channel publication is locked")
			destination = warderPiconSync.validate_destination(queue.get("destination"))
			if not destination:
				raise ValueError("invalid Warder picon destination")
			os.makedirs(destination, exist_ok=True)
			destination = warderPiconSync.validate_destination(destination)
			if not destination or os.path.islink(destination) or not os.path.isdir(destination):
				raise ValueError("unsafe Warder picon destination")
			queue["destination"] = destination
			document = self._warderLoadChannelManifest(queue.get("manifest_url"))
			plan = warderPiconSync.plan_runtime_packages(document, queue, queue.get("manifest_url"))
			jobs = warderPiconSync.build_download_jobs(document, plan, queue.get("manifest_url"))
			if jobs.get("state") not in ("ready", "partial"):
				raise ValueError("Warder channel package plan is not executable")
			if jobs.get("missing_selectors"):
				raise ValueError("missing Warder channel packages: " + ", ".join(jobs["missing_selectors"]))
			self.warderChannelQueue = queue
			self.warderChannelJobs = list(jobs.get("jobs", []))
			self.warderChannelInstalled = set()
			self.warderChannelAvailable = set()
			self.warderChannelPackageResults = [
				{"package_selector": job.get("selector_id"), "orbital_position": job.get("orbital_position"),
				 "family": job.get("family"), "updated": 0, "failures": 0}
				for job in self.warderChannelJobs
			]
			if not self.warderChannelJobs and not (queue.get("mode") in (warderPiconSync.UPDATE_MODE_SYNC_TV, warderPiconSync.UPDATE_MODE_SYNC_TV_RADIO) and not queue.get("services")):
				self.warderChannelQueue = None
				self.warderChannelState = "error"
				raise ValueError("Warder channel selection resolved to no packages")
			if queue.get("mode") in (warderPiconSync.UPDATE_MODE_SYNC_TV, warderPiconSync.UPDATE_MODE_SYNC_TV_RADIO) and not queue.get("services"):
				self.warderChannelQueue = None
				self.warderChannelState = "error"
				raise ValueError("no selected TV or radio bouquet services found for Warder selective sync")
		if not getattr(self, "warderChannelJobs", []):
			installed_set = getattr(self, "warderChannelInstalled", set())
			wanted = warderPiconSync.wanted_picon_names(queue)
			coverage = warderPiconSync.classify_requested_picons(
				wanted, getattr(self, "warderChannelAvailable", set()), installed_set)
			missing_files = sorted(coverage["missing"])
			for filename in missing_files:
				position = warderPiconSync.service_orbital_position(filename[:-4].replace("_", ":"))
				for item in self.warderChannelPackageResults:
					if item.get("orbital_position") == position:
						item["failures"] += 1
						break
			summary = warderPiconSync.package_result_summary(self.warderChannelPackageResults, _)
			if queue.get("mode") == warderPiconSync.UPDATE_MODE_REPLACE_ALL and not summary["failures"]:
				self._warderRemoveStaleChannelPicons(queue.get("destination"), queue.get("positions", []), getattr(self, "warderChannelAvailable", set()))
			self.warderChannelQueue = None
			self.warderChannelJobs = []
			self.warderChannelState = "done" if not summary["failures"] else ("partial" if summary["updated"] else "error")
			result = summary["status"] + ": " + summary["text"]
			self.warderChannelInstalled = set()
			return result
		job = self.warderChannelJobs.pop(0)
		self.warderChannelCurrentJob = job
		result_row = next((item for item in self.warderChannelPackageResults
			if item.get("package_selector") == job.get("selector_id") and item.get("family") == job.get("family")), None)
		archive = None
		try:
			required = int((int(job.get("bytes", 0)) * 2.2) / (1024 * 1024)) + 10
			try:
				free_mb = int(shutil.disk_usage("/tmp").free / (1024 * 1024))
			except OSError:
				free_mb = 0
			if free_mb < required:
				raise ValueError("insufficient temporary space for Warder channel package")
			destination = warderPiconSync.validate_destination(self.warderChannelQueue.get("destination"))
			if not destination or os.path.islink(destination) or not os.path.isdir(destination):
				raise ValueError("unsafe Warder picon destination")
			try:
				dest_free_mb = int(shutil.disk_usage(destination).free / (1024 * 1024))
			except OSError:
				dest_free_mb = 0
			if dest_free_mb < required:
				raise ValueError("insufficient destination space for Warder channel package")
			fd, archive = tempfile.mkstemp(prefix="warder-channel-", suffix=".zip", dir="/tmp")
			os.close(fd)
			self._warderFetchChannelJob(job, archive)
			wanted = warderPiconSync.wanted_picon_names(self.warderChannelQueue)
			installed, available = self._warderInstallChannelArchive(archive, self.warderChannelQueue["destination"], wanted)
			self.warderChannelInstalled.update(installed)
			self.warderChannelAvailable.update(available)
			if result_row is not None:
				result_row["updated"] = len(installed)
		except Exception as err:
			if result_row is not None:
				result_row["failures"] += 1
				result_row["error"] = str(err)
			print("FullHDGlass17 Warder package failed (%s/%s): %s" % (job.get("orbital_position"), job.get("selector_id"), err))
		finally:
			if archive:
				try:
					os.unlink(archive)
				except OSError:
					pass
		return None

	def dwnLoop(self, txt=""):
		if self.dwnTimer.isActive():
			self.dwnTimer.stop()
		if txt:
			self._recordWarderOperationResult(txt)
		if self.clrSelectsat:
			self.session.openWithCallback(self.dwnFin, historyScreen, _("Result"),txt)
		else:
			if txt != "":
				self.msg += ({False:"("+self.dwnJob + ") ",True:""}["icon_sets_preview" in self.type_download or self.type_download.isdigit()]) + txt + "\n"
			# A required helper is prepared before OLED/legacy archives in the same task.
			if not find_sevenzip(SEVENZIP):
				tool_row = next((row for row in self.menuListAll.values() if row[0] == "7z" and row[4] == "d" and row[0] not in self.warderFailedRows), None)
				if tool_row is not None:
					self.warderCurrentActionRow = "7z"
					tool_row[4] = "x"
					self.type_download = str(tool_row[2])
					self.zzz = self.setWdir()
					self.dwnJob = "7zip"
					self.downAnswerNow()
					return
			if (self.warderPiconPrefs.get("prepared") and not self.warderDABOnly
					and warderPiconSync.channel_delivery_backend(self.warderPiconPrefs.get("resolution"), self.warderPiconPrefs.get("style")) == "pinned-legacy"
					and self.warderLegacyChannelQueue):
				self.dwnJob = _("Channel picons")
				resolution = self.warderPiconPrefs.get("resolution")
				folder = warderPiconSync.legacy_channel_destination(resolution)
				self.enaSelectsat = True
				self.type_download = "legacy-channel-" + str(resolution)
				self.zzz = self.setWdir()
				self.warderLegacyChannelFailures = 0
				self.warderLegacyArchivesProcessed = 0
				legacy_queue = list(self.warderLegacyChannelQueue)
				archive_count = len(legacy_queue)
				self.warderLegacyProcessedPositions = set()
				self.warderLegacyCurrentPackageLabel = None
				self.warderLegacyPackageResults = [
					{"selector_id": str(selector_id),
					 "orbital_position": warderPiconSync.canonical_position_for_selector(str(selector_id)),
					 "updated": 0, "failures": 0, "processed": False}
					for selector_id, archive_id in legacy_queue
				]
				legacy_destination = self.warderLegacyPiconDestination
				legacy_result = self.downMulti(self.warderLegacyChannelQueue, folder, False)
				if self.warderLegacyArchivesProcessed < archive_count:
					self.warderLegacyChannelFailures += archive_count - self.warderLegacyArchivesProcessed
				self.enaSelectsat = False
				self.warderLegacyChannelQueue = None
				self.warderLegacyPiconDestination = None
				coverage = warderPiconSync.classify_requested_picons(
					self.warderLegacyChannelWanted,
					self.warderLegacyChannelAvailable,
					self.warderLegacyChannelInstalled)
				missing_by_position = {}
				for filename in coverage["missing"]:
					position = warderPiconSync.service_orbital_position(filename[:-4].replace("_", ":"))
					missing_by_position[position] = missing_by_position.get(position, 0) + 1
				package_results = []
				for item in getattr(self, "warderLegacyPackageResults", []):
					position = item.get("orbital_position")
					item["failures"] += missing_by_position.pop(position, 0) if position else 0
					if position and not item.get("processed"):
						item["failures"] += 1
					package_results.append(item)
				for position, failures in missing_by_position.items():
					package_results.append({"selector_id": "unbound", "orbital_position": position,
						"updated": 0, "failures": failures})
				if self.warderPiconPrefs.get("update_mode") == warderPiconSync.UPDATE_MODE_REPLACE_ALL and not self.warderLegacyChannelFailures:
					try:
						self._warderRemoveStaleChannelPicons(legacy_destination, self.warderPiconPrefs.get("positions", []), self.warderLegacyChannelAvailable)
					except Exception:
						if package_results:
							package_results[0]["failures"] += 1
				summary = warderPiconSync.package_result_summary(package_results, _)
				self.warderChannelState = "done" if not summary["failures"] else ("partial" if summary["updated"] else "error")
				result_text = summary["status"] + ": " + summary["text"]
				self.msg += "(" + self.dwnJob + ") " + result_text + "\n"
				self._recordWarderOperationResult(result_text)
			if (self.warderPiconPrefs.get("prepared") and not self.warderDABOnly
					and warderPiconSync.channel_delivery_backend(self.warderPiconPrefs.get("resolution"), self.warderPiconPrefs.get("style")) == "warder"
					and self.warderChannelState not in ("locked", "error", "done", "partial")):
				self.dwnJob = _("Warder channel picons")
				try:
					warder_result = self._warderRunChannelQueue()
				except Exception as err:
					self.warderChannelState = "error"
					snapshot = getattr(self, "warderChannelTaskSnapshot", None)
					if snapshot is not None:
						self.warderPiconPrefs = warderPiconSync.preferences_after_task(snapshot, "error")
					self.warderChannelTaskSnapshot = None
					self.warderChannelQueue = None
					self.warderChannelJobs = []
					self.warderChannelInstalled = set()
					self.warderChannelAvailable = set()
					self.warderOperationFailed = True
					self.warderFailedRows.add("wp-pos")
					if str(err) == "no-satellite-position-selected":
						error_text = _("Select at least one satellite position.")
					else:
						error_text = str(err)
					self.msg += "(" + self.dwnJob + ") " + _("ERROR") + ": " + error_text + "\n"
				else:
					if warder_result is None:
						# One package per GUI timer tick keeps the receiver event loop responsive.
						self.dwnTimer.start(25, True)
						return
					self.msg += "(" + self.dwnJob + ") " + warder_result + "\n"
					self._recordWarderOperationResult(warder_result)
			if self.warderDABPending:
				self.warderDABPending = False
				self._warderDABStart()
				return
			if self.warderLargeSelectionPending:
				self.warderLargeSelectionPending = False
				self.warderCurrentActionRow = "wp-res"
				for row_index in self.menuListAll:
					if self.menuListAll[row_index][0] == "wp-res":
						self.menuListAll[row_index][4] = "x"
				self.type_download = "CHSPiconbig"
				self.zzz = self.setWdir()
				self.dwnJob = _("Large channel selection icons (710 x 682)")
				self.downAnswerNow()
				return
			ena = True
			self.enaSelectsat = False
			for x in self.menuListAll:
				if self.menuListAll[x][4] == "d" and self.menuListAll[x][0] not in self.warderPiconRows and self.menuListAll[x][0] not in self.warderFailedRows:
					ena = False
					self.warderCurrentActionRow = self.menuListAll[x][0]
					self.menuListAll[x][4] = 'x'
					self.type_download = str(self.menuListAll[x][2])
					self.zzz = self.setWdir()
					self.dwnJob = str(self.menuListAll[x][1])
					if self.menuListAll[x][0] in ("aux-prov", "aux-sat"):
						try:
							aux_result = self._warderRunAuxiliaryComposite(self.menuListAll[x][0], self.type_download)
						except Exception as err:
							aux_result = _("ERROR") + ": " + str(err)
						self.dwnLoop(aux_result)
						return
					elif '***' in self.menuListAll[x][1]:
						self.enaSelectsat = True
						self.downMulti(self.menuListAll[x][3],self.destDir(self.menuListAll[x][2]))
					else:
						self.downAnswerNow()
					break
			if ena:
				if self.warderOperationSucceeded and not self.warderOperationFailed:
					self.resetWarderWorkingState()
				self.session.openWithCallback(self.dwnFin, historyScreen, _("Result"),self.msg) 		
		
	def dwnFin(self, answer=""):
		if self.warderChannelState in ("done", "error", "locked"):
			self.warderChannelState = "idle"
		self.createList()
		self.ena = True
		self.clrSelectsat = False
		self.enaSelectsat = False
		self["dwn"].hide()
		self.instance.resize(eSize(1920,1080))
                  		
	def downAnswerNow(self):
		err, assets = getWarderAssets()
		if err != "":
			self.dwnLoop(_("ERROR")+": "+err)
			return
		asset = assets.get(self.type_download)
		if not asset:
			self.dwnLoop(_("ERROR")+": "+_("This download is not available in Warder repository yet.") + " [" + self.type_download + "]")
			return
		try:
			filename = str(asset["filename"])
			size_bytes = int(asset["size"])
			url = str(asset.get("url", ""))
			parts = asset.get("parts", [])
			sha256 = str(asset["sha256"]).lower()
			root = str(asset["root"])
		except Exception:
			self.dwnLoop(_("ERROR")+": "+_("Invalid Warder download catalog entry."))
			return
		source_id = asset.get("publication_source_id", "fullhd-production")
		valid_parts = isinstance(parts, list) and len(parts) > 0 and all(warderPiconSync.trusted_auxiliary_url(str(x), source_id) for x in parts)
		valid_sha = re.match(r"^[0-9a-f]{64}$", sha256) is not None
		valid_filename = bool(filename) and os.path.basename(filename) == filename and filename not in (".", "..")
		valid_url = (not url) or warderPiconSync.trusted_auxiliary_url(url, source_id)
		if (not valid_url or (not url and not valid_parts)) or not valid_sha or not valid_filename or "/" in root or "\\" in root or ".." in root:
			self.dwnLoop(_("ERROR")+": "+_("Unsafe Warder download catalog entry."))
			return
		self.warderAsset = asset
		# Keep the original conservative free-space calculation.
		size = int(round(1.0 * size_bytes/(1024*1024))*2.2+10)
		ret, ret1 = self.getFreeSpace()
		if ret > size and ret1 > (size/2):
			self.downloadPicons(filename)
			return
		msg = "%s(%s/%s)MB:\n%s - %s/%s, %s - %s/%s" % (_("Sorry, too low free space"),_("Required"),_("Free"),config.plugins.setupGlass17.par39.value,size/2,ret1,self.zzz[:-1],size,ret)
		self.dwnLoop(_("ERROR")+": "+str(msg))

	def _safeExtractZip(self, archive, destination):
		"""Extract a ZIP without path traversal or archive-created symlinks."""
		dest = os.path.realpath(destination)
		with zipfile.ZipFile(archive, "r") as zf:
			for info in zf.infolist():
				name = info.filename.replace("\\", "/")
				if not name or name.startswith("/") or name.startswith("../") or "/../" in ("/" + name):
					raise ValueError("unsafe ZIP path")
				mode = (info.external_attr >> 16) & 0xFFFF
				if stat.S_ISLNK(mode):
					raise ValueError("ZIP symlink entry rejected")
				target = os.path.realpath(os.path.join(dest, name))
				if target != dest and not target.startswith(dest + os.sep):
					raise ValueError("ZIP path traversal rejected")
			for info in zf.infolist():
				zf.extract(info, dest)

	def rmTmp(self):
		shutil.rmtree("/tmp/more_icons", ignore_errors=True)

	def rmTmp2(self,a,b):
		path = os.path.realpath(os.path.join(a, b))
		base = os.path.realpath(a)
		if path != base and path.startswith(base + os.sep):
			shutil.rmtree(path, ignore_errors=True)
				
	def downloadPicons(self, what):
		state = False
		target = self.zzz + what
		asset = getattr(self, "warderAsset", {})
		try:
			expected = str(asset["sha256"]).lower()
			parts = asset.get("parts", [])
			urls = [str(x) for x in parts] if isinstance(parts, list) and parts else [str(asset["url"])]
			source_id = asset.get("publication_source_id", "fullhd-production")
			if re.match(r"^[0-9a-f]{64}$", expected) is None or not urls or not all(warderPiconSync.trusted_auxiliary_url(url, source_id) for url in urls):
				raise ValueError("unsafe asset metadata")
			h = hashlib.sha256()
			with open(target, "wb") as out:
				for url in urls:
					req = Request(url, headers={"User-Agent": "FullHDGlass17-Warder-Evolution/1.0.5-test1"})
					with urlopen(req, timeout=45) as response:
						if not warderPiconSync.trusted_auxiliary_url(str(response.geturl()), source_id):
							raise ValueError("unsafe asset redirect")
						while True:
							chunk = response.read(1024 * 128)
							if not chunk:
								break
							out.write(chunk)
							h.update(chunk)
			if h.hexdigest().lower() != expected:
				raise ValueError("SHA-256 mismatch")
			state = True
		except Exception as err:
			try:
				if os.path.isfile(target):
					os.remove(target)
			except:
				pass
			state = False
		if state:
			if os.path.exists(("/tmp/more_icons")):
				self.rmTmp()
			root = str(asset.get("root", what[:-4]))
			if os.path.exists(self.zzz + root):
				self.rmTmp2(self.zzz, root)
			try:
				self._safeExtractZip(target, self.zzz[:-1])
			except Exception:
				try:
					os.remove(target)
				except OSError:
					pass
				if os.path.exists(self.zzz + root):
					self.rmTmp2(self.zzz, root)
				self.dwnLoop(_("ERROR")+": "+"Unzip " + what + " " + _("failed"))
				return
			try:
				os.remove(target)
			except OSError:
				pass
			if not os.path.exists(self.zzz + root):
				self.dwnLoop(_("ERROR")+": "+"Unzip " + what + " " + _("failed"))
				return
			if "7z" in self.type_download:
				# Original archive extracts to /tmp/7z/7z_g.
				try:
					os.makedirs(os.path.dirname(SEVENZIP), exist_ok=True)
					shutil.copy2(os.path.join(self.zzz, root, "7z_g"), SEVENZIP)
					os.chmod(SEVENZIP, 0o755)
				except OSError:
					pass
				self.rmTmp2(self.zzz, root)
				numPict = 0
				if find_sevenzip(SEVENZIP):
					numPict = 1
				total = 1
			elif "icon_sets_preview" in self.type_download:
				self.iconPreviewManage()
				return
			elif self.type_download in ['animWeatherIcons',"weatherIconsN","extraScreens","menuicons"]:
				numPict = 0
				total = 0
				if "animWeatherIcons" in self.type_download:
					rng = 48
					typeGrf = "animIconWeather"
				else:
					rng = MAXSCREENS
					typeGrf = "extraScreens17"
					if not "extraScreens" in self.type_download:
						rng = MAXICONS
						typeGrf = "menuIcons"
						if "weatherIconsN" in self.type_download:
							typeGrf = "weatherIcons"
				for i in range(1,rng):
					subPath = "%s/%s" % (typeGrf, i)
					if os.path.exists(("/tmp/%s" % subPath)):
						if not os.path.exists((config.plugins.setupGlass17.par39.value + "/" + subPath)):
							os.makedirs(config.plugins.setupGlass17.par39.value + "/" + subPath, exist_ok=True)
						x1, x2 = self.cprmFiles(subPath)
						numPict += x1
						total += x2
				try:
					os.rmdir("/tmp/%s" % typeGrf)
				except OSError:
					pass
			else:
				numPict, total = self.cprmFiles(root)
			if numPict-total == 0:
				self.dwnLoop(_("SUCCESSFUL")+": "+warderPiconSync.success_summary(total, None, _))
			else:
				self.dwnLoop(_("ERROR")+": " + what[:-4] + ", " + (_("%d of %d picons failed to install") % (total-numPict, total)))
		else:
			self.dwnLoop(_("ERROR")+": " + what[:-4])

	def _warderFetchChannelJob(self, job, archive):
		"""Reassemble a package only from the root bound to its source manifest."""
		source_id = job.get("publication_source_id")
		source = warderPiconSync.publication_source(source_id)
		if source is None or job.get("publication_root") != source.get("package_root"):
			raise ValueError("untrusted Warder channel publication source")
		full_hash = hashlib.sha256()
		total = 0
		with open(archive, "wb") as out:
			for part in job.get("parts", []):
				url = str(part.get("url", ""))
				if not warderPiconSync.trusted_publication_url(url, source_id):
					raise ValueError("unsafe Warder channel URL")
				part_hash = hashlib.sha256()
				part_size = 0
				req = Request(url, headers={"User-Agent": "FullHDGlass17-Warder-Evolution/channel-picons"})
				with urlopen(req, timeout=45) as response:
					if not warderPiconSync.trusted_publication_url(str(response.geturl()), source_id):
						raise ValueError("unsafe Warder channel redirect")
					expected_part = int(part.get("bytes", -1))
					if expected_part < 1 or expected_part > 20 * 1024 * 1024:
						raise ValueError("invalid Warder channel part size")
					while True:
						chunk = response.read(1024 * 128)
						if not chunk:
							break
						part_size += len(chunk)
						total += len(chunk)
						if part_size > expected_part or total > int(job.get("bytes", -1)):
							raise ValueError("oversized Warder channel download")
						out.write(chunk)
						full_hash.update(chunk)
						part_hash.update(chunk)
				if part_size != int(part.get("bytes", -1)) or part_hash.hexdigest().lower() != str(part.get("sha256", "")).lower():
					raise ValueError("Warder channel part integrity mismatch")
		if total != int(job.get("bytes", -1)) or full_hash.hexdigest().lower() != str(job.get("sha256", "")).lower():
			raise ValueError("Warder channel package integrity mismatch")

	def _warderInstallChannelArchive(self, archive, destination, wanted=None):
		"""No-delete install: validate ZIP and atomically replace only selected PNG files."""
		dest = warderPiconSync.validate_destination(destination)
		if not dest:
			raise ValueError("invalid Warder picon destination")
		os.makedirs(dest, exist_ok=True)
		installed = set()
		available = set()
		with zipfile.ZipFile(archive, "r") as zf:
			entries = []
			seen = set()
			for info in zf.infolist():
				if info.filename.endswith("/"):
					continue
				if info.file_size < 1 or info.file_size > 16 * 1024 * 1024:
					raise ValueError("unsafe Warder picon PNG size")
				if info.compress_size > 0 and info.file_size > info.compress_size * 250:
					raise ValueError("unsafe Warder picon ZIP compression ratio")
				if not warderPiconSync.safe_archive_member(info.filename):
					raise ValueError("unsafe Warder picon ZIP path")
				mode = (info.external_attr >> 16) & 0xFFFF
				if stat.S_ISLNK(mode):
					raise ValueError("Warder picon ZIP symlink rejected")
				name = info.filename.replace("\\", "/").rsplit("/", 1)[-1]
				if not name.lower().endswith(".png") or os.path.basename(name) != name:
					raise ValueError("unexpected Warder channel archive member")
				if name in seen:
					raise ValueError("duplicate Warder picon archive member")
				seen.add(name)
				available.add(name)
				if wanted is None or name in wanted:
					entries.append((info, name))
			for info, name in entries:
				fd, tmp = tempfile.mkstemp(prefix=".warder-picon-", suffix=".tmp", dir=dest)
				try:
					with os.fdopen(fd, "wb") as out:
						with zf.open(info, "r") as src:
							signature = src.read(8)
							if signature != b"\x89PNG\r\n\x1a\n":
								raise ValueError("invalid Warder picon PNG signature")
							out.write(signature)
							shutil.copyfileobj(src, out, 1024 * 128)
						out.flush()
						os.fsync(out.fileno())
					os.replace(tmp, os.path.join(dest, name))
					installed.add(name)
				finally:
					if os.path.exists(tmp):
						os.unlink(tmp)
		return installed, available

	def _legacyPiconArchiveUrl(self, legacy_id):
		"""Resolve one preserved legacy numeric ID without guessing or retired-host fallback."""
		try:
			if not hasattr(self, "_warderLegacyPiconArchives"):
				catalog_path = os.path.join(PLUGINPATH, "legacyPiconArchives.json")
				with open(catalog_path, "r", encoding="utf-8") as handle:
					catalog = json.load(handle)
				valid = (
					catalog.get("schema") == 1 and
					catalog.get("mapped") == 370 and
					catalog.get("unmapped") == 29 and
					catalog.get("source", {}).get("commit") == "9cdda4ab414e7d50a97ca9285db8ebbb75fba615" and
					catalog.get("policy", {}).get("guess_missing") is False and
					catalog.get("policy", {}).get("picon_cz_fallback") is False
				)
				self._warderLegacyPiconArchives = catalog.get("archives", {}) if valid else {}
			entry = self._warderLegacyPiconArchives.get(str(legacy_id), {})
			url = str(entry.get("url", ""))
			filename = str(entry.get("filename", ""))
			official = "https://raw.githubusercontent.com/Evolution-by-Warder/Trezor/9cdda4ab414e7d50a97ca9285db8ebbb75fba615/archives/chocholousek-picons/originals/"
			if filename and "/" not in filename and "\\" not in filename and ".." not in filename and filename.endswith(".7z") and url == official + filename:
				return url
		except Exception:
			self._warderLegacyPiconArchives = {}
		return ""

	def downMulti(self, k, Ddir, continue_loop=True):
		tmp = ""
		if internet():
			if ENAFINDER:
				for x in range(0,len(k)):
					self.warderLegacyCurrentPackageLabel = k[x][0] if getattr(self, "warderLegacyPiconDestination", None) else None
					self.warderLegacyCurrentPackageResult = (self.warderLegacyPackageResults[x]
						if getattr(self, "warderLegacyPiconDestination", None) and x < len(self.warderLegacyPackageResults) else None)
					archive = "/tmp/a.7z"
					extract_dir = os.path.realpath(os.path.join("/tmp", Ddir))
					if not (extract_dir == "/tmp" or extract_dir.startswith("/tmp/")):
						tmp += _("ERROR")+": ("+Ddir+ ") "+_("Invalid extraction path")+"\n"
						continue
					try:
						os.remove(archive)
					except OSError:
						pass
					shutil.rmtree(extract_dir, ignore_errors=True)
					url = self._legacyPiconArchiveUrl(k[x][1])
					if not url:
						tmp += _("ERROR")+": ("+Ddir+ ") "+k[x][0]+", "+_("Preserved legacy archive is not available in Warder migration catalogue")+" ["+str(k[x][1])+"]\n"
						continue
					headers = {'User-Agent':'FHDG17-Warder'}
					try:
						cookie_jar = cookielib.CookieJar()
						opener = build_opener(HTTPCookieProcessor(cookie_jar))
						req = Request(url, data=None, headers=headers)
						with opener.open(req, timeout=15) as handler, open(archive, 'wb') as f:
							while True:
								chunk = handler.read(1024 * 128)
								if not chunk:
									break
								f.write(chunk)
					except Exception:
						try:
							os.remove(archive)
						except OSError:
							pass
					if os.path.isfile(archive):
						size = 1.0*os.path.getsize(archive)/(1024*1024)
						if size != 0:
							ret, ret1 = self.getFreeSpace()
							if ret > size and ret1 > (size/2):
								os.makedirs(extract_dir, exist_ok=True)
								cmd = [find_sevenzip(SEVENZIP) or SEVENZIP, "e", "-y", "-o%s" % extract_dir, archive]
								try:
									extract_ok = subprocess.call(cmd) == 0
								except (OSError, ValueError):
									extract_ok = False
								try:
									os.remove(archive)
								except OSError:
									pass
								if not extract_ok:
									shutil.rmtree(extract_dir, ignore_errors=True)
									tmp += _("ERROR")+": ("+Ddir+ ") "+_("Archive extraction failed")+"\n"
									continue
								available_before = len(getattr(self, "warderLegacyChannelAvailable", set()))
								numPict, total = self.cprmFiles(Ddir)
								if getattr(self, "warderLegacyPiconDestination", None) and len(self.warderLegacyChannelAvailable) <= available_before:
									self.warderLegacyChannelFailures += 1
								if total == 0:
									tmp += _("ERROR")+": ("+Ddir+ ") "+k[x][0]+", "+_("No picons were downloaded.")+"\n"
								elif numPict-total == 0:
									tmp += _("SUCCESSFUL")+": ("+Ddir+ ") "+k[x][0]+", "+warderPiconSync.success_summary(total, None, _)+"\n"
								else:
									tmp += _("ERROR")+": ("+Ddir+ ") "+k[x][0]+", " + (_("%d of %d picons failed to install") % (total-numPict, total))+"\n"
							else:
								tmp += _("ERROR")+": ("+Ddir+ ") "+k[x][0]+", "+ "%s(%s/%s)MB:\n%s - %s/%s, %s - %s/%s" % (_("Sorry, too low free space"),_("Required"),_("Free"),config.plugins.setupGlass17.par39.value,size/2,ret1,self.zzz[:-1],size,ret)+"\n"
						else:
							tmp += _("ERROR")+": ("+Ddir+ ") "+k[x][0]+", "+_("Error while downloading file!") + " " + _("No picons were downloaded.")+"\n"
							try:
								os.remove(archive)
							except OSError:
								pass
					else:
						tmp += _("ERROR")+": ("+Ddir+ ") "+k[x][0]+", "+_("Error while downloading file!")+"\n"
			else:
				tmp += _("ERROR")+": "+_("Loading URL tools failed")+"\n"
		else:
			tmp += _("ERROR")+": "+_("Internet connection failed")+"\n"
		if tmp != "":
			if continue_loop:
				self.dwnLoop(tmp[:-1])
			return tmp[:-1]
		message = _("ERROR")+": "+_("Unknown error detected, try again!!!")
		if continue_loop:
			self.dwnLoop(message)
		return message

	def cprmFiles(self, what):
		f = listDir(self.zzz + what)
		numPict = 0
		total = 0
		legacy_destination = getattr(self, "warderLegacyPiconDestination", None)
		if legacy_destination:
			legacy_destination = warderPiconSync.validate_destination(legacy_destination)
			if not legacy_destination or os.path.islink(legacy_destination):
				self.warderLegacyChannelFailures += 1
				self.rmTmp2(self.zzz, what)
				return 0, 0
			os.makedirs(legacy_destination, exist_ok=True)
			wanted = self.warderLegacyChannelWanted
			available_before = len(self.warderLegacyChannelAvailable)
			current_result = getattr(self, "warderLegacyCurrentPackageResult", None)
			if current_result is not None:
				current_result["processed"] = True
			for name in f or []:
				if not str(name).lower().endswith(".png"):
					continue
				self.warderLegacyChannelAvailable.add(name)
				if wanted is not None and name not in wanted:
					continue
				source = os.path.join(self.zzz, what, name)
				destination = os.path.join(legacy_destination, name)
				if os.path.islink(destination):
					self.warderLegacyChannelFailures += 1
					if current_result is not None:
						current_result["failures"] += 1
					continue
				try:
					shutil.copy2(source, destination)
				except OSError:
					self.warderLegacyChannelFailures += 1
					if current_result is not None:
						current_result["failures"] += 1
					total += 1
					continue
				total += 1
				if os.path.isfile(destination) and not os.path.islink(destination):
					numPict += 1
					self.warderLegacyChannelInstalled.add(name)
					if current_result is not None:
						current_result["updated"] += 1
			if len(self.warderLegacyChannelAvailable) <= available_before:
				self.warderLegacyChannelFailures += 1
			self.warderLegacyArchivesProcessed += 1
			self.rmTmp2(self.zzz, what)
			return numPict, total
		destDir = what
		if f:
			for x in f:
				if not str(x).lower().endswith(".png"):
					continue
				source = os.path.join(self.zzz, what, x)
				if not os.path.isfile(source) or os.path.islink(source):
					continue
				destination = os.path.join(config.plugins.setupGlass17.par39.value, destDir, x)
				total += 1
				try:
					if os.path.islink(destination):
						raise OSError("destination is a symbolic link")
					shutil.copy2(source, destination)
				except OSError:
					continue
				if (os.path.isfile(destination) and not os.path.islink(destination)
						and self._warderFilesMatch(source, destination)):
					numPict += 1
		self.rmTmp2(self.zzz, what)
		return numPict, total

	def _warderFilesMatch(self, source, destination):
		# Compare the bytes copied during this task; a stale same-name file cannot
		# turn a failed copy into a reported success.
		try:
			return (os.path.getsize(source) == os.path.getsize(destination)
				and self._warderSha256(source) == self._warderSha256(destination))
		except OSError:
			return False

	def _warderSha256(self, path):
		digest = hashlib.sha256()
		with open(path, "rb") as stream:
			for chunk in iter(lambda: stream.read(1024 * 1024), b""):
				digest.update(chunk)
		return digest.hexdigest()

	def chck(self, s):
		try:
			i = s.split("_")   
			i = i[len(i)-4]   
			if len(i) in (5,6,7,8):
				i = i[0:len(i)-4]
				for tt in self.answer:
					if i.lower() == tt.lower():				
						return True
		except: pass
		return False 

	def iconPreviewManage(self):
		tmp = ""
		path = config.plugins.setupGlass17.par39.value
		if not os.path.exists((path+"/more_icons/scr_prew")):
			os.makedirs(path + "/more_icons/scr_prew", exist_ok=True)
		numPict = 0
		total = 0
		for i in range(1,MAXSCREENS):
			if fileExists(("/tmp/more_icons/scr_prew/screen-"+str(i)+".png")):
				shutil.copy2("/tmp/more_icons/scr_prew/screen-" + str(i) + ".png", path + "/more_icons/scr_prew/screen-" + str(i) + ".png")
				total += 1
				if fileExists((path+"/more_icons/scr_prew/screen-"+str(i)+".png")):
					numPict += 1
		if total != 0:
			if numPict-total == 0:
				tmp = _("SUCCESSFUL")+": "+_("Previews downloaded successfully!") + "\n"
			else:
				tmp = _("ERROR")+": "+_("Previews:") + " " + str(total-numPict) + " " + _("file(s) from") + " " + str(total) + "\n"
		global allIcons
		for i in range(1,MAXICONS):
			if os.path.exists(("/tmp/more_icons/i_type-"+str(i))):
				if not os.path.exists((path+"/more_icons/i_type-"+str(i))):
					os.makedirs(path + "/more_icons/i_type-"+str(i), exist_ok=True)
				for tt in allIcons:
					shutil.copy2("/tmp/more_icons/i_type-" + str(i) + "/" + tt + ".png", path + "/more_icons/i_type-" + str(i) + "/" + tt + ".png")
				shutil.rmtree("/tmp/more_icons/i_type-"+str(i), ignore_errors=True)
				shutil.copy2("/tmp/more_icons/scr_prew/icons-" + str(i) + ".png", path + "/more_icons/scr_prew/icons-" + str(i) + ".png")
				if checkIcons(i):
					tmp += _("SUCCESSFUL")+": "+_("Icons type") + " " + str(i) + "\n"
				else:
					tmp += _("ERROR")+": "+_("Icons type") + " " + str(i) + "\n"				
		self.rmTmp()
		if tmp != "":
			self.dwnLoop(tmp[:-1])
		else:
			self.dwnLoop(_("ERROR")+": "+_("Unknown error detected, try again!!!")) 	
##########################################################################################################################
class satSelectorScr(Screen): 
	skin = """
<screen name="satSelectorScr" position="0,0" size="1920,1080" title="Select" backgroundColor="#ff000000" flags="wfNoBorder">
			<widget position="0,0" size="1920,164" source="global.CurrentTime" render="WarderSettingsHeader" zPosition="-3" /><eLabel position="424,164" size="1071,855" backgroundColor="#1a102136" zPosition="-1" /><eLabel position="1493,164" size="2,855" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="424,164" size="2,855" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="424,1017" size="1071,2" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="424,164" size="1071,2" backgroundColor="#003ee8ff" zPosition="1" /><widget name="list" position="439,169" scrollbarMode="showOnDemand" size="1040,780" foregroundColor="#00ffffff" backgroundColor="#ff000000" transparent="1" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" zPosition="4" scrollbarBackgroundColor="#00102136" scrollbarForegroundColor="#003ee8ff" />
	<widget name="key_red" position="444,969" size="333,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#00ff526a" backgroundColor="#ff000000" noWrap="1" />
	<widget name="key_green" position="793,969" size="333,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#0039ff59" backgroundColor="#ff000000" noWrap="1" />
	<widget name="key_yellow" position="1142,969" size="333,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#00f5d54e" backgroundColor="#ff000000" noWrap="1" />
   <eLabel position="444,963" size="333,2" backgroundColor="#00ff526a" zPosition="1" /><eLabel position="793,963" size="333,2" backgroundColor="#0039ff59" zPosition="1" /><eLabel position="1142,963" size="333,2" backgroundColor="#00f5d54e" zPosition="1" /><widget position="1120,25" size="250,36" font="Regular;25" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%A</convert></widget><widget position="1020,70" size="350,36" font="Regular;24" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%d. %B %Y</convert></widget><widget position="1398,32" size="190,85" font="Regular;62" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Default</convert></widget><widget position="1590,58" size="66,54" font="Regular;38" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="left" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format::%S</convert></widget><eLabel position="1680,25" size="210,36" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="Version:" /><eLabel position="1680,70" size="210,36" font="Regular;24" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="1.0.35" /><eLabel position="1392,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><eLabel position="1664,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><widget position="850,120" size="700,38" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="Title" render="Label" /><eLabel position="0,164" size="424,855" backgroundColor="#00071627" zPosition="-2" /><eLabel position="1495,164" size="425,855" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,1019" size="1920,61" backgroundColor="#00071627" zPosition="-2" /></screen>
"""

	def __init__(self, session, delP = 1):
		Screen.__init__(self, session)
		self.delP = delP		
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Select"))
		self["key_yellow"] = Label(_("Save"))
		self.list = SelectionList()
		self["list"] = self.list
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], 
		{
			"ok": self.list.toggleSelection, 
			"cancel": self.exit,
			"red": self.exit,
			"yellow": self.finishSelect,
			"green": self.list.toggleSelection
		}, -1)
		self.onLayoutFinish.append(self.startSelect)
		
	def startSelect(self):		
		for x in range(0, len(SATLIST)):
			if SATLIST[x][self.delP] != "": 
				p = config.plugins.setupGlass17.par39.value+"/piconSat/"+SATLIST[x][2]+"-75.png"
				if not os.path.isfile(p): 
					p = SKINPATH+"icons/75.png"
				self.list.addSelection(SATLIST[x][0], (SATLIST[x][0],SATLIST[x][self.delP]), x, False, p)    

	def downAnswerNow(self, answer):
		if answer:
			self.finish()

	def finishSelect(self):
		if self.delP == 1:
			ret = ""
			for x in self.list.getSelectionsList():  
				ret += "%s, " % x[0]
			if len(ret) == 0:
				return self.exit()
			else:
				restartbox = self.session.openWithCallback(self.downAnswerNow, MessageBox, _("Delete") + " " + ret + _("now?"), MessageBox.TYPE_YESNO)
				restartbox.setTitle(_("Delete"))
		else:
			self.finish()

	def finish(self):
		ret = []
		for x in self.list.getSelectionsList():  
			if self.delP == 1:
				ret.append(x[1][1])
			else:
				ret.append(x[1]) 
		if len(ret) == 0:
			return self.exit()    
		else:          		
			return self.exit(ret)
			
	def exit(self,r=None):
		self.close(r)


class warderPositionSelectorScr(Screen):
	skin = satSelectorScr.skin

	def __init__(self, session, selected=None):
		Screen.__init__(self, session)
		self.selected = set(warderPiconSync.task_package_selectors_from_bindings([item for item in (selected or []) if not warderRadio.is_radio(item)]))
		if any(warderRadio.is_dab(item) for item in (selected or [])):self.selected.add("DAB")
		if any(warderRadio.is_iptv(item) for item in (selected or [])):self.selected.add("IPTV-SK-CZ")
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Select"))
		self["key_yellow"] = Label(_("Save"))
		self.list = SelectionList()
		self["list"] = self.list
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
			"ok": self.list.toggleSelection, "green": self.list.toggleSelection,
			"cancel": self.cancel, "red": self.cancel, "yellow": self.finish
		}, -1)
		self.onLayoutFinish.append(self.startSelect)

	def startSelect(self):
		self.list.addSelection(warderRadio.label({"include_iptv": True}), dict(warderRadio.IPTV_BINDING), -1, "IPTV-SK-CZ" in self.selected, PLUGINPATH + "images/selectors/IPTV-SK-CZ.png")
		self.list.addSelection("DAB / DAB+", dict(warderRadio.DAB_BINDING), 0, "DAB" in self.selected, PLUGINPATH + "images/selectors/DAB.png")
		ordered = sorted(range(len(SATLIST)), key=lambda i: (warderPiconSync.task_binding_for_display_label(SATLIST[i][0]) or {}).get("package_selector") != "DVB-T-SK-CZ")
		for x in ordered:
			label = SATLIST[x][0]
			value = SATLIST[x][2] if len(SATLIST[x]) > 2 else label
			# Attach immutable selector identity to the item. The displayed label and
			# SATLIST icon value are presentation data only.
			binding = warderPiconSync.task_binding_for_display_label(label)
			if not binding:
				continue
			selector = binding["package_selector"]
			# Always show the operator logo beside each Canal+ FastScan table;
			# the SK and CZ tables remain distinct even though both use 23.5E.
			canal_icon = {
				"CANALPLUS_SK": "icons/CANALPLUS_SK-75.png",
				"CANALPLUS_CZ": "icons/CANALPLUS_CZ-75.png",
			}.get(selector)
			selector_icon = PLUGINPATH + "images/selectors/" + selector + ".png"
			p = selector_icon if os.path.isfile(selector_icon) else (SKINPATH + canal_icon if canal_icon else "")
			if not p or not os.path.isfile(p):
				p = config.plugins.setupGlass17.par39.value + "/piconSat/" + str(value) + "-75.png"
			if not os.path.isfile(p):
				p = SKINPATH + "icons/75.png"
			self.list.addSelection(label, binding, x+1, selector in self.selected, p)

	def finish(self):
		ret = [x[1] for x in self.list.getSelectionsList()]
		self.close(ret)

	def cancel(self):
		# openWithCallback calls callback(*retVal); close() supplies no arguments.
		# Pass one explicit None so cancel follows a stable callback contract.
		self.close(None)

class styleSelectorScr(Screen):   

	skin = """
<screen name="SelectExtraScreen" position="0,0" size="1920,1080" title="" backgroundColor="#ff000000" flags="wfNoBorder">
  <widget position="0,0" size="1920,164" source="global.CurrentTime" render="WarderSettingsHeader" zPosition="-3" /><eLabel position="630,374" size="660,372" backgroundColor="#1a102136" zPosition="-1" /><eLabel position="1288,374" size="2,372" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="630,374" size="2,372" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="630,744" size="660,2" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="630,374" size="660,2" backgroundColor="#003ee8ff" zPosition="1" /><widget name="list" position="675,389" size="570,292" zPosition="4" scrollbarMode="showOnDemand" backgroundColor="#ff000000" foregroundColor="#00ffffff" transparent="1" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" scrollbarBackgroundColor="#00102136" scrollbarForegroundColor="#003ee8ff" />
	<widget name="key_red" position="650,696" size="196,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#00ff526a" backgroundColor="#ff000000" noWrap="1" />
	<widget name="key_green" position="862,696" size="196,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#0039ff59" backgroundColor="#ff000000" noWrap="1" />
	<widget name="key_blue" position="1074,696" size="196,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#0045b9ff" backgroundColor="#ff000000" noWrap="1" />
   <eLabel position="650,690" size="196,2" backgroundColor="#00ff526a" zPosition="1" /><eLabel position="862,690" size="196,2" backgroundColor="#0039ff59" zPosition="1" /><eLabel position="1074,690" size="196,2" backgroundColor="#0045b9ff" zPosition="1" /><widget position="1120,25" size="250,36" font="Regular;25" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%A</convert></widget><widget position="1020,70" size="350,36" font="Regular;24" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%d. %B %Y</convert></widget><widget position="1398,32" size="190,85" font="Regular;62" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Default</convert></widget><widget position="1590,58" size="66,54" font="Regular;38" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="left" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format::%S</convert></widget><eLabel position="1680,25" size="210,36" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="Version:" /><eLabel position="1680,70" size="210,36" font="Regular;24" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="1.0.35" /><eLabel position="1392,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><eLabel position="1664,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><widget position="850,120" size="700,38" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="Title" render="Label" /><eLabel position="0,164" size="1920,210" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,374" size="630,372" backgroundColor="#00071627" zPosition="-2" /><eLabel position="1290,374" size="630,372" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,746" size="1920,334" backgroundColor="#00071627" zPosition="-2" /></screen>
"""

	def __init__(self, session, style, scrNum):
		self.skin = styleSelectorScr.skin
		self.session = session
		self.style = style
		self.scrNum = scrNum
		Screen.__init__(self, session)
		self.list = []
		self["key_green"] = Label(_("Select"))
		self["key_blue"] = Label(_("Edit color"))
		self["key_red"] = Label(_("Cancel"))
		self['list'] = thumbList2(self.list)	
		self["actions"] = ActionMap(['WizardActions', 'ColorActions'],
		{
			"green": self.save,
			"ok": self.save,
			"red": self.close,
			"blue": self.enterColor,
			"back": self.close
		})    
		self.onLayoutFinish.append(self.generateData)

	def setWindowTitle(self):
		self.setTitle(_("Style menu"))

	def enterColor(self):
		selection = self['list'].getCurrent()
		if selection:
			tmp = str(selection[0])
			tmp = tmp.strip().split("*")
			self.session.openWithCallback(self.enterColorAnswer,InputBox, title="Please enter color (#AARRGGBB): ", text=tmp[1], maxSize=12, type=Input.TEXT)

	def enterColorAnswer(self, color):
		if color is None:
			return		
		x = ""
		try:
			color = color.strip()
			if len(color) == 9:
				x = int(color.replace("#","0x"), 16)
		except: pass
		if x == "":
			self.session.open(MessageBox, _("Sorry, you have entered a wrong color:") + color + "!!!", MessageBox.TYPE_ERROR, 6)
		else:
			selection = self['list'].getCurrent()
			x = ""
			if selection:
				tmp = str(selection[0])
				tmp = tmp.strip().split("*") 
				try:
					f = open("%sstyle/%s/title_color.cfg" % (SKINPATH, tmp[0]), "w")
					f.write(color)
					f.close()
					self.style = int(tmp[0])
					x = "ok"					
				except: pass					
			if x == "":					
				self.session.open(MessageBox, _("Sorry, writing color:") + " " + color + " " + _("failed !!!"), MessageBox.TYPE_ERROR, 6)
			else:
				self.session.open(MessageBox, _("Color:") + " " + color + " " + _("writed successfully !!!"), MessageBox.TYPE_INFO, 6)
				self.generateData()

	def generateData(self):
		self.setWindowTitle()
		self.list = []
		for x in range(1,MAXICONS):
			if checkStyle(x): 				
				clr = readcolorStyle(str(x))
				item = [str(x)+"*"+clr]
				item.append(MultiContentEntryText(pos=(0, 15), size=(465, 33), font=0, color_sel=int('0xffffff', 16), text=("***  " + str(x) + "  ***")))
				item.append(MultiContentEntryText(pos=(0, 52), size=(465, 33), font=1, color_sel=int('0xffffff', 16), color=int('0xffcc00', 16), text=("Color: " + clr)))
				pix = LoadPixmap(SKINPATH + 'style/'+str(x)+'/b_tl.png')
				item.append(MultiContentEntryPixmap(pos=(210, 0), size=(180, 97), png=pix, backcolor=int('0xffffff', 16)))
				item.append(MultiContentEntryText(pos=(315, 37), size=(150, 33), font=0, text="Title", color_sel=int('0xffffff', 16), color=int(clr.replace('#','0x'), 16)))
				pix = LoadPixmap(SKINPATH + 'style/'+str(x)+'/b_tr.png')
				item.append(MultiContentEntryPixmap(pos=(390, 0), size=(180, 97), png=pix, backcolor=int('0xffffff', 16)))
				self.list.append(item)
		if len(self.list) == 0:
			item = [str(x)+"*"+clr]
			item.append(MultiContentEntryText(pos=(0, 30), size=(465, 33), font=0, color_sel=int('0xffffff', 16), text=("***  None style detected !!!  ***")))
			self.list.append(item)
			self['list'].l.setList(self.list)
		else:
			self['list'].l.setList(self.list)
			self["list"].instance.moveSelectionTo(self.style-1)

	def save(self):
		selection = self['list'].getCurrent()
		if selection:
			tmp = str(selection[0])
			tmp = tmp.strip().split("*")
			if not writeStyleCfg(self.scrNum, int(tmp[0])):			
				self.session.open(MessageBox, _("Sorry, write to g17Screens.cfg failed !!!"), MessageBox.TYPE_ERROR, 6)
			else:
				self.session.open(MessageBox, _("Changes writed successfully !!!"), MessageBox.TYPE_INFO, 6)
		self.close()			
##########################################################################################################################
class selectScreenShowed(Screen):   

	skin = """
<screen name="SelectExtraScreen" position="0,0" size="1920,1080" title="" backgroundColor="#ff000000" flags="wfNoBorder">
  <widget position="0,0" size="1920,164" source="global.CurrentTime" render="WarderSettingsHeader" zPosition="-3" /><eLabel position="741,244" size="960,540" backgroundColor="#00102136" zPosition="3" /><eLabel position="176,181" size="1567,757" backgroundColor="#1a102136" zPosition="-1" /><eLabel position="1741,181" size="2,757" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="176,181" size="2,757" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="176,936" size="1567,2" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="176,181" size="1567,2" backgroundColor="#003ee8ff" zPosition="1" /><widget name="list" position="221,221" size="495,585" zPosition="4" scrollbarMode="showOnDemand" backgroundColor="#ff000000" foregroundColor="#00ffffff" transparent="1" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" scrollbarBackgroundColor="#00102136" scrollbarForegroundColor="#003ee8ff" />
  <widget name="scr_preview" position="741,244" size="960,540" zPosition="4" backgroundColor="#00102136" alphatest="off" />
	<widget name="res" position="741,806" size="960,50" zPosition="4" valign="center" halign="center" font="Prive3;30" transparent="1" foregroundColor="#00ffffff" backgroundColor="#ff000000" />
	<widget name="key_red" position="196,888" size="498,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#00ff526a" backgroundColor="#ff000000" noWrap="1" />
	<widget name="key_green" position="710,888" size="498,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#0039ff59" backgroundColor="#ff000000" noWrap="1" />
	<widget name="key_blue" position="1224,888" size="498,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#0045b9ff" backgroundColor="#ff000000" noWrap="1" />
   <eLabel position="196,882" size="498,2" backgroundColor="#00ff526a" zPosition="1" /><eLabel position="710,882" size="498,2" backgroundColor="#0039ff59" zPosition="1" /><eLabel position="1224,882" size="498,2" backgroundColor="#0045b9ff" zPosition="1" /><widget position="1120,25" size="250,36" font="Regular;25" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%A</convert></widget><widget position="1020,70" size="350,36" font="Regular;24" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%d. %B %Y</convert></widget><widget position="1398,32" size="190,85" font="Regular;62" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Default</convert></widget><widget position="1590,58" size="66,54" font="Regular;38" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="left" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format::%S</convert></widget><eLabel position="1680,25" size="210,36" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="Version:" /><eLabel position="1680,70" size="210,36" font="Regular;24" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="1.0.35" /><eLabel position="1392,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><eLabel position="1664,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><widget position="850,120" size="700,38" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="Title" render="Label" /><eLabel position="0,164" size="1920,17" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,181" size="176,757" backgroundColor="#00071627" zPosition="-2" /><eLabel position="1743,181" size="177,757" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,938" size="1920,142" backgroundColor="#00071627" zPosition="-2" /></screen>
"""

	def __init__(self,session):
		self.skin = selectScreenShowed.skin
		self.session = session
		Screen.__init__(self, session)
		self.list = []
		self["key_green"] = Label(_("Select"))
		self["key_blue"] = Label(_("Edit"))
		self["key_red"] = Label(_("Cancel"))
		self["scr_preview"] = Pixmap()
		self["res"] = Label("")
		self['list'] = thumbList2(self.list)
		self['list'].onSelectionChanged.append(self.reactivate)		
		self["actions"] = ActionMap(['WizardActions', 'ColorActions'],
		{
			"green": self.save,
			"ok": self.save,
			"red": self.exit,
			"blue": self.styleSelector,
			"back": self.exit
		})    
		self.onLayoutFinish.append(self.mainFnc)

	def setWindowTitle(self):
		self.setTitle(_("Extra Screen"))

	def styleSelector(self):
		selection = self['list'].getCurrent()
		if selection:
			tmp = str(selection[0])
			tmp = tmp.strip().split("*")
			self.session.openWithCallback(self.mainFnc, styleSelectorScr, int(tmp[1]), int(tmp[0]))

	def exit(self):
		isOk, color = checkStyleFull(config.plugins.setupGlass17.par6.value, True)
		if isOk != "?":
			config.plugins.setupGlass17.par44.value = int(isOk)
			config.plugins.setupGlass17.par45.value = color
		self.close()
		
	def save(self):
		selection = self['list'].getCurrent()
		if selection:
			tmp = str(selection[0])
			tmp = tmp.strip().split("*")
			config.plugins.setupGlass17.par6.value = int(tmp[0])
			config.plugins.setupGlass17.par44.value = int(tmp[1])
			config.plugins.setupGlass17.par45.value = tmp[2]
		self.close()
		
	def mainFnc(self):
		self.setWindowTitle()
		self.list = []
		c = a = 0
		for x in range(1,MAXSCREENS):
			tmp = checkScreen(x) 
			if x == config.plugins.setupGlass17.par6.value:
				a = c
			if tmp:
				c += 1
				s, colorS = checkStyleFull(x)
				item = [str(x)+"*"+s+"*"+colorS]
				item.append(MultiContentEntryText(pos=(0, 31), size=(47, 33), font=0, color_sel=int('0xffffff', 16), color=int('0x00d100', 16), text=(str(c)+".")))
				item.append(MultiContentEntryText(pos=(60, 15), size=(360, 33), font=0, color_sel=int('0xffffff', 16), text=(ui_text("Type") + " " + str(x))))
				item.append(MultiContentEntryText(pos=(90, 52), size=(360, 33), font=1, color_sel=int('0xffffff', 16), color=int('0xffcc00', 16), text=(_("Style:")+" " + s)))
				thumb = thumbnail_path(x)
				if thumb:
					item.append(MultiContentEntryPixmap(pos=(270, 0), size=(174, 97), png=LoadPixmap(thumb)))
				self.list.append(item)
		self['list'].l.setList(self.list)
		self["list"].instance.moveSelectionTo(a)

	def reactivate(self):
		selection = self['list'].getCurrent()
		if selection:
			tmp = str(selection[0])
			tmp = tmp.strip().split("*")
			tmp2 = config.plugins.setupGlass17.par39.value + "/more_icons/scr_prew/screen-" + tmp[0] + ".png"
			try:
				if fileExists(tmp2):
					self["scr_preview"].instance.setPixmapFromFile(tmp2)
				else:        
					self["scr_preview"].instance.setPixmapFromFile((SKINPATH + "no-preview.png"))        
				from Screens.G17screens import g17_extraScreen	
				tmp = g17_extraScreen.get(str(tmp[0]))
				tmp = tmp.split("\n")
				for i in tmp:
					if "g17picon" in i:
						tmp2 = (i.split('size="')[1]).split('"')[0]
						tmp2 = tmp2.strip().split(',')
						break
				if len(tmp2) == 2:
					self["res"].setText(_("Picon path")+": "+config.plugins.setupGlass17.par39.value+"/" + piconSize(tmp2[0]+","+tmp2[1]))
				else:
					self["res"].setText("")
			except: pass      		
##########################################################################################################################
class selectIconsDisplayed(Screen):   

	skin = """
<screen name="selectIconsScreen" position="0,0" size="1920,1080" title="" backgroundColor="#ff000000" flags="wfNoBorder">
  <widget position="0,0" size="1920,164" source="global.CurrentTime" render="WarderSettingsHeader" zPosition="-3" /><eLabel position="267,164" size="1386,757" backgroundColor="#1a102136" zPosition="-1" /><eLabel position="1651,164" size="2,757" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="267,164" size="2,757" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="267,919" size="1386,2" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="267,164" size="1386,2" backgroundColor="#003ee8ff" zPosition="1" /><widget name="list" position="312,291" size="315,370" zPosition="4" scrollbarMode="showOnDemand" backgroundColor="#ff000000" foregroundColor="#00ffffff" transparent="1" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" scrollbarBackgroundColor="#00102136" scrollbarForegroundColor="#003ee8ff" />
	<widget name="key_red" position="267,871" size="693,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#00ff526a" backgroundColor="#ff000000" noWrap="1" />
	<widget name="key_green" position="960,871" size="693,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#0039ff59" backgroundColor="#ff000000" noWrap="1" />
   <eLabel position="267,865" size="693,2" backgroundColor="#00ff526a" zPosition="1" /><eLabel position="960,865" size="693,2" backgroundColor="#0039ff59" zPosition="1" /><widget position="1120,25" size="250,36" font="Regular;25" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%A</convert></widget><widget position="1020,70" size="350,36" font="Regular;24" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%d. %B %Y</convert></widget><widget position="1398,32" size="190,85" font="Regular;62" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Default</convert></widget><widget position="1590,58" size="66,54" font="Regular;38" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="left" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format::%S</convert></widget><eLabel position="1680,25" size="210,36" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="Version:" /><eLabel position="1680,70" size="210,36" font="Regular;24" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="1.0.35" /><eLabel position="1392,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><eLabel position="1664,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><widget position="850,120" size="700,38" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="Title" render="Label" /><eLabel position="0,164" size="267,757" backgroundColor="#00071627" zPosition="-2" /><eLabel position="1653,164" size="267,757" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,921" size="1920,159" backgroundColor="#00071627" zPosition="-2" />
"""

	def __init__(self,session,what=0):
		self.what = what
		self.session = session
		self.skin = selectIconsDisplayed.skin
		Screen.__init__(self, session)
		self.list = []
		self["key_green"] = Label(_("Select"))
		self["key_red"] = Label(_("Cancel"))
		self.wahtType = "/menuIcons/"
		self.rng = MAXICONS
		if self.what != 0:
			if self.what == 1:
				self.samle = ["av_setup","setup","standby_restart_list","system_selection","timer_edit","tuner_setup","info_screen","manual_scan","network_setup"]
			else:
				self.samle = ["0","1","26","27","28","32","38","47","23"]
				self.wahtType = "/weatherIcons/"
			y = 0
			off = 0
			for x in range(0,9):
				self["ico%s" % x] = Pixmap()
				if x > 5:
					y = 375
					off = 6
				elif x > 2:
					y = 187
					off = 3
				self.skin += '<widget name="ico'+str(x)+'" position="'+str(672+(x-off)*300)+','+str(221+y)+'" size="300,183" zPosition="2" backgroundColor="background" alphatest="blend" />'
		else:
			self["scr_preview"] = Pixmap()
			self.skin += """<widget name="scr_preview" position="748,260" size="768,432" zPosition="2" backgroundColor="background" alphatest="blend"/>"""
		self.skin += """</screen>"""
		self['list'] = thumbList(self.list)
		self['list'].onSelectionChanged.append(self.reactivate)		
		self["actions"] = ActionMap(['WizardActions', 'ColorActions'],
		{
			"green": self.save,
			"ok": self.save,
			"red": self.close,
			"back": self.close
		})    
		self.onLayoutFinish.append(self.mainFnc)

	def setWindowTitle(self):
		self.setTitle(_("Choose Icons"))

	def save(self):
		selection = self['list'].getCurrent()
		if selection:
			tmp = selection[0]
			if tmp != "*":
				if self.what != 0:
					if self.what == 1:
						config.plugins.setupGlass17.par69.value = int(tmp)
						config.plugins.setupGlass17.par69.save()
					else:
						config.plugins.setupGlass17.par72.value = int(tmp)
						config.plugins.setupGlass17.par72.save()
				else:
					config.plugins.setupGlass17.par1.value = int(tmp)
		self.close()
		
	def mainFnc(self):
		self.setWindowTitle()
		self.list = []
		a = c = 0
		for x in range(1,self.rng):
			if self.what != 0:
				num = 0
				tmp = False
				for sample in self.samle:
					fileSample = config.plugins.setupGlass17.par39.value + self.wahtType + str(x) + "/" + sample + ".png"
					if fileExists(fileSample):
						num += 1
				if num == 9:
					tmp = True
			else:
				tmp = checkIcons(x) 
			if (x == config.plugins.setupGlass17.par1.value and self.what == 0) or (x == config.plugins.setupGlass17.par72.value and self.what == 2) or (x == config.plugins.setupGlass17.par69.value and self.what == 1):
				a = x - 1
			if tmp:
				c += 1
				item = [str(x)]
				item.append(MultiContentEntryText(pos=(0, 0), size=(52, 33), font=0, text=(str(c)+".")))
				item.append(MultiContentEntryText(pos=(67, 0), size=(495, 33), font=0, text=("***  " + str(x) + "  ***")))
				self.list.append(item)
		if c == 0:
			item = ["*"]
			item.append(MultiContentEntryText(pos=(0, 0), size=(495, 33), font=0, text=("***  " + _("No data") + "  ***")))
			self.list.append(item)
		self['list'].l.setList(self.list)
		self["list"].instance.moveSelectionTo(a)

	def reactivate(self):
		selection = self['list'].getCurrent()
		if selection:
			tmp = selection[0]
			if tmp != "*":
				if self.what != 0:
					i = 0
					for sample in self.samle:
						fileSample = config.plugins.setupGlass17.par39.value + self.wahtType + tmp + "/" + sample + ".png"
						try:
							if fileExists(fileSample):
								self["ico%s" % i].instance.setPixmapFromFile(fileSample)
							else:        
								if self.what == 1:
									self["ico%s" % i].instance.setPixmapFromFile(SKINPATH +"menu/undefined.png")        
								else:
									self["ico%s" % i].instance.setPixmapFromFile(SKINPATH + "icons/3200.png")
						except: pass 
						i += 1
				else:
					tmp2 = config.plugins.setupGlass17.par39.value + "/more_icons/scr_prew/icons-" + tmp + ".png"
					try:
						if fileExists(tmp2):
							self["scr_preview"].instance.setPixmapFromFile(tmp2)
						else:        
							self["scr_preview"].instance.setPixmapFromFile((SKINPATH + "no-preview.png"))        
					except: pass       		
##########################################################################################################################
class historyScreen(Screen):
	skin = """
<screen name="g17_History" position="0,0" size="1920,1080" zPosition="8" title="" backgroundColor="#ff000000" flags="wfNoBorder">
<widget position="0,0" size="1920,164" source="global.CurrentTime" render="WarderSettingsHeader" zPosition="-3" /><eLabel position="135,164" size="1650,796" backgroundColor="#1a102136" zPosition="-1" /><eLabel position="1783,164" size="2,796" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="135,164" size="2,796" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="135,958" size="1650,2" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="135,164" size="1650,2" backgroundColor="#003ee8ff" zPosition="1" /><widget name="Changelog_info" position="150,194" size="1620,740" scrollbarMode="showOnDemand" backgroundColor="#ff000000" foregroundColor="#00ffffff" transparent="1" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" zPosition="4" scrollbarBackgroundColor="#00102136" scrollbarForegroundColor="#003ee8ff" />
	<widget name="key_red" position="135,1006" size="825,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="0" foregroundColor="#00ff526a" backgroundColor="#00071627" noWrap="1" />
	<widget name="key_green" position="960,1006" size="825,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="0" foregroundColor="#0039ff59" backgroundColor="#00071627" noWrap="1" />
   <widget name="line_red" position="135,996" size="825,2" backgroundColor="#00ff526a" zPosition="5" transparent="0" foregroundColor="#00ffffff" />
    <widget name="line_green" position="960,996" size="825,2" backgroundColor="#0039ff59" zPosition="5" transparent="0" foregroundColor="#00ffffff" />
<widget position="1120,25" size="250,36" font="Regular;25" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%A</convert></widget><widget position="1020,70" size="350,36" font="Regular;24" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%d. %B %Y</convert></widget><widget position="1398,32" size="190,85" font="Regular;62" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Default</convert></widget><widget position="1590,58" size="66,54" font="Regular;38" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="left" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format::%S</convert></widget><eLabel position="1680,25" size="210,36" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="Version:" /><eLabel position="1680,70" size="210,36" font="Regular;24" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="1.0.35" /><eLabel position="1392,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><eLabel position="1664,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><widget position="850,120" size="700,38" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="Title" render="Label" /><eLabel position="0,164" size="135,796" backgroundColor="#00071627" zPosition="-2" /><eLabel position="1785,164" size="135,796" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,960" size="1920,120" backgroundColor="#00071627" zPosition="-2" /></screen>
"""
                        
	def __init__(self, session, ver="", new=""):
		Screen.__init__(self, session)
		self.skin = historyScreen.skin
		self.new = new
		self.ver = ver
		self.res = self.ver == "" or self.ver == _("Result")
		self.list = []
		self['Changelog_info'] = thumbList(self.list)	
		self["key_red"] = Label(_("Close") if self.res else _("Cancel"))
		self["key_green"] = Label(_("Update"))
		self["line_red"] = Label("")
		self["line_green"] = Label("")
		self["actions"] = ActionMap(["ColorActions", "SetupActions", "DirectionActions"],
		{
            "green": self.update,
            "ok": self.update,
            "red": self.exit,
            "cancel": self.exit,
            "blue": self.exit,
            "yellow": self.exit
		}, -2)
		self.onLayoutFinish.append(self.readandshow)	

	def exit(self):
		if self.res:
			self.close()
		else:
			self.close(False)

	def update(self):
		if self.res:
			self.close()
		else:
			self.close(True)
		
	def setWindowTitle(self, t):
		self.setTitle(t)

	def readandshow(self):
		if self.res:
			self["key_green"].hide()
			self["key_red"].move(ePoint(547,1006))
			self["line_red"].move(ePoint(547,996))
			self["line_green"].hide()
		txt = _("Changelog")
		item = []
		a = self.ver == _("Result")
		if a:
			txt = self.ver
		elif self.new != "":
			txt += " ver."+self.ver
			f = self.new
		else:
			f = PLUGINPATH + HIST		
		self.setWindowTitle(txt)
		try:
			if a:
				f = self.new.split("\n")
				color=int("0xdddddd", 16)
				xOff = 32
			else:
				xOff = 0
				f = open(f, 'r').readlines()
			for x in f: 
				tt = x.replace("\n","")
				if tt != "" and len(tt) > 0:
					item = [tt]
					if a:
						p = "white"
						if _("SUCCESSFUL") in x:
							p = "green"	
						elif _("ERROR") in x or _("PARTIAL SUCCESS") in x:
							p = "red"
						item.append(MultiContentEntryPixmapAlphaTest(pos=(0, 7), size=(22, 23), png=LoadPixmap("%sicons/%s.png" % (SKINPATH,p))))
					else:
						if "*" in x:
							color=int("0xff9c00", 16)	
						else:
							color=int("0xffffff", 16)
					item.append(MultiContentEntryText(pos=(xOff, 0), size=(1620-xOff, 33), font=0, text=tt, color=color))
					self.list.append(item)
		except:	pass	
		if len(self.list) == 0:
			item = ["*"]
			item.append(MultiContentEntryText(pos=(0, 0), size=(802, 33), font=0, text=_("No Changelog info !!!")))
			self.list.append(item)
		self['Changelog_info'].l.setList(self.list)
		self['Changelog_info'].selectionEnabled(0)
##########################################################################################################################
class SelectPosition(Screen):                     
	def __init__(self, session, typeObj=""):
		Screen.__init__(self, session)
		self.typeObj = typeObj
		if self.typeObj == "volMute": 
			self.valueX = config.plugins.setupGlass17.par51.value
			self.valueY = config.plugins.setupGlass17.par52.value
			self.skinName = ['Volume']
			from Components.VolumeBar import VolumeBar
			self.volumeBar = VolumeBar()		
			self["Volume"] = self.volumeBar   
		elif self.typeObj == "netspeed": 
			self.valueX = config.plugins.setupGlass17.par210.value
			self.valueY = config.plugins.setupGlass17.par211.value       
			if config.plugins.setupGlass17.par226.value != "2":
				self.skin = """<screen name="NetspeedPos" position="0,0" size="270,50" zPosition="0" title="NetspeedPos" backgroundColor="black" flags="wfNoBorder">
				<ePixmap position="0,0" size="270,50" pixmap="hd_glass17/icons/netspeed.png" zPosition="7" alphatest="off" />
				<widget source="global.CurrentTime" render="g17ShowNetSpeed" position="80,0" size="190,50" zPosition="8" font="Regular2;26" noWrap="1" valign="center" halign="center" foregroundColor="yellow" backgroundColor="background" transparent="1"/>
				</screen>"""
			else:
				self.skin = """<screen name="NetspeedPos" position="0,0" size="220,40" zPosition="0" title="NetspeedPos" backgroundColor="transparent" flags="wfNoBorder">
				<widget source="global.CurrentTime" render="g17ShowNetSpeed" position="0,0" size="220,40" zPosition="8" font="Prive3;27" noWrap="1" valign="center" halign="right" backgroundColor="un353e575e" shadowColor="#1A58A6" shadowOffset="-1,-1" transparent="1"/>
				</screen>"""
		elif self.typeObj == "poster": 
			self.valueX = config.plugins.setupGlass17.par200.value
			self.valueY = config.plugins.setupGlass17.par201.value       
			self.skin = """<screen name="Poster" position="0,0" size="%s" zPosition="0" title="Poster" backgroundColor="black" flags="wfNoBorder">                                           
			<widget name="cover" position="0,0" size="%s" pixmap="hd_glass17/videodb/cover_no.png" alphatest="off" />
			</screen>""" % (config.plugins.setupGlass17.par202.value,config.plugins.setupGlass17.par202.value) 
			self["cover"] = Pixmap()
		else:                                                           
			self.skin = """<screen name="SpecialScreen" position="1155,195" size="810,412" zPosition="8" title="Ecm and TP Status" backgroundColor="background" >                                           
			<widget name="ecm_items" font="Prive3;24" position="7,15" zPosition="2" size="150,532" valign="top" halign="left" foregroundColor="yellow" backgroundColor="background" transparent="1" />
			<widget name="ecm_Values" font="Prive3;24" position="96,15" zPosition="3" size="337,532" valign="top" halign="left"  backgroundColor="background" transparent="1" />
			<widget name="tp_items" font="Prive3;24" position="435,15" zPosition="2" size="150,480" valign="top" halign="left" foregroundColor="yellow" backgroundColor="background" transparent="1" />
			<widget name="tp_Values" font="Prive3;24" position="577,15" zPosition="3" size="232,480" valign="top" halign="left"  backgroundColor="background" transparent="1" />                         
			</screen>""" 
			self['ecm_items'] = Label(ECM_LABELS)
			self['ecm_Values'] = Label(CLRDATA)
			self['tp_items'] = Label("Video PID:\nAudio PID:\nPCR PID:\nPMT PID:\nTXT PID:\nSID:\nTSID:\nONID:\nV. Format:\nV. Size:\nAudio Type:\nA. Tracks:\nSubtitles:")
			self['tp_Values'] = Label(CLRTP)
			self.valueX = config.plugins.setupGlass17.par10.value
			self.valueY = config.plugins.setupGlass17.par11.value
		self["actions"] = ActionMap(["WizardActions"],
		{
			"left": self.left,
			"up": self.up,
			"right": self.right,
			"down": self.down,
			"ok": self.ok,
			"back": self.close
		}, -1)		
		self.moveTimer = eTimer()
		try:
			self.moveTimer_conn = self.moveTimer.timeout.connect(self.setNewPosition)
		except AttributeError:
			self.moveTimer.callback.append(self.setNewPosition)
		self.moveTimer.start(80)
		self.onLayoutFinish.append(self.setVol)

	def setVol(self):
		if self.typeObj == "volMute":
			from enigma import eDVBVolumecontrol
			self.volumeBar.setValue(int(eDVBVolumecontrol.getInstance().getVolume()))
		elif self.typeObj == "poster":
			self["cover"].instance.setScale(1)
			
	def setNewPosition(self):
		self.instance.move(ePoint(self.valueX, self.valueY))
		self.moveTimer.start(80)

	def left(self):
		self.valueX -= 10
		if self.valueX < 0:
			self.valueX = 0

	def up(self):
		self.valueY -= 10
		if self.valueY < 0:
			self.valueY = 0

	def right(self):
		self.valueX += 10
		if self.valueX > 1820:
			self.valueX = 1820

	def down(self):
		self.valueY += 10
		if self.valueY > 1000:
			self.valueY = 1000

	def ok(self):
		if self.valueX == 0:
			self.valueX = 1
		if self.valueY == 0:
			self.valueY = 1
		if self.typeObj == "volMute":
			config.plugins.setupGlass17.par51.value = self.valueX
			config.plugins.setupGlass17.par52.value = self.valueY			
		elif self.typeObj == "poster":
			config.plugins.setupGlass17.par200.value = self.valueX
			config.plugins.setupGlass17.par201.value = self.valueY	
		elif self.typeObj == "netspeed":
			config.plugins.setupGlass17.par210.value = self.valueX
			config.plugins.setupGlass17.par211.value = self.valueY
		else:
			config.plugins.setupGlass17.par10.value = self.valueX
			config.plugins.setupGlass17.par11.value = self.valueY
		self.close()
##########################################################################################################################
class weatherCitySelector(Screen):
	"""OK-driven selector for cities already present in /etc/my_city_Code.txt."""

	skin = """
<screen name="weatherCitySelector" position="0,0" size="1920,1080" title="Weather for City" backgroundColor="#ff000000" flags="wfNoBorder">
		<widget position="0,0" size="1920,164" source="global.CurrentTime" render="WarderSettingsHeader" zPosition="-3" /><eLabel position="510,210" size="900,700" backgroundColor="#1a102136" zPosition="-1" /><eLabel position="1408,210" size="2,700" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="510,210" size="2,700" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="510,908" size="900,2" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="510,210" size="900,2" backgroundColor="#003ee8ff" zPosition="1" /><widget name="list" position="535,235" size="850,590" scrollbarMode="showOnDemand" backgroundColor="#ff000000" foregroundColor="#00ffffff" transparent="1" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" zPosition="4" scrollbarBackgroundColor="#00102136" scrollbarForegroundColor="#003ee8ff" />
		<widget name="key_red" position="530,860" size="422,50" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#00ff526a" backgroundColor="#ff000000" noWrap="1" zPosition="4" />
		<widget name="key_green" position="968,860" size="422,50" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#0039ff59" backgroundColor="#ff000000" noWrap="1" zPosition="4" />
	<eLabel position="530,854" size="422,2" backgroundColor="#00ff526a" zPosition="1" /><eLabel position="968,854" size="422,2" backgroundColor="#0039ff59" zPosition="1" /><widget position="1120,25" size="250,36" font="Regular;25" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%A</convert></widget><widget position="1020,70" size="350,36" font="Regular;24" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%d. %B %Y</convert></widget><widget position="1398,32" size="190,85" font="Regular;62" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Default</convert></widget><widget position="1590,58" size="66,54" font="Regular;38" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="left" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format::%S</convert></widget><eLabel position="1680,25" size="210,36" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="Version:" /><eLabel position="1680,70" size="210,36" font="Regular;24" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="1.0.35" /><eLabel position="1392,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><eLabel position="1664,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><widget position="850,120" size="700,38" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="Title" render="Label" /><eLabel position="0,164" size="1920,46" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,210" size="510,700" backgroundColor="#00071627" zPosition="-2" /><eLabel position="1410,210" size="510,700" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,910" size="1920,170" backgroundColor="#00071627" zPosition="-2" /></screen>
"""

	def __init__(self, session, current=None):
		Screen.__init__(self, session)
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Select"))
		self.items = []
		currentIndex = 0
		for value, label in getCitiesCode():
			item = [value]
			item.append(MultiContentEntryText(pos=(15, 0), size=(820, 42), font=2, color_sel=int("0xffffff",16), text=str(label)))
			if value == current:
				currentIndex = len(self.items)
			self.items.append(item)
		self["list"] = thumbList(self.items)
		self["list"].l.setItemHeight(45)
		self.currentIndex = currentIndex
		self.onLayoutFinish.append(self._restoreSelection)
		self["actions"] = ActionMap(["SetupActions", "DirectionActions", "ColorActions"], {
			"ok": self.select, "green": self.select, "cancel": self.close, "red": self.close,
			"up": self["list"].up, "down": self["list"].down,
			"left": self["list"].pageUp, "right": self["list"].pageDown,
		}, -1)

	def _restoreSelection(self):
		if self.items and self["list"].instance is not None:
			self["list"].instance.moveSelectionTo(self.currentIndex)

	def select(self):
		selection = self["list"].getCurrent()
		self.close(str(selection[0]) if selection and str(selection[0]) != "None" else None)


class cityFinder(Screen):   

	skin = """
<screen name="cityFinder" position="0,0" size="1920,1080" title="To move in both menu use P+/- or Bqt +/-" backgroundColor="#ff000000" flags="wfNoBorder">
  <widget position="0,0" size="1920,164" source="global.CurrentTime" render="WarderSettingsHeader" zPosition="-3" /><eLabel position="210,164" size="1500,916" backgroundColor="#1a102136" zPosition="-1" /><eLabel position="1708,164" size="2,916" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="210,164" size="2,916" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="210,1078" size="1500,2" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="210,164" size="1500,2" backgroundColor="#003ee8ff" zPosition="1" /><widget name="info" font="Prive3;33" position="255,171" zPosition="4" size="570,37" valign="center" halign="center" transparent="1" foregroundColor="#00ffffff" backgroundColor="#ff000000" />
  <widget name="list" position="210,216" size="790,675" zPosition="4" scrollbarMode="showOnDemand" backgroundColor="#ff000000" foregroundColor="#00ffffff" transparent="1" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" scrollbarBackgroundColor="#00102136" scrollbarForegroundColor="#003ee8ff" />
  <widget name="myCity" position="1010,216" size="700,802" zPosition="4" scrollbarMode="showOnDemand" backgroundColor="#ff000000" foregroundColor="#00ffffff" transparent="1" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" scrollbarBackgroundColor="#00102136" scrollbarForegroundColor="#003ee8ff" />
	<widget name="key_red" position="230,1030" size="353,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="0" foregroundColor="#00ff526a" backgroundColor="#00071627" noWrap="1" />
	<widget name="key_green" position="599,1030" size="353,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="0" foregroundColor="#0039ff59" backgroundColor="#00071627" noWrap="1" />
	<widget name="key_yellow" position="968,1030" size="353,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="0" foregroundColor="#00f5d54e" backgroundColor="#00071627" noWrap="1" />
	<widget name="key_blue" position="1337,1030" size="353,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="0" foregroundColor="#0045b9ff" backgroundColor="#00071627" noWrap="1" />
   <eLabel position="230,1024" size="353,2" backgroundColor="#00ff526a" zPosition="1" /><eLabel position="599,1024" size="353,2" backgroundColor="#0039ff59" zPosition="1" /><eLabel position="968,1024" size="353,2" backgroundColor="#00f5d54e" zPosition="1" /><eLabel position="1337,1024" size="353,2" backgroundColor="#0045b9ff" zPosition="1" /><widget position="1120,25" size="250,36" font="Regular;25" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%A</convert></widget><widget position="1020,70" size="350,36" font="Regular;24" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%d. %B %Y</convert></widget><widget position="1398,32" size="190,85" font="Regular;62" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Default</convert></widget><widget position="1590,58" size="66,54" font="Regular;38" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="left" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format::%S</convert></widget><eLabel position="1680,25" size="210,36" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="Version:" /><eLabel position="1680,70" size="210,36" font="Regular;24" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="1.0.35" /><eLabel position="1392,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><eLabel position="1664,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><widget position="850,120" size="700,38" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="Title" render="Label" /><eLabel position="0,164" size="210,916" backgroundColor="#00071627" zPosition="-2" /><eLabel position="1710,164" size="210,916" backgroundColor="#00071627" zPosition="-2" /></screen>
"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skin = cityFinder.skin
		self.session = session
		self.list = []
		self.citylist = []
		self.allLabels = [_("Edit")+" my_city...", _("Edit line"),_("Find a city")+" (TXT)", _("Delete line"), _("Select"), _("Add line")+" (TXT)"]
		self["key_green"] = Label(self.allLabels[4])
		self["key_blue"] = Label(self.allLabels[2])
		self["key_yellow"] = Label(self.allLabels[0])
		self["key_red"] = Label(_("Cancel"))
		self['list'] = thumbList2(self.list)
		self['myCity'] = thumbList(self.citylist)	
		self['list'].l.setItemHeight(301)
		self['info'] = Label(_("up")+"/"+_("down")+" P+/- or Bqt +/-")
		self.findC = True
		self.cityLevel = "root"
		self.activeCountry = None
		self.countryNames = {}
		self.selectedLine = None
		self.oldLine = None
		self["actions"] = ActionMap(['WizardActions', 'ColorActions','VirtualKeyboardActions','ChannelSelectBaseActions'],
		{
			"nextBouquet": self.moveMainmenuUp,
			"prevBouquet": self.moveMainmenuDown,
			"green": self.save,
			"ok": self.save,
			"red": self.exit,
			"blue": self.findCity,
			"yellow": self.editMCC,
			'showVirtualKeyboard': self.KeyText,
			"back": self.exit
		})    
		self.onLayoutFinish.append(self.generateData)
		self.onLayoutFinish.append(self.setWindowTitle)
		
	def moveMainmenuUp(self):
		if self.findC:
			self['list'].up()
		else:
			self['myCity'].up()		
		
	def moveMainmenuDown(self):
		if self.findC:	
			self['list'].down()	
		else:
			self['myCity'].down()

	def setWindowTitle(self,txt=""):
		self.setTitle(_("Find a city")+txt)

	def exit(self):
		if not self.findC:
			self["key_yellow"].setText(self.allLabels[0])
			self["key_blue"].setText(self.allLabels[2])
			self.findC = True
			self['list'].selectionEnabled(1)
			self['myCity'].selectionEnabled(0)
			self["key_green"].setText(self.allLabels[4])
		elif self.cityLevel == "cities":
			self.cityLevel = "root"
			self.activeCountry = None
			self.generateData()
		else:
			self.close(0)

	def KeyText(self):
		from Screens.VirtualKeyBoard import VirtualKeyBoard
		if self.findC:
			self.session.openWithCallback(self.findCityAnswer, VirtualKeyBoard, title=_("Please enter a city name")+": ", text="banska bystrica")
		else:
			self.session.openWithCallback(self.addNewLine, VirtualKeyBoard, title=self.allLabels[5], text="                                                 ")
		
	def findCity(self):
		if not self.findC:
			try:
				self.citylist.remove(self.citylist[self['myCity'].getSelectionIndex()])
				self.writeMCC()      		
			except: pass
		else:	
			self.session.openWithCallback(self.findCityAnswer, InputBox, title=_("Please enter a city name")+": ", text="banska bystrica                   ", maxSize=50, type=Input.TEXT)
		
	def save(self):
		if self.findC:
			selection = self["list"].getCurrent()
			if not selection or str(selection[0]) == "*":
				return
			value = str(selection[0])
			if value.startswith("country|"):
				self.cityLevel, self.activeCountry = "cities", value.split("|", 1)[1]
				self.generateData()
			else:
				self.appMCC(value)
		else:
			self.session.openWithCallback(self.addNewLine, InputBox, title=self.allLabels[5], text="                                                 ", maxSize=120, type=Input.TEXT)

	def editMCC(self):
		if self.findC:
			self["key_yellow"].setText(self.allLabels[1])   
			self.findC = False
			self['list'].selectionEnabled(0)       
			self['myCity'].selectionEnabled(1)      
			self["key_green"].setText(self.allLabels[5])
			self["key_blue"].setText(self.allLabels[3])
		else:
			try:
				self.selectedLine = self['myCity'].getSelectionIndex()
				self.oldLine = self.citylist[self.selectedLine]
				self.session.openWithCallback(self.writeEditLine, InputBox, title=self.allLabels[1], text=self.oldLine[:-1]+"            ", maxSize=50, type=Input.TEXT)
			except: pass    
                 
	def writeEditLine(self, newline):
		if newline is not None:
			if self.chckLine(newline):
				self.session.open(MessageBox, ER_F, MessageBox.TYPE_ERROR, 6)			
			else:
				newline = ' '.join((newline).strip().split()) + '\n'
				if newline != self.oldLine:
					self.citylist[self.selectedLine] = newline
					self.writeMCC()
		self.selectedLine = None
		self.oldLine = None 
		
	def writeMCC(self):
		try:
			_atomicWriteText("/etc/my_city_Code.txt", "".join(self.citylist))
		except Exception:
			pass
		self.generateData()  
                   		
	def findCityAnswer(self, name):
		if name is None and name != "":
			return		
		self.generateData(name.strip())

	def _loadLocalCities(self):
		cities = []
		self.countryNames = {}
		try:
			db = "/etc/city_Code-17.txt" if os.path.isfile("/etc/city_Code-17.txt") else "/etc/city_Code.txt"
			currentName = ""
			with open(db, "r") as f:
				for raw in f:
					line = raw.strip()
					if line.startswith("# "):
						currentName = line[2:].strip()
						if currentName == "SK": currentName = "Slovakia"
						elif currentName == "CZ": currentName = "Czechia"
						continue
					x = _cityLine(raw)
					if not x:
						continue
					country = ""
					if line.startswith("om|"):
						p = line.split("|")
						country = p[3].upper() if len(p) > 3 else ""
					if country and currentName:
						self.countryNames[country] = currentName
					cities.append((country, x[1], x[2]))
		except Exception as e:
			Writelog("city database: %s" % e)
		return cities

	def _onlineCitySearch(self, what):
		result = []
		try:
			if ISP38:
				from urllib.parse import urlencode
			else:
				from urllib import urlencode
			url = "https://geocoding-api.open-meteo.com/v1/search?" + urlencode({"name": what, "count": 20, "language": WLANG[:2], "format": "json"})
			raw = urlopen(Request(url, headers={"User-Agent": "FullHDGlass17-Warder-Evolution/1.0.5"}), timeout=8).read()
			if not isinstance(raw, str):
				raw = raw.decode("utf-8", "replace")
			for loc in (json.loads(raw).get("results") or []):
				name = loc.get("name") or ""
				cc = (loc.get("country_code") or "").upper()
				admin = loc.get("admin1") or ""
				postal = ""
				pcs = loc.get("postcodes") or []
				if isinstance(pcs, list) and pcs:
					postal = str(pcs[0])
				if name and cc:
					value = "om|%s|%s|%s|%s|%s" % (name, name, cc, admin, postal)
					label = name + (", " + admin if admin else "") + (", " + cc if cc else "")
					result.append((label, value))
		except Exception as e:
			Writelog("Open-Meteo city search: %s" % e)
		return result

	def generateData(self, what=""):
		self.list = []
		local = self._loadLocalCities()
		needle = _citySearchKey(what)
		if needle:
			for country, display, value in local:
				if needle in _citySearchKey(display):
					item = [value]
					label = display + ((" [" + self.countryNames.get(country, country) + "]") if country else "")
					item.append(MultiContentEntryText(pos=(15, 0), size=(760, 37), font=2, color_sel=int("0x00d100",16), color=int("0xff3300",16), text=label))
					self.list.append(item)
			if not self.list:
				for label, value in self._onlineCitySearch(what):
					item = [value]
					item.append(MultiContentEntryText(pos=(15, 0), size=(760, 37), font=2, color_sel=int("0x00d100",16), color=int("0xff3300",16), text=label))
					self.list.append(item)
			self.setWindowTitle(": " + what)
		elif self.cityLevel == "root":
			# r12 authority: show every country directly. The database itself keeps
			# Slovakia first, Czechia second, followed by the remaining countries.
			seen = []
			for country, display, value in local:
				if country and country not in seen:
					seen.append(country)
			for country in seen:
				item = ["country|" + country]
				item.append(MultiContentEntryText(pos=(15, 0), size=(760, 40), font=0, color_sel=int("0x00d100",16), color=int("0xffcc00",16), text=self.countryNames.get(country, country)))
				self.list.append(item)
			self.setWindowTitle(": " + _("Select country"))
		else:
			for country, display, value in local:
				if country == self.activeCountry:
					item = [value]
					item.append(MultiContentEntryText(pos=(15, 0), size=(760, 37), font=2, color_sel=int("0x00d100",16), color=int("0xff3300",16), text=display))
					self.list.append(item)
			self.setWindowTitle(": " + self.countryNames.get(self.activeCountry, self.activeCountry or ""))
		self.citylist = []
		self.list2 = []
		try:
			with open("/etc/my_city_Code.txt", "r") as f:
				for line in f:
					self.citylist.append(line)
					x = _cityLine(line)
					display = x[1] if x else line.strip()
					item = [line]
					item.append(MultiContentEntryText(pos=(0, 0), size=(620, 37), font=2, color_sel=int("0x00d100",16), color=int("0xffcc00",16), text=display))
					self.list2.append(item)
		except Exception:
			pass
		if not self.list2:
			item = ["*"]
			item.append(MultiContentEntryText(pos=(0, 0), size=(620, 33), font=0, color_sel=int("0xff3300",16), text=("***  " + _("None city detected") + " !!!  ***")))
			self.list2.append(item)
		self["myCity"].l.setList(self.list2)
		if self.findC:
			self["myCity"].selectionEnabled(0)
		if not self.list:
			item = ["*"]
			item.append(MultiContentEntryText(pos=(15, 0), size=(760, 33), font=0, color_sel=int("0xff3300",16), text=("***  " + _("None city detected") + " !!!  ***")))
			self.list.append(item)
		self["list"].l.setList(self.list)
		self["list"].l.setItemHeight(45)
		self["key_blue"].setText(self.allLabels[2])


	def addNewLine(self, tmp):
		if tmp is not None and tmp != "":
			if self.chckLine(tmp):
				self.session.open(MessageBox, ER_F, MessageBox.TYPE_ERROR, 6)			
			else:
				self.appMCC(tmp)       
            			
	def chckLine(self, tmp):
		try:
			return _cityLine(" ".join(str(tmp).strip().split())) is None
		except Exception:
			return True

	def appMCC(self, tmp):
		path = "/etc/my_city_Code.txt"
		written = False
		try:
			old = open(path, "r").read() if os.path.exists(path) else ""
			lines = [x.strip() for x in old.splitlines() if x.strip()]
			if str(tmp).strip() not in lines:
				written = _atomicWriteText(path, old + ("" if not old or old.endswith("\n") else "\n") + "%s\n" % str(tmp).strip())
			else:
				written = True
		except (IOError, OSError):
			pass
		f = open(path, "r").read() if os.path.exists(path) else ""
		if written and f.find(str(tmp).strip()) != -1:
			selected = _cityLine(str(tmp).strip())
			if selected:
				_setWeatherCityChoices(selected[0])
				config.plugins.setupGlass17.par13.save()
				configfile.save()
				_refreshLiveWeather()
			self.session.open(MessageBox, _("Changes writed successfully !!!"), MessageBox.TYPE_INFO, 6)
			self.generateData()
		else:
			self.session.open(MessageBox, ER_F, MessageBox.TYPE_ERROR, 6)

      
class dirBrowser(Screen):      
         
	skin = """
<screen name="DirBrowser" position="0,0" size="1920,1080" title="Dir Browser" backgroundColor="#ff000000" flags="wfNoBorder">
			<widget position="0,0" size="1920,164" source="global.CurrentTime" render="WarderSettingsHeader" zPosition="-3" /><eLabel position="570,185" size="780,750" backgroundColor="#1a102136" zPosition="-1" /><eLabel position="1348,185" size="2,750" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="570,185" size="2,750" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="570,933" size="780,2" backgroundColor="#003ee8ff" zPosition="1" /><eLabel position="570,185" size="780,2" backgroundColor="#003ee8ff" zPosition="1" /><widget name="filelist" position="585,200" size="750,660" scrollbarMode="showOnDemand" foregroundColor="#00ffffff" backgroundColor="#ff000000" transparent="1" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" zPosition="4" scrollbarBackgroundColor="#00102136" scrollbarForegroundColor="#003ee8ff" />
	<widget source="key_red" render="Label" position="590,885" size="362,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#00ff526a" backgroundColor="#ff000000" noWrap="1" />
	<widget source="key_green" render="Label" position="968,885" size="362,50" zPosition="4" valign="center" halign="center" font="Regular;28" transparent="1" foregroundColor="#0039ff59" backgroundColor="#ff000000" noWrap="1" />
   <eLabel position="590,879" size="362,2" backgroundColor="#00ff526a" zPosition="1" /><eLabel position="968,879" size="362,2" backgroundColor="#0039ff59" zPosition="1" /><widget position="1120,25" size="250,36" font="Regular;25" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%A</convert></widget><widget position="1020,70" size="350,36" font="Regular;24" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="right" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format:%d. %B %Y</convert></widget><widget position="1398,32" size="190,85" font="Regular;62" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Default</convert></widget><widget position="1590,58" size="66,54" font="Regular;38" foregroundColor="#00ffffff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="left" shadowColor="#00071627" shadowOffset="1,1" source="global.CurrentTime" render="Label"><convert type="g17ClockToText">Format::%S</convert></widget><eLabel position="1680,25" size="210,36" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="Version:" /><eLabel position="1680,70" size="210,36" font="Regular;24" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" text="1.0.35" /><eLabel position="1392,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><eLabel position="1664,25" size="2,84" backgroundColor="#003ee8ff" zPosition="5" /><widget position="850,120" size="700,38" font="Regular;25" foregroundColor="#003ee8ff" backgroundColor="#00071627" transparent="1" zPosition="5" valign="center" noWrap="1" halign="center" shadowColor="#00071627" shadowOffset="1,1" source="Title" render="Label" /><eLabel position="0,164" size="1920,21" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,185" size="570,750" backgroundColor="#00071627" zPosition="-2" /><eLabel position="1350,185" size="570,750" backgroundColor="#00071627" zPosition="-2" /><eLabel position="0,935" size="1920,145" backgroundColor="#00071627" zPosition="-2" /></screen>
"""
    
	def __init__(self, session, dd, files=False):
		Screen.__init__(self, session)
		self.files = files
		self.matchingPattern = None
		if self.files:
			self.matchingPattern = r"^.*\.(conf)"
		self.filelist = FileList(dd, showDirectories = True, showFiles = self.files, matchingPattern = self.matchingPattern, inhibitDirs = ["/autofs", "/bin", "/boot", "/dev", "/opt", "/lib", "/proc", "/sbin", "/sys", "/tmp", "/home", "/run"])
		self["filelist"] = self.filelist

		self["actions"] = ActionMap(["SetupActions", "DirectionActions", "ColorActions"],
		{
			"ok": self.ok,
			"cancel": self.cancel,
			"left": self.left,
			"right": self.right,
			"up": self.up,
			"down": self.down,
			"green": self.green,
			"red": self.cancel
		}, -1)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Select"))
		self.onLayoutFinish.append(self.updTitle)

	def updTitle(self):
		a = self["filelist"].getCurrentDirectory()
		if a is not None:
			if a.startswith("/") and a.endswith("/"):
				aa = a.split("/")
				b = len(aa)
				if b > 5:
					a = ".../"+aa[b-4]+"/"+aa[b-3]+"/"+aa[b-2]+"/"
			self.setTitle(a)

	def cancel(self):
		self.close(None)

	def green(self):
		if self.files:
			a = self['filelist'].getCurrentDirectory()
			b = self['filelist'].getFilename()
			if a is None or b is None:
				self.close(None)
			else:
				if a in b:
					self.close(b)				
				else:
					self.close(a + b)
		else:
			ret = self["filelist"].getSelection()[0]
			if self["filelist"].getSelection()[1]:
				if ret is not None and not ret.endswith("/"):
					ret += "/"									
				self.close(ret)

	def up(self):
		self["filelist"].up()

	def down(self):
		self["filelist"].down()

	def left(self):
		self["filelist"].pageUp()

	def right(self):
		self["filelist"].pageDown()

	def ok(self):
		if self["filelist"].canDescent():
			self["filelist"].descent()
			self.updTitle()					

