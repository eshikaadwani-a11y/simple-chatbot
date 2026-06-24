# Data Structures & Algorithms — Core Notes

## Big-O and complexity
Big-O describes how runtime or memory grows with input size n. Common classes:
O(1) constant, O(log n) logarithmic, O(n) linear, O(n log n) linearithmic,
O(n^2) quadratic, O(2^n) exponential. Analyze the dominant term and drop
constants. Always state both time and space complexity.

## Arrays and two pointers
The two-pointer technique uses two indices moving toward each other or in the same
direction to solve problems in O(n) instead of O(n^2). Classic uses: pair-sum in a
sorted array, removing duplicates, reversing, and partitioning. A related pattern,
the sliding window, maintains a moving range to compute running aggregates
(longest substring without repeats, max sum subarray of size k).

## Binary search
Binary search finds a target in a sorted array in O(log n) by halving the search
space. Beyond exact match, "binary search on the answer" solves optimization
problems where a predicate is monotonic (e.g., minimum capacity to ship within D
days). Watch the loop invariant and mid computation to avoid overflow/off-by-one.

## Hashing
Hash maps give average O(1) insert/lookup and are the workhorse for frequency
counts, deduplication, and caching (memoization). Trade-offs: worst-case O(n) on
collisions and unordered iteration. Use them to turn O(n^2) brute force into O(n).

## Stacks, queues, and monotonic stacks
Stacks (LIFO) support DFS, expression parsing, and "next greater element" via a
monotonic stack in O(n). Queues (FIFO) drive BFS and level-order traversal.

## Trees and graphs
Binary search trees give O(log n) operations when balanced (AVL, red-black). Tree
traversals: inorder, preorder, postorder, and level-order (BFS). Graph traversals:
BFS (shortest path in unweighted graphs), DFS (cycle detection, topological sort).
Dijkstra finds shortest paths with non-negative weights in O((V+E) log V) using a
priority queue.

## Dynamic programming
DP solves problems with overlapping subproblems and optimal substructure. Define a
state, a recurrence, and base cases; implement top-down (memoization) or bottom-up
(tabulation). Classic problems: knapsack, longest common subsequence, edit
distance, coin change. Optimize space by keeping only the needed previous states.

## Interview heuristics
Clarify constraints, state brute force first, then optimize. Recognize patterns:
sorted input → binary search/two pointers; substring/subarray → sliding window;
"k largest" → heap; combinatorial search → backtracking; optimal value over
choices → DP.
