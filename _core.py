import tkinter as tk
from tkinter import Canvas
import random
import numpy as np
from typing import Iterable
from typing import Iterable, List, Tuple


points = []
ga = []
optimized_solution = []


def is_convex(polygon: Iterable) -> bool:
    polygon = np.array(polygon)
    if len(polygon) < 3:
        return False
    orientation = 0
    for p1, p2, p3 in zip(*[np.roll(polygon, i, axis=0) for i in range(3)]):
        dxa, dya = p2 - p1
        dxb, dyb = p3 - p2
        cross = dxa * dyb - dya * dxb
        if not (-1e-5 < cross < 1e-5):
            if orientation == 0:
                orientation = np.sign(cross)
            elif orientation != np.sign(cross):
                return False
    return True


class PolygonateGA:

    def __init__(self, points: Iterable, pop_size: int = 100, generations: int = 500, mutation_rate: float = 0.1):
        self._points = np.array(points)
        self.pop_size = pop_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.population = self._initialize_population()

    def _initialize_population(self) -> List[List[List[int]]]:

        if len(self._points) < 3:
            raise ValueError("At least 3 points are required to initialize the population.")

        population = []
        indices = list(range(len(self._points)))
        for _ in range(self.pop_size):
            random.shuffle(indices)
            population.append(self._create_random_tessellation(indices))
        return population

    def _create_random_tessellation(self, indices: List[int]) -> List[List[int]]:

        tessellation = []
        while len(indices) > 3:
            size = random.randint(3, min(6, len(indices)))
            polygon = indices[:size]
            if self._is_valid_polygon(polygon):
                tessellation.append(polygon)
                indices = indices[size:]
            else:
                break
        if len(indices) >= 3 and self._is_valid_polygon(indices):
            tessellation.append(indices)
        return tessellation

    def _is_valid_polygon(self, indices: List[int]) -> bool:

        polygon = self._points[indices]
        return is_convex(polygon)

    def _fitness(self, tessellation: List[List[int]]) -> float:

        fitness = 0

        for poly in tessellation:
            polygon = self._points[poly]
            area = 0.5 * abs(np.dot(polygon[:, 0], np.roll(polygon[:, 1], 1)) -
                             np.dot(polygon[:, 1], np.roll(polygon[:, 0], 1)))
            perimeter = np.sum(np.linalg.norm(np.diff(polygon, axis=0, append=polygon[:1]), axis=1))
            if area < 1e-5:
                area = 1e-5
            fitness += perimeter ** 2 / (4 * np.pi * area)
        return fitness

    def _crossover(self, parent1: List[List[int]], parent2: List[List[int]]) -> List[List[int]]:

        split = random.randint(1, len(parent1) - 1) if len(parent1) > 1 else 1
        offspring = parent1[:split] + [poly for poly in parent2 if poly not in parent1[:split]]
        return offspring

    def _mutate(self, tessellation: List[List[int]]) -> List[List[int]]:

        if not tessellation or len(tessellation) < 1:
            return tessellation

        if random.random() < self.mutation_rate:
            idx = random.randint(0, len(tessellation) - 1)
            polygon = tessellation[idx]
            if len(polygon) > 3:
                split_point = random.randint(1, len(polygon) - 2)
                tessellation[idx] = polygon[:split_point]
                tessellation.append(polygon[split_point:])
        return tessellation

    def _select_parents(self, fitness_scores: List[float]) -> Tuple[List[List[int]], List[List[int]]]:

        total_fitness = sum(fitness_scores)
        probabilities = [1 - (score / (total_fitness + 0.001)) for score in fitness_scores]
        probabilities /= np.sum(probabilities)
        idx1, idx2 = np.random.choice(len(self.population), size=2, p=probabilities)
        return self.population[idx1], self.population[idx2]

    def optimize(self) -> List[List[int]]:
        for _ in range(self.generations):
            fitness_scores = [self._fitness(tess) for tess in self.population]
            new_population = []
            for _ in range(self.pop_size // 2):
                parent1, parent2 = self._select_parents(fitness_scores)
                offspring1 = self._mutate(self._crossover(parent1, parent2))
                offspring2 = self._mutate(self._crossover(parent2, parent1))
                new_population.extend([offspring1, offspring2])
            self.population = new_population
        fitness_scores = [self._fitness(tess) for tess in self.population]
        best_tessellation = self.population[np.argmin(fitness_scores)]
        return [list(set(poly)) for poly in best_tessellation if len(set(poly)) > 2]

class PointInputWindow:
    def __init__(self, master):
        self.master = master
        master.title("Point Input")

        self.canvas_width = 400
        self.canvas_height = 300
        self.canvas = Canvas(master, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas.pack()

        self.points = []
        self.point_radius = 3
        self.grid_color = "lightgrey"
        self.grid_spacing = 20

        self.draw_grid()

        self.canvas.bind("<Button-1>", self.add_point)
        self.canvas.bind("<Configure>", self.redraw_grid) 

        self.coordinates_label = tk.Label(master, text="Coordinates:")
        self.coordinates_label.pack()

        self.coordinates_text = tk.Text(master, height=5, width=40)
        self.coordinates_text.pack()

        self.process_button = tk.Button(master, text="Начать обработку", command=self.start_processing)
        self.process_button.pack()

        self.update_coordinates_display()

        self.ga = None

    def draw_grid(self):
        for i in range(0, self.canvas_width, self.grid_spacing):
            self.canvas.create_line(i, 0, i, self.canvas_height, fill=self.grid_color, tag="grid")
        for i in range(0, self.canvas_height, self.grid_spacing):            self.canvas.create_line(0, i, self.canvas_width, i, fill=self.grid_color, tag="grid")

    def redraw_grid(self, event=None):
        self.canvas_width = event.width
        self.canvas_height = event.height
        self.canvas.delete("grid")
        self.draw_grid()
        self.redisplay_points()

    def redisplay_points(self):
        for x, y in self.points:
            self.canvas.create_oval(x - self.point_radius, y - self.point_radius,
                                     x + self.point_radius, y + self.point_radius,
                                     fill="black", outline="black")

    def add_point(self, event):
        x = event.x
        y = event.y
        self.points.append((x, y))
        self.canvas.create_oval(x - self.point_radius, y - self.point_radius,
                                 x + self.point_radius, y + self.point_radius,
                                 fill="black", outline="black")
        self.update_coordinates_display()

    def update_coordinates_display(self):
        self.coordinates_text.delete("1.0", tk.END)
        self.coordinates_text.insert(tk.END, "Coordinates:\n")
        for x, y in self.points:
            self.coordinates_text.insert(tk.END, f"({x}, {y})\n")

    def start_processing(self):

        if not self.points:
            self.coordinates_text.insert(tk.END, "Please add points first.\n")
            return
        self.ga = PolygonateGA(self.points)
        optimized_solution = self.ga.optimize()

        self.coordinates_text.insert(tk.END, "\nOptimized Solution:\n")
        self.coordinates_text.insert(tk.END, str(optimized_solution))


if __name__ == "__main__":
    root = tk.Tk()
    window = PointInputWindow(root)
    root.mainloop()
