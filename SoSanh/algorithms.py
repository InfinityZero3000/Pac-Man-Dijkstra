import heapq

def reconstruct_path(came_from, start, goal):
    if goal not in came_from:
        return None

    path = [goal]
    cur = goal
    while cur != start:
        cur = came_from[cur]
        path.append(cur)

    return list(reversed(path))


# ----------------------------------------------------------
# DIJKSTRA CÓ TRACK QUÁ TRÌNH QUÉT
# ----------------------------------------------------------
def dijkstra(maze):
    start = maze.start
    goal = maze.goal

    pq = [(0, start)]
    dist = {start: 0}
    came_from = {}
    visited = set()
    explored = []     # <--- danh sách các node được quét (mới)

    while pq:
        cost, current = heapq.heappop(pq)

        if current in visited:
            continue
        visited.add(current)
        explored.append(current)   # <--- lưu thứ tự duyệt

        if current == goal:
            break

        for nb in maze.get_neighbors(current):
            new_cost = cost + 1
            if new_cost < dist.get(nb, float("inf")):
                dist[nb] = new_cost
                came_from[nb] = current
                heapq.heappush(pq, (new_cost, nb))

    return reconstruct_path(came_from, start, goal), dist.get(goal, float("inf")), explored


# ----------------------------------------------------------
# A* CÓ TRACK QUÁ TRÌNH QUÉT
# ----------------------------------------------------------
def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(maze):
    start = maze.start
    goal = maze.goal

    open_list = [(heuristic(start, goal), 0, start)]
    came_from = {}
    g = {start: 0}
    closed = set()
    explored = []     # <--- radar scanning list

    while open_list:
        f, cost, current = heapq.heappop(open_list)

        if current in closed:
            continue
        closed.add(current)
        explored.append(current)   # <--- lưu thứ tự duyệt

        if current == goal:
            break

        for nb in maze.get_neighbors(current):
            new_g = g[current] + 1

            if new_g < g.get(nb, float("inf")):
                g[nb] = new_g
                came_from[nb] = current
                f_new = new_g + heuristic(nb, goal)
                heapq.heappush(open_list, (f_new, new_g, nb))

    return reconstruct_path(came_from, start, goal), g.get(goal, float("inf")), explored
