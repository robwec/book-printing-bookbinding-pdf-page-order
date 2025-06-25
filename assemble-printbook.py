import time
#import numpy as np
import os
import subprocess
from subprocess import call
import math
import cv2
import numpy as np
from PIL import Image
from tqdm import tqdm
import shutil
##prerequisites
'''
sudo apt-get install ghostscript libtiff-tools poppler-utils -y
'''

"""
This script takes a PDF, bursts it into .tif files, dilates the .tifs (making the text larger and bolder), then assembles them into a print order for 4-page duplex folio.
	The reason for dilating the pages is when printing 4-to-a-page, the text is often smaller than readable. Dilate helps make it readable.

This is meant to be printed at 4 pages per sheet, duplex. Then, the pages are picked up in groups (of 25, by default, but can be whatever size you like) of 25 and the pages are cut horizontally through the longer edge, so you have two wide stacks. Then, fold each stack in half. The pages are now arranged such that you just have to stack the top stack on the bottom stack, then continue to the next page.
This format is easy to print and assemble into a book that can fit in the pocket and be read like a book. All you need is scissors.

The best way to print duplex on a consumer printer is to print even pages first, flip the pages and reinsert into the printer (on Brother HL-2270DW printer the pages should face text-up, top text towards the front of the printer so text goes down into its depths), then print odd pages.
"""

"""
PDF input criteria:
Should have decent margins: 0.6 inner, 0.6 outer, 0.4 top, 0 bottom
	This results in a very close cut on the outer margin, and the inner looks big. Perhaps 0.4 inner, 0.8 outer? Then the shift won't put the outer so close to the edge...
"""

#1: explode the PDF into tif
#2: dilate each tif to make it more easily readable.
def explodeTargetPDF_makeTifs(filename, outfolder, fitit=True):
	os.makedirs(outfolder, exist_ok = True)
	#make single-page tifs from full pdf
	time_start = time.time()
	#cmd = "gs -q -dAutoRotatePages=/None -dPDFFitPage -dNOPAUSE -dQUIET -dBATCH -sDEVICE=tiffscaled -r300 -dCenterPages=true -sOutputFile=\"" + outfolder + "/page_%05d.tif\" \""+filename+"\""
	#<>cmd = "gs -q -dAutoRotatePages=/None -dPDFFitPage -dNOPAUSE -dQUIET -dBATCH -sDEVICE=tiff24nc -r300 -dCenterPages=true -sOutputFile=\"" + outfolder + "/page_%05d.tif\" \""+filename+"\"" #HUUUUGE but color.
	if fitit:
		cmd = "gs -q -dAutoRotatePages=/None -dPDFFitPage -dNOPAUSE -dQUIET -dBATCH -sDEVICE=tiff24nc -r300 -dCenterPages=true -sCompression=lzw -sOutputFile=\"" + outfolder + "/page_%05d.tif\" \""+filename+"\"" #compressed color.
	else:
		cmd = "gs -q -dAutoRotatePages=/None -dNOPAUSE -dQUIET -dBATCH -sDEVICE=tiff24nc -r300 -dCenterPages=true -sCompression=lzw -sOutputFile=\"" + outfolder + "/page_%05d.tif\" \""+filename+"\"" #compressed color.
	_ = subprocess.call(cmd, shell = True)
	time_end = time.time()
	print(round(time_end - time_start, 2), "seconds to split the PDF into tifs with ghostscript.")
	return

def dilateTifs(outfolder):
	#dilate the tifs
	time_start = time.time()
	#cmd = "for file in \""+outfolder+"/*.tif\"; do\n\tmogrify -negate -morphology dilate octagon:1 -negate \"$file\"\ndone"
	#_ = subprocess.call(cmd, shell = True)
	files = os.listdir(outfolder)
	files = [x for x in files if x.split(".")[-1] in ['tif', 'tiff']]
	files.sort()
	for f in files:
		cmd = "convert '"+outfolder+"/"+f+"' -negate -morphology dilate octagon:1 -negate \""+outfolder+"/"+f+"\""
		_ = subprocess.call(cmd, shell = True)
	
	time_end = time.time()
	print(round(time_end - time_start, 2), "seconds to dilate all the tifs.")
	return

#3: convert each tiff/tif into a pdf.
def makePDFsFromTIFFs(outfolder, replace_existing=True):
	allimages = os.listdir(outfolder)
	allimages = list(filter(lambda x: x.split(".")[-1] in ["tiff", "tif"], allimages))
	allimages.sort()
	for i in tqdm(range(len(allimages))):
		thisimage = allimages[i]
		if not replace_existing and os.path.exists(outfolder+'/'+thisimage):
			continue
		#cmd = "tiff2pdf \""+outfolder+"/"+thisimage+"\" -o \""+outfolder+"/"+".".join(thisimage.split(".")[:-1])+".pdf"+"\"" #BIG. -z adds compression.
		cmd = "tiff2pdf \""+outfolder+"/"+thisimage+"\" -z -o \""+outfolder+"/"+".".join(thisimage.split(".")[:-1])+".pdf"+"\""
			#sudo apt-get install libtiff-tools
		_ = subprocess.call(cmd, shell=True)
	return

#4: get the correct order to add the PDF pages in to get.
	#prints 1 2 3 4 5 6 7 8 correctly, reading left-to-right, then down, then flip the page over the long edge and 5 is in top left corner.
	#an 8-page document would need to say 1 2 5 6 3 4 7 8 to print correctly.
	#For folio labeling, start at the back of the bottom page in the folio (page 25 in my size). Number from 1 to 50 going up, then from 51 to 100 going down.
def make25FoldPageOrder_2per(n):
	"""
	2 per page: goes from right side down, then from left side up.
	"""
	finished_layout = {}
	max_printsheets = math.ceil(n/4)
	for i in range(1, max_printsheets+1):
		finished_layout[i] = {"front":{"left":-1, "right":-1}, "back":{"left":-1, "right":-1}}
	currentpagenum = 1
	for i in range(1, max_printsheets+1):
		finished_layout[i]["front"]["right"] = currentpagenum
		if currentpagenum+1 <= n:
			finished_layout[i]["back"]["left"] = currentpagenum+1
		currentpagenum += 2
	for i in list(range(1, max_printsheets+1))[::-1]:
		if currentpagenum <= n:
			finished_layout[i]["back"]["right"] = currentpagenum
		if currentpagenum+1 <= n:
			finished_layout[i]["front"]["left"] = currentpagenum+1
		currentpagenum += 2
	return finished_layout

#how to loop through layout:
	#front top left, front top right, front bottom left, front bottom right, back top left, back top right, back bottom left, back bottom right. This is how the print layout will lay the pages going 1234, so go through the layout dict and pull out the page names that are supposed to be at each of those positions.
	#if a page position has -1, insert the blank page there.

def createPDFPageOrder_2PerPage_promiseSize(infolder, outpdfname, savemode = "normal", printer="MFC-L2740DW"):
	'''difference: Target dimensions is 4.25" wide by 6.75" tall, at landscape resolution'''
	allimages = os.listdir(infolder)
	allimages = list(filter(lambda x: x.split(".")[-1] in ["pdf"], allimages))
	allimages.sort()
	allimages = ['"' + infolder + '/' + x + '"' for x in allimages]
	def createBlankPDFPage(outfolder):
		_ = subprocess.call("gs -q -dNOPAUSE -dQUIET -sDEVICE=pdfwrite -o \""+outfolder+"/blank.pdf\"", shell=True)
		return
	
	createBlankPDFPage(".") #blank.pdf in cwd, outside of infolder
	#create and fix layout
	#layout = make25FoldPageOrder(len(allimages), folio_size)
	#import pdb
	#pdb.set_trace()
	layout = make25FoldPageOrder_2per(len(allimages))
	layout = updateLayout_PageNames_2PerPage(allimages, layout)
	#make big image list
	biglist = []
	for i in range(1, len(layout)+1):
		thispage = layout[i]
		biglist.append(layout[i]["front"]["left"])
		biglist.append(layout[i]["front"]["right"])
		biglist.append(layout[i]["back"]["left"])
		biglist.append(layout[i]["back"]["right"])
	if savemode == "combine_add_lines":
		_ = call("rm -rf combined_temp", shell = True)
		os.makedirs("combined_temp", exist_ok = True)
		i = 0; pagenum = 0; lb = len(biglist)
		def saveit_promise(newpage, pagenum, printer):
			#add bold lines
			newpage[:, 1647:1653] = 0
			#_ = cv2.imwrite("combined_"+str(pagenum)+".tif", newpage)
			if printer == "HL-1450" and pagenum % 2 == 0:
				#odd pages need to be shifted 20 pixels to the left and 2 up to align exactly with the even sheet when shrunk to fit page.
				newpage = cv2.warpAffine(src = newpage, M = np.array([[1,0,-35], [0,1,2]]).astype(float), dsize = (3300, 2550))
				newpage[:, -35:] = 255
				newpage[:2, :] = 255
				#problem with this alignment correction is the printer just doesn't print consistently enough in center. Darn. ... but it only does that sometimes. Most of the time it's more consistent.
			
			##swap BGR to RGB
			newpage_rgb = cv2.cvtColor(newpage, cv2.COLOR_BGR2RGB)
			img = Image.fromarray(newpage_rgb)
			#print("saving 2!")
			_ = img.save("combined_temp/combined_"+str(pagenum).zfill(5)+".tif", compression="tiff_deflate", dpi=(300,300), resolution=24)
			return
		
		while i < lb:
			newpage = np.ones((2550, 3300, 3)).astype(np.uint8)*255
			topleft = cv2.imread(biglist[i][1:-4]+"tif")
			if topleft is not None:
				#3300x2550 resized into 2550x1650 -> 2135x1650 OR 3300x1970 -> use 2135x1650. That then leaves 365 horizontal pixels left, so put it around 182 in.
				newpage[182:(182+2135), :1650] = cv2.resize(topleft, (1650, 2135), 0, 0, cv2.INTER_LINEAR)
			
			i += 1
			if i >= lb:
				saveit_promise(newpage, pagenum, printer)
				break
			topright = cv2.imread(biglist[i][1:-4]+"tif")
			if topright is not None:
				newpage[182:(182+2135), 1650:] = cv2.resize(topright, (1650, 2135), 0, 0, cv2.INTER_LINEAR)
			i += 1
			if i >= lb:
				saveit_promise(newpage, pagenum, printer)
				break
			
			saveit_promise(newpage, pagenum, printer)
			pagenum += 1
		
		makePDFsFromTIFFs("combined_temp")
		infolder = "combined_temp"
		allimages = os.listdir(infolder)
		allimages = list(filter(lambda x: x.split(".")[-1] in ["pdf"], allimages))
		allimages.sort()
		biglist = ['"' + infolder + '/' + x + '"' for x in allimages]
	
	bigblob = " ".join(biglist)
	#create full pdf
	cmd = "pdftk "+bigblob+" cat output \""+outpdfname+"\""
	_ = subprocess.call(cmd, shell=True)
	''' #install
	sudo add-apt-repository ppa:malteworld/ppa
	sudo apt-get update
	sudo apt-get install pdftk
	'''
	#clean up the blank
	_ = subprocess.call("rm blank.pdf", shell=True)
	return


def createPDFPageOrder_2PerPage(infolder, outpdfname, savemode = "normal", printer="MFC-L2740DW"):
	allimages = os.listdir(infolder)
	allimages = list(filter(lambda x: x.split(".")[-1] in ["pdf"], allimages))
	allimages.sort()
	allimages = ['"' + infolder + '/' + x + '"' for x in allimages]
	def createBlankPDFPage(outfolder):
		_ = subprocess.call("gs -q -dNOPAUSE -dQUIET -sDEVICE=pdfwrite -o \""+outfolder+"/blank.pdf\"", shell=True)
		return
	createBlankPDFPage(".") #blank.pdf in cwd, outside of infolder
	#create and fix layout
	#layout = make25FoldPageOrder(len(allimages), folio_size)
	#import pdb
	#pdb.set_trace()
	layout = make25FoldPageOrder_2per(len(allimages))
	layout = updateLayout_PageNames_2PerPage(allimages, layout)
	#make big image list
	biglist = []
	for i in range(1, len(layout)+1):
		thispage = layout[i]
		biglist.append(layout[i]["front"]["left"])
		biglist.append(layout[i]["front"]["right"])
		biglist.append(layout[i]["back"]["left"])
		biglist.append(layout[i]["back"]["right"])
	
	if savemode == "combine_add_lines":
		_ = call("rm -rf combined_temp", shell = True)
		os.makedirs("combined_temp", exist_ok = True)
		i = 0; pagenum = 0; lb = len(biglist)
		def saveit(newpage, pagenum, printer):
			#add bold lines
			newpage[:, 1647:1653] = 0
			#_ = cv2.imwrite("combined_"+str(pagenum)+".tif", newpage)
			if printer == "HL-1450" and pagenum % 2 == 0:
				#odd pages need to be shifted 20 pixels to the left and 2 up to align exactly with the even sheet when shrunk to fit page.
				newpage = cv2.warpAffine(src = newpage, M = np.array([[1,0,-35], [0,1,2]]).astype(float), dsize = (3300, 2550))
				newpage[:, -35:] = 255
				newpage[:2, :] = 255
				#problem with this alignment correction is the printer just doesn't print consistently enough in center. Darn. ... but it only does that sometimes. Most of the time it's more consistent.
			
			##swap BGR to RGB
			newpage_rgb = cv2.cvtColor(newpage, cv2.COLOR_BGR2RGB)
			img = Image.fromarray(newpage_rgb)
			#print("saving 2!")
			_ = img.save("combined_temp/combined_"+str(pagenum).zfill(5)+".tif", compression="tiff_deflate", dpi=(300,300), resolution=24)
			return
		while i < lb:
			newpage = np.ones((2550, 3300, 3)).astype(np.uint8)*255
			topleft = cv2.imread(biglist[i][1:-4]+"tif")
			if topleft is not None:
				#3300x2550 resized into 2550x1650 -> 2135x1650 OR 3300x1970 -> use 2135x1650. That then leaves 365 horizontal pixels left, so put it around 182 in.
				newpage[182:(182+2135), :1650] = cv2.resize(topleft, (1650, 2135), 0, 0, cv2.INTER_LINEAR)
			i += 1
			if i >= lb:
				saveit(newpage, pagenum, printer)
				break
			topright = cv2.imread(biglist[i][1:-4]+"tif")
			if topright is not None:
				newpage[182:(182+2135), 1650:] = cv2.resize(topright, (1650, 2135), 0, 0, cv2.INTER_LINEAR)
			i += 1
			if i >= lb:
				saveit(newpage, pagenum, printer)
				break
			saveit(newpage, pagenum, printer)
			pagenum += 1
		
		makePDFsFromTIFFs("combined_temp")
		infolder = "combined_temp"
		allimages = os.listdir(infolder)
		allimages = list(filter(lambda x: x.split(".")[-1] in ["pdf"], allimages))
		allimages.sort()
		biglist = ['"' + infolder + '/' + x + '"' for x in allimages]
	
	bigblob = " ".join(biglist)
	#create full pdf
	cmd = "pdftk "+bigblob+" cat output \""+outpdfname+"\""
	_ = subprocess.call(cmd, shell=True)
	''' #install
	sudo add-apt-repository ppa:malteworld/ppa
	sudo apt-get update
	sudo apt-get install pdftk
	'''
	#clean up the blank
	_ = subprocess.call("rm blank.pdf", shell=True)
	return

def updateLayout_PageNames_2PerPage(allimages, layout):
	def getLayoutName_forPagePos(pagepos, allimages):
		if pagepos == -1:
			return "blank.pdf"
		else:
			return allimages[pagepos-1]
	for i in range(1, len(layout)+1):
		'''
		if layout[i]["front"]["top_left"] == -1:
			layout[i]["front"]["top_left"] = "blank.pdf"
		else:
			layout[i]["front"]["top_left"] = allimages[layout[i]["front"]["top_left"]-1]
		'''
		layout[i]["front"]["left"] = getLayoutName_forPagePos(layout[i]["front"]["left"], allimages)
		layout[i]["front"]["right"] = getLayoutName_forPagePos(layout[i]["front"]["right"], allimages)
		layout[i]["back"]["left"] = getLayoutName_forPagePos(layout[i]["back"]["left"], allimages)
		layout[i]["back"]["right"] = getLayoutName_forPagePos(layout[i]["back"]["right"], allimages)
	return layout

def pdf_4panels_Main_2Big(inpdfname, tempfolder, outpdfname):
	explodeTargetPDF_makeTifs(inpdfname, tempfolder)
	dilateTifs(outfolder)
	#shiftMargins_inner(tempfolder)
	makePDFsFromTIFFs(tempfolder)
	#createPDFPageOrder_4PerPage(tempfolder, outpdfname)
	createPDFPageOrder_2PerPage(tempfolder, outpdfname)
	return

def shiftMargins_inner(tempfolder, grayscale=False):
	"""
	odd-numbered pages (right side): shift several px to right
	even-numbered pages (left side): shift several px to left
	"""
	time_start = time.time()
	files = os.listdir(tempfolder)
	files = [tempfolder + "/" + x for x in files]
	files.sort()
	#dilate the tifs
	for i in range(len(files)):
		if i % 2 == 0:
			#shift = '+150+0' #bad on 0.6/0.6 inner/outer margins. Shave off 0.2 = 30 pixels -> 120 px shift
			#shift = '+120+0'
			shift = '+100+0' #brother: May need to shift the right page ~20px less
		else:
			shift = '-120+0' 
		if grayscale:
			graystr = '-colorspace gray '
		else:
			graystr = ''
		cmd = "mogrify -page "+shift+" -background white "+graystr+"-flatten +repage \""+files[i]+"\""
		_ = subprocess.call(cmd, shell = True)
	#150: almost the maximum.
	time_end = time.time()
	print(round(time_end - time_start, 2), "seconds to shift", len(files), "tifs.")
		#47 seconds for 208 pages. fast.
	return

def grayScale_folder(outfolder):
	time_start = time.time()
	#cmd = for f in *.tif; do    convert "$f" -colorspace gray +repage "$f"; done
	#_ = subprocess.call(cmd, shell = True)
	files = os.listdir(outfolder)
	files = [x for x in files if x.split(".")[-1] in ['tif', 'tiff']]
	files.sort()
	for f in files:
		cmd = "convert '"+outfolder+"/"+f+"' -colorspace gray +repage \""+outfolder+"/"+f+"\""
		_ = subprocess.call(cmd, shell = True)
	
	time_end = time.time()
	print(round(time_end - time_start, 2), "seconds to grayscale all the tifs.")
	return


def main_assemble(tempfolder, outpdfname, shiftmargins=True):
	#explodeTargetPDF_makeTifs(inpdfname, tempfolder)
	if shiftmargins:
		shiftMargins_inner(tempfolder)
	
	makePDFsFromTIFFs(tempfolder)
	#createPDFPageOrder_4PerPage(tempfolder, outpdfname)
	createPDFPageOrder_2PerPage(tempfolder, outpdfname)
	return

###BONUS: clasps
#4: get the correct order to add the PDF pages in to get.
	#prints 1 2 3 4 5 6 7 8 correctly, reading left-to-right, then down, then flip the page over the long edge and 5 is in top left corner.
	#an 8-page document would need to say 1 2 5 6 3 4 7 8 to print correctly.
	#For folio labeling, start at the back of the bottom page in the folio (page 25 in my size). Number from 1 to 50 going up, then from 51 to 100 going down.
def make25FoldPageOrder_printfold(n, folio_size = 25):
	finished_layout = {}
	max_printsheets = math.ceil(n/8)
	for i in range(1, max_printsheets+1):
		finished_layout[i] = {"front":{"top_left":-1, "top_right":-1, "bottom_left":-1, "bottom_right":-1}, "back":{"top_left":-1, "top_right":-1, "bottom_left":-1, "bottom_right":-1}}
	foldgroups = list(range(0, n))[::folio_size*8]
	num_folios = len(foldgroups)
	currentpagenum = 0
	folio_num = 0
	currentprintsheetnum = 0
	back = "back"
	top = "top"
	left = "right"
	while currentpagenum <= n:
		#if currentpagenum % (8*folio_size) == 0:
		folio_num += 1
		currentpagenum = 8*folio_size*(folio_num-1) + 1
		maxoksheet = min(folio_size*folio_num, max_printsheets)
		currentprintsheetnum = maxoksheet
		minoksheet = folio_size*(folio_num-1)+1
		#do it in groups of 8
		#stack direction: bottom to top, top left front (up from back at bottom of stack)
		while currentprintsheetnum >= minoksheet:
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["back"]["top_right"] = currentpagenum
			currentpagenum += 1
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["front"]["top_left"] = currentpagenum
			currentpagenum += 1
			currentprintsheetnum -= 1
		currentprintsheetnum = minoksheet
		#stack direction: top to bottom, top right side front.
		while currentprintsheetnum <= maxoksheet:
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["front"]["top_right"] = currentpagenum
			currentpagenum += 1
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["back"]["top_left"] = currentpagenum
			currentpagenum += 1
			currentprintsheetnum += 1
		currentprintsheetnum = maxoksheet
		#stack direction: bottom to top, bottom left side up from back.
		while currentprintsheetnum >= minoksheet:
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["back"]["bottom_right"] = currentpagenum
			currentpagenum += 1
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["front"]["bottom_left"] = currentpagenum
			currentpagenum += 1
			currentprintsheetnum -= 1
		currentprintsheetnum = minoksheet
		#stack direction: top to bottom, bottom right side front to back.
		while currentprintsheetnum <= maxoksheet:
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["front"]["bottom_right"] = currentpagenum
			currentpagenum += 1
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["back"]["bottom_left"] = currentpagenum
			currentpagenum += 1
			currentprintsheetnum += 1
	return finished_layout

def make25FoldPageOrder(n):
	"""
	cut and clasp version: print first 1/2 pages consecutively on top, then second 1/2 consecutively on bottom. In other words, folio size is fixed to ceiling(n/2).
	"""
	folio_size = math.ceil(n/2)
	finished_layout = {}
	max_printsheets = math.ceil(n/8)
	for i in range(1, max_printsheets+1):
		finished_layout[i] = {"front":{"top_left":-1, "top_right":-1, "bottom_left":-1, "bottom_right":-1}, "back":{"top_left":-1, "top_right":-1, "bottom_left":-1, "bottom_right":-1}}
	foldgroups = list(range(0, n))[::folio_size*8]
	num_folios = len(foldgroups)
	currentpagenum = 0
	folio_num = 0
	currentprintsheetnum = 0
	back = "back"
	top = "top"
	left = "right"
	while currentpagenum <= n:
		#if currentpagenum % (8*folio_size) == 0:
		folio_num += 1
		currentpagenum = 8*folio_size*(folio_num-1) + 1
		maxoksheet = min(folio_size*folio_num, max_printsheets)
		currentprintsheetnum = maxoksheet
		minoksheet = folio_size*(folio_num-1)+1
		#do it in groups of 8
		#stack direction: bottom to top, top left front (up from back at bottom of stack)
		while currentprintsheetnum >= minoksheet:
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["back"]["top_right"] = currentpagenum
			currentpagenum += 1
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["front"]["top_left"] = currentpagenum
			currentpagenum += 1
			currentprintsheetnum -= 1
		currentprintsheetnum = minoksheet
		#stack direction: top to bottom, top right side front.
		while currentprintsheetnum <= maxoksheet:
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["front"]["top_right"] = currentpagenum
			currentpagenum += 1
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["back"]["top_left"] = currentpagenum
			currentpagenum += 1
			currentprintsheetnum += 1
		currentprintsheetnum = maxoksheet
		#stack direction: bottom to top, bottom left side up from back.
		while currentprintsheetnum >= minoksheet:
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["back"]["bottom_right"] = currentpagenum
			currentpagenum += 1
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["front"]["bottom_left"] = currentpagenum
			currentpagenum += 1
			currentprintsheetnum -= 1
		currentprintsheetnum = minoksheet
		#stack direction: top to bottom, bottom right side front to back.
		while currentprintsheetnum <= maxoksheet:
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["front"]["bottom_right"] = currentpagenum
			currentpagenum += 1
			if currentpagenum > n:
				break
			finished_layout[currentprintsheetnum]["back"]["bottom_left"] = currentpagenum
			currentpagenum += 1
			currentprintsheetnum += 1
	return finished_layout

#how to loop through layout:
	#front top left, front top right, front bottom left, front bottom right, back top left, back top right, back bottom left, back bottom right. This is how the print layout will lay the pages going 1234, so go through the layout dict and pull out the page names that are supposed to be at each of those positions.
	#if a page position has -1, insert the blank page there.
def createPDFPageOrder_4PerPage(infolder, outpdfname, savemode = "normal", printer="MFC-L2740DW", pagesize=(2550,3300)):
	allimages = os.listdir(infolder)
	allimages = list(filter(lambda x: x.split(".")[-1] in ["pdf"], allimages))
	allimages.sort()
	allimages = ['"' + infolder + '/' + x + '"' for x in allimages]
	def createBlankPDFPage(outfolder):
		_ = subprocess.call("gs -q -dNOPAUSE -dQUIET -sDEVICE=pdfwrite -o \""+outfolder+"/blank.pdf\"", shell=True)
		return
	createBlankPDFPage(".") #blank.pdf in cwd, outside of infolder
	#create and fix layout
	#layout = make25FoldPageOrder(len(allimages), folio_size)
	layout = make25FoldPageOrder(len(allimages))
	layout = updateLayout_PageNames_4PerPage(allimages, layout)
	#make big image list
	biglist = []
	for i in range(1, len(layout)+1):
		thispage = layout[i]
		biglist.append(layout[i]["front"]["top_left"])
		biglist.append(layout[i]["front"]["top_right"])
		biglist.append(layout[i]["front"]["bottom_left"])
		biglist.append(layout[i]["front"]["bottom_right"])
		biglist.append(layout[i]["back"]["top_left"])
		biglist.append(layout[i]["back"]["top_right"])
		biglist.append(layout[i]["back"]["bottom_left"])
		biglist.append(layout[i]["back"]["bottom_right"])
	if savemode == "combine_add_lines":
		_ = call("rm -rf combined_temp", shell = True)
		os.makedirs("combined_temp", exist_ok = True)
		i = 0; pagenum = 0; lb = len(biglist)
		def saveit(newpage, pagenum, printer):
			#add bold lines
			newpage[pagesize[1]//2-3:pagesize[1]//2+3, :] = 0
			newpage[:, pagesize[0]//2-3:pagesize[0]//2+3] = 0
			#_ = cv2.imwrite("combined_"+str(pagenum)+".tif", newpage)
			if printer == "HL-1450" and pagenum % 2 == 0:
				#odd pages need to be shifted 20 pixels to the left and 2 up to align exactly with the even sheet when shrunk to fit page.
				newpage = cv2.warpAffine(src = newpage, M = np.array([[1,0,-35], [0,1,2]]).astype(float), dsize = pagesize)
				newpage[:, -35:] = 255
				newpage[:2, :] = 255
				#problem with this alignment correction is the printer just doesn't print consistently enough in center. Darn. ... but it only does that sometimes. Most of the time it's more consistent.
			if printer == "MFC-L2740DW" and pagenum % 2 == 0:
				#THIS WAS DESIGNED FOR PRINTING STYLE: "FIT TO PAGE". However, it also works for printing with no scaling.
				shift_odd_pages_right = 10
				shift_odd_pages_up = 20
				newpage = cv2.warpAffine(src = newpage, M = np.array([[1,0,shift_odd_pages_right], [0,1,shift_odd_pages_up]]).astype(float), dsize = pagesize)
				if shift_odd_pages_right > 0:
					newpage[:, :shift_odd_pages_right] = 255
				elif shift_odd_pages_right < 0:
					newpage[:, shift_odd_pages_right:] = 255
				
				if shift_odd_pages_up > 0:
					newpage[:shift_odd_pages_up, :] = 255
				elif shift_odd_pages_up < 0:
					newpage[shift_odd_pages_up:, :] = 255
			if printer == "Canon-G2060" and pagenum % 2 == 0:
				#THIS WAS DESIGNED FOR PRINTING STYLE: "FIT TO PAGE". However, it also works for printing with no scaling.
				shift_odd_pages_right = -18
				shift_odd_pages_up = 0
				newpage = cv2.warpAffine(src = newpage, M = np.array([[1,0,shift_odd_pages_right], [0,1,shift_odd_pages_up]]).astype(float), dsize = pagesize)
				if shift_odd_pages_right > 0:
					newpage[:, :shift_odd_pages_right] = 255
				elif shift_odd_pages_right < 0:
					newpage[:, shift_odd_pages_right:] = 255
				
				if shift_odd_pages_up > 0:
					newpage[:shift_odd_pages_up, :] = 255
				elif shift_odd_pages_up < 0:
					newpage[shift_odd_pages_up:, :] = 255
			
			##swap BGR to RGB
			newpage_rgb = cv2.cvtColor(newpage, cv2.COLOR_BGR2RGB)
			img = Image.fromarray(newpage_rgb)
			#print("saving 4!")
			_ = img.save("combined_temp/combined_"+str(pagenum).zfill(5)+".tif", compression="tiff_deflate", dpi=(300,300), resolution=24)
			return
		while i < lb:
			newpage = np.ones((3300, 2550, 3)).astype(np.uint8)*255
			topleft = cv2.imread(biglist[i][1:-4]+"tif")
			if topleft is not None:
				newpage[0:1650, 0:1275] = cv2.resize(topleft, (1275, 1650), 0, 0, cv2.INTER_LINEAR)
			
			i += 1
			if i >= lb:
				saveit(newpage, pagenum, printer)
				break
			
			topright = cv2.imread(biglist[i][1:-4]+"tif")
			if topright is not None:
				newpage[0:1650, 1275:] = cv2.resize(topright, (1275, 1650), 0, 0, cv2.INTER_LINEAR)
			
			i += 1
			if i >= lb:
				saveit(newpage, pagenum, printer)
				break
			
			bottomleft = cv2.imread(biglist[i][1:-4]+"tif")
			if bottomleft is not None:
				newpage[1650:, 0:1275] = cv2.resize(bottomleft, (1275, 1650), 0, 0, cv2.INTER_LINEAR)
			
			i += 1
			if i >= lb:
				saveit(newpage, pagenum, printer)
				break
			
			bottomright = cv2.imread(biglist[i][1:-4]+"tif")
			if bottomright is not None:
				newpage[1650:, 1275:] = cv2.resize(bottomright, (1275, 1650), 0, 0, cv2.INTER_LINEAR)
			
			i += 1
			saveit(newpage, pagenum, printer)
			pagenum += 1
		
		makePDFsFromTIFFs("combined_temp")
		infolder = "combined_temp"
		allimages = os.listdir(infolder)
		allimages = list(filter(lambda x: x.split(".")[-1] in ["pdf"], allimages))
		allimages.sort()
		biglist = ['"' + infolder + '/' + x + '"' for x in allimages]
	bigblob = " ".join(biglist)
	#create full pdf: single pages
	cmd = "pdftk "+bigblob+" cat output \""+outpdfname+"\""
	_ = subprocess.call(cmd, shell=True)
	''' #install
	sudo add-apt-repository ppa:malteworld/ppa
	sudo apt-get update
	sudo apt-get install pdftk
	'''
	#clean up the blank
	_ = subprocess.call("rm blank.pdf", shell=True)
	return

def updateLayout_PageNames_4PerPage(allimages, layout):
	def getLayoutName_forPagePos(pagepos, allimages):
		if pagepos == -1:
			return "blank.pdf"
		else:
			return allimages[pagepos-1]
	for i in range(1, len(layout)+1):
		'''
		if layout[i]["front"]["top_left"] == -1:
			layout[i]["front"]["top_left"] = "blank.pdf"
		else:
			layout[i]["front"]["top_left"] = allimages[layout[i]["front"]["top_left"]-1]
		'''
		layout[i]["front"]["top_left"] = getLayoutName_forPagePos(layout[i]["front"]["top_left"], allimages)
		layout[i]["front"]["top_right"] = getLayoutName_forPagePos(layout[i]["front"]["top_right"], allimages)
		layout[i]["front"]["bottom_left"] = getLayoutName_forPagePos(layout[i]["front"]["bottom_left"], allimages)
		layout[i]["front"]["bottom_right"] = getLayoutName_forPagePos(layout[i]["front"]["bottom_right"], allimages)
		layout[i]["back"]["top_left"] = getLayoutName_forPagePos(layout[i]["back"]["top_left"], allimages)
		layout[i]["back"]["top_right"] = getLayoutName_forPagePos(layout[i]["back"]["top_right"], allimages)
		layout[i]["back"]["bottom_left"] = getLayoutName_forPagePos(layout[i]["back"]["bottom_left"], allimages)
		layout[i]["back"]["bottom_right"] = getLayoutName_forPagePos(layout[i]["back"]["bottom_right"], allimages)
	return layout


def grayBoldFolder_8pdfs(foldername, savemode, printer, editstuff=False):
	st = time.time()
	#
	if editstuff:
		shiftMargins_inner(foldername)
		call('cp -R \"'+foldername+'\" \"'+foldername+'_gray\"', shell=True)
		call('cp -R \"'+foldername+'\" \"'+foldername+'_bold\"', shell=True)
		dilateTifs(foldername+"_bold")
		call('cp -R \"'+foldername+'_bold\" \"'+foldername+'_bold_gray\"', shell=True)
		grayScale_folder(foldername+"_gray")
		grayScale_folder(foldername+"_bold_gray")
	#
	#main_assemble(foldername, foldername+"_color.pdf", shiftmargins=False)
	#main_assemble(foldername+"_bold", foldername+"_color_bold.pdf", shiftmargins=False)
	#main_assemble(foldername+"_gray", foldername+"_gray.pdf", shiftmargins=False)
	#main_assemble(foldername+"_bold_gray", foldername+"_gray_bold.pdf", shiftmargins=False)
	makePDFsFromTIFFs(foldername, replace_existing=editstuff)
	makePDFsFromTIFFs(foldername+"_bold", replace_existing=editstuff)
	makePDFsFromTIFFs(foldername+"_gray", replace_existing=editstuff)
	makePDFsFromTIFFs(foldername+"_bold_gray", replace_existing=editstuff)
	#
	createPDFPageOrder_2PerPage(foldername, foldername+"_color.pdf", savemode=savemode, printer=printer)
	createPDFPageOrder_2PerPage(foldername+"_bold", foldername+"_color_bold.pdf", savemode=savemode, printer=printer)
	createPDFPageOrder_2PerPage(foldername+"_gray", foldername+"_gray.pdf", savemode=savemode, printer=printer)
	createPDFPageOrder_2PerPage(foldername+"_bold_gray", foldername+"_gray_bold.pdf", savemode=savemode, printer=printer)
	#
	createPDFPageOrder_4PerPage(foldername, foldername+"_4page_color.pdf", savemode=savemode, printer=printer)
	createPDFPageOrder_4PerPage(foldername+"_gray", foldername+"_4page_gray.pdf", savemode=savemode, printer=printer)
	createPDFPageOrder_4PerPage(foldername+"_bold", foldername+"_4page_color_bold.pdf", savemode=savemode, printer=printer)
	createPDFPageOrder_4PerPage(foldername+"_bold_gray", foldername+"_4page_gray_bold.pdf", savemode=savemode, printer=printer)
	#
	print(round(time.time() - st, 2), "seconds for four 2-page pdfs + four 4-page pdfs.")
	return

def justMakeColorBold4page(foldername, savemode, printer, editstuff=False, shiftmargins=True):
	st = time.time()
	#
	if editstuff:
		if shiftmargins:
			shiftMargins_inner(foldername)
		
		#<>call('cp -R \"'+foldername+'\" \"'+foldername+'_gray\"', shell=True)
		call('cp -R \"'+foldername+'\" \"'+foldername+'_bold\"', shell=True)
		dilateTifs(foldername+"_bold")
		#<>call('cp -R \"'+foldername+'_bold\" \"'+foldername+'_bold_gray\"', shell=True)
		#<>grayScale_folder(foldername+"_gray")
		#<>grayScale_folder(foldername+"_bold_gray")
	#
	#main_assemble(foldername, foldername+"_color.pdf", shiftmargins=False)
	#main_assemble(foldername+"_bold", foldername+"_color_bold.pdf", shiftmargins=False)
	#main_assemble(foldername+"_gray", foldername+"_gray.pdf", shiftmargins=False)
	#main_assemble(foldername+"_bold_gray", foldername+"_gray_bold.pdf", shiftmargins=False)
	# makePDFsFromTIFFs(foldername, replace_existing=editstuff)
	makePDFsFromTIFFs(foldername+"_bold", replace_existing=editstuff)
	# makePDFsFromTIFFs(foldername+"_gray", replace_existing=editstuff)
	# makePDFsFromTIFFs(foldername+"_bold_gray", replace_existing=editstuff)
	#
	# createPDFPageOrder_2PerPage(foldername, foldername+"_color.pdf", savemode=savemode, printer=printer)
	# createPDFPageOrder_2PerPage(foldername+"_bold", foldername+"_color_bold.pdf", savemode=savemode, printer=printer)
	# createPDFPageOrder_2PerPage(foldername+"_gray", foldername+"_gray.pdf", savemode=savemode, printer=printer)
	# createPDFPageOrder_2PerPage(foldername+"_bold_gray", foldername+"_gray_bold.pdf", savemode=savemode, printer=printer)
	# #
	# createPDFPageOrder_4PerPage(foldername, foldername+"_4page_color.pdf", savemode=savemode, printer=printer)
	# createPDFPageOrder_4PerPage(foldername+"_gray", foldername+"_4page_gray.pdf", savemode=savemode, printer=printer)
	createPDFPageOrder_4PerPage(foldername+"_bold", foldername+"_4page_color_bold.pdf", savemode=savemode, printer=printer)
	# createPDFPageOrder_4PerPage(foldername+"_bold_gray", foldername+"_4page_gray_bold.pdf", savemode=savemode, printer=printer)
	#
	print(round(time.time() - st, 2), "seconds for just 4-page color bold.")
	return

def justMakeColorBold2and4page(foldername, savemode, printer, editstuff=False, shiftmargins=True):
	st = time.time()
	#
	if editstuff:
		if shiftmargins:
			shiftMargins_inner(foldername)
		
		#<>call('cp -R \"'+foldername+'\" \"'+foldername+'_gray\"', shell=True)
		call('cp -R \"'+foldername+'\" \"'+foldername+'_bold\"', shell=True)
		dilateTifs(foldername+"_bold")
		#<>call('cp -R \"'+foldername+'_bold\" \"'+foldername+'_bold_gray\"', shell=True)
		#<>grayScale_folder(foldername+"_gray")
		#<>grayScale_folder(foldername+"_bold_gray")
	#
	#main_assemble(foldername, foldername+"_color.pdf", shiftmargins=False)
	#main_assemble(foldername+"_bold", foldername+"_color_bold.pdf", shiftmargins=False)
	#main_assemble(foldername+"_gray", foldername+"_gray.pdf", shiftmargins=False)
	#main_assemble(foldername+"_bold_gray", foldername+"_gray_bold.pdf", shiftmargins=False)
	# makePDFsFromTIFFs(foldername, replace_existing=editstuff)
	makePDFsFromTIFFs(foldername+"_bold", replace_existing=editstuff)
	# makePDFsFromTIFFs(foldername+"_gray", replace_existing=editstuff)
	# makePDFsFromTIFFs(foldername+"_bold_gray", replace_existing=editstuff)
	#
	# createPDFPageOrder_2PerPage(foldername, foldername+"_color.pdf", savemode=savemode, printer=printer)
	createPDFPageOrder_2PerPage(foldername+"_bold", foldername+"_color_bold.pdf", savemode=savemode, printer=printer)
	# createPDFPageOrder_2PerPage(foldername+"_gray", foldername+"_gray.pdf", savemode=savemode, printer=printer)
	# createPDFPageOrder_2PerPage(foldername+"_bold_gray", foldername+"_gray_bold.pdf", savemode=savemode, printer=printer)
	# #
	# createPDFPageOrder_4PerPage(foldername, foldername+"_4page_color.pdf", savemode=savemode, printer=printer)
	# createPDFPageOrder_4PerPage(foldername+"_gray", foldername+"_4page_gray.pdf", savemode=savemode, printer=printer)
	createPDFPageOrder_4PerPage(foldername+"_bold", foldername+"_4page_color_bold.pdf", savemode=savemode, printer=printer)
	# createPDFPageOrder_4PerPage(foldername+"_bold_gray", foldername+"_4page_gray_bold.pdf", savemode=savemode, printer=printer)
	#
	print(round(time.time() - st, 2), "seconds for 2 and 4-page color bold.")
	return


def justMakeGrayBoldBook_2PerAnd4Per(foldername, editstuff=False, savemode="combine_add_lines", printer="MFC-L2740DW"):
	st = time.time()
	if editstuff:
		shiftMargins_inner(foldername)
		_ = call('cp -R \"'+foldername+'\" \"'+foldername+'_bold\"', shell=True)
		dilateTifs(foldername+"_bold")
		#_ = call('cp -R \"'+foldername+'\" \"'+foldername+'_bold_gray\"', shell=True)
		#grayScale_folder(foldername+"_bold_gray")
	
	#main_assemble(foldername, foldername+"_color.pdf", shiftmargins=False)
	#main_assemble(foldername+"_bold", foldername+"_color_bold.pdf", shiftmargins=False)
	#main_assemble(foldername+"_gray", foldername+"_gray.pdf", shiftmargins=False)
	#main_assemble(foldername+"_bold_gray", foldername+"_gray_bold.pdf", shiftmargins=False)
	#makePDFsFromTIFFs(foldername)
	#makePDFsFromTIFFs(foldername+"_bold")
	#makePDFsFromTIFFs(foldername+"_gray")
	#makePDFsFromTIFFs(foldername+"_bold_gray", replace_existing=editstuff)
	makePDFsFromTIFFs(foldername+"_bold", replace_existing=editstuff)
	
	#
	#createPDFPageOrder_2PerPage(foldername, foldername+"_color.pdf")
	#createPDFPageOrder_2PerPage(foldername+"_bold", foldername+"_color_bold.pdf")
	#createPDFPageOrder_2PerPage(foldername+"_gray", foldername+"_gray.pdf")
	#createPDFPageOrder_2PerPage(foldername+"_bold_gray", foldername+"_gray_bold.pdf", printer=printer)
	createPDFPageOrder_2PerPage(foldername+"_bold", foldername+"_gray_bold_lines.pdf", printer=printer, savemode="combine_add_lines")
	#
	#createPDFPageOrder_4PerPage(foldername, foldername+"_4page_color.pdf")
	#createPDFPageOrder_4PerPage(foldername+"_gray", foldername+"_4page_gray.pdf")
	#createPDFPageOrder_4PerPage(foldername+"_bold", foldername+"_4page_color_bold.pdf")
	createPDFPageOrder_4PerPage(foldername+"_bold", foldername+"_4page_gray_bold_lines.pdf", printer=printer, savemode="combine_add_lines")
	#
	#_ = call('rm -rf combined_temp', shell=True)
	#
	print(round(time.time() - st, 2), "seconds for bold gray 2-page pdf + 4-page pdf.")
	return

default_printer = "MFC-L2740DW"
#default_printer = "Canon-G2060" #"Epson-ET-2760"
color_printer = "Canon-G2060"

def pipeline_BW(myfile):
	explodeTargetPDF_makeTifs(myfile, "out")
	justMakeGrayBoldBook_2PerAnd4Per("out", editstuff=True, savemode="combine_add_lines", printer=default_printer)
	try:
		shutil.rmtree('combined_temp')
		shutil.rmtree('out')
		shutil.rmtree('out_bold')
	except:
		pass
	
	return

def pipeline_all(myfile):
	explodeTargetPDF_makeTifs(myfile, "out")
	grayBoldFolder_8pdfs("out", savemode="combine_add_lines", printer=default_printer, editstuff=True)
	try:
		shutil.rmtree('combined_temp')
		shutil.rmtree('out')
		shutil.rmtree('out_bold')
	except:
		pass
	
	return

##main commands:
#pipeline_BW("test.pdf")
#pipeline_all("test.pdf")

##waterproof print notes: Koala paper we wanted Thicker Paper in the Advanced print menu, but for the Highh Image 200x vinyl, we want Thin Paper instead. Thick Paper will grab it too hard and mess it up!

