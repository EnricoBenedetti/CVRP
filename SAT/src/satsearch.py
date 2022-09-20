# USAGE FROM \src folder run in CMD: python sat_search.py instancepath

from z3 import *
import numpy as np
import re
import time

# length of bit vectors
default_tolerance = 17

def at_least_k(bool_vars, k, name):
    return at_most_k([Not(var) for var in bool_vars], len(bool_vars)-k, name)

def at_most_k(bool_vars, k, name):
    constraints = []
    n = len(bool_vars)
    s = [[Bool(f"s_{name}_{i}_{j}") for j in range(k)] for i in range(n - 1)]
    constraints.append(Or(Not(bool_vars[0]), s[0][0]))
    constraints += [Not(s[0][j]) for j in range(1, k)]
    for i in range(1, n-1):
        constraints.append(Or(Not(bool_vars[i]), s[i][0]))
        constraints.append(Or(Not(s[i-1][0]), s[i][0]))
        constraints.append(Or(Not(bool_vars[i]), Not(s[i-1][k-1])))
        for j in range(1, k):
            constraints.append(Or(Not(bool_vars[i]), Not(s[i-1][j-1]), s[i][j]))
            constraints.append(Or(Not(s[i-1][j]), s[i][j]))
    constraints.append(Or(Not(bool_vars[n-1]), Not(s[n-2][k-1])))   
    return And(constraints)

def exactly_k(bool_vars, k, name):
    return And(at_most_k(bool_vars, k, name+"1"), at_least_k(bool_vars, k, name+"2"))

def greater_or_equal_boolean_function(b1, b2):
    """returns clauses for bit1 >= b2"""
    clauses = []
    #clauses.append(Implies(b1, Or(b2, Not(b2))))
    clauses.append(Not(And(Not(b1), b2)))

    return clauses

def less_or_equal_boolean_function(b1, b2):
    """returns proposition for bit1 >= b2"""
    #clauses.append(Implies(b1, Or(b2, Not(b2))))
    return Not(And(Not(b2), b1))

def less_or_equal(v1, v2, tolerance = default_tolerance):
    """"v1, v2: boolean arrays"""
    #makes v1 the same length as v2
    clauses = []
    val1_name = str(v1[0])
    val2_name = str(v2[0])
    if len(v1) != len(v2):
        if len(v1) > len(v2):
            for i in range(len(v1) - len(v2)):
                v2.insert(0, Bool(f"less_eq_n_{val2_name}_minus_{i}"))
                clauses.append(Not(v2[0]))
        else:
            for i in range(len(v2) - len(v1)):
                v1.insert(0, Bool(f"less_eq_{val1_name}_minus_{i}"))
                clauses.append(Not(v1[0]))
    for i in range(tolerance - len(v1)):
        v1.insert(0, Bool(f"less_eq_{val1_name}_minus_{i}_tollerance"))
        clauses.append(Not(v1[0]))
        v2.insert(0, Bool(f"less_eq_{val2_name}_minus_{i}_tollerance"))
        clauses.append(Not(v2[0]))

    # first bit is 
    clauses.append(less_or_equal_boolean_function(v1[0],v2[0]))
    for i in range(0, len(v1)-1):
        bit_wise_and = []
        for j in range(0, i+1):
            bit_wise_and.append(v1[j]==v2[j])
        clauses.append(Implies(And(bit_wise_and), less_or_equal_boolean_function(v1[i+1],v2[i+1])))
    
    return clauses

def readVar(var_name, model):
    """returns int value of a given variable name. 0 if not present."""
    res = ''
    for i in range(bit_array_len):
        if model[Bool(f"{var_name}_{i}")]:
            res = res + "1"
        else:
            res = res + "0"
    res_int = int(res,2)
    return res_int


# code to print the paths from the boolean variables
def get_tour(model):
    tour = np.zeros(n+m+1).astype('int')
    for i in range(vo_len):
        for j in range(vo_len):
            if model.evaluate(visit_order[i][j], True):
                #print(i,j, visit_order[i,j]) # add +1 to i, j to get package and position in 1..n+m
                tour[j] = i+1
    tour[-1] = 0
    return tour


def tour_to_string(tour):
    tour_string = '['
    for p in tour:
        if p > n: #transform all bases into the same origin
            tour_string += '0'
        else: tour_string += str(p)
        tour_string += ', '
    tour_string = tour_string[0:-2] # remove unneeded ', '
    tour_string += ']' # close array
    return tour_string

def tour_to_string_couriers(tour):
    tour_list = ['[', '[', '[']
    courier = 0
    for p in tour:
        if p > n: #transform all bases into the same origin. when base, switch courier
            if p != n+1:
                tour_list[courier] += '0, '
                courier += 1 # start filling next list
            tour_list[courier] += '0'
        else: tour_list[courier] += str(p)
        tour_list[courier] += ', '
    
    for courier in range(m):
        tour_list[courier] = tour_list[courier][0:-2] # remove unneeded ', '
        tour_list[courier] += ']' # close array
    return tour_list


def tour_to_plot_string(tour):
    tour_list = [ [] for k in range(m)]
    courier = 0
    for p in tour:
        if p > n: #transform all bases into the same origin. when base, switch courier
            if p != n+1:
                tour_list[courier].append(0)
                courier += 1 # start filling next list
            tour_list[courier].append(0)
        else: tour_list[courier].append(p)
    return tour_list 

# -------READ DATA FROM FILE-----

# Read instance and extract data

instance_filename = sys.argv[1]
instance_name = instance_filename.split('\\')[-1]
instance_name = instance_name.split('.')[0]

lines = []
with open(instance_filename) as f:
    for line in f:
        line = re.sub("[^0123456789\.\ -]","",line)
        line = line.strip()
        lines.append(line)
# line 1: m
m = int(lines[0])
n = int(lines[1])
l = [int(s) for s in lines[2].split()]
weights = [int(s) for s in lines[3].split()]
x = [int(s) for s in lines[4].split()]
y = [int(s) for s in lines[5].split()]

#instance = {'m': m, 'n':n, 'capacities':l, 'weigths':weights, 'instancedx':x, 'instancedy':y}
#print(instance)

# --------- FUNCTIONS ---------

x = x[-1:] + x[:-1]
y = y[-1:] + y[:-1]
 

def manhattan_distance(x1, y1, x2, y2):
    distance = 0
    absX = abs(x2 - x1)
    absY = abs(y2 - y1)
    distance = absX + absY
    return distance
 
def create_distance_matrix(listX, listY):
    distance_matrix = np.zeros( (len(listX), len(listX)) )
    for i in range(len(listX)):
        for j in range(len(listX)):
            distance_matrix[i, j] = manhattan_distance(listX[i], listY[i], listX[j], listY[j])
 
    return distance_matrix.astype('int')
 
# --------- VARIABLES ---------
 
distance_matrix = create_distance_matrix(x, y)
#print(distance_matrix)

def all_tours_distance(t):
    tot = 0
    for i in range(len(t)-1):
        tot += distance_matrix[t[i], t[i+1]]
    return tot

def intToBool(val, include_tolerance = False, tol=default_tolerance, name=None):
    if name == None:
        name=str(val)
    clauses = []
    bits = format(val, "b")
    length = len(str(bits))
    if include_tolerance == True:
        if tol < length:
            raise Exception('tol must be greater than the length of the int')
        res = [Bool(f"{name}_{i}") for i in range(tol)]
        bits = '0'*(tol-length) + bits
        length = tol
        
    else: res = [Bool(f"{name}_{i}") for i in range(length)]

    for i in range(length):
        if bits[i] == "1":
            clauses.append(res[i])
        else:
            clauses.append(Not(res[i]))

    return (res, clauses)

def boolToString(model, include_tolerance = False, res_name='res'):
    res = ""
    for i in range(len(model)):
        try:
            if model.evaluate(Bool(f"{res_name}_{i}")):
                res = res + "1"
            else:
                res = res + "0"
        except:
            ""
    if include_tolerance:
        return res
    new_res = ""
    found = False
    for i in range(len(res)):
        if not found and res[i] == "1":
            found = True
        if found:
            new_res = new_res + res[i]
    return new_res

def boolToInt(model, res_name='res'):            
    return int(boolToString(model, res_name=res_name), 2)

def addBools(v1, v2, tolerance = default_tolerance, res_name='res'):
    clauses = []
    val1_name = str(v1[0])
    val2_name = str(v2[0])
    if len(v1) != len(v2):
        if len(v1) > len(v2):
            for i in range(len(v1) - len(v2)):
                v2.insert(0, Bool(f"n_{val2_name}_minus_{i}"))
                clauses.append(Not(v2[0]))
        else:
            for i in range(len(v2) - len(v1)):
                v1.insert(0, Bool(f"n_{val1_name}_minus_{i}"))
                clauses.append(Not(v1[0]))
    for i in range(tolerance - len(v1)):
        v1.insert(0, Bool(f"n_{val1_name}_minus_{i}_tollerance"))
        clauses.append(Not(v1[0]))
        v2.insert(0, Bool(f"n_{val2_name}_minus_{i}_tollerance"))
        clauses.append(Not(v2[0]))
    res = [Bool(f"{res_name}_{i}") for i in range(len(v1))]
    carry = [Bool(f"c_{res_name}_{i}") for i in range(len(v1) + 1)]
    for i in range(0, len(v1)):
        clauses.append(((v1[i] == v2[i]) == res[i]) == carry[i+1])
        clauses.append(carry[i] == Or([And(v1[i], v2[i]), And(v1[i], carry[i+1]), And(v2[i], carry[i+1])]))
    clauses.append(And(Not(carry[0]), Not(carry[-1])))
    return (res, clauses)

print('Generating formulas...')
fixed_clauses_gen_time_start = time.time()

visit_order_l = [[Bool(f"visit_{i}_{j}") for j in range(1,n+m+1)] for i in range(1,n+m+1)]
visit_order = np.array(visit_order_l)
vo_len = visit_order.shape[0]
#assert vo_len == m+n
#print(visit_order)
#  edges as a single matrix of (n+m)^2 elements where we have m bases.
couriers_edges_l = [[Bool(f"edge_{i}_{j}") for j in range(1,n+m+1)] for i in range(1,n+m+1)]
couriers_edges = np.array(couriers_edges_l)

ce_len = couriers_edges.shape[0]
assert ce_len == vo_len

#s = Solver()
fixed_clauses = []
# constraints for the couriers edges

# each package appears in exactly one edge (C2)
for row in range(ce_len):
    c2 = exactly_k(couriers_edges[row,:], 1, f'ce_exactly_one_visited_row_{row}')
    try:
        fixed_clauses.extend(c2)
    except:
        fixed_clauses.append(c2)

# each package appears in exactly one edge (C2)
for col in range(ce_len):
    c2_b = exactly_k(couriers_edges[:,col], 1, f'ce_exactly_one_visited_col_{col}')
    try:
        fixed_clauses.extend(c2_b)
    except:
        fixed_clauses.append(c2_b)

# no edges between the same packages (false on the diagonals)
for i in range(ce_len):
    try:
        fixed_clauses.extend(Not(couriers_edges[i][i]))
    except:
        fixed_clauses.append(Not(couriers_edges[i][i]))

# constraints for the visit orders

# each package location is visited exactly once (C6)
for row in range(vo_len):
    c6 = exactly_k(visit_order[row,:], 1, f'vo_exactly_one_visited_row_{row}')
    try:
        fixed_clauses.extend(c6)
    except:
        fixed_clauses.append(c6)

# each position is related to only one vertex (theoretically duplicate constr)
for col in range(vo_len):
    c6_c = exactly_k(visit_order[:,col], 1, f'vo_exactly_one_visited_col_{col}')
    try:
        fixed_clauses.extend(c6_c)
    except:
        fixed_clauses.append(c6_c)

# package base of the first courier is visited first
first_base = n
try:
    fixed_clauses.extend(visit_order[first_base, 0])
except:
    fixed_clauses.append(visit_order[first_base, 0])

# if there is an edge from v1 to vi then vi's position is 2 (C3')
#v1 in our case is the base of the first courier (index n in  the array)
# if there is an edge from vi to v1 then vi's position is last (n+m) (C4')
# index of the first base is n (from 0..n-1 there are packages)

for i in range(vo_len):
    if i != first_base:
        c3 = Implies(couriers_edges[first_base, i], visit_order[i,2-1])
        c4 = Implies(couriers_edges[i, first_base], visit_order[i,n+m-1])
        try:
            fixed_clauses.extend(c3)
        except:
            fixed_clauses.append(c3)
        try:
            fixed_clauses.extend(c4)
        except:
            fixed_clauses.append(c4)

# ensures that if edge (i, j)is in the Hamiltonian cycle, and vertex i’s position 
# is p, then vertex j’s position is p + 1. (C5')
for i in range(vo_len):
    for j in range(vo_len):
        for p in range(2, vo_len-1):
            if i != first_base and j != first_base and i!=j:
                c5 = Implies(And(couriers_edges[i,j], visit_order[i,p]), visit_order[j,p+1])
                try:
                    fixed_clauses.extend(c5)
                except:
                    fixed_clauses.append(c5)
                
bit_array_len = default_tolerance
partial_sum = []

# adds values for distance matrix into the solver
distance_matrix_bool = [[None for _ in  range(n+1)] for _ in range(n+1)]
for i in range (n+1):
    for j in range (n+1):
        res, clauses = intToBool(distance_matrix[i,j], name=f"distance_matrix_{i}_{j}", include_tolerance=True)
        distance_matrix_bool[i][j] = res
        try:
            fixed_clauses.extend(clauses)
        except:
            fixed_clauses.append(clauses)


#[111] <=> [111] maybe?
#init of partial sums
partial_sum_prev = [Bool(f"partial_distance_sum_0_{ind}") for ind in range(0, bit_array_len)]
for var in partial_sum_prev:
    fixed_clauses.append(Not(var)) # set to 0b
    

weights_bool = [None for _ in  range(n)]
for i in range (n):
    res, clauses = intToBool(weights[i], name=f"weights_{i+1}", include_tolerance=True)
    weights_bool[i] = res
    fixed_clauses.extend(clauses)

capacities_bool = [None for _ in  range(m)]
for i in range (m):
    res, clauses = intToBool(l[i], name=f"capacities_{i+1}", include_tolerance=True)
    capacities_bool[i] = res
    fixed_clauses.extend(clauses)

# delivered by m x n, there a 1 in pos i,j iff i delivers package j
delivered_by = [[Bool(f'{j+1}_delivered_by_{i+1}') for j in range(n)] for i in  range(m)]
delivered_by = np.array(delivered_by)

# exactly 1 in a column (1 package is delivered by only 1 courier)
for col in range(n):
    clauses = exactly_k(delivered_by[:,col], 1, f'delivered_by_exactly_one_{col}')
    try:
        fixed_clauses.extend(clauses)
    except:
        fixed_clauses.append(clauses)

# there is a 1 for package i of courier k iff visit order[i, x]. x 

for k in range(m):
    for i in range(n):
        for j in range(n):
            if j!=i:
                clauses = Implies((And(delivered_by[k,j], couriers_edges[j,i])), delivered_by[k,i])
                try:
                    fixed_clauses.extend(clauses)
                except: 
                    fixed_clauses.append(clauses)

for k in range(m):
    for i in range(n):
        clauses = Implies(couriers_edges[n+k,i], delivered_by[k,i])
        try:
            fixed_clauses.extend(clauses)
        except:
            fixed_clauses.append(clauses)

fixed_clauses_gen_time_end = time.time()

print("Fixed clauses generation time: ", fixed_clauses_gen_time_end-fixed_clauses_gen_time_start)

# ---- STARTS THE SEARCH ----
print("Starting the search")


start_time = time.time()
#s = Solver()
s = Then('simplify', 
                'dom-simplify',
                'elim-uncnstr', 
                'aig',
                'qe',
                'sat').solver()
#s = Then('simplify', 
#             'aig',
#             'sat').solver()
test_start = time.time()
s.add(fixed_clauses)
test_end = time.time()
print("Fixed clauses adding time: ", test_end - test_start)
partial_sum_index = 1
test_start = time.time()
## Total distance using couriers_edges
for i in range(ce_len): #ce_len = n+m
    for j in range(ce_len):
        # this is to manage bases n+1..n+m+1
        i_sum, j_sum = i+1, j+1 #indexes in bool distance matrix are 0+1-n while indexes here are 0-n+m
        if i+1>n:
            i_sum=0
        if j+1>n:
            j_sum=0
        partial_sum_curr, clauses = addBools(distance_matrix_bool[i_sum][j_sum], partial_sum_prev, res_name=f'partial_distance_sum_{partial_sum_index}')
        s.add(Implies(couriers_edges[i][j], And(clauses)))
        for u in range(len(partial_sum_prev)):
            s.add(Implies(Not(couriers_edges[i][j]),partial_sum_curr[u] == partial_sum_prev[u]))
        partial_sum_prev = partial_sum_curr
        partial_sum_index+=1


total_distance = partial_sum_curr

total_load_per_courier = []

zero_sum = [Bool(f"partial_sum_weights_0_{ind}") for ind in range(0, bit_array_len)]
for var in zero_sum:
    s.add(Not(var)) # set to 0b

for k in range(m):
    partial_sum_index = 1
    partial_sum_prev = zero_sum
    for i in range(n):
        partial_sum_curr, clauses = addBools(weights_bool[i], partial_sum_prev, res_name=f'partial_sum_weights_courier_{k+1}_{partial_sum_index}')
        s.add(Implies(delivered_by[k][i], And(clauses)))
        for u in range(len(partial_sum_prev)):
            s.add(Implies(Not(delivered_by[k,i]),partial_sum_curr[u] == partial_sum_prev[u]))
        partial_sum_prev = partial_sum_curr
        partial_sum_index+=1
    total_load_per_courier.append(partial_sum_curr)

for k in range(m):
    s.add(less_or_equal(total_load_per_courier[k], capacities_bool[k]))

test_end = time.time()
print("Variable clauses adding time: ", test_end - test_start)

l = 0
r = 1000000
mid = 0
while l<=r:
    #print(l,r, int(np.ceil(mid)))
    mid = l + (r-l)/2
    if str(s.check())=='sat':
        model = s.model()
        res_comp = []
        #print total distance
        r = readVar(str(total_distance[0])[:-2], s.model())
        mid = l + (r-l)/2
        print('tot_d', r)
        #print tours
        tour = get_tour(model)
        tour = tour_to_plot_string(tour)
        print('tour of couriers:', tour)

        #write best solution so far to output txt file
        with open("../out/" + instance_name + '_out.txt', 'a') as f:
            f.write(str(r) + ' ')
            f.write(str(tour) + '\n\n')
        
        end_time = time.time()
        print("Time from the start of the search: ", end_time-start_time, end='\n\n')
        s.push()
        mid_bool, clauses = intToBool(int(np.floor(mid)))
        s.add(clauses)
        s.add(less_or_equal(total_distance, mid_bool))
    else:
        s.pop()
        s.push()
        l = mid+1
        mid_bool, clauses = intToBool(int(np.floor(mid)))
        s.add(clauses)
        s.add(less_or_equal(total_distance, mid_bool))
    
end_time = time.time()
print(f"Final result: ", r, " executed in ", end_time-start_time,'s')