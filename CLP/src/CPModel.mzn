include "nvalue.mzn";
include "subcircuit.mzn";

% Data --------------------------------------------
 
% Couriers
int: m;
% Packages to be delivered
int: n;

% Set of ints of length m (couriers) and n (packages)
set of int: COURIERS = 1..m;
set of int: PACKAGES = 1..n;

% Array of capacities of each courier
array[COURIERS] of int: capacities;
% Array of weights of each package
array[PACKAGES] of int: weights;

% Coordinates of each drop-off point
array[1..n+1] of int: Xs;
array[1..n+1] of int: Ys;


% Reorganizing inputs ----------------------------

% Reorganized Xs and Ys with the orgin at the 0 index
array[0..n] of int: new_Xs = array1d(0..n, [Xs[n+1]] ++ Xs[1..n]);
array[0..n] of int: new_Ys = array1d(0..n, [Ys[n+1]] ++ Ys[1..n]);

% Reorganize the weight array inserting the weight of the origin (0) in the first position
array[0..n] of int: weights_plus_zero = array1d(0..n, [0] ++ weights);

% Organizing couriers in descending capacity order
array[COURIERS] of var int: capacities_sort = reverse(sort(capacities));

% Distance function -------------------------------

% Manhattan distance between two point
function int: manhattan_distance (int: x1, int: y1, int: x2, int: y2) = abs(x1-x2) + abs(y1-y2);
  
% Calculating the distance matrix
array[0..n, 0..n] of int: distance_matrix = array2d(0..n, 0..n, [manhattan_distance(new_Xs[i], new_Ys[i], new_Xs[j], new_Ys[j]) | i,j in 0..n]);

% Returns the number of distinct values in x 
function var int: nvalue(array[int] of var int: x) =
  let { var 0..length(x): n::is_defined_var; constraint nvalue(n,x)::defines_var(n); } in n;


% Variables ---------------------------------------

% For each package i, deliveredBy[i] define which courier operated the delivery
array[PACKAGES] of var COURIERS: deliveredBy;

% Matrix that for each courier define the circuit of deliveries
array[COURIERS, 0..n] of var 0..n: deliveries;


% Constraints -------------------------------------

% Create circuit for each courier 
constraint forall(c in COURIERS) (subcircuit(row(deliveries, c)));

% A column must have one and only one value different from the other (one and only one courier deliveres that package)
constraint forall(i in PACKAGES) (nvalue(col(deliveries,i)) = 2);

% If the courier doesn't start, prevent creation of subcircuits
constraint forall(c in COURIERS where row(deliveries, c)[0] == 0) (
              forall(i in PACKAGES) (row(deliveries, c)[i] == i));
       
% Capacities constraint, descending from the largest couriers
constraint forall(c in COURIERS) (sum(i in PACKAGES where deliveredBy[i] = c) (weights_plus_zero[i]) <= capacities_sort[c]);            
                         
% Check correct courier delivery, also a package can be delivere by one and only one (mapping between deliveries and deliveredBy)
constraint forall(c in COURIERS) (forall(i in PACKAGES where deliveredBy[i] == c) (row(deliveries, c)[i] != i));
constraint forall(c in COURIERS) (forall(i in PACKAGES where row(deliveries, c)[i] != i) (deliveredBy[i] = c));

% Prevent same start for two different courier (redundant)
constraint forall(c1, c2 in COURIERS where row(deliveries, c1)[0] != 0 /\ row(deliveries, c2)[0] != 0 /\ c1 < c2) (row(deliveries, c1)[0] != row(deliveries, c2)[0]);

% Prevent 1-2-3 3-2-1 (symmetry)
constraint forall(c in COURIERS where row(deliveries, c)[0] != 0) (
              forall(i in 0..n where row(deliveries, c)[i] == 0) (row(deliveries, c)[0] > i));
              
% Try to fit the largest courier first
constraint forall(c1, c2 in COURIERS where c1 < c2) (
              sum(i in PACKAGES where deliveredBy[i] = c1) (weights_plus_zero[i]) >= sum(j in PACKAGES where deliveredBy[j] = c2) (weights_plus_zero[j]));


var int: dist = sum(c in COURIERS where row(deliveries, c)[0] != 0) (sum(i in 0..n where row(deliveries, c)[i] != i) (distance_matrix[i, row(deliveries, c)[i]]));


solve :: int_search(deliveredBy, first_fail, indomain_split)
      :: restart_luby(1000)
minimize dist;


% Functions used to print
function array[int] of int: get_tour_rec(array[int] of int: tour, int: curr_i) =
  if curr_i == 0 then [0]
  else [curr_i] ++ get_tour_rec(tour, tour[curr_i])
  endif;
  
function array[int] of int: get_tour(array[int] of int: tour) =
  if tour[0] != 0 then
  [0] ++ get_tour_rec(tour, tour[0])
  endif;
  
  

% Prints

array[0..n] of var int: p1 = row(deliveries,1);
array[0..n] of var int: p2 = row(deliveries,2);
array[0..n] of var int: p3 = row(deliveries,3);
array[0..n] of var int: p4 = row(deliveries,4);

array[0..n] of var int: p5 = row(deliveries,5);
array[0..n] of var int: p6 = row(deliveries,6);
array[0..n] of var int: p7 = row(deliveries,7);
array[0..n] of var int: p8 = row(deliveries,8);
array[0..n] of var int: p9 = row(deliveries,9);
array[0..n] of var int: p10 = row(deliveries,10);
array[0..n] of var int: p11 = row(deliveries,11);
array[0..n] of var int: p12 = row(deliveries,12);
array[0..n] of var int: p13 = row(deliveries,13);
array[0..n] of var int: p14 = row(deliveries,14);
array[0..n] of var int: p15 = row(deliveries,15);
array[0..n] of var int: p16 = row(deliveries,16);
array[0..n] of var int: p17 = row(deliveries,17);
array[0..n] of var int: p18 = row(deliveries,18);
array[0..n] of var int: p19 = row(deliveries,19);
array[0..n] of var int: p20 = row(deliveries,20);


output["["];
output[show(get_tour(fix(p1))) ++ "," ++ show(get_tour(fix(p2))) ++ "," ++ show(get_tour(fix(p3))) ++ "," ++ show(get_tour(fix(p4)))];
output["," ++ show(get_tour(fix(p5))) ++ "," ++ show(get_tour(fix(p6))) ++ "," ++ show(get_tour(fix(p7))) ++ "," ++ show(get_tour(fix(p8))) ++ "," ++ show(get_tour(fix(p9))) ++ "," ++ show(get_tour(fix(p10))) ++ "," ++ show(get_tour(fix(p11))) ++ "," ++ show(get_tour(fix(p12))) ++ "," ++ show(get_tour(fix(p13))) ++ "," ++ show(get_tour(fix(p14))) ++ "," ++ show(get_tour(fix(p15))) ++ "," ++ show(get_tour(fix(p16))) ++ "," ++ show(get_tour(fix(p17))) ++ "," ++ show(get_tour(fix(p18))) ++ "," ++ show(get_tour(fix(p19))) ++ "," ++ show(get_tour(fix(p20)))];
output["]"];
%output["\n\n"];

%output ["deliveredBy: " ++ show(deliveredBy)];
output["\n\n"];
output ["Total distance = " ++ show(dist)];



% Best results
% Inst01 = 2968 {with random best 2916, worst 3212}
% inst02 = 6628
% inst03 = 13278
% inst04 = 16012
% inst05 = 18498 
% inst06 = 25386
% inst07 = 5228
% inst08 = 12286
% inst09 = 19182
% inst10 = 24742
% inst11 = 3174



