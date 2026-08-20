# Hyperparameter Optimization using Genetic Algorithms & Ensemble Voting

This subproject implements an automated Hyperparameter Optimization pipeline for machine learning models using a custom **Genetic Algorithm (GA)** coupled with **Multiprocessing Parallel Computing** and an **Ensemble Voting Mechanism**.

---

## Technical Overview

The framework optimizes a heterogeneous ensemble composed of three distinct classifiers:
* **K-Nearest Neighbors (K-NN)**
* **Random Forest (RF)**
* **Multi-Layer Perceptron (MLP)**

### Workflow Architecture
1. **Data Preprocessing & Transformation:** Loads tabular data (`StudentPerformanceFactors.csv`), discretizes target performance continuous scores into classification classes, applies one-hot encoding to categorical features, and performs training/testing splits (`80/20`).
2. **Genetic Representation (Chromosome):** Each individual in the population is encoded as a tuple of dictionary hyperparameter spaces for all three algorithms:
   $$\text{Individual} = (\Theta_{\text{KNN}}, \Theta_{\text{RF}}, \Theta_{\text{MLP}})$$
3. **Ensemble Fitness Function:** Fitness is computed by training all three models on the assigned hyperparameters and aggregating their predictions via **Majority Voting**. In cases of tie votes, the `MLP` classifier prediction serves as the ultimate tie-breaker.
4. **Parallel Processing Execution:** Population evaluation per generation is evenly distributed across multiple CPU worker processes using Python's `multiprocess.Process`, `Manager.list()`, and mutual exclusion (`Lock`) to optimize throughput.
5. **Genetic Operators:**
   * **Selection:** Tournament/Elite selection based on top-performing fitness metrics.
   * **Crossover:** Uniform crossover per hyperparameter key across parent pairs.
   * **Mutation:** Random parameter mutation based on defined constraints with probability $P_m = 0.2$.
   * **Elitism:** Preserves the global best chromosome across generations.

---

## File Structure

* `optimizacion.py`: Main script containing the Genetic Algorithm loop, parallel evaluation logic, voting classifier ensemble, and CSV exporter.
* `restricciones.py`: Configuration dictionary defining hyperparameter search boundaries per classifier.
* `StudentPerformanceFactors.csv`: Input dataset for training and validation.

---

## Performance Logging & Output

The pipeline outputs execution metrics per generation directly to the console and exports the final population's full hyperparameter layout alongside achieved accuracy into structured CSV files (`resultados_Genetico_N_hilos.csv`).

## How to Run

Ensure the dependencies (`pandas`, `scikit-learn`, `multiprocess`) are installed and execute:

```bash
python optimizacion.py
