all:
	python fp_analysis.py --dir ~/Desktop/fp-analysis --langs "C"

clean:
	rm *.csv
	rm -d file-results