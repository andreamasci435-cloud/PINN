# Allineamento alla proposta PINN-CANON

| Richiesta del PDF | Implementazione / stato |
|---|---|
| Conduzione transitoria 1D con dispersione | `physics.py`, `fdm.py`, unità e ipotesi in METHODS |
| PINN forward di partenza | Base tanh/autograd conservata; originale in `legacy/` |
| Stima inversa α, β positivi | `pinn.py`, softplus, M0–M3 |
| α(x), β(x), α(T) | Parametrizzazioni a pochi coefficienti; β locale ha centro/larghezza noti |
| M4 congiunto | Non implementato: opzionale nel PDF, richiede prima identificabilità dei casi semplici |
| PDE + dati + IC + BC + regolarizzazione | Termini separati e pesi configurabili; ablation disponibili |
| 5.000–20.000 collocation, 4–5 layer 64 | Preset research: 5.000/4×64. Demo/confronto breve: 512/4×48, dichiarato |
| Adam + L-BFGS | Implementati; loss e checkpoint salvati |
| ≥5 seed | Preset confronto e research; demo rapida 1 seed |
| Soluzione analitica e convergenza | Test del decadimento di modi sinusoidali e raffinamento spaziale/temporale |
| Fit classico e MLP | Entrambi eseguiti sugli stessi split |
| Test indipendente | Intere prove, nuova forzante; selezione congelata su validation |
| Metriche, residuo, costi | JSON, CSV, figure e tempi; campo neurale diretto separato da PINN→FDM |
| Incertezza | Dispersione tra seed e copertura sintetica; bootstrap per intere prove. Non calibrata metrologicamente |
| Identificabilità | Diagnostica locale del Jacobiano; non prova di identificabilità globale |
| Sensibilità e ablation | 19 configurazioni predisposte. Esecuzione estesa non implicita |
| Rumore e numero sensori | Configurabili e inclusi nel piano |
| Incertezza posizione / bordo | Registrata nei metadati; propagazione automatica ancora da aggiungere |
| Calibrazione e dati raw immutabili | CLI di calibrazione con hash; nessuna sovrascrittura; QC timestamp/duplicati/salti |
| Dati reali con metadati | Loader e benchmark CLI, testati con fixture sintetiche; nessuna misura reale fornita |
| Ambiente variabile | Rifiutato esplicitamente oltre tolleranza 0,1 °C |
| Bordo con flusso ignoto / convezione destra | Non implementati; attualmente Dirichlet sinistro misurato e Neumann destro nullo |
| Apparato e repliche fisiche | Protocollo fornito; costruzione, calibrazione e acquisizione da eseguire |
| Interfaccia web 3D | WebGL locale, controlli fisici, timeline, sensori, profili, confronto e download |
| Pacchetto riproducibile | Requirements bloccati, configurazioni, hash, test, CLI e README |
| Paper finale | Metodo documentato; nessun paper con risultati fisici inventati |
| Freccia del tempo / 2D / Bayesian PINN | Estensioni non implementate |

La distinzione fra «implementato», «testato su sintetico» e «validato fisicamente» deve rimanere presente nel portfolio e nell'eventuale articolo.
