# Dati, calibrazione e metadati

## CSV lungo, una riga per sensore e istante

Colonne obbligatorie:

```csv
run_id,time_s,sensor_id,x_m,temperature_C,ambient_C,heater_state,configuration,notes
```

Unità: m, s, °C. `heater_state` e `notes` sono descrittivi: **non sostituiscono la temperatura al bordo misurata**. `temperature_C` nel CSV raw è la lettura; dopo calibrazione è la lettura corretta. Gli ID di prova sono disgiunti fra train, validation e test. La posizione di ciascun sensore deve essere costante dentro una prova.

Il validatore blocca duplicati, valori non finiti, sensori fuori barra e ID mancanti. Segnala temperature fuori −20…120 °C, gap superiori a 1,5 volte il passo mediano e salti >10 °C/s. Queste sono soglie QC, non un'autorizzazione a eliminare dati. Nessun outlier viene eliminato automaticamente. La saturazione deve essere valutata rispetto alla scheda del sensore e annotata dall'operatore.

Il loader per training richiede una griglia sensore×tempo completa. Dati mancanti richiedono una decisione documentata a monte: niente interpolazione invisibile.

## File di calibrazione

JSON indicizzato per `sensor_id`:

```json
{
  "S1": {"gain": 1.002, "offset_C": -0.12},
  "S2": {"gain": 0.998, "offset_C": 0.08}
}
```

**Numeri puramente illustrativi, da non applicare a sensori reali.** Fornire tutti i sensori effettivi. Formula `T_corretto = gain × T_raw + offset_C`. Stimare gain/offset da riferimenti indipendenti; il programma applica i coefficienti, non sostituisce una procedura di calibrazione.

L'ambiente e il bordo devono essere calibrati a monte con i propri riferimenti, registrati nei metadati. `calibrate` scrive un nuovo CSV e un JSON di hash SHA-256 per raw, calibrazione e output. Non sovrascrive file.

## Metadati della campagna

Esempio strutturale incompleto (non eseguibile prima di inserire le misure):

```json
{
  "provenance": "measured",
  "operator": "NOME DA COMPILARE",
  "date": "DATA DA COMPILARE",
  "material": "MATERIALE MISURATO",
  "geometry": {"length_m": 0.5, "width_m": null, "thickness_m": null},
  "calibration_id": "PERCORSO O HASH",
  "ambient_calibration_id": "PERCORSO O HASH",
  "sensor_position_uncertainty_m": 0.001,
  "temperature_uncertainty_C": 0.15,
  "notes": "COMPILARE anomalie, foto, montaggio e configurazione",
  "split": {"train": ["A01", "A02", "A03"], "validation": ["A04"], "test": ["A05"]},
  "runs": {
    "A01": {
      "amplitude_C": 45,
      "off_s": 190,
      "boundary_time_s": [0, 1, 2],
      "boundary_temperature_C": [20, 20, 20]
    }
  }
}
```

Le incertezze e gli altri numeri sono esempi, non valori misurati. Inserire ogni run presente nello split e l'intera serie del bordo fino alla durata configurata. `amplitude_C` e `off_s` sono descrittori del protocollo per la rete condizionata. La forzante effettiva nel solver e nelle loss BC deriva dalla serie misurata, interpolata linearmente nel tempo. Evitare una frequenza di registrazione del bordo troppo bassa rispetto alla rampa termica.

Limite attuale: due prove con descrittori identici ma storie di bordo diverse non sono rappresentabili univocamente dalla rete condizionata. Il loader richiede descrittori distinti. Non falsificare i metadati per aggirare questo controllo: usare descrittori misurati distinti quando reali oppure estendere l'architettura a campi separati per replica/encoder della forzante.

La geometria del config deve coincidere con quella registrata. Il loader controlla la lunghezza, le incertezze e la copertura temporale. Lo schema completo di massa, sezione, contatto, isolamento e fotografie resta responsabilità del protocollo sperimentale.

## Output reale

`run-measured` produce `measured_results.json`, `selection.json`, config, QC, metadati, loss e checkpoint. Non calcola un errore contro un inesistente campo vero. RMSE e MAE usano solo le misure tenute fuori. La dashboard sintetica non carica questi risultati automaticamente e non li confonde con una ground truth numerica.
