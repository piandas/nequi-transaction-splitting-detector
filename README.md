# Nequi – Detección de Fraccionamiento Transaccional

## Paso 1: Alcance y Planteamiento del Problema

### 1. Descripción del problema
El **fraccionamiento transaccional** consiste en dividir una transacción de alto valor en varias de menor monto que, sumadas, igualan o superan ligeramente el valor original. Esta técnica suele usarse para evadir controles antifraude o límites regulatorios, por lo que necesitamos detectarla de forma automática y diaria sobre el histórico de operaciones.

### 2. Objetivo
Construir un **producto de datos** que, al ejecutarse, analice las transacciones de las últimas 24 horas y asigne a cada cuenta un **Suspicion Score** basado en desviaciones respecto a su comportamiento “normal” y a patrones complementarios (comercio, sucursal, perfil de usuario, temporalidad). Con un único umbral (p. ej. Score ≥ 3σ) se generará una alerta para investigación.

---

## 3. Variables originales y su uso

| Columna              | Descripción                                                                                                                                             |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| `_id`                | Identificador único de registro. Se usa para trazar cada transacción en el dataset y evitar duplicados.                                                |
| `merchant_id`        | Código único del comercio o aliado. Permite derivar cuántos comercios distintos participan en la ventana y si el fraccionamiento ocurre siempre en uno solo. |
| `subsidiary`         | Código de la sucursal o “punto físico”. Ayuda a medir dispersión geográfica del fraccionamiento.                                                         |
| `transaction_date`   | Fecha y hora de la transacción en el Core financiero. Base para construir la ventana de 24 h y extraer información horaria y de intervalos.             |
| `account_number`     | Número único de cuenta de origen. Núcleo del análisis: agrupamos transacciones por cuenta.                                                              |
| `user_id`            | Identificador del usuario dueño de la cuenta. Permite perfilar comportamiento agregado de todas sus cuentas.                                             |
| `transaction_amount` | Monto de la transacción (moneda local ficticia). Base para sumar montos en cada ventana y calcular z-scores de volumen.                                  |
| `transaction_type`   | Naturaleza de la transacción (“debit” o “credit”). Nos centramos en débito para fraccionamiento, pero rastreamos ratio débito/crédito.                    |

---

## 4. Features derivadas y su rol

| Feature                           | Definición                                                                                                                                             | Objetivo                                                                                                                                          |
|-----------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| **cnt_24h**                       | Conteo de transacciones **débito** en las últimas 24 h.                                                                                                 | Captar picos de frecuencia.                                                                                                                       |
| **sum_24h**                       | Suma de montos **débito** en las últimas 24 h.                                                                                                         | Medir el volumen total fragmentado.                                                                                                               |
| **cnt_merchants_24h**             | Número de `merchant_id` distintos en la ventana de 24 h.                                                                                                | Distinguir si el fraccionamiento se concentra en un solo comercio o se dispersa en varios.                                                       |
| **top_merchant_freq**             | Frecuencia (conteo) de transacciones en el `merchant_id` más repetido.                                                                                 | Detectar patrones de “mismo POS” o comercio favorito.                                                                                              |
| **cnt_subsidiaries_24h**          | Número de `subsidiary` distintos en 24 h.                                                                                                               | Ver si las transacciones se reparten en varias sucursales para evadir límites locales.                                                            |
| **ratio_same_sub**                | `cnt` en la sucursal más usada / `cnt_24h`.                                                                                                             | Medir concentración geográfica.                                                                                                                    |
| **avg_cnt_24h_user**, **avg_sum_24h_user** | Media histórica (últimos 90 d) de `cnt_24h` y `sum_24h` para ese `user_id`.                                                                   | Contextualizar la anomalía respecto al perfil global del usuario (puede tener varias cuentas).                                                    |
| **z_cnt_user**, **z_sum_user**    | Z-scores a nivel usuario: desviación de la ventana actual frente a su propia media y σ (últimos 90 d).                                                  | Ajustar el score para usuarios muy activos o muy inactivos.                                                                                        |
| **pct_debit**, **pct_credit**     | Porcentaje de débito vs. crédito en la ventana de 24 h.                                                                                                 | Distinguir fraccionamiento puro de débitos frente a operaciones mixtas o reembolsos.                                                             |
| **hour_of_day**, **day_of_week**  | Hora (0–23) y día de la semana (L–D) de cada transacción o de su ventana promedio.                                                                     | Captar patrones horarios o de fin de semana que sugieran scripts automáticos o comportamientos atípicos.                                          |
| **tiempo_entre_tx**               | Media y desviación de los intervalos (en minutos) entre transacciones sucesivas en la ventana.                                                           | Detectar “ráfagas” de transacciones muy juntas, indicativo de automatización.                                                                     |

---

## 5. Estadística global y cálculo de z-scores

1. **Histórico de referencia**  
   Reunir *todas* las ventanas de 24 h de los últimos **90 días**, para cada cuenta y usuario.

2. **Media (μ) y desviación estándar (σ)**  
   Para cada métrica (cnt_24h, sum_24h, cnt_merchants_24h, …, tiempo_entre_tx) calculamos:  
   ```
   μ_x = promedio histórico de x
   σ_x = desviación estándar histórica de x
   ```

3. **Z-score**  
   Para cada métrica x en la ventana actual:
   ```
   z_x = (x_observado – μ_x) / σ_x
   ```
   Indica “cuántas desviaciones estándar” estás por encima (o por debajo, si es negativo) de la media.

---

## 6. Suspicion Score y umbral de alerta

- **Fórmula**  
  ```  
  Suspicion_Score = Σ_i ( w_i · z_i )
  ```  
  donde cada z_i es el z-score de una feature derivada, y w_i su peso (inicialmente todos = 1).

- **Umbral**  
  - Se fija **Score ≥ 3** (equivale a “3σ”): solo ~0.15 % de los casos superaría esto en una distribución normal.
  - Fácil de justificar ante auditoría (“3 desviaciones estándar” es estándar en detección de anomalías).

- **Salida final**  
  Cada ejecucion genera una tabla:

  | Columna             | Descripción                                                           |
  |---------------------|-----------------------------------------------------------------------|
  | `account_number`    | Cuenta analizada                                                     |
  | `window_start`      | Inicio de la ventana 24 h                                            |
  | `window_end`        | Fin de la ventana 24 h                                               |
  | Todas las features  | cnt_24h, sum_24h, cnt_merchants_24h, …                                 |
  | Todos los z_scores  | z_cnt, z_sum, z_merchants, …                                          |
  | `Suspicion_Score`   | Suma ponderada de z_scores                                           |
  | `flag_suspicious`   | Booleano: `true` si `Suspicion_Score ≥ 3`                             |

---

## 7. Frecuencia y modo de operación

- **Ejecución batch diaria** a las **02:00 AM** (America/Bogotá).  
- **Rolling window** de **90 días** para recalcular μ y σ y adaptarse a cambios de actividad.  
- Todo el proceso se implementa en **Python/Pandas** (o Spark si el volumen lo exige), rastreado con **MLflow local** y empaquetado en **Docker** para reproducibilidad completa.
