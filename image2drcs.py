#!/usr/bin/env python3

import argparse
import os
import re
import sys

from PIL import Image

class PtuWriter:
	def __init__(self):
		# Triplets 1-12 of X/28/3 in TTI format for DRCS mode
		self.x283 = None
		self.pageNumber = '1a0'
		self.description = None
		# Global or Normal DRCS: influences PF command and triplet 0 of X/28/3
		self.globalSrc = False
		self.outFile = None

		# Subtable 0 to 15
		self.__subTable = 0
		# PTU number 0 to 47 on this subtable
		# used for tracking if PTU is written on left half or right half of row
		# and for starting new subtables after 48 PTUs
		self.__ptuNum = 0

	def beginPage(self):
		if self.description != None:
			self.outFile.write('DE,{0}\n'.format(self.description))
		self.beginSubPage()

	def beginSubPage(self):
		self.outFile.write('PN,{0}0{1:01x}\n'.format(self.pageNumber, self.__subTable))
		self.outFile.write('SC,000{0:01x}\n'.format(self.__subTable))
		self.outFile.write('PS,8010\n')

		if self.globalSrc:
			self.outFile.write('PF,4,0\n')
		else:
			self.outFile.write('PF,5,0\n')
			
		if self.x283 != None:
			if self.globalSrc:
				self.outFile.write('OL,28,CD@@')
			else:
				self.outFile.write('OL,28,CE@@')
			self.outFile.write('{0}\n'.format(self.x283))

	def writePtu(self, ptu):
		if self.__ptuNum == 48:
			self.__ptuNum = 0
			self.__subTable += 1
			self.beginSubPage()

		if self.__ptuNum & 1 == 0:
			outLine = self.__ptuNum // 2 + 1;
			self.outFile.write('OL,{},'.format(outLine))
		self.outFile.write(fr'{ptu}')
		self.__ptuNum += 1

		if self.__ptuNum & 1 == 0:
			self.outFile.write('\n')

	def endPage(self):
		if self.__ptuNum & 1 == 1:
			# 20 spaces
			self.outFile.write('                    \n')

def main():
	parser = argparse.ArgumentParser()

	# Validators
	# Check if page number is a valid teletext page number
	def pageNumberValid(value):
		try:
			return re.match('[1-8][0-9A-Fa-f][0-9A-Fa-f]', value).group(0)
		except:
			raise argparse.ArgumentTypeError('Not a valid page number');

	parser.add_argument('-i', '--infile', required=True, type=argparse.FileType('rb'), help='input image file')
	parser.add_argument('-o', '--outfile', default='-', help='output TTI file')
	parser.add_argument('-p', '--pagenumber', default='1a0', type=pageNumberValid, help='page number (default: %(default)s)')
	parser.add_argument('-d', '--description', help='description in TTI file')
	parser.add_argument('-g', '--global', dest='globalsrc', action="store_true", help='set DRCS source type to Global (default: Normal)')
	parser.add_argument('-3', '--mode3', action="store_true", help='write mode 3 PTUs')
	args = parser.parse_args()

	im = Image.open(args.infile)

	colours = im.getcolors(maxcolors=16)
	if colours == None:
		sys.exit('Error: Image has more than 16 colours.')

	numColours = len(im.getcolors())

	ptuWriter = PtuWriter()

	# For modes other than 0, put in a X/28/3 packet to specify the mode
	# These packets use the 1110 bits for "subsequent PTUs" but do NOT use
	# the 1111 bits for "no data" if the page has less than 48 PTUs
	if args.mode3:
		ptuMode = 3
		ptuWriter.x283 = 'sLsLsLsLsLsLsLsLsLsLsLsLsLsLsLsL@@@@'
		if numColours <= 4:
			print('Warning: Mode 3 but only {0} colours in image'.format(numColours), file=sys.stderr)
	elif numColours <= 2:
		ptuMode = 0
	elif numColours <= 4:
		ptuMode = 1
		ptuWriter.x283 = 'aG^xaG^xaG^xaG^xaG^xaG^xaG^xaG^x@@@@'
	else:
		ptuMode = 2
		ptuWriter.x283 = 'b{nxnKn{b{nxnKn{b{nxnKn{b{nxnKn{@@@@'

	ptuWriter.globalSrc = args.globalsrc

	pixels = im.load()
	width, height = im.size

	# Work out how many PTUs to store this bitmap
	# First convert the pixel size to PTU size
	# The negating means we round up instead of down
	if ptuMode != 3:
		charWidth  = -(-width  // 12)
		charHeight = -(-height // 10)
	else:
		charWidth  = -(-width  // 6)
		charHeight = -(-height // 5)

	# Now multiply the total by the number of bitplanes required
	ptuTotal = charWidth * charHeight
	if ptuMode == 1:
		ptuTotal *= 2
	elif ptuMode == 2:
		ptuTotal *= 4

	if ptuTotal > 768:
		sys.exit('Error: Image would exceed 16 subtables')

	ptuWriter.pageNumber = args.pagenumber
	if args.description:
		ptuWriter.description = args.description

	if args.outfile == '-':
		outFile = sys.stdout
	else:
		try:
			outFile = open(args.outfile, 'w')
		except OSError as e:
			print('Cannot open output file \'{0}\': error {1} {2}'.format(args.outfile, e.errno, e.strerror), file=sys.stderr)
			sys.exit(os.EX_OSFILE)

	ptuWriter.outFile = outFile

	ptuWriter.beginPage()

	if ptuMode != 3:
		# Modes 0, 1 or 2 - 12x10 with 1, 2 or 4 bitplanes
		# Each complete bitplane stored sequentially across multiple PTUs
		for cy in range(charHeight):
			for cx in range(charWidth):
				# PTU that will grow to 20 D-bytes and be added to the output line/OL
				# One PTU for each bitplane
				ptu = []
				ptu.append(r'')
				ptu.append(r'')
				ptu.append(r'')
				ptu.append(r'')

				for suby in range(10):
					scany = cy * 10 + suby
					if scany >= height:
						# Pad with "zero" pixels if PTU height exceeds image height
						ptu[0] = ptu[0] + '@'
						if ptuMode != 0:
							ptu[1] = ptu[1] + '@'
							if ptuMode == 2:
								ptu[2] = ptu[2] + '@'
								ptu[3] = ptu[3] + '@'
						continue
					# D-Byte that will be added to the PTU
					# One D-Byte for each bitplane
					dbyte = []
					dbyte.append(0x40)
					dbyte.append(0x40)
					dbyte.append(0x40)
					dbyte.append(0x40)
					bitset = 5
					for subx in range(12):
						scanx = cx * 12 + subx
						# Pad with "zero" pixels if PTU width exceeds image width
						if scanx >= width:
							pixel = 0
						else:
							pixel = pixels[scanx, scany]
						if pixel & 1 == 1:
							dbyte[0] |= (1 << bitset)
						if pixel & 2 == 2:
							dbyte[1] |= (1 << bitset)
						if pixel & 4 == 4:
							dbyte[2] |= (1 << bitset)
						if pixel & 8 == 8:
							dbyte[3] |= (1 << bitset)
						# Once the left 6 pixels are collected, write the D-Bytes into the PTUs
						# then clear the D-Bytes ready for the right 6 pixels
						if subx == 5 or subx == 11:
							ptu[0] = ptu[0] + chr(dbyte[0])
							ptu[1] = ptu[1] + chr(dbyte[1])
							ptu[2] = ptu[2] + chr(dbyte[2])
							ptu[3] = ptu[3] + chr(dbyte[3])
							dbyte[0] = 0x40
							dbyte[1] = 0x40
							dbyte[2] = 0x40
							dbyte[3] = 0x40
							bitset = 5
						else:
							bitset -= 1
				ptuWriter.writePtu(ptu[0])
				if ptuMode != 0:
					ptuWriter.writePtu(ptu[1])
					if ptuMode == 2:
						ptuWriter.writePtu(ptu[2])
						ptuWriter.writePtu(ptu[3])
	else:
		# Mode 3 - 6x5 with 4 bitplanes
		# First row of six pixels is stored four times sequentially, one for
		# each bitplane, then second row of pixels four times, and so on
		for cy in range(charHeight):
			for cx in range(charWidth):
				ptu = r''

				for suby in range(5):
					scany = cy * 5 + suby
					# Pad with "zero" pixels if PTU height exceeds image height
					if scany >= height:
						ptu = ptu + '@@@@'
						continue
					bitplanerow = []
					bitplanerow.append(0x40)
					bitplanerow.append(0x40)
					bitplanerow.append(0x40)
					bitplanerow.append(0x40)
					for subx in range(6):
						scanx = cx * 6 + subx
						# Pad with "zero" pixels if PTU width exceeds image width
						if scanx >= width:
							pixel = 0
						else:
							pixel = pixels[scanx, scany]
						bitset = 5 - subx
						if pixel & 1 == 1:
							bitplanerow[0] |= (1 << bitset)
						if pixel & 2 == 2:
							bitplanerow[1] |= (1 << bitset)
						if pixel & 4 == 4:
							bitplanerow[2] |= (1 << bitset)
						if pixel & 8 == 8:
							bitplanerow[3] |= (1 << bitset)
					for bp in range(4):
						ptu = ptu + chr(bitplanerow[bp])
				ptuWriter.writePtu(ptu)

	ptuWriter.endPage()

if __name__ == '__main__':
	main()
