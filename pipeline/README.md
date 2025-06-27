# Pipeline de Detección de Fraccionamiento Transaccional

Este pipeline automatiza el proceso de scoring y generación de alertas para identificar usuarios con patrones sospechosos de fraccionamiento en transacciones.

## ¿Qué hace cada script?

- **1_ingest_clean.py**: Toma los datos brutos diarios, los filtra por fecha, elimina duplicados y valores atípicos, y los guarda particionados por año/mes/día en formato Parquet.
- **2_featurize.py**: Calcula métricas clave por usuario y día (frecuencia de transacciones, suma y promedio de montos, concentración de comercios, variabilidad, etc.) y las guarda como features para el modelado.
- **3_train.py**: Entrena un modelo Isolation Forest usando el histórico de features, aprendiendo el comportamiento normal y ajustando el umbral de anomalía. El pipeline completo se guarda para scoring futuro.
- **4_score.py**: Aplica el modelo entrenado a nuevas fechas, calcula el anomaly_score para cada usuario/día y genera flags de alerta. Consolida los resultados y muestra el top de casos más anómalos.
- **run_pipeline.py**: Permite ejecutar todos los pasos anteriores de forma automática sobre un rango de fechas, facilitando la operación batch.

## Métricas y lógica de scoring

- El modelo utiliza métricas como:
  - **cnt_24h**: Número de transacciones en 24h
  - **sum_24h**: Suma total de montos en 24h
  - **avg_amount**: Monto promedio
  - **unique_merchants**: Comercios únicos
- Se calcula un **anomaly_score** para cada usuario/día:
  - Este score es generado por el modelo Isolation Forest, que aprende el comportamiento normal de los usuarios y asigna valores más bajos (negativos) a los casos más anómalos. Un anomaly_score bajo indica mayor sospecha de fraccionamiento.
- Se generan dos flags de alerta:
  - **flag_suspicious**: Es True si el modelo considera al usuario como anómalo según el umbral interno de Isolation Forest (predicción < 0).
  - **flag_suspicious_dynamic**: Es True si el anomaly_score del usuario está por debajo de un umbral dinámico calculado según la proporción de anomalías esperadas (contamination).

## Ejemplo de resultado

🏆 Top 10 estático de usuarios más anómalos:

| user_id                          | date       | cnt_24h | sum_24h | avg_amount | unique_merchants | anomaly_score | flag_suspicious | flag_suspicious_dynamic |
|----------------------------------|------------|---------|---------|------------|------------------|---------------|-----------------|------------------------|
| 7cac676a8d21f4fb7a66d4966dd3a12c | 2021-02-15 |   12    | 3608.3  |   300.69   |        1         |   -0.1027     |      True       |         True           |
| cfa366b65fa843bf78ca52f9524e1244 | 2021-02-11 |   33    | 18361.7 |   556.41   |        1         |   -0.0948     |      True       |         True           |

En este ejemplo, ambos usuarios presentan un número alto de transacciones en un solo día, montos totales elevados y concentración en un solo comercio. El anomaly_score negativo y los flags en True indican que son casos prioritarios para revisión por posible fraccionamiento.

## Análisis de los resultados
- Los usuarios con scores más bajos y ambos flags en True suelen mostrar patrones de actividad inusual: muchas transacciones en poco tiempo, montos altos y poca diversidad de comercios.
- El pipeline permite detectar estos casos automáticamente y priorizarlos para análisis manual, facilitando la gestión de alertas y la toma de decisiones.

## ¿Qué aporta este pipeline?
- Permite identificar automáticamente patrones atípicos de fraccionamiento.
- Facilita la priorización de casos críticos para análisis manual.
- Es flexible y escalable para nuevos datos o reglas.

---

Para ejecutar el scoring sobre un rango de fechas:

```bash
python pipeline/4_score.py --start-date 2021-01-01 --end-date 2021-11-30
```

El resultado consolidado se guarda en `data/alerts/alerts_consolidated.csv`.
