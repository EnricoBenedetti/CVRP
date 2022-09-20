from __future__ import print_function
from __future__ import division
from builtins import range
from logging import log, DEBUG
import sys
import numpy as np

from gurobipy import *
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Path, Arrow
from matplotlib.ticker import MaxNLocator


# The savings algorithm code, which we modified, came with the following meta-data
__author__ = "Jussi Rasku"
__copyright__ = "Copyright 2018, Jussi Rasku"
__credits__ = ["Jussi Rasku"]
__license__ = "MIT"
__maintainer__ = "Jussi Rasku"
__email__ = "jussi.rasku@jyu.fi"
__status__ = "Development"

S_EPS = 1e-10
C_EPS = 1e-10


def objf(sol, D):
	"""A quick procedure for calclulating the quality of an solution (or a 
	route). Assumes that the solution (or the route) contains all visits (incl. 
	the first and the last) to the depot."""
	return sum(( D[sol[i-1],sol[i]] for i in range(1,len(sol))))


def routes2sol(routes):
	"""Concatenates a list of routes to a solution. Routes may or may not have
	visits to the depot (node 0), but the procedure will make sure that 
	the solution leaves from the depot, returns to the depot, and that the 
	routes are separated by a visit to the depot."""
	if not routes:
		return None
	
	sol = [0]
	for r in routes:
		if r:
			if r[0]==0:
				sol += r[1:]
			else:
				sol += r
			if sol[-1]!=0:
				sol += [0]
	return sol


def clarke_wright_savings_function(D):
	N = len(D)
	n = N-1
	savings = [None]*int((n*n-n)/2)
	idx = 0
	for i in range(1,N):
		for j in range(i+1,N):
			s = D[i,0]+D[0,j]-D[i,j]
			savings[idx] = (s,-D[i,j],i,j)
			idx+=1
	savings.sort(reverse=True)
	return savings 


def fits(current_loads, idx1, idx2, capacities, new_demand):

	small_idx = min(idx1, idx2)
	big_idx   = max(idx1, idx2)

	current_loads.pop(big_idx)
	current_loads.pop(small_idx)
	current_loads.append(new_demand)
	current_loads.sort()
	current_loads.reverse()

	for i, item in enumerate(capacities):
		if current_loads[i] > item:
			return False

	return True


def parallel_savings_init(D, d, C, L=None, minimize_K=False,
						  savings_callback=clarke_wright_savings_function):
	"""
	Implementation of the basic savings algorithm / construction heuristic for
	capaciated vehicle routing problems with symmetric distances (see, e.g.
	Clarke-Wright (1964)). This is the parallel route version, aka. best
	feasible merge version, that builds all of the routes in the solution in
	parallel making always the best possible merge (according to varied savings
	criteria, see below).
	
	* D is a numpy ndarray (or equvalent) of the full 2D distance matrix.
	* d is a list of demands. d[0] should be 0.0 as it is the depot.
	* C is the capacity constraint limit for the identical vehicles.
	* L is the optional constraint for the maximum route length/duration/cost.
	
	* minimize_K sets the primary optimization objective. If set to True, it is
	   the minimum number of routes. If set to False (default) the algorithm 
	   optimizes for the mimimum solution/routing cost. In savings algorithms 
	   this is done by ignoring a merge that would increase the total distance.
	   WARNING: This only works when the solution from the savings algorithm is
	   final. With postoptimimization this non-improving move might have still
	   led to improved solution.
   
	* optional savings_callback is a function of the signature:
		sorted([(s_11,x_11,i_1,j_1)...(s_ij,x_ij,i,j)...(s_nn,x_nn,n,n) ]) =
			savings_callback(D)
	  where the returned (sorted!) list contains savings (that is, how much 
	   solution cost approximately improves if a route merge with an edge
	   (i,j) is made). This should be calculated for each i \in {1..n},
	   j \in {i+1..n}, where n is the number of customers. The x is a secondary
	   sorting criterion but otherwise ignored by the savings heuristic.
	  The default is to use the Clarke Wright savings criterion.
		
	See clarke_wright_savings.py, gaskell_savings.py, yellow_savings.py etc.
	to find specific savings variants. They all use this implementation to do 
	the basic savings procedure and they differ only by the savings
	calculation. There is also the sequental_savings.py, which builds the 
	routes one by one.
	
	Clarke, G. and Wright, J. (1964). Scheduling of vehicles from a central
	 depot to a number of delivery points. Operations Research, 12, 568-81.
	"""
	N = len(D)
	ignore_negative_savings = not minimize_K
	
	## 1. make route for each customer
	routes = [[i] for i in range(1,N)]
	route_demands = d[1:] if C else [0]*N
	if L: route_costs = [D[0,i]+D[i,0] for i in range(1,N)]
	
	try:
		## 2. compute initial savings 
		savings = savings_callback(D)
		
		# zero based node indexing!
		endnode_to_route = [0]+list(range(0,N-1))
		
		## 3. merge
		# Get potential merges best savings first (second element is secondary
		#  sorting criterion, and it it ignored)
		courier_k = 0
		for best_saving, _, i, j in savings:
			if __debug__:
				log(DEBUG-1, "Popped savings s_{%d,%d}=%.2f" % (i,j,best_saving))
				
			if ignore_negative_savings:
				cw_saving = D[i,0]+D[0,j]-D[i,j]
				if cw_saving<0.0:
					break
				
			left_route = endnode_to_route[i]
			right_route = endnode_to_route[j]
			
			# the node is already an internal part of a longer segment
			if ((left_route is None) or
				(right_route is None) or
				(left_route==right_route)):
				continue
			
			if __debug__:
				log(DEBUG-1, "Route #%d : %s"%
							 (left_route, str(routes[left_route])))
				log(DEBUG-1, "Route #%d : %s"%
							 (right_route, str(routes[right_route])))
				
			# check capacity constraint validity
			if C:
				merged_demand = route_demands[left_route]+route_demands[right_route]
				if not fits(route_demands.copy(), left_route, right_route, capacities, merged_demand):
					continue

			# if there are route cost constraint, check its validity        
			if L:
				merged_cost = route_costs[left_route]-D[0,i]+\
								route_costs[right_route]-D[0,j]+\
								D[i,j]
				if merged_cost-S_EPS > L:
					if __debug__:
						log(DEBUG-1, "Reject merge due to "+
							"maximum route length constraint violation")
					continue
			
			# update bookkeeping only on the receiving (left) route
			if C:
				route_demands[left_route] = merged_demand
				# update capacity considered when merged
				# if route_demands[left_route] > C[courier_k]:
				# 	courier_k+=1 # todo: understand where to put this statement
			if L: route_costs[left_route] = merged_cost
			
			

			# merging is done based on the joined endpoints, reverse the 
			#  merged routes as necessary
			if routes[left_route][0]==i:
				routes[left_route].reverse()
			if routes[right_route][-1]==j:
				routes[right_route].reverse()
	
			# the nodes that become midroute points cannot be merged
			if len(routes[left_route])>1:
				endnode_to_route[ routes[left_route][-1] ] = None
			if len(routes[right_route])>1:
				endnode_to_route[ routes[right_route][0] ] = None
			
			# all future references to right_route are to merged route
			endnode_to_route[ routes[right_route][-1] ] = left_route
			
			# merge with list concatenation
			routes[left_route].extend( routes[right_route] )
			routes[right_route] = None
			route_demands[right_route] = 0

			if __debug__:
				dbg_sol = routes2sol(routes)
				log(DEBUG-1, "Merged, resulting solution is %s (%.2f)"%
							 (str(dbg_sol), objf(dbg_sol,D)))
	except KeyboardInterrupt: # or SIGINT
		interrupted_sol = routes2sol(routes)
		raise KeyboardInterrupt(interrupted_sol)
	
	# sort and return a list of paths by decreasing total demand
	i=0
	routes = [route for route in routes if route is not None]
	total_demands = np.zeros(len(routes))
	for route in routes:
		for node in route:
			total_demands[i] += d[node]
		i+=1
	inds = total_demands.argsort()
	inds = np.flip(inds)
	sortedRoutesByCapa = []
	for i in inds:
		sortedRoutesByCapa.append(routes[i])
	return sortedRoutesByCapa


def process_input():
	# expected input format
	# m (am couriers)
	# n (am_packages)
	# min_couriers
	# l1, l2, .., lm (capacity of each vehicle)
	# s1, s2, .., sn (weight of each package)
	# dx1, dx2 .., dxn, ox
	# dy1, dy2 .., dyn, oy

	lines = sys.stdin.readlines()

	m = int(lines[0].strip())
	n = int(lines[1].strip())
	min_couriers = int(lines[2].strip())
	capacities = [int(s) for s in lines[3].split()]
	capacities.sort()
	capacities.reverse()
	weights = [int(s) for s in lines[4].split()]
	xs = [int(s) for s in lines[5].split()]
	ys = [int(s) for s in lines[6].split()]

	return m, n, min_couriers, capacities, weights, xs, ys


def dist(x1, x2, y1, y2):
	return abs(x1-x2) + abs(y1-y2) # manhatten
	#return np.sqrt((x1-x2)**2 + (y1-y2)**2)


def get_distance_matrix(xs, ys):
	n = len(xs)
	xs = xs[-1:] + xs[:-1]
	ys = ys[-1:] + ys[:-1]
	
	D = np.zeros((n,n))
	for i in range(n):
		for j in range(n):
			D[i,j] = dist(xs[i], xs[j], ys[i], ys[j])
	return D


def real_dist(list_of_tours, xs, ys):
	xs = xs[-1:] + xs[:-1]
	ys = ys[-1:] + ys[:-1]
	total = 0
	for island in list_of_tours:
		for idx in range(len(island)-1):
			p = island[idx]
			n = island[idx+1]
			total += dist(xs[p], xs[n], ys[p], ys[n])
	return total


def plot_solution(xs, ys, m, n, matrices, val, opt, raw_name):

	if opt:
		print("The solution is optimal!")
	else:
		print("The solution could be better...")

	plt.rcParams["figure.figsize"] = (20,20)
	fig, ax = plt.subplots()
	ax.yaxis.set_major_locator(MaxNLocator(nbins='auto',integer=True))
	ax.xaxis.set_major_locator(MaxNLocator(nbins='auto',integer=True))
	ax.grid(color='#000000', linestyle='--', linewidth=0.5)
	ax.autoscale(enable=True, axis='both', tight=False)

	# annotates the point names
	i = 0 #labelcount
	for i in range(n+1):
		label = f"$d_{{{i+1}}}$"
		if i==n:
			label = 'o'
		ax.annotate(label, # this is the text
				(xs[i],ys[i]), # these are the coordinates to position the label
				textcoords="offset points", # how to position the text
				xytext=(0,10), # distance from text to points (x,y)
				ha='center', # horizontal alignment can be left, right or center
				**{'fontsize':17, })

	# gets m random colors
	number_of_colors = m

	color_map = plt.cm.get_cmap('gist_rainbow', number_of_colors)
	colors = color_map(np.arange(0,1,1/number_of_colors))

	# drawing unconnected nodes as well
	for i in range(n):
		ax.plot(xs[i],ys[i], marker="o", color="black")

	for k in range(m):
		color = colors[k]
		for i in range(n+1):
			for j in range(n+1):
				if matrices[i,j,k] > 0:
					current = (xs[i-1], ys[i-1])
					next = (xs[j-1], ys[j-1])
					arrow = FancyArrowPatch(posA=current, posB=next, arrowstyle='-|>,head_length=10,head_width=5', alpha = 1,
						**{'color':color})
					ax.add_patch(arrow)
					# draws the point
					ax.plot(current[0],current[1], marker="o", color=color)

	# draws the origin at the end
	ax.plot(xs[-1],ys[-1], marker="o", color="black")

	plt.savefig(raw_name)


def get_edges_cost(edges_cost, am_packages, am_couriers, xs, ys):

	for i in range(am_packages+1):

		smallest		= np.inf
		second_smallest = np.inf

		for j in range(am_packages+1):
			if i != j:
				if edges_cost[i,j,0] < second_smallest:
					if edges_cost[i,j,0] < smallest:
						second_smallest = smallest
						smallest = edges_cost[i,j,0]
					else:
						second_smallest = edges_cost[i,j,0]

		for j in range(am_packages+1):
			for k in range(am_couriers):
				edges_cost[i,j,k] = max(0,edges_cost[i,j,k]-second_smallest)

	
	for i in range(am_packages+1):
		for j in range(i):
			for k in range(am_couriers):
				edges_cost[i,j,k] = max(edges_cost[i,j,k], edges_cost[j,i,k])
				edges_cost[j,i,k] = edges_cost[i,j,k]

	return edges_cost


# assumes tours start and end at 0, code enters infinite loop here somewhere
def reformat(matrices, min_couriers, n):

	n = n+1
	#n is am packages

	tours = []

	count = 0

	for k in range(min_couriers):
		for j in range(n):
			if matrices[0,j,k] == 1:
				tour = []

				tour.append(0)

				i = j
				
				for q in range(n+1): # move back to while true
					if not i:
						break
					tour.append(i)
					count += 1
					for t in range(n):
						if matrices[i,t,k] == 1:
							i = t
							break
					if q == n:
						# failed
						pass

				tour.append(0)

				tours.append(tour)

				break
	
	return tours


def go_gurobi(heur_am_couriers, min_am_couriers, am_packages, weights_edges, weights_trucks, edges_cost, capacities, warm_routes, timeout_s):

	with Env(empty=True) as env:
		
		env.start()
		with Model(env=env) as m:

			m.setParam('TimeLimit', timeout_s)

			# MIP really loves binary variables
			edges = m.addVars(am_packages+1, am_packages+1, heur_am_couriers, lb=0, ub=1, vtype='B', name="edges" )

			# Stores which package is delivered by which truck so not 1 * [0..10] but 10 * [0..1]
			trucks = m.addVars(am_packages, heur_am_couriers, lb=0, ub=1, vtype='B', name="trucks" )

			# Every truck is assigned to one package
			m.addConstrs( (trucks.sum(i,'*') == 1 for i in range(am_packages)) )

			# Edge is only available if both packages are delivered by the same truck
			# These are equivalent to edges[i,j,k] <= trucks[i,k]*trucks[j,k]
			m.addConstrs(edges[j,i+1,k] <= trucks[i,k] 
							for i in range(am_packages) for j in range(heur_am_couriers+1) for k in range(heur_am_couriers))
			m.addConstrs(edges[i+1,j,k] <= trucks[i,k] 
							for i in range(am_packages) for j in range(heur_am_couriers+1) for k in range(heur_am_couriers))

			# Ensure that the number of times a vehicle enters a node is equal to the number of times it leaves that node
			# Note that this is not a symmetry constraint
			# Note that the origin *is* relevant for this constraint
			m.addConstrs( (edges.sum(j,'*',k) == edges.sum('*',j,k) for j in range(am_packages+1) for k in range(heur_am_couriers)))

			# Together with the first constraint, it ensures that the every node is entered only once, and it is left by the same vehicle.
			# Note that the origin is *not* relevant for this constraint
			m.addConstrs( (edges.sum('*',j,k) == trucks[j-1,k] for j in range(1, am_packages+1) for k in range(heur_am_couriers)))
			m.addConstrs( (edges.sum(i,'*',k) == trucks[i-1,k] for i in range(1, am_packages+1) for k in range(heur_am_couriers))) # redundant constraint

			# Together with constraint 1, we know that every vehicle arrives again at the depot.
			m.addConstrs( (edges.sum(0,'*',k) == 1 for k in range(min_am_couriers)) )
			m.addConstrs( (edges.sum('*',0,k) == 1 for k in range(min_am_couriers)) ) # redundant constraint

			# Capacity constraints
			m.addConstrs( (trucks.prod(weights_trucks, '*', k) <= capacities[k] for k in range(heur_am_couriers)))
			m.addConstrs( (edges.prod(weights_edges, '*', '*', k) <= capacities[k] for k in range(heur_am_couriers)))

			# No edges to itself allowed
			m.addConstrs( (edges[i,i,k] == 0 for i in range(am_packages+1) for k in range(heur_am_couriers)))

			# No two edges between two nodes
			m.addConstrs( edges.sum(i,j,'*') + edges.sum(j,i,'*') <= 1 for i in range(1,am_packages+1) for j in range(1,i))
			
			# mzt formulation
			C = sum(capacities)
			u = m.addVars(am_packages, lb=0, ub=C, vtype='C', name="u")
			m.addConstrs((u[j] - u[i] >= weights_edges[0,j+1,0] - C*(1-edges[i+1,j+1,k])
							for i in range(am_packages) for j in range(am_packages) for k in range(heur_am_couriers)))

			m.addConstrs((weights_edges[0,i+1,0] <= u[i] for i in  range(am_packages)))
			
			m.addConstrs((u[i] <= C*(1-trucks[i,k]) + (capacities[k])*trucks[i,k]
							for i in range(am_packages) for k in range(heur_am_couriers)))

			# setting warm solution
			for k, warm_route in enumerate(warm_routes):
				if k < heur_am_couriers:
					for t in range(len(warm_route)-1):
						i = warm_route[t]
						j = warm_route[t+1]
						edges[i,j,k].start = 1

			# the solution is to minimize the total cost of edges used
			m.setObjective(edges.prod(edges_cost), GRB.MINIMIZE)
			
			print("Waiting for optimizer...")
			m.optimize()
			print("Done waiting!")

			opt = (m.status == GRB.Status.OPTIMAL)

			val = m.getAttr('objVal')
			val = "{:.2f}".format(val)
			
			matrices = m.getAttr('x', edges)

			return opt, val, matrices


def go_gurobi_wrapper(heur_am_couriers, min_couriers, n, capacities, weights, warm_routes, xs, ys, timeout_s):

	xs_o = xs
	ys_o = ys

	xs = xs[-1:] + xs[:-1]
	ys = ys[-1:] + ys[:-1]

	weights_edges = dict()
	weights_trucks = dict()
	for i in range(n+1):
		for k in range(heur_am_couriers):
			if i >= 1:
				weights_trucks[i-1,k] = weights[i-1]
			for j in range(n+1):			
				if i == 0:
					weights_edges[j,i,k] = 0
				else:
					weights_edges[j,i,k] = weights[i-1]

	edges_cost = dict()
	for i in range(n+1):
		for j in range(n+1):
			for k in range(heur_am_couriers):
				edges_cost[i,j,k] = dist(xs[i], xs[j], ys[i], ys[j])

	edges_cost = get_edges_cost(edges_cost, n, heur_am_couriers, xs_o, ys_o)

	opt, val, matrices = go_gurobi(heur_am_couriers, heur_am_couriers, n, weights_edges, weights_trucks, edges_cost, capacities, warm_routes, timeout_s)

	return opt, val, matrices


def round_it(matrices, n, min_couriers):
	for i in range(n+1):
		for j in range(n+1):
			for k in range(min_couriers):
				matrices[i,j,k] = int(round(matrices[i,j,k]))
	return matrices


if __name__ == '__main__':

	m, n, min_couriers, capacities, weights, xs, ys = process_input()
	
	D = get_distance_matrix(xs,ys)

	sorted_routes = parallel_savings_init(D=D, d=[0]+weights, C=capacities, L=None, minimize_K=False, savings_callback=clarke_wright_savings_function)
	print("Heuristic solution:", sorted_routes)
	val_heuristic = objf(routes2sol(sorted_routes),D)
	print("Heuristic val:", val_heuristic)

	heur_am_couriers = len(sorted_routes)

	print(min_couriers, "<=", heur_am_couriers, "<=", m)

	violated = False
	for k, route in enumerate(sorted_routes):
		load = 0
		for item in route:
			load += weights[item-1]
		print(load, "<=", end=' ')
		if k < len(capacities):
			print(capacities[k])
		else:
			print('-1')
		if k >= m or load > capacities[k]:
			violated = True

	if heur_am_couriers > m or heur_am_couriers < min_couriers:
		violated = True
	
	if violated:
		print("HEURISTICS FAILED TO DELIVER FEASIBLE WARM START!")
		print("Terrible solution incoming, as if there was no heuristic at all..")

	for i in range(heur_am_couriers):
		sorted_routes[i] = [0] + sorted_routes[i] + [0]

	heur_am_couriers = min(heur_am_couriers, m)

	opt, val, matrices = go_gurobi_wrapper(heur_am_couriers, min_couriers, n, capacities, weights, sorted_routes, xs, ys, 5*60)

	matrices = round_it(matrices, n, heur_am_couriers)

	std_format = reformat(matrices, heur_am_couriers, n)

	print("MIP improvement:", std_format)
	print("MIP value:", real_dist(std_format, xs, ys))

	plot_solution(xs, ys, heur_am_couriers, n, matrices, val, opt, sys.argv[1])
	
	