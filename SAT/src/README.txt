How to run:

With a command line, with working directory /SAT/sr:

	> python satsearch.py instance_file_path

The program outputs the final objective function value, and a string representing the tours.
It also saves them in an output file located in /SAT/out/instname_out.txt. 

To plot the solution in a graph:

	- open the ipython notebook plot_output.ipynb located in /SAT/src;
	- copy the path to the correct instance file in the *second block* of the notebook;
	- paste the tour string in the *solution* variable;
	- run all cells;
	- right click+save as instname_out.png in /SAT/out.