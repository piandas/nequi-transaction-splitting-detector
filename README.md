# Detección de Fraccionamiento Transaccional – Prueba Técnica NEQUI

## Propósito

Este proyecto aborda la detección de **Mala Práctica Transaccional** enfocada en el **Fraccionamiento Transaccional**: identificar usuarios que dividen grandes montos en múltiples transacciones pequeñas en una ventana de 24h, usando datos reales y sintéticos proporcionados.

---

## 1. Alcance y Objetivo

- **Objetivo:** Desarrollar un producto de datos capaz de identificar patrones de fraccionamiento transaccional, documentar el proceso y detallar cómo incorporar la solución en un marco operativo.
- **Enfoque:** Se implementaron dos enfoques/modelos:
  - **Modelo 1:** Basado en análisis descriptivo y reglas heurísticas.
  - **Modelo 2:** Pipeline automatizado con machine learning (Isolation Forest) y scoring.

---

## 2. Exploración y Evaluación de los Datos (EDA)

- Se analizaron más de 21 millones de transacciones, identificando:
  - Outliers en número y monto de transacciones por usuario/día.
  - Patrones de ráfagas (intervalos cortos), concentración de comercios y repetición de montos.
- Se validó la hipótesis: los usuarios que fraccionan presentan alta frecuencia, baja variabilidad y concentración en pocos comercios.
- Se generaron features clave: `cnt_24h`, `sum_24h`, `avg_amount`, `unique_merchants`, `same_amount_ratio`, `merchant_concentration`, `avg_interval_minutes`.

---

## 3. Modelos Analíticos

### Modelo 1: Descriptivo y Heurístico

- Basado en reglas y umbrales derivados del EDA.
- Permite identificar casos críticos y patrones atípicos de forma interpretable.
- Hallazgos:
  - Solo el 0.003% de usuarios presentaron scores críticos.
  - Se detectaron patrones de automatización y evasión.

### Modelo 2: Pipeline Automatizado (Isolation Forest)

- **Flujo:**
  1. **Ingesta y limpieza:** Filtrado y particionado de datos diarios.
  2. **Featurización:** Cálculo de métricas clave por usuario/día.
  3. **Entrenamiento:** Isolation Forest aprende el comportamiento normal.
  4. **Scoring:** Se calcula un `anomaly_score` y flags de alerta para cada usuario/día.
  5. **Consolidación:** Se genera un ranking de los casos más anómalos.
- **Métricas principales:**  
  - Algoritmo: Suspicion Score (Isolation Forest)
  - Umbral: 3σ (99.85% especificidad)
  - Features: frecuencia, montos, concentración, intervalos, etc.
- **Hallazgos:**  
  - Los usuarios más anómalos presentan alta frecuencia, montos elevados y baja diversidad de comercios.
  - El pipeline permite priorizar casos críticos para revisión manual.

---

## 4. Uso del Pipeline con Docker

### Requisitos

- Tener Docker instalado.

### Ejecución rápida

1. **Construir la imagen (solo una vez):**
   ```bash
   docker build -t nequi-pipeline .
   ```

2. **Ejecutar el scoring (creando la carpeta de alertas si es necesario):**
   ```bash
   docker run --rm --entrypoint /bin/sh nequi-pipeline -c "mkdir -p data/alerts && python pipeline/4_score.py --start-date 2021-01-01 --end-date 2021-01-10"
   ```

3. **(Opcional) Guardar los resultados fuera del contenedor:**
   ```bash
   docker run --rm -v $(pwd)/outputs:/app/data/alerts --entrypoint /bin/sh nequi-pipeline -c "mkdir -p data/alerts && python pipeline/4_score.py --start-date 2021-01-01 --end-date 2021-01-10"
   ```

---

## 5. Frecuencia de actualización y despliegue

- **Frecuencia recomendada:** Ejecución diaria (batch) para detectar patrones recientes y adaptarse a cambios de comportamiento.
- **Despliegue:** El pipeline es portable vía Docker, lo que facilita su integración en cualquier entorno operativo.

---

## 6. Resumen de pasos y entregables

1. **Exploración y limpieza de datos:** Análisis de calidad, outliers y patrones.
2. **Generación de features:** Métricas clave para modelado.
3. **Modelado y scoring:** Dos enfoques, uno heurístico y otro automatizado.
4. **Documentación y hallazgos:** Explicación detallada de cada etapa y resultados.
5. **Producto de datos listo para producción:** Pipeline reproducible y portable con Docker.

---

## 7. Repositorio y ejecución

- El repositorio contiene scripts, modelo entrenado y features de ejemplo (enero).
- Solo se suben los features de enero como muestra, para facilitar pruebas y mostrar el formato esperado. Los features completos no se incluyen para evitar archivos pesados y porque pueden regenerse fácilmente.
- El pipeline está preparado para generar todos los features a partir de los datos brutos, siguiendo los scripts de limpieza y featurización.
- El archivo de la imagen Docker (`nequi-pipeline.tar`) no fue subido a GitHub por su tamaño. Puedes descargarlo desde: [Google Drive](https://drive.google.com/file/d/1vZWITMKi3HA3VHiy51JO7CooLOWabibP/view?usp=sharing)
- Para probar el pipeline, solo necesitas Docker y seguir las instrucciones de la sección 4.

---

## 8. Consideraciones finales

- La solución es flexible, escalable y fácilmente interpretable.
- Permite priorizar casos críticos y automatizar la detección de fraccionamiento.
- Se documenta cada etapa y se entregan hallazgos claros, alineados con los objetivos de la prueba.

---

## 9. Respuestas a los puntos clave de la prueba

### 1. Flujo de datos y criterio de selección del modelo final

- **Flujo de datos:**
  1. **Ingesta:** Se reciben los datos brutos diarios, se filtran por fecha y se limpian (eliminación de duplicados, valores atípicos y validación de estructura).
  2. **Featurización:** Se generan métricas clave por usuario y día, como frecuencia, suma de montos, concentración de comercios, variabilidad y patrones de intervalos.
  3. **Entrenamiento:** Se utiliza Isolation Forest para aprender el comportamiento normal de los usuarios a partir del histórico de features.
  4. **Scoring:** El modelo calcula un anomaly_score y flags de alerta para cada usuario/día, priorizando los casos más anómalos.
  5. **Consolidación y alertas:** Se genera un ranking de los usuarios más sospechosos y se consolidan los resultados para revisión manual o integración con sistemas de monitoreo.
- **Criterio de selección:**
  - Se eligió Isolation Forest por su capacidad para detectar outliers en conjuntos de datos no etiquetados, su robustez ante ruido y su fácil integración en pipelines productivos. Además, permite ajustar el umbral de alerta y es interpretable para equipos de negocio.
  - El modelo heurístico se mantuvo como referencia y validación cruzada, pero el pipeline automatizado es más escalable y reproducible.

### 2. Frecuencia de actualización de los datos

- **Recomendación:** Actualización y scoring diario.
- **Justificación:**
  - El fraccionamiento puede ocurrir en cualquier momento y es importante detectar patrones recientes para una respuesta oportuna.
  - La actualización diaria permite recalibrar el modelo con nuevos datos, adaptarse a cambios de comportamiento y reducir falsos positivos.
  - En escenarios de alto riesgo, se podría aumentar la frecuencia a varias veces al día (batch o streaming), pero el análisis muestra que la ventana de 24h es suficiente para la mayoría de los casos.
- **Reentrenamiento del modelo:**
  - Se recomienda reentrenar el modelo Isolation Forest al menos una vez al mes, o ante cambios significativos en los patrones de datos, para asegurar que el modelo se mantenga actualizado y relevante frente a nuevas tendencias de comportamiento.

### 3. Arquitectura ideal y recursos necesarios (Opcional)

- **Arquitectura propuesta:**
  - **Ingesta:** Proceso ETL diario que extrae los datos transaccionales y los almacena en un data lake o base de datos particionada por fecha.
  - **Procesamiento:** Un pipeline orquestado (por ejemplo, con Airflow, Prefect o similar) que ejecuta los scripts de limpieza, featurización y scoring.
  - **Modelo:** El modelo Isolation Forest se entrena periódicamente y se versiona para trazabilidad.
  - **Despliegue:** El pipeline se empaqueta en un contenedor Docker, facilitando su despliegue en cualquier entorno (on-premise, nube, etc.).
  - **Almacenamiento de resultados:** Las alertas y scores se almacenan en una base de datos o sistema de reportes para revisión y acción.
  - **Recursos:**
    - CPU y RAM moderados (el pipeline es eficiente y puede correr en servidores estándar).
    - Almacenamiento para features históricos y resultados.
    - Opcional: integración con sistemas de monitoreo y dashboards para visualización de alertas.

---
