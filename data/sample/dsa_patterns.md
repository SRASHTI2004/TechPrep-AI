# Knapsack Problem
Prerequisite knowledge: Introduction to Dynamic Programming

## Introduction
Consider the following example:

## [USACO07 Dec] Charm Bracelet
There are  
$n$  distinct items and a knapsack of capacity  
$W$ . Each item has 2 attributes, weight ( 
$w_{i}$ ) and value ( 
$v_{i}$ ). You have to select a subset of items to put into the knapsack such that the total weight does not exceed the capacity  
$W$  and the total value is maximized.

In the example above, each object has only two possible states (taken or not taken), corresponding to binary 0 and 1. Thus, this type of problem is called "0-1 knapsack problem".

## 0-1 Knapsack
## Explanation
In the example above, the input to the problem is the following: the weight of  
$i^{th}$  item  
$w_{i}$ , the value of  
$i^{th}$  item  
$v_{i}$ , and the total capacity of the knapsack  
$W$ .

Let  
$f_{i, j}$  be the dynamic programming state holding the maximum total value the knapsack can carry with capacity  
$j$ , when only the first  
$i$  items are considered.

Assuming that all states of the first  
$i-1$  items have been processed, what are the options for the  
$i^{th}$  item?

When it is not put into the knapsack, the remaining capacity remains unchanged and total value does not change. Therefore, the maximum value in this case is  
$f_{i-1, j}$ 
When it is put into the knapsack, the remaining capacity decreases by  
$w_{i}$  and the total value increases by  
$v_{i}$ , so the maximum value in this case is  
$f_{i-1, j-w_i} + v_i$ 
From this we can derive the dp transition equation:

 
$$f_{i, j} = \max(f_{i-1, j}, f_{i-1, j-w_i} + v_i)$$ 
Further, as  
$f_{i}$  is only dependent on  
$f_{i-1}$ , we can remove the first dimension. We obtain the transition rule

 
$$f_j \gets \max(f_j, f_{j-w_i}+v_i)$$ 
that should be executed in the decreasing order of  
$j$  (so that  
$f_{j-w_i}$  implicitly corresponds to  
$f_{i-1,j-w_i}$  and not  
$f_{i,j-w_i}$ ).

It is important to understand this transition rule, because most of the transitions for knapsack problems are derived in a similar way.

## Implementation
The algorithm described can be implemented in  
$O(nW)$  as:


for (int i = 1; i <= n; i++)
  for (int j = W; j >= w[i]; j--)
    f[j] = max(f[j], f[j - w[i]] + v[i]);
Again, note the order of execution. It should be strictly followed to ensure the following invariant: Right before the pair  
$(i, j)$  is processed,  
$f_k$  corresponds to  
$f_{i,k}$  for  
$k > j$ , but to  
$f_{i-1,k}$  for  
$k < j$ . This ensures that  
$f_{j-w_i}$  is taken from the  
$(i-1)$ -th step, rather than from the  
$i$ -th one.

## Complete Knapsack
The complete knapsack model is similar to the 0-1 knapsack, the only difference from the 0-1 knapsack is that an item can be selected an unlimited number of times instead of only once.

We can refer to the idea of 0-1 knapsack to define the state:  
$f_{i, j}$ , the maximum value the knapsack can obtain using the first  
$i$  items with maximum capacity  
$j$ .

It should be noted that although the state definition is similar to that of a 0-1 knapsack, its transition rule is different from that of a 0-1 knapsack.

## Explanation
The trivial approach is, for the first  
$i$  items, enumerate how many times each item is to be taken. The time complexity of this is  
$O(n^2W)$ .

This yields the following transition equation:

 
$$f_{i, j} = \max\limits_{k=0}^{\infty}(f_{i-1, j-k\cdot w_i} + k\cdot v_i)$$ 
At the same time, it simplifies into a "flat" equation:

 
$$f_{i, j} = \max(f_{i-1, j},f_{i, j-w_i} + v_i)$$ 
The reason this works is that  
$f_{i, j-w_i}$  has already been updated by  
$f_{i, j-2\cdot w_i}$  and so on.

Similar to the 0-1 knapsack, we can remove the first dimension to optimize the space complexity. This gives us the same transition rule as 0-1 knapsack.

 
$$f_j \gets \max(f_j, f_{j-w_i}+v_i)$$ 
## Implementation
The algorithm described can be implemented in  
$O(nW)$  as:


for (int i = 1; i <= n; i++)
  for (int j = w[i]; j <= W; j++)
    f[j] = max(f[j], f[j - w[i]] + v[i]);
Despite having the same transition rule, the code above is incorrect for 0-1 knapsack.

Observing the code carefully, we see that for the currently processed item  
$i$  and the current state  
$f_{i,j}$ , when  
$j\geqslant w_{i}$ ,  
$f_{i,j}$  will be affected by  
$f_{i,j-w_{i}}$ . This is equivalent to being able to put item  
$i$  into the backpack multiple times, which is consistent with the complete knapsack problem and not the 0-1 knapsack problem.

## Multiple Knapsack
Multiple knapsack is also a variant of 0-1 knapsack. The main difference is that there are  
$k_i$  of each item instead of just  
$1$ .

## Explanation
A very simple idea is: "choose each item  
$k_i$  times" is equivalent to " 
$k_i$  of the same item is selected one by one". Thus converting it to a 0-1 knapsack model, which can be described by the transition function:

 
$$f_{i, j} = \max_{k=0}^{k_i}(f_{i-1,j-k\cdot w_i} + k\cdot v_i)$$ 
The time complexity of this process is  
$O(W\sum\limits_{i=1}^{n}k_i)$ 

## Binary Grouping Optimization
We still consider converting the multiple knapsack model into a 0-1 knapsack model for optimization. The time complexity  
$O(Wn)$  can not be further optimized with the approach above, so we focus on  
$O(\sum k_i)$  component.

Let  
$A_{i, j}$  denote the  
$j^{th}$  item split from the  
$i^{th}$  item. In the trivial approach discussed above,  
$A_{i, j}$  represents the same item for all  
$j \leq k_i$ . The main reason for our low efficiency is that we are doing a lot of repetetive work. For example, consider selecting  
$\{A_{i, 1},A_{i, 2}\}$ , and selecting  
$\{A_{i, 2}, A_{i, 3}\}$ . These two situations are completely equivalent. Thus optimizing the splitting method will greatly reduce the time complexity.

The grouping is made more efficient by using binary grouping.

Specifically,  
$A_{i, j}$  holds  
$2^j$  individual items ( 
$j\in[0,\lfloor \log_2(k_i+1)\rfloor-1]$ ).If  
$k_i + 1$  is not an integer power of  
$2$ , another bundle of size  
$k_i-(2^{\lfloor \log_2(k_i+1)\rfloor}-1)$  is used to make up for it.

Through the above splitting method, it is possible to obtain any sum of  
$\leq k_i$  items by selecting a few  
$A_{i, j}$ 's. After splitting each item in the described way, it is sufficient to use 0-1 knapsack method to solve the new formulation of the problem.

This optimization gives us a time complexity of  
$O(W\sum\limits_{i=1}^{n}\log k_i)$ .

## Implementation

index = 0;
for (int i = 1; i <= n; i++) {
  int c = 1, p, h, k;
  cin >> p >> h >> k;
  while (k > c) {
    k -= c;
    list[++index].w = c * p;
    list[index].v = c * h;
    c *= 2;
  }
  list[++index].w = p * k;
  list[index].v = h * k;
}
## Monotone Queue Optimization
In this optimization, we aim to convert the knapsack problem into a maximum queue one.

For convenience of description, let  
$g_{x, y} = f_{i, x \cdot w_i + y} ,\space g'_{x, y} = f_{i-1, x \cdot w_i + y}$ . Then the transition rule can be written as:

 
$$g_{x, y} = \max_{k=0}^{k_i}(g'_{x-k, y} + v_i \cdot k)$$ 
Further, let  
$G_{x, y} = g'_{x, y} - v_i \cdot x$ . Then the transition rule can be expressed as:

 
$$g_{x, y} \gets \max_{k=0}^{k_i}(G_{x-k, y}) + v_i \cdot x$$ 
This transforms into a classic monotone queue optimization form.  
$G_{x, y}$  can be calculated in  
$O(1)$ , so for a fixed  
$y$ , we can calculate  
$g_{x, y}$  in  
 
 
$O(\lfloor \frac{W}{w_i} \rfloor)$  time. Therefore, the complexity of finding all  
$g_{x, y}$  is  
 
 
$O(\lfloor \frac{W}{w_i} \rfloor) \times O(w_i) = O(W)$ . In this way, the total complexity of the algorithm is reduced to  
$O(nW)$ .

## Mixed Knapsack
The mixed knapsack problem involves a combination of the three problems described above. That is, some items can only be taken once, some can be taken infinitely, and some can be taken atmost  
$k$  times.

The problem may seem daunting, but as long as you understand the core ideas of the previous knapsack problems and combine them together, you can do it. The pseudo code for the solution is as:


for (each item) {
  if (0-1 knapsack)
    Apply 0-1 knapsack code;
  else if (complete knapsack)
    Apply complete knapsack code;
  else if (multiple knapsack)
    Apply multiple knapsack code;
}


# 0-1 BFS
It is well-known, that you can find the shortest paths between a single source and all other vertices in  
$O(|E|)$  using Breadth First Search in an unweighted graph, i.e. the distance is the minimal number of edges that you need to traverse from the source to another vertex. We can interpret such a graph also as a weighted graph, where every edge has the weight  
$1$ . If not all edges in graph have the same weight, then we need a more general algorithm, like Dijkstra which runs in  
$O(|V|^2 + |E|)$  or  
$O(|E| \log |V|)$  time.

However if the weights are more constrained, we can often do better. In this article we demonstrate how we can use BFS to solve the SSSP (single-source shortest path) problem in  
$O(|E|)$ , if the weight of each edge is either  
$0$  or  
$1$ .

## Algorithm
We can develop the algorithm by closely studying Dijkstra's algorithm and thinking about the consequences that our special graph implies. The general form of Dijkstra's algorithm is (here a set is used for the priority queue):


d.assign(n, INF);
d[s] = 0;
set<pair<int, int>> q;
q.insert({0, s});
while (!q.empty()) {
    int v = q.begin()->second;
    q.erase(q.begin());

    for (auto edge : adj[v]) {
        int u = edge.first;
        int w = edge.second;

        if (d[v] + w < d[u]) {
            q.erase({d[u], u});
            d[u] = d[v] + w;
            q.insert({d[u], u});
        }
    }
}
We can notice that the difference between the distances between the source s and two other vertices in the queue differs by at most one. Especially, we know that  
$d[v] \le d[u] \le d[v] + 1$  for each  
$u \in Q$ . The reason for this is, that we only add vertices with equal distance or with distance plus one to the queue during each iteration. Assuming there exists a  
$u$  in the queue with  
$d[u] - d[v] > 1$ , then  
$u$  must have been inserted into the queue via a different vertex  
$t$  with  
$d[t] \ge d[u] - 1 > d[v]$ . However this is impossible, since Dijkstra's algorithm iterates over the vertices in increasing order.

This means, that the order of the queue looks like this:

  
 
 
  
 
 
  
 
 
  
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
$$Q = \underbrace{v}_{d[v]}, \dots, \underbrace{u}_{d[v]}, \underbrace{m}_{d[v]+1} \dots \underbrace{n}_{d[v]+1}$$ 
This structure is so simple, that we don't need an actual priority queue, i.e. using a balanced binary tree would be an overkill. We can simply use a normal queue, and append new vertices at the beginning if the corresponding edge has weight  
$0$ , i.e. if  
$d[u] = d[v]$ , or at the end if the edge has weight  
$1$ , i.e. if  
$d[u] = d[v] + 1$ . This way the queue still remains sorted at all time.


vector<int> d(n, INF);
d[s] = 0;
deque<int> q;
q.push_front(s);
while (!q.empty()) {
    int v = q.front();
    q.pop_front();
    for (auto edge : adj[v]) {
        int u = edge.first;
        int w = edge.second;
        if (d[v] + w < d[u]) {
            d[u] = d[v] + w;
            if (w == 1)
                q.push_back(u);
            else
                q.push_front(u);
        }
    }
}
## Dial's algorithm
We can extend this even further if we allow the weights of the edges to be even bigger. If every edge in the graph has a weight  
$\le k$ , then the distances of vertices in the queue will differ by at most  
$k$  from the distance of  
$v$  to the source. So we can keep  
$k + 1$  buckets for the vertices in the queue, and whenever the bucket corresponding to the smallest distance gets empty, we make a cyclic shift to get the bucket with the next higher distance. This extension is called Dial's algorithm


# Minimum spanning tree - Kruskal's algorithm
Given a weighted undirected graph. We want to find a subtree of this graph which connects all vertices (i.e. it is a spanning tree) and has the least weight (i.e. the sum of weights of all the edges is minimum) of all possible spanning trees. This spanning tree is called a minimum spanning tree.

In the left image you can see a weighted undirected graph, and in the right image you can see the corresponding minimum spanning tree.

Random graph MST of this graph

This article will discuss few important facts associated with minimum spanning trees, and then will give the simplest implementation of Kruskal's algorithm for finding minimum spanning tree.

## Properties of the minimum spanning tree
A minimum spanning tree of a graph is unique, if the weight of all the edges are distinct. Otherwise, there may be multiple minimum spanning trees. (Specific algorithms typically output one of the possible minimum spanning trees).
Minimum spanning tree is also the tree with minimum product of weights of edges. (It can be easily proved by replacing the weights of all edges with their logarithms)
In a minimum spanning tree of a graph, the maximum weight of an edge is the minimum possible from all possible spanning trees of that graph. (This follows from the validity of Kruskal's algorithm).
The maximum spanning tree (spanning tree with the sum of weights of edges being maximum) of a graph can be obtained similarly to that of the minimum spanning tree, by changing the signs of the weights of all the edges to their opposite and then applying any of the minimum spanning tree algorithm.
## Kruskal's algorithm
This algorithm was described by Joseph Bernard Kruskal, Jr. in 1956.

Kruskal's algorithm initially places all the nodes of the original graph isolated from each other, to form a forest of single node trees, and then gradually merges these trees, combining at each iteration any two of all the trees with some edge of the original graph. Before the execution of the algorithm, all edges are sorted by weight (in non-decreasing order). Then begins the process of unification: pick all edges from the first to the last (in sorted order), and if the ends of the currently picked edge belong to different subtrees, these subtrees are combined, and the edge is added to the answer. After iterating through all the edges, all the vertices will belong to the same sub-tree, and we will get the answer.

## The simplest implementation
The following code directly implements the algorithm described above, and is having  
$O(M \log M + N^2)$  time complexity. Sorting edges requires  
$O(M \log N)$  (which is the same as  
$O(M \log M)$ ) operations. Information regarding the subtree to which a vertex belongs is maintained with the help of an array tree_id[] - for each vertex v, tree_id[v] stores the number of the tree , to which v belongs. For each edge, whether it belongs to the ends of different trees, can be determined in  
$O(1)$ . Finally, the union of the two trees is carried out in  
$O(N)$  by a simple pass through tree_id[] array. Given that the total number of merge operations is  
$N-1$ , we obtain the asymptotic behavior of  
$O(M \log N + N^2)$ .


struct Edge {
    int u, v, weight;
    bool operator<(Edge const& other) {
        return weight < other.weight;
    }
};

int n;
vector<Edge> edges;

int cost = 0;
vector<int> tree_id(n);
vector<Edge> result;
for (int i = 0; i < n; i++)
    tree_id[i] = i;

sort(edges.begin(), edges.end());

for (Edge e : edges) {
    if (tree_id[e.u] != tree_id[e.v]) {
        cost += e.weight;
        result.push_back(e);

        int old_id = tree_id[e.u], new_id = tree_id[e.v];
        for (int i = 0; i < n; i++) {
            if (tree_id[i] == old_id)
                tree_id[i] = new_id;
        }
    }
}
## Proof of correctness
Why does Kruskal's algorithm give us the correct result?

If the original graph was connected, then also the resulting graph will be connected. Because otherwise there would be two components that could be connected with at least one edge. Though this is impossible, because Kruskal would have chosen one of these edges, since the ids of the components are different. Also the resulting graph doesn't contain any cycles, since we forbid this explicitly in the algorithm. Therefore the algorithm generates a spanning tree.

So why does this algorithm give us a minimum spanning tree?

We can show the proposal "if  
$F$  is a set of edges chosen by the algorithm at any stage in the algorithm, then there exists a MST that contains all edges of  
$F$ " using induction.

The proposal is obviously true at the beginning, the empty set is a subset of any MST.

Now let's assume  
$F$  is some edge set at any stage of the algorithm,  
$T$  is a MST containing  
$F$  and  
$e$  is the new edge we want to add using Kruskal.

If  
$e$  generates a cycle, then we don't add it, and so the proposal is still true after this step.

In case that  
$T$  already contains  
$e$ , the proposal is also true after this step.

In case  
$T$  doesn't contain the edge  
$e$ , then  
$T + e$  will contain a cycle  
$C$ . This cycle will contain at least one edge  
$f$ , that is not in  
$F$ . The set of edges  
$T - f + e$  will also be a spanning tree. Notice that the weight of  
$f$  cannot be smaller than the weight of  
$e$ , because otherwise Kruskal would have chosen  
$f$  earlier. It also cannot have a bigger weight, since that would make the total weight of  
$T - f + e$  smaller than the total weight of  
$T$ , which is impossible since  
$T$  is already a MST. This means that the weight of  
$e$  has to be the same as the weight of  
$f$ . Therefore  
$T - f + e$  is also a MST, and it contains all edges from  
$F + e$ . So also here the proposal is still fulfilled after the step.

This proves the proposal. Which means that after iterating over all edges the resulting edge set will be connected, and will be contained in a MST, which means that it has to be a MST already.

## Improved implementation
We can use the Disjoint Set Union (DSU) data structure to write a faster implementation of the Kruskal's algorithm with the time complexity of about  
$O(M \log N)$ . This article details such an approach.


# Rabin-Karp Algorithm for string matching
This algorithm is based on the concept of hashing, so if you are not familiar with string hashing, refer to the string hashing article.

This algorithm was authored by Rabin and Karp in 1987.

Problem: Given two strings - a pattern  
$s$  and a text  
$t$ , determine if the pattern appears in the text and if it does, enumerate all its occurrences in  
$O(|s| + |t|)$  time.

Algorithm: Calculate the hash for the pattern  
$s$ . Calculate hash values for all the prefixes of the text  
$t$ . Now, we can compare a substring of length  
$|s|$  with  
$s$  in constant time using the calculated hashes. So, compare each substring of length  
$|s|$  with the pattern. This will take a total of  
$O(|t|)$  time. Hence the final complexity of the algorithm is  
$O(|t| + |s|)$ :  
$O(|s|)$  is required for calculating the hash of the pattern and  
$O(|t|)$  for comparing each substring of length  
$|s|$  with the pattern.

## Implementation

vector<int> rabin_karp(string const& s, string const& t) {
    const int p = 31; 
    const int m = 1e9 + 9;
    int S = s.size(), T = t.size();

    vector<long long> p_pow(max(S, T)); 
    p_pow[0] = 1; 
    for (int i = 1; i < (int)p_pow.size(); i++) 
        p_pow[i] = (p_pow[i-1] * p) % m;

    vector<long long> h(T + 1, 0); 
    for (int i = 0; i < T; i++)
        h[i+1] = (h[i] + (t[i] - 'a' + 1) * p_pow[i]) % m; 
    long long h_s = 0; 
    for (int i = 0; i < S; i++) 
        h_s = (h_s + (s[i] - 'a' + 1) * p_pow[i]) % m; 

    vector<int> occurrences;
    for (int i = 0; i + S - 1 < T; i++) {
        long long cur_h = (h[i+S] + m - h[i]) % m;
        if (cur_h == h_s * p_pow[i] % m)
            occurrences.push_back(i);
    }
    return occurrences;
}


# Prefix function. Knuth–Morris–Pratt algorithm
## Prefix function definition
You are given a string  
$s$  of length  
$n$ . The prefix function for this string is defined as an array  
$\pi$  of length  
$n$ , where  
$\pi[i]$  is the length of the longest proper prefix of the substring  
$s[0 \dots i]$  which is also a suffix of this substring. A proper prefix of a string is a prefix that is not equal to the string itself. By definition,  
$\pi[0] = 0$ .

Mathematically the definition of the prefix function can be written as follows:

  
 
 
$$\pi[i] = \max_ {k = 0 \dots i} \{k : s[0 \dots k-1] = s[i-(k-1) \dots i] \}$$ 
For example, prefix function of string "abcabcd" is  
$[0, 0, 0, 1, 2, 3, 0]$ , and prefix function of string "aabaaab" is  
$[0, 1, 0, 1, 2, 2, 3]$ .

## Trivial Algorithm
An algorithm which follows the definition of prefix function exactly is the following:


vector<int> prefix_function(string s) {
    int n = (int)s.length();
    vector<int> pi(n);
    for (int i = 0; i < n; i++)
        for (int k = 0; k <= i; k++)
            if (s.substr(0, k) == s.substr(i-k+1, k))
                pi[i] = k;
    return pi;
}
It is easy to see that its complexity is  
$O(n^3)$ , which has room for improvement.

## Efficient Algorithm
This algorithm was proposed by Knuth and Pratt and independently from them by Morris in 1977. It was used as the main function of a substring search algorithm.

## First optimization
The first important observation is, that the values of the prefix function can only increase by at most one.

Indeed, otherwise, if  
$\pi[i + 1] \gt \pi[i] + 1$ , then we can take this suffix ending in position  
$i + 1$  with the length  
$\pi[i + 1]$  and remove the last character from it. We end up with a suffix ending in position  
$i$  with the length  
$\pi[i + 1] - 1$ , which is better than  
$\pi[i]$ , i.e. we get a contradiction.

The following illustration shows this contradiction. The longest proper suffix at position  
$i$  that also is a prefix is of length  
$2$ , and at position  
$i+1$  it is of length  
$4$ . Therefore the string  
$s_0 ~ s_1 ~ s_2 ~ s_3$  is equal to the string  
$s_{i-2} ~ s_{i-1} ~ s_i ~ s_{i+1}$ , which means that also the strings  
$s_0 ~ s_1 ~ s_2$  and  
$s_{i-2} ~ s_{i-1} ~ s_i$  are equal, therefore  
$\pi[i]$  has to be  
$3$ .

  
 
 
 
  
 
 
 
 
 
 
 
 
 
 
 
 
$$\underbrace{\overbrace{s_0 ~ s_1}^{\pi[i] = 2} ~ s_2 ~ s_3}_{\pi[i+1] = 4} ~ \dots ~ \underbrace{s_{i-2} ~ \overbrace{s_{i-1} ~ s_{i}}^{\pi[i] = 2} ~ s_{i+1}}_{\pi[i+1] = 4}$$ 
Thus when moving to the next position, the value of the prefix function can either increase by one, stay the same, or decrease by some amount. This fact already allows us to reduce the complexity of the algorithm to  
$O(n^2)$ , because in one step the prefix function can grow at most by one. In total the function can grow at most  
$n$  steps, and therefore also only can decrease a total of  
$n$  steps. This means we only have to perform  
$O(n)$  string comparisons, and reach the complexity  
$O(n^2)$ .

## Second optimization
Let's go further, we want to get rid of the string comparisons. To accomplish this, we have to use all the information computed in the previous steps.

So let us compute the value of the prefix function  
$\pi$  for  
$i + 1$ . If  
$s[i+1] = s[\pi[i]]$ , then we can say with certainty that  
$\pi[i+1] = \pi[i] + 1$ , since we already know that the suffix at position  
$i$  of length  
$\pi[i]$  is equal to the prefix of length  
$\pi[i]$ . This is illustrated again with an example.

  
 
 
 
 
  
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
$$\underbrace{\overbrace{s_0 ~ s_1 ~ s_2}^{\pi[i]} ~ \overbrace{s_3}^{s_3 = s_{i+1}}}_{\pi[i+1] = \pi[i] + 1} ~ \dots ~ \underbrace{\overbrace{s_{i-2} ~ s_{i-1} ~ s_{i}}^{\pi[i]} ~ \overbrace{s_{i+1}}^{s_3 = s_{i + 1}}}_{\pi[i+1] = \pi[i] + 1}$$ 
If this is not the case,  
$s[i+1] \neq s[\pi[i]]$ , then we need to try a shorter string. In order to speed things up, we would like to immediately move to the longest length  
$j \lt \pi[i]$ , such that the prefix property in the position  
$i$  holds, i.e.  
$s[0 \dots j-1] = s[i-j+1 \dots i]$ :

 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
$$\overbrace{\underbrace{s_0 ~ s_1}_j ~ s_2 ~ s_3}^{\pi[i]} ~ \dots ~ \overbrace{s_{i-3} ~ s_{i-2} ~ \underbrace{s_{i-1} ~ s_{i}}_j}^{\pi[i]} ~ s_{i+1}$$ 
Indeed, if we find such a length  
$j$ , then we again only need to compare the characters  
$s[i+1]$  and  
$s[j]$ . If they are equal, then we can assign  
$\pi[i+1] = j + 1$ . Otherwise we will need to find the largest value smaller than  
$j$ , for which the prefix property holds, and so on. It can happen that this goes until  
$j = 0$ . If then  
$s[i+1] = s[0]$ , we assign  
$\pi[i+1] = 1$ , and  
$\pi[i+1] = 0$  otherwise.

So we already have a general scheme of the algorithm. The only question left is how do we effectively find the lengths for  
$j$ . Let's recap: for the current length  
$j$  at the position  
$i$  for which the prefix property holds, i.e.  
$s[0 \dots j-1] = s[i-j+1 \dots i]$ , we want to find the greatest  
$k \lt j$ , for which the prefix property holds.

 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
$$\overbrace{\underbrace{s_0 ~ s_1}_k ~ s_2 ~ s_3}^j ~ \dots ~ \overbrace{s_{i-3} ~ s_{i-2} ~ \underbrace{s_{i-1} ~ s_{i}}_k}^j ~s_{i+1}$$ 
The illustration shows, that this has to be the value of  
$\pi[j-1]$ , which we already calculated earlier.

## Final algorithm
So we finally can build an algorithm that doesn't perform any string comparisons and only performs  
$O(n)$  actions.

Here is the final procedure:

We compute the prefix values  
$\pi[i]$  in a loop by iterating from  
$i = 1$  to  
$i = n-1$  ( 
$\pi[0]$  just gets assigned with  
$0$ ).
To calculate the current value  
$\pi[i]$  we set the variable  
$j$  denoting the length of the best suffix for  
$i-1$ . Initially  
$j = \pi[i-1]$ .
Test if the suffix of length  
$j+1$  is also a prefix by comparing  
$s[j]$  and  
$s[i]$ . If they are equal then we assign  
$\pi[i] = j + 1$ , otherwise we reduce  
$j$  to  
$\pi[j-1]$  and repeat this step.
If we have reached the length  
$j = 0$  and still don't have a match, then we assign  
$\pi[i] = 0$  and go to the next index  
$i + 1$ .
## Implementation
The implementation ends up being surprisingly short and expressive.


vector<int> prefix_function(string s) {
    int n = (int)s.length();
    vector<int> pi(n);
    for (int i = 1; i < n; i++) {
        int j = pi[i-1];
        while (j > 0 && s[i] != s[j])
            j = pi[j-1];
        if (s[i] == s[j])
            j++;
        pi[i] = j;
    }
    return pi;
}
This is an online algorithm, i.e. it processes the data as it arrives - for example, you can read the string characters one by one and process them immediately, finding the value of prefix function for each next character. The algorithm still requires storing the string itself and the previously calculated values of prefix function, but if we know beforehand the maximum value  
$M$  the prefix function can take on the string, we can store only  
$M+1$  first characters of the string and the same number of values of the prefix function.

## Applications
## Search for a substring in a string. The Knuth-Morris-Pratt algorithm
The task is the classical application of the prefix function.

Given a text  
$t$  and a string  
$s$ , we want to find and display the positions of all occurrences of the string  
$s$  in the text  
$t$ .

For convenience we denote with  
$n$  the length of the string s and with  
$m$  the length of the text  
$t$ .

We generate the string  
$s + \# + t$ , where  
$\#$  is a separator that appears neither in  
$s$  nor in  
$t$ . Let us calculate the prefix function for this string. Now think about the meaning of the values of the prefix function, except for the first  
$n + 1$  entries (which belong to the string  
$s$  and the separator). By definition the value  
$\pi[i]$  shows the longest length of a substring ending in position  
$i$  that coincides with the prefix. But in our case this is nothing more than the largest block that coincides with  
$s$  and ends at position  
$i$ . This length cannot be bigger than  
$n$  due to the separator. But if equality  
$\pi[i] = n$  is achieved, then it means that the string  
$s$  appears completely in at this position, i.e. it ends at position  
$i$ . Just do not forget that the positions are indexed in the string  
$s + \# + t$ .

Thus if at some position  
$i$  we have  
$\pi[i] = n$ , then at the position  
$i - (n + 1) - n + 1 = i - 2n$  in the string  
$t$  the string  
$s$  appears.

As already mentioned in the description of the prefix function computation, if we know that the prefix values never exceed a certain value, then we do not need to store the entire string and the entire function, but only its beginning. In our case this means that we only need to store the string  
$s + \#$  and the values of the prefix function for it. We can read one character at a time of the string  
$t$  and calculate the current value of the prefix function.

Thus the Knuth-Morris-Pratt algorithm solves the problem in  
$O(n + m)$  time and  
$O(n)$  memory.

## Counting the number of occurrences of each prefix
Here we discuss two problems at once. Given a string  
$s$  of length  
$n$ . In the first variation of the problem we want to count the number of appearances of each prefix  
$s[0 \dots i]$  in the same string. In the second variation of the problem another string  
$t$  is given and we want to count the number of appearances of each prefix  
$s[0 \dots i]$  in  
$t$ .

First we solve the first problem. Consider the value of the prefix function  
$\pi[i]$  at a position  
$i$ . By definition it means that the prefix of length  
$\pi[i]$  of the string  
$s$  occurs and ends at position  
$i$ , and there is no longer prefix that follows this definition. At the same time shorter prefixes can end at this position. It is not difficult to see, that we have the same question that we already answered when we computed the prefix function itself: Given a prefix of length  
$j$  that is a suffix ending at position  
$i$ , what is the next smaller prefix  
$\lt j$  that is also a suffix ending at position  
$i$ . Thus at the position  
$i$  ends the prefix of length  
$\pi[i]$ , the prefix of length  
$\pi[\pi[i] - 1]$ , the prefix  
$\pi[\pi[\pi[i] - 1] - 1]$ , and so on, until the index becomes zero. Thus we can compute the answer in the following way.


vector<int> ans(n + 1);
for (int i = 0; i < n; i++)
    ans[pi[i]]++;
for (int i = n-1; i > 0; i--)
    ans[pi[i-1]] += ans[i];
for (int i = 0; i <= n; i++)
    ans[i]++;
Here for each value of the prefix function we first count how many times it occurs in the array  
$\pi$ , and then compute the final answers: if we know that the length prefix  
$i$  appears exactly  
$\text{ans}[i]$  times, then this number must be added to the number of occurrences of its longest suffix that is also a prefix. At the end we need to add  
$1$  to each result, since we also need to count the original prefixes also.

Now let us consider the second problem. We apply the trick from Knuth-Morris-Pratt: we create the string  
$s + \# + t$  and compute its prefix function. The only differences to the first task is, that we are only interested in the prefix values that relate to the string  
$t$ , i.e.  
$\pi[i]$  for  
$i \ge n + 1$ . With those values we can perform the exact same computations as in the first task.

## The number of different substring in a string
Given a string  
$s$  of length  
$n$ . We want to compute the number of different substrings appearing in it.

We will solve this problem iteratively. Namely we will learn, knowing the current number of different substrings, how to recompute this count by adding a character to the end.

So let  
$k$  be the current number of different substrings in  
$s$ , and we add the character  
$c$  to the end of  
$s$ . Obviously some new substrings ending in  
$c$  will appear. We want to count these new substrings that didn't appear before.

We take the string  
$t = s + c$  and reverse it. Now the task is transformed into computing how many prefixes there are that don't appear anywhere else. If we compute the maximal value of the prefix function  
$\pi_{\text{max}}$  of the reversed string  
$t$ , then the longest prefix that appears in  
$s$  is  
$\pi_{\text{max}}$  long. Clearly also all prefixes of smaller length appear in it.

Therefore the number of new substrings appearing when we add a new character  
$c$  is  
$|s| + 1 - \pi_{\text{max}}$ .

So for each character appended we can compute the number of new substrings in  
$O(n)$  times, which gives a time complexity of  
$O(n^2)$  in total.

It is worth noting, that we can also compute the number of different substrings by appending the characters at the beginning, or by deleting characters from the beginning or the end.

## Compressing a string
Given a string  
$s$  of length  
$n$ . We want to find the shortest "compressed" representation of the string, i.e. we want to find a string  
$t$  of smallest length such that  
$s$  can be represented as a concatenation of one or more copies of  
$t$ .

It is clear, that we only need to find the length of  
$t$ . Knowing the length, the answer to the problem will be the prefix of  
$s$  with this length.

Let us compute the prefix function for  
$s$ . Using the last value of it we define the value  
$k = n - \pi[n - 1]$ . We will show, that if  
$k$  divides  
$n$ , then  
$k$  will be the answer, otherwise there is no effective compression and the answer is  
$n$ .

Let  
$n$  be divisible by  
$k$ . Then the string can be partitioned into blocks of the length  
$k$ . By definition of the prefix function, the prefix of length  
$n - k$  will be equal with its suffix. But this means that the last block is equal to the block before. And the block before has to be equal to the block before it. And so on. As a result, it turns out that all blocks are equal, therefore we can compress the string  
$s$  to length  
$k$ .

Of course we still need to show that this is actually the optimum. Indeed, if there was a smaller compression than  
$k$ , than the prefix function at the end would be greater than  
$n - k$ . Therefore  
$k$  is really the answer.

Now let us assume that  
$n$  is not divisible by  
$k$ . We show that this implies that the length of the answer is  
$n$ . We prove it by contradiction. Assuming there exists an answer, and the compression has length  
$p$  ( 
$p$  divides  
$n$ ). Then the last value of the prefix function has to be greater than  
$n - p$ , i.e. the suffix will partially cover the first block. Now consider the second block of the string. Since the prefix is equal with the suffix, and both the prefix and the suffix cover this block and their displacement relative to each other  
$k$  does not divide the block length  
$p$  (otherwise  
$k$  divides  
$n$ ), then all the characters of the block have to be identical. But then the string consists of only one character repeated over and over, hence we can compress it to a string of size  
$1$ , which gives  
$k = 1$ , and  
$k$  divides  
$n$ . Contradiction.

 
 
 
 
 
$$\overbrace{s_0 ~ s_1 ~ s_2 ~ s_3}^p ~ \overbrace{s_4 ~ s_5 ~ s_6 ~ s_7}^p$$ 
  
 
 
 
 
 
 
 
 
$$s_0 ~ s_1 ~ s_2 ~ \underbrace{\overbrace{s_3 ~ s_4 ~ s_5 ~ s_6}^p ~ s_7}_{\pi[7] = 5}$$ 
 
$$s_4 = s_3, ~ s_5 = s_4, ~ s_6 = s_5, ~ s_7 = s_6 ~ \Rightarrow ~ s_0 = s_1 = s_2 = s_3$$ 
## Building an automaton according to the prefix function
Let's return to the concatenation to the two strings through a separator, i.e. for the strings  
$s$  and  
$t$  we compute the prefix function for the string  
$s + \# + t$ . Obviously, since  
$\#$  is a separator, the value of the prefix function will never exceed  
$|s|$ . It follows, that it is sufficient to only store the string  
$s + \#$  and the values of the prefix function for it, and we can compute the prefix function for all subsequent character on the fly:

  
 
 
  
 
 
 
 
 
 
 
 
 
$$\underbrace{s_0 ~ s_1 ~ \dots ~ s_{n-1} ~ \#}_{\text{need to store}} ~ \underbrace{t_0 ~ t_1 ~ \dots ~ t_{m-1}}_{\text{do not need to store}}$$ 
Indeed, in such a situation, knowing the next character  
$c \in t$  and the value of the prefix function of the previous position is enough information to compute the next value of the prefix function, without using any previous characters of the string  
$t$  and the value of the prefix function in them.

In other words, we can construct an automaton (a finite state machine): the state in it is the current value of the prefix function, and the transition from one state to another will be performed via the next character.

Thus, even without having the string  
$t$ , we can construct such a transition table  
$(\text{old}_\pi, c) \rightarrow \text{new}_\pi$  using the same algorithm as for calculating the transition table:


void compute_automaton(string s, vector<vector<int>>& aut) {
    s += '#';
    int n = s.size();
    vector<int> pi = prefix_function(s);
    aut.assign(n, vector<int>(26));
    for (int i = 0; i < n; i++) {
        for (int c = 0; c < 26; c++) {
            int j = i;
            while (j > 0 && 'a' + c != s[j])
                j = pi[j-1];
            if ('a' + c == s[j])
                j++;
            aut[i][c] = j;
        }
    }
}
However in this form the algorithm runs in  
$O(n^2 26)$  time for the lowercase letters of the alphabet. Note that we can apply dynamic programming and use the already calculated parts of the table. Whenever we go from the value  
$j$  to the value  
$\pi[j-1]$ , we actually mean that the transition  
$(j, c)$  leads to the same state as the transition as  
$(\pi[j-1], c)$ , and this answer is already accurately computed.


void compute_automaton(string s, vector<vector<int>>& aut) {
    s += '#';
    int n = s.size();
    vector<int> pi = prefix_function(s);
    aut.assign(n, vector<int>(26));
    for (int i = 0; i < n; i++) {
        for (int c = 0; c < 26; c++) {
            if (i > 0 && 'a' + c != s[i])
                aut[i][c] = aut[pi[i-1]][c];
            else
                aut[i][c] = i + ('a' + c == s[i]);
        }
    }
}
As a result we construct the automaton in  
$O(26 n)$  time.

When is such a automaton useful? To begin with, remember that we use the prefix function for the string  
$s + \# + t$  and its values mostly for a single purpose: find all occurrences of the string  
$s$  in the string  
$t$ .

Therefore the most obvious benefit of this automaton is the acceleration of calculating the prefix function for the string  
$s + \# + t$ . By building the automaton for  
$s + \#$ , we no longer need to store the string  
$s$  or the values of the prefix function in it. All transitions are already computed in the table.

But there is a second, less obvious, application. We can use the automaton when the string  
$t$  is a gigantic string constructed using some rules. This can for instance be the Gray strings, or a string formed by a recursive combination of several short strings from the input.

For completeness we will solve such a problem: given a number  
$k \le 10^5$  and a string  
$s$  of length  
$\le 10^5$ . We have to compute the number of occurrences of  
$s$  in the  
$k$ -th Gray string. Recall that Gray's strings are define in the following way:

  
 
 
$$\begin{align} g_1 &= \text{"a"}\\ g_2 &= \text{"aba"}\\ g_3 &= \text{"abacaba"}\\ g_4 &= \text{"abacabadabacaba"} \end{align}$$ 
In such cases even constructing the string  
$t$  will be impossible, because of its astronomical length. The  
$k$ -th Gray string is  
$2^k-1$  characters long. However we can calculate the value of the prefix function at the end of the string effectively, by only knowing the value of the prefix function at the start.

In addition to the automaton itself, we also compute values  
$G[i][j]$  - the value of the automaton after processing the string  
$g_i$  starting with the state  
$j$ . And additionally we compute values  
$K[i][j]$  - the number of occurrences of  
$s$  in  
$g_i$ , before during the processing of  
$g_i$  starting with the state  
$j$ . Actually  
$K[i][j]$  is the number of times that the prefix function took the value  
$|s|$  while performing the operations. The answer to the problem will then be  
$K[k][0]$ .

How can we compute these values? First the basic values are  
$G[0][j] = j$  and  
$K[0][j] = 0$ . And all subsequent values can be calculated from the previous values and using the automaton. To calculate the value for some  
$i$  we remember that the string  
$g_i$  consists of  
$g_{i-1}$ , the  
$i$  character of the alphabet, and  
$g_{i-1}$ . Thus the automaton will go into the state:


$$\text{mid} = \text{aut}[G[i-1][j]][i]$$ 
 
$$G[i][j] = G[i-1][\text{mid}]$$ 
The values for  
$K[i][j]$  can also be easily counted.

 
$$K[i][j] = K[i-1][j] + (\text{mid} == |s|) + K[i-1][\text{mid}]$$ 
So we can solve the problem for Gray strings, and similarly also a huge number of other similar problems. For example the exact same method also solves the following problem: we are given a string  
$s$  and some patterns  
$t_i$ , each of which is specified as follows: it is a string of ordinary characters, and there might be some recursive insertions of the previous strings of the form  
$t_k^{\text{cnt}}$ , which means that at this place we have to insert the string  
$t_k$   
$\text{cnt}$  times. An example of such patterns:

  
 
 
$$\begin{align} t_1 &= \text{"abdeca"}\\ t_2 &= \text{"abc"} + t_1^{30} + \text{"abd"}\\ t_3 &= t_2^{50} + t_1^{100}\\ t_4 &= t_2^{10} + t_3^{100} \end{align}$$ 
The recursive substitutions blow the string up, so that their lengths can reach the order of  
$100^{100}$ .

We have to find the number of times the string  
$s$  appears in each of the strings.

The problem can be solved in the same way by constructing the automaton of the prefix function, and then we calculate the transitions in for each pattern by using the previous results.