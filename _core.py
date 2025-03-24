import numpy as np
from scipy.spatial import Delaunay
from typing import Iterable, List, Tuple, Dict
import random

points = []


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
        # Ensure valid tessellation for the final generation
        fitness_scores = [self._fitness(tess) for tess in self.population]
        best_tessellation = self.population[np.argmin(fitness_scores)]
        return [list(set(poly)) for poly in best_tessellation if len(set(poly)) > 2]


if __name__ == "__main__":
    num_points = int(input("Enter the number of points: "))
    points = []
    for i in range(num_points):
        x, y = map(float, input(f"Enter the coordinates for point {i + 1} (format: x y): ").split())
        points.append((x, y))

    ga = PolygonateGA(points)
    optimized_solution = ga.optimize()

    print("Optimized Tessellation:")
    for polygon in optimized_solution:
        print([points[index] for index in polygon])
