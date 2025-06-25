# pdf-book-printer
Wow! Some scripts to turn PDFs into printable, bindable books by printing 2, 4, or any number of PDF pages to a single 8.5 x 11" sheet.

Make books by editing PDFs for printing at 2-per-page or 4-per-page in correct order.

This script is designed to convert PDFs for 2-per-page (left to right, then flip short edge) and 4-per-page (four stacks of consecutive pages which can then all be stacked) printing.

Needs GhostScript, ImageMagick, pdftk, and libtiff-tools (tiff2pdf). Commands designed for Linux filesystem, but same process should work fairly easily on Windows.

```
apt-get install ghostscript libtiff-tools poppler-utils -y
```

The 2-per-page PDFs are meant to be print 2-per-page, flip short edge. Then you cut them in half down the middle and stack the halves.

The 4-per-page PDFs are printed 1 2 3 4 going left to right, top to bottom, flip long edge (like a normal duplex sheet). You get four stacks out of these.

For binding, I recommend a 2-hole punch, prong fastener clasps, and bookbinding / 3-inch tape (to cover the sharp edges of the clasp). This works fairly well even for large books.

ImageMagick is used to call a dilation function to make the print bolder. This may be necessary for the 4-page PDFs to be legible on eight-and-a-half by eleven size paper.

The full-color intermediate .tiffs are quite large (about 25MB per page). I recommend running this script on a drive with several dozen GB free for larger PDFs with hundreds of pages.

The sample PDF is The Autobiography of Benjamin Franklin.

python3 -i assemble_printbook.py and run the appropriate pipeline command to generate 4-8 variants of the PDF depending on whether you want color or not.

make_mini.pdf allows you to specify the number of rows and columns of pages to print per page. You can make very small pocket-books this way. You will have best success with this if the input PDF has large enough font.
