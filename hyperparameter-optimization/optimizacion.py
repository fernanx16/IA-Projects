import random
import time
import os
import csv
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score
from collections import Counter
import multiprocess
from restricciones import hiperparametros

random.seed(0)

# ==============================================
# ================ UTILIDADES ==================
# ==============================================

def nivelacion_cargas(D, n_p):
    """
    Reparte la lista D en n_p subconjuntos lo más equitativos posible.
    """
    s = len(D) % n_p
    n_D = D[:s]
    t = int((len(D) - s) / n_p)
    out = []
    temp = []
    for i in D[s:]:
        temp.append(i)
        if len(temp) == t:
            out.append(temp)
            temp = []
    for i in range(len(n_D)):
        out[i].append(n_D[i])
    return out

def cargar_y_preprocesar_datos(filepath):
    """
    Carga el CSV y realiza un preprocesado sencillo.
    """
    df = pd.read_csv(filepath)
    df['rounded_score'] = (df['Exam_Score'] / 10).round(0) * 10
    df['class'] = df['rounded_score'].astype(int)

    # One-hot encoding de variables categóricas
    categorical_columns = df.select_dtypes(include=['object']).columns.tolist()
    df = pd.get_dummies(df, columns=categorical_columns, drop_first=True)

    X = df.drop(['Exam_Score', 'rounded_score', 'class'], axis=1)
    y = df['class']
    return X, y

def dividir_datos(X, y, test_size=0.2, random_state=0):
    """
    Separa el dataset en train y test.
    """
    return train_test_split(X, y, test_size=test_size, random_state=random_state)

def evaluar_combinacion(combinacion, X_train, X_test, y_train, y_test):
    """
    Entrena KNN, RF y MLP con hiperparámetros dados. 
    Hace votación de mayorías y retorna (combinacion, accuracy).
    """
    params_knn, params_rf, params_mlp = combinacion

    modelos = {
        'K-NN': KNeighborsClassifier(**params_knn),
        'Random Forest': RandomForestClassifier(random_state=0, **params_rf),
        'MLP': MLPClassifier(random_state=0, **params_mlp),
    }
    
    predicciones = {}
    for modelo, clf in modelos.items():
        clf.fit(X_train, y_train)
        predicciones[modelo] = clf.predict(X_test)
    
    # Votación
    predicciones_ensamble = []
    for i in range(len(y_test)):
        votos = [predicciones['K-NN'][i], 
                 predicciones['Random Forest'][i], 
                 predicciones['MLP'][i]]
        conteo = Counter(votos)
        max_votos = max(conteo.values())
        clases_empate = [clase for clase, cuenta in conteo.items() if cuenta == max_votos]
        # Si hay empate, usar la predicción de MLP como desempate
        prediccion_final = int(clases_empate[0] if len(clases_empate) == 1 
                               else predicciones['MLP'][i])
        predicciones_ensamble.append(prediccion_final)
    
    accuracy_ensamble = accuracy_score(y_test, predicciones_ensamble)
    return combinacion, accuracy_ensamble

def evaluate_set(combinations, X_train, X_test, y_train, y_test, return_dict, lock):
    """
    Evalúa un subconjunto de combinaciones (individuos) en paralelo.
    """
    local_results = []
    for combinacion in combinations:
        resultado = evaluar_combinacion(combinacion, X_train, X_test, y_train, y_test)
        local_results.append(resultado)

    # Guardar resultados en el diccionario compartido
    with lock:
        return_dict.extend(local_results)

def guardar_resultados_csv(resultados, archivo_salida="resultados.csv"):
    """
    Guarda los resultados en un CSV, manteniendo el formato:
    [param_knn..., param_rf..., param_mlp..., accuracy]
    """
    if not resultados:
        print("No hay resultados para guardar.")
        return
    
    # Tomar nombres de hiperparámetros de la primera combinación
    columnas_hiperparam_knn   = list(resultados[0][0][0].keys())
    columnas_hiperparam_rf    = list(resultados[0][0][1].keys())
    columnas_hiperparam_mlp   = list(resultados[0][0][2].keys())
    columnas_hiperparametros  = columnas_hiperparam_knn + columnas_hiperparam_rf + columnas_hiperparam_mlp

    resultados_guardar = []
    for combinacion, accuracy in resultados:
        # combinacion = (dict_knn, dict_rf, dict_mlp)
        hiper_k   = list(combinacion[0].values())
        hiper_rf  = list(combinacion[1].values())
        hiper_mlp = list(combinacion[2].values())
        
        resultados_guardar.append(hiper_k + hiper_rf + hiper_mlp + [accuracy])
    
    with open(archivo_salida, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(columnas_hiperparametros + ['accuracy'])  # Encabezados
        writer.writerows(resultados_guardar)  # Datos
    
    print(f"Resultados guardados en {archivo_salida}")

# ==============================================
# =========== ALGORITMO GENÉTICO ==============
# ==============================================

def generar_individuo():
    """
    Genera un individuo aleatorio (combinación de hiperparámetros) 
    basado en las listas definidas en 'hiperparametros'.
    Salida: (params_knn, params_rf, params_mlp)
    """
    # Para cada hiperparámetro, elegir un valor al azar de la lista en hiperparametros
    knn_params = {}
    for k, v in hiperparametros['K-NN'].items():
        knn_params[k] = random.choice(v)
    
    rf_params = {}
    for k, v in hiperparametros['Random Forest'].items():
        rf_params[k] = random.choice(v)
    
    mlp_params = {}
    for k, v in hiperparametros['MLP'].items():
        mlp_params[k] = random.choice(v)
    
    return (knn_params, rf_params, mlp_params)

def generar_poblacion(tamano_poblacion):
    """
    Genera una lista con 'tamano_poblacion' individuos.
    """
    return [generar_individuo() for _ in range(tamano_poblacion)]

def seleccion(poblacion, fitness, num_seleccionados=10):
    """
    Selección proporcional o por torneo. 
    Aquí, por simplicidad, se usará selección por torneo:
    - Se eligen aleatoriamente 'num_seleccionados' individuos 
      y nos quedamos con el top 2 (por ejemplo) para cruzar.
    """
    # Ordenamos la población por fitness (mayor es mejor).
    # fitness[i] corresponde a la precisión del individuo poblacion[i].
    indices_ordenados = sorted(range(len(poblacion)), key=lambda i: fitness[i], reverse=True)
    
    # Podemos quedarnos con la parte superior de la población.
    # Ej. si num_seleccionados=10, tomamos los 10 mejores
    mejores_indices = indices_ordenados[:num_seleccionados]
    
    # Retornamos la subpoblación y sus fitness
    nueva_poblacion = [poblacion[i] for i in mejores_indices]
    nueva_fitness   = [fitness[i]    for i in mejores_indices]
    return nueva_poblacion, nueva_fitness

def crossover(ind1, ind2):
    """
    Cruzamiento uniforme por hiperparámetro.
    indX = (dict_knn, dict_rf, dict_mlp)
    """
    knn1, rf1, mlp1 = ind1
    knn2, rf2, mlp2 = ind2

    hijo1_knn = {}
    hijo2_knn = {}
    for k in knn1.keys():
        if random.random() < 0.5:
            hijo1_knn[k] = knn1[k]
            hijo2_knn[k] = knn2[k]
        else:
            hijo1_knn[k] = knn2[k]
            hijo2_knn[k] = knn1[k]
            
    hijo1_rf = {}
    hijo2_rf = {}
    for k in rf1.keys():
        if random.random() < 0.5:
            hijo1_rf[k] = rf1[k]
            hijo2_rf[k] = rf2[k]
        else:
            hijo1_rf[k] = rf2[k]
            hijo2_rf[k] = rf1[k]
    
    hijo1_mlp = {}
    hijo2_mlp = {}
    for k in mlp1.keys():
        if random.random() < 0.5:
            hijo1_mlp[k] = mlp1[k]
            hijo2_mlp[k] = mlp2[k]
        else:
            hijo1_mlp[k] = mlp2[k]
            hijo2_mlp[k] = mlp1[k]
    
    return (hijo1_knn, hijo1_rf, hijo1_mlp), (hijo2_knn, hijo2_rf, hijo2_mlp)

def mutacion(individuo, prob_mut=0.1):
    """
    Muta un individuo con probabilidad prob_mut en cada hiperparámetro.
    """
    knn_params, rf_params, mlp_params = individuo
    
    # Mutación en KNN
    for k in knn_params.keys():
        if random.random() < prob_mut:
            # Elegimos un nuevo valor para k entre la lista de hiperparametros
            knn_params[k] = random.choice(hiperparametros['K-NN'][k])
    
    # Mutación en RF
    for k in rf_params.keys():
        if random.random() < prob_mut:
            rf_params[k] = random.choice(hiperparametros['Random Forest'][k])
    
    # Mutación en MLP
    for k in mlp_params.keys():
        if random.random() < prob_mut:
            mlp_params[k] = random.choice(hiperparametros['MLP'][k])
    
    return (knn_params, rf_params, mlp_params)

# ==============================================
# =========== MAIN: ALGORITMO GENÉTICO ========
# ==============================================

def main_genetico(num_procesos=2, tamano_poblacion=10, num_generaciones=5):
    """
    Algoritmo Genético para optimizar hiperparámetros.
    Se conserva el cómputo paralelo y el mismo formato de salida.
    """

    # 1. Cargar datos
    X, y = cargar_y_preprocesar_datos('StudentPerformanceFactors.csv')
    X_train, X_test, y_train, y_test = dividir_datos(X, y)
    
    start_time = time.time()
    
    # 2. Generar población inicial
    poblacion = generar_poblacion(tamano_poblacion)
    
    # Para ir almacenando los mejores resultados finales
    mejor_global = None
    mejor_acc_global = -1.0
    
    for gen in range(num_generaciones):
        print(f"\n=== GENERACIÓN {gen+1}/{num_generaciones} ===")
        
        # 3. Evaluar toda la población en paralelo
        #    Dividimos 'poblacion' en subconjuntos
        cargas = nivelacion_cargas(poblacion, num_procesos)
        
        manager = multiprocess.Manager()
        return_dict = manager.list()
        lock = manager.Lock()
        procesos = []

        t0 = time.time()
        for i in range(num_procesos):
            p = multiprocess.Process(target=evaluate_set,
                                     args=(cargas[i], X_train, X_test, y_train, y_test, return_dict, lock))
            procesos.append(p)
            p.start()
        
        for p in procesos:
            p.join()
        tiempo_evaluacion = time.time() - t0
        
        # Convertir resultados a lista
        resultados = list(return_dict)
        # resultados es una lista de ((params_knn, params_rf, params_mlp), accuracy)
        
        # 4. Extraer fitness (accuracy) para cada individuo en la población
        accuracies = [res[1] for res in resultados]
        
        # Guardar el mejor de esta generación
        max_acc = max(accuracies)
        idx_max = accuracies.index(max_acc)
        mejor_gen = resultados[idx_max][0]  # combinacion de hiperparametros
        print(f"Mejor individuo de la generación {gen+1} -> accuracy: {max_acc:.4f}")

        # Actualizar mejor global
        if max_acc > mejor_acc_global:
            mejor_acc_global = max_acc
            mejor_global = mejor_gen
        
        # 5. SELECCIÓN: tomamos los mejores N (ej. 10) individuos de la población
        #    la cantidad la decides según tu criterio (aquí 10)
        num_elite = min(5, len(poblacion))
        poblacion_ordenada, accuracies_ordenadas = seleccion(poblacion, accuracies, num_elite)
        
        # 6. CRUCE: generamos nuevos hijos a partir de los mejores
        nueva_poblacion = []
        # Cruzamos por parejas (tomamos la mitad superior para formar padres)
        while len(nueva_poblacion) < tamano_poblacion:
            # Seleccionar dos padres al azar dentro de la élite
            p1 = random.choice(poblacion_ordenada)
            p2 = random.choice(poblacion_ordenada)
            hijo1, hijo2 = crossover(p1, p2)
            
            # 7. MUTACIÓN
            hijo1 = mutacion(hijo1, prob_mut=0.2)
            hijo2 = mutacion(hijo2, prob_mut=0.2)
            
            nueva_poblacion.append(hijo1)
            if len(nueva_poblacion) < tamano_poblacion - 1:
                nueva_poblacion.append(hijo2)
        
        # Remplazamos la población vieja por la nueva
        nueva_poblacion.append(mejor_global)
        poblacion = nueva_poblacion
    
    tiempo_total = time.time() - start_time
    print(f'El tiempo total para {num_procesos} hilos fue: {tiempo_total}')
    
    print("\n=== RESULTADOS FINALES ===")
    print(f"Mejor individuo global: {mejor_global}")
    print(f"Mejor accuracy global: {mejor_acc_global:.4f}")
    
    # OPCIONAL: Evaluamos toda la población final y guardamos en CSV
    # (Podríamos guardar la población de la última generación)
    cargas_final = nivelacion_cargas(poblacion, num_procesos)
    manager = multiprocess.Manager()
    return_dict = manager.list()
    lock = manager.Lock()
    procesos = []

    for i in range(num_procesos):
        p = multiprocess.Process(target=evaluate_set,
                                 args=(cargas_final[i], X_train, X_test, y_train, y_test, return_dict, lock))
        procesos.append(p)
        p.start()
    for p in procesos:
        p.join()
    
    resultados_finales = list(return_dict)
    
    # Guardamos con el mismo formato
    guardar_resultados_csv(resultados_finales, 
                           archivo_salida=f"resultados_Genetico_{num_procesos}_hilos.csv")

    return mejor_global, mejor_acc_global

if __name__ == "__main__":
    # Ajusta estos parámetros a tu gusto
    mejor_individuo, mejor_acc = main_genetico(
        num_procesos=4,
        tamano_poblacion=20,
        num_generaciones=10
    )
