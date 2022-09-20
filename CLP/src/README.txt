How to run:

Open the MiniZinc ide and:

	- Import the CPModel.mzn
	- Import the desired InstXX.dzn

The program outputs a string representing all the tours and the relative total distance calculated.

To plot the solution in a graph:

	- open the ipython notebook plot_output.ipynb located in /CLP/src;
	- copy the path to the correct instance file in the *second block* of the notebook;
	- paste the tour string in the *solution* variable;
	- run all cells;
	- right click+save as instname_out.png in /CLP/out.
