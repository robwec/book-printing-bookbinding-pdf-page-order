import os
import re
import cv2
import numpy as np
from subprocess import call
from tqdm import tqdm
import shutil
import time
import math
import pdb

def roundup_nstacks(n_imgs, nstacks):
    while n_imgs % (2*nstacks) != 0:
        n_imgs += 1
    
    return n_imgs    

def make_pageorder(n_imgs, rows, cols):
    ##get numbers
    n_imgs_orig = n_imgs
    nstacks = rows*cols
    ##pad imgs to fill all of last page
    n_imgs = roundup_nstacks(n_imgs, nstacks)
    #ndoublesidedpages = int(round(n_imgs/(2*nstacks)))
    ndoublesidedpages = int(round(2*nstacks))
    
    ##next, we get the first page number for each front page
    #firstpagenums = list(range(1, math.ceil(n_imgs/nstacks)))
    firstpagenums = [(2*nstacks*x) for x in list(range(0, math.ceil(n_imgs/(2*rows*cols))+1))]
    #firstpagenums = list(range(n_imgs//2)) #note: even number = odd page
    #print(firstpagenums)
    
    pagenumbers = []
    for page_i in range(ndoublesidedpages):
        if page_i % 2 == 1:
            newpages = []
            for j in range(nstacks):
                newpages.append(page_i+firstpagenums[0]+j*2*nstacks)
            
            #print(newpages)
            newpages = np.array(newpages).reshape(rows, cols)
            #print(newpages)
            
            #newpages = np.flip(newpages, axis=1)
            #print(newpages)
            newpages = newpages.reshape(-1).tolist()
            #print(newpages)
            pagenumbers += newpages
        else: ##reverse left to right on even pages
            newpages = []
            for j in range(nstacks):
                newpages.append(page_i+firstpagenums[0]+j*2*nstacks)
            
            #print(newpages)
            newpages = np.array(newpages).reshape(rows, cols)
            #print(newpages)
            newpages = np.flip(newpages, axis=1)
            #print(newpages)
            newpages = newpages.reshape(-1).tolist()
            #print(newpages)
            pagenumbers += newpages
    
    #print('2:\n', pagenumbers)
    
    ###this variant can make page numbers HIGHER than the limit. Set to -1 and use blank when -1 is the value
    pagenumbers = [x if x < n_imgs_orig else -1 for x in pagenumbers]
    while len(pagenumbers) % (2*nstacks) != 0:
        pagenumbers.append(-1)
    
    #print('3:\n', pagenumbers)
    return pagenumbers

# n_imgs = 128; rows = 3; cols = 3
# pn = make_pageorder(n_imgs, rows, cols)
# print(pn)

def createBlankPDFPage():
    _ = call("gs -q -dNOPAUSE -dQUIET -sDEVICE=pdfwrite -o \"./blank.pdf\"", shell=True)
    return

# n_imgs = 217
# rows = 1
# cols = 2
# testo = make_pageorder(n_imgs, rows, cols)

def make_pageimages(imgpaths_ordered_chunked, rows, cols, image_width=900, image_height=1165):
    '''Make combined images out of the ordered pages.'''
    _ = os.makedirs('combined', exist_ok=True)
    ##convert pages to paths
    for i in range(len(imgpaths_ordered_chunked)):
        thispagepaths = imgpaths_ordered_chunked[i]
        #<>img = np.ones((image_height*rows,image_width*cols, 3), dtype = np.uint8)*255
        img = np.ones((6600, 5100, 3), dtype = np.uint8)*255
        borderX = (5100 - image_width*cols) // 2 
        borderY = (6600 - image_height*rows) // 2
        for jy in range(len(thispagepaths)):
            for jx in range(len(thispagepaths[jy])):
                thispath = thispagepaths[jy][jx]
                if thispath == 'blank.pdf':
                    continue
                
                thisimg = cv2.imread(thispath)
                # cur_row = j // cols
                # cur_col = j % cols
                cur_row = jy
                cur_col = jx
                try:
                    #if i % 2 == 0:
                    img[(borderY+cur_row*image_height):(borderY+(cur_row+1)*image_height), (borderX+cur_col*image_width):(borderX+(cur_col+1)*image_width), :] = thisimg
                    #else: ##flip columns left-to-right on back/even pages
                    #   img[(borderY+cur_row*image_height):(borderY+(cur_row+1)*image_height), (borderX+(cols-1-cur_col)*image_width):(borderX+(cols-cur_col)*image_width), :] = thisimg
                    ##no need to flip again now that it's been done in the pageorder process...
                except Exception as e:
                    print(e)
                    import pdb; pdb.set_trace()
        
        _ = cv2.imwrite('combined/page_'+str(i).zfill(5)+'.png', img)
    
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
        _ = call(cmd, shell = True)
    
    time_end = time.time()
    print(round(time_end - time_start, 2), "seconds to dilate all the tifs.")
    return


'''
inpdfname = "test.pdf"
outpdfname = "test-waterproof-25per-3x3-margins.pdf"
nrows = 3
ncols = 3
density = 600 #pixels per inch, so 5100 x 6600 here
img_width = 1333 #(5100-600)/ncols
img_height = 1500 #(6600-775)/nrows
'''
inpdfname = "test.pdf"
outpdfname = "test-3x3per-margins.pdf"
#nrows = 1; ncols = 2
nrows = 3; ncols = 3  ##note: always adjust rows and cols for portrait mode; if rows != cols then set rows to the higher number and cols to the lower one. Assuming portrait mode page orientation of the document, too.
density = 600 #pixels per inch, so 5100 x 6600 here
#img_width = 2550 #(5100-600)/ncols
#img_height = 4050 #(6600-775)/nrows
img_width = int(round((5100-600)/ncols, 0))
img_height = int(round((6600-775)/nrows, 0))

#_ = os.system('mkdir out; gs -q -dAutoRotatePages=/None -dPDFFitPage -dNOPAUSE -dQUIET -dBATCH -sDEVICE=tiff24nc -r300 -dCenterPages=true -sCompression=lzw -sOutputFile="out/page_%05d.tif" "'+inpdfname+'"') ##split PDF
    #this is always 2550x3300
#_ = os.system('for f in out/*.tif; do convert "$f" -quality 100 -units PixelsPerInch -density 600x300 -filter Lanczos -resize '+str(img_width)+'x'+str(img_height)+'! -shave 2x2 -bordercolor black -border 2 "${f%.tif}.png"; done') #convert to png
if not os.path.exists('out/'):
    print("gs splitting pages")
    _ = os.system('mkdir out; gs -q -dAutoRotatePages=/None -dPDFFitPage -dNOPAUSE -dQUIET -dBATCH -sDEVICE=tiff24nc -r600 -g'+str(img_width)+'x'+str(img_height)+' -dCenterPages=true -sCompression=lzw -sOutputFile="out/page_%05d.tif" "'+inpdfname+'"') ##split PDF
    print("imagemagick adding black border")
    _ = os.system('for f in out/*.tif; do convert "$f" -quality 100 -units PixelsPerInch -density 600x600 -filter Lanczos -shave 2x2 -bordercolor black -border 2 "${f%.tif}.png"; done') #convert to png
else:
    pass

use_bold = True
if not use_bold:
    imglist = os.listdir('out')
    imglist = ['out/'+x for x in imglist if x.split('.')[-1] in ['png']]
    imglist.sort()
else:
    print("making bold...")
    outpdfname = outpdfname[:-4]+'_bold.pdf'
    if not os.path.exists('out_bold'):
        _ = call('cp -R \"out\" \"out_bold\"', shell=True)
        imglist = os.listdir('out_bold')
        imglist = ['out_bold/'+x for x in imglist if x.split('.')[-1] in ['png']]
        imglist.sort()
        dilateTifs("out_bold")
    else:
        imglist = os.listdir('out_bold')
        imglist = ['out_bold/'+x for x in imglist if x.split('.')[-1] in ['png']]
        imglist.sort()

#1 inch: 600 x 777, 7x7 = 98 per page (49 per side)
#1.5 inch: 900 x 1165, 5x5 = 50 per page (25 per side)
#4x4
#3x3: 1333 x 2000, about 2.22" wide by 3.33" tall
print("combining page images into multi-per-page...")
pagenumbers = make_pageorder(len(imglist), rows=nrows, cols=ncols) ##wrong: needs to reverse every 2nd page also
_ = createBlankPDFPage()

#pagenumbers = [-1]+pagenumbers
#while len(pagenumbers) % 4 != 0:
#    if pagenumbers[-1] == -1:
#        pagenumbers = pagenumbers[:-1]
#    else:
#        break

imgpaths_ordered_chunked = [['blank.pdf' if x == -1 else imglist[x] for x in pagenumbers]]
imgpaths_ordered_chunked = [x for x in np.array([imgpaths_ordered_chunked]).reshape(-1,nrows,ncols).tolist()]
make_pageimages(imgpaths_ordered_chunked, rows=nrows, cols=ncols, image_width=img_width, image_height=img_height)

##convert the new combined pages to PDF
cpagelist = ['combined/'+x for x in os.listdir('combined') if x.split('.')[-1] == 'png']
cpagelist.sort()

print("converting new pages to PDF...")
for i in tqdm(range(len(cpagelist))):
    _ = call('convert -units PixelsPerInch -density 600 "'+cpagelist[i]+'" "'+cpagelist[i][:-4]+'.pdf"', shell=True)

##combined PDFs
print("combining PDFs")
ppagelist = ['combined/'+x for x in os.listdir('combined') if x.split('.')[-1] == 'pdf']
ppagelist.sort()

bigblob = " ".join(ppagelist)
_ = call("pdftk "+bigblob+" cat output \""+outpdfname+"\"", shell=True)

print("uncomment 1/0 to clean up")
1/0
print("cleaning up")
_ = os.remove('blank.pdf')
_ = shutil.rmtree('out')
if use_bold:
    _ = shutil.rmtree('out_bold')

_ = shutil.rmtree('combined')

##font that looks good at 5x5 or 7x7: Calibri 22 bold

