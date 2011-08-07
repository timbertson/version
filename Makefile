test:
	0launch --command=test version-local.xml

0:
	mkzero-gfxmonk -p version.py version.xml
	
.PHONY: 0 test
