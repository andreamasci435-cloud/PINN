# Protocollo fisico da eseguire

Questo documento è una procedura proposta, non una registrazione di esperimenti già svolti.

1. **Definire l'apparato.** Barra di circa 0,50 m con sezione costante; misurare lunghezza, larghezza, spessore, massa e posizioni dei sensori con incertezza. Fotografare montaggio, supporti, isolamento e contatto dei sensori. La sezione deve essere sufficientemente sottile da rendere plausibile la temperatura trasversalmente uniforme; verificare Biot con proprietà e geometria effettive.
2. **Preparare la misura.** Otto sensori lungo la barra, un sensore ambiente lontano dal riscaldatore e un sensore di temperatura al bordo riscaldato. Calibrare ogni canale in almeno due condizioni stabili, con riferimento e incertezze documentati. Registrare ritardo e qualità del contatto. Il codice accetta coefficienti, non certifica la calibrazione.
3. **Impostare la sicurezza del banco.** Alimentatore isolato a bassa tensione, protezione e soglia di spegnimento hardware, protezione dalle superfici calde, supporti non infiammabili e verifica dei collegamenti da parte di un docente competente. Non usare la dashboard come controllo di sicurezza: non comanda l'hardware.
4. **Registrare una prova pilota.** Partire dalla barra in equilibrio con l'ambiente. Acquisire timestamp sincronizzati, stato del riscaldatore e temperatura al bordo durante riscaldamento e raffreddamento. Scegliere frequenza e durata rispetto alla dinamica osservata, non copiando automaticamente 400 s o 5 s del sintetico.
5. **Separare le prove prima del fit.** Almeno cinque repliche uniformi e almeno tre per ogni perturbazione. Dedicare prove distinte alla scelta del modello e al test finale. Una replica test non deve entrare nel tuning, neanche attraverso una scelta manuale dei pesi dopo aver visto i suoi errori.
6. **Perturbare una causa alla volta.** A: uniforme e isolata. B: regione di perdita nota e fotografata. C: ampiezza di riscaldamento differente per mettere alla prova α(T). Mantenere documentate geometria, supporti e contatti. Non attribuire automaticamente un α(x) appreso a un materiale non uniforme.
7. **Tracciare i dati.** Conservare raw originali, calibrazioni, metadati, fotografie, log degli eventi, motivazioni di esclusione e output processati. Nessuna prova fallita deve sparire. Il validatore segnala problemi; l'operatore decide con regole predefinite.
8. **Confrontare.** Fit classico, MLP, PINN; poi seed multipli, ablation e sensibilità. Valutare residui per posizione e fase del ciclo. Verificare che la conclusione resista a ipotesi alternative sul bordo e sul ritardo dei sensori.
9. **Confermare.** Quando la scelta del modello è fissata, usare una nuova prova finale mai consultata. Quantificare l'incertezza sperimentale; l'ensemble di seed non la sostituisce. Se il risultato non distingue le ipotesi, riportare la non identificabilità.
10. **Preparare la comunicazione.** Scrivere prima metodo e limiti, poi risultati effettivi. Lo studente deve saper derivare il residuo, spiegare lo split, difendere le baseline e riconoscere un fallimento. Annotare il contributo dell'assistenza AI e le decisioni personali nel diario.

## Diario minimo

Per ogni sessione: data, obiettivo, decisioni prese prima di osservare i risultati, file/config/hash, operatore, guasti, controlli, risultato, interpretazioni alternative e prossimo esperimento. Non confondere performance software, inferenza fisica e speculazione filosofica.
