How to run:

Opening the notebook SMT.ipynb:
	-change the variable *instance_name* to the appropriate instance;
	-run all cells.

The program outputs the objective function values, and a string representing the tours while it performs binary search.
It saves them in an output file located in /SMT/out/instname_out.txt. 

To plot the solution in a graph:

	- open the ipython notebook plot_output.ipynb located in /SMT/src;
	- copy the path to the correct instance file in the *second block* of the notebook;
	- paste the tour string in the *solution* variable;
	- run all cells;
	- right click+save as instname_out.png in /SMT/out.