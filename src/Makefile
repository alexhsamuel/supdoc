.PHONY: jslib

all: jslib

jslib:
	cd js;              	\
	while read url; do  	\
	  wget -N -q "$$url";   \
	done < ./urls.txt
	mkdir -p js/fonts/
	mv js/glyphicons-halflings-regular.woff js/fonts/


