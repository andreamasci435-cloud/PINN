# Risultati computazionali effettivamente ottenuti

Campagna sintetica con perdita localizzata, cinque seed per modello neurale, 1.800 epoche Adam e 150 iterazioni massime L-BFGS. Non sono misure fisiche.

| Metodo | N seed | RMSE test medio (°C) | SD fra seed (°C) |
|---|---:|---:|---:|
| Classical-M0 | 1 | 0.5798 | — |
| PINN-M0 | 5 | 0.9181 | 0.0897 |
| Classical-M1 | 1 | 0.3013 | — |
| PINN-M1 | 5 | 0.7085 | 0.1095 |
| Classical-M2 | 1 | 0.1495 | — |
| PINN-M2 | 5 | 0.7457 | 0.1085 |
| Classical-M3 | 1 | 0.4180 | — |
| PINN-M3 | 5 | 0.9187 | 0.1988 |
| MLP-M0 | 5 | 3.0835 | 0.8489 |

Scelta sulla validation: **Classical-M2**. La scelta è stata salvata prima del calcolo delle metriche test.

## Interpretazione

Il fit classico M2 descrive questa simulazione con errore prossimo al rumore imposto (σ = 0,15 °C). Il modello costante M0 è meno accurato. Tuttavia, con il budget breve utilizzato, la PINN M1 ottiene una RMSE media leggermente inferiore alla PINN M2, pur attribuendo al materiale una variabilità che la verità sintetica assegna alle perdite. Questo benchmark non dimostra che la PINN distingua le due spiegazioni: rende visibile un limite di ottimizzazione/inferenza.

Le baseline classiche battono le PINN in tutti e quattro i modelli di questa campagna. La rete puramente data-driven generalizza peggio. Il confronto PINN/classico riguarda parametri trasferiti al solver FDM; le prestazioni della rete PINN diretta sono diverse e salvate separatamente.

Cinque inizializzazioni quantificano una parte della variabilità numerica, non l’incertezza sperimentale o una probabilità di correttezza del modello. La famiglia sintetica appartiene esattamente ai modelli candidati, e centro/larghezza della perdita sono noti a priori. Una prova fuori famiglia e una nuova campagna fisica sono necessarie.

## Riproduzione

`.venv/bin/python main-2.py run --config configs/comparison.json --output results/comparison-new`

Fonte numerica: `results/comparison/results.json`, `summary.json`, `selection.json`, `metrics.csv`. Le figure aggregate sono `comparison-summary.svg`, `parameter-stability.svg` e `training-diagnostics.png`.

Anche la demo M0 è stata ripetuta tramite il pulsante web. Il bootstrap sintetico con 10 resample di intere prove è salvato in `results/bootstrap-demo.json`: è un controllo funzionale esplorativo, non una stima definitiva di copertura.
