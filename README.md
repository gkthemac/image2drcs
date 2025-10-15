# image2drcs
image2drcs is a python script which reads an image file and converts it to teletext DRCS PTUs. The PTUs are written to a teletext page file in TTI format.

If a monochrome or 2 colour image is read, the result is Mode 0 PTUs suitable for Level 2.5 teletext decoding. The script can also convert 4 colour images to Mode 1 PTUs and 16 colour images to Mode 2 or 3 PTUs, these modes are only suitable for Level 3.5 teletext decoding.

The script depends on the [Python Imaging Library](https://pillow.readthedocs.io/) to read in images.

## Basic usage
`image2drcs.py -i INFILE [-o OUTFILE]`

`INFILE` is an image file in any format which is readable with the Python Imaging Library.

Any large and/or colourful source images must be pre-processed with an external tool before being read into the script. For Level 2.5 decoder compatibility the source image must be monochrome or 2 colours and an individual image should not exceed the size of 24 PTUs.

## Parameters
`-i, --infile=INFILE`\
Filename of input image, required parameter. If `-` is specified the image is read from stdin.

`-o, --outfile=OUTFILE`\
Filename of output TTI file. Defaults to `-` which is to write the TTI to stdout.

`-p, --pagenumber=NUMBER`\
Set the page number in the output page, must be a valid teletext page number. Defaults to `1a0`.

`-d, --description=DESCRIPTION`\
Set the description in the output TTI file.

`-g, --global`\
Set the DRCS source type in the output page to Global DRCS. Without this parameter the DRCS source type in the output page will be Normal DRCS.

`-r, --reverse`\
Invert all pixels. Only works for 2 colour Mode 0 PTUs.

`-3, --mode3`\
Write Mode 3 PTUs. The default is to convert 16 colour images to Mode 2 PTUs. A warning will be printed if the image has 4 colours or less.
