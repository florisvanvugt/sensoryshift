default: run

kill: # Kill the robot, reasonably gently
	python3 -c "import robot.interface as robot; robot.start_shm(); robot.unload();"

doc: documentation.html
	xdg-open documentation.html

documentation.html: readme.md fonts/github-pandoc.css
	pandoc -f markdown -t html readme.md -s -c fonts/github-pandoc.css -o documentation.html

run: rob
	python3 run.py 

rob:
	make -C robot

clean:
	rm -f *.pyc
	rm -f *~
	make -C robot clean



