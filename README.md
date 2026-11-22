# RFID Access Control v1.3.0

<p align="center">
  <img src="icon.png" alt="RFID Access Control" width="128" />
</p>

Integrazione per Home Assistant che gestisce il controllo accessi con il tastierino Zigbee **KEPZB-110** (PIN e tessere RFID), con una card Lovelace per tutto il lavoro quotidiano.

## Novità 1.3.0

- **Card automatica**: l'integrazione serve la card e la registra da sola in Lovelace. Dopo un aggiornamento HACS non serve copiare nulla. Se c'era la vecchia copia in `/config/www/rfid-access-control-card.js`, viene sostituita.
- **Ritardo coperchio**: nuova opzione (predefinito 3 secondi). Il tastierino si blocca solo se il coperchio resta aperto più a lungo del ritardo. L'apertura viene sempre registrata nel log e nell'evento `rfid_tamper_detected`.
- **Più tastierini**: un solo sistema può gestire più tastierini. Il selettore in Home sceglie quale usare. Dal Menu operatore si aggiunge un tastierino trovato in Zigbee2MQTT; quelli già aggiunti compaiono ma non si scelgono di nuovo.
- **Copia utente**: copia un utente su un altro tastierino (nome, PIN, tessera, azioni, periodo di accesso). Chiede il PIN admin del tastierino di destinazione. Controlla le azioni: le entità possono essere diverse.
- **Tasto per azione**: ogni azione sceglie il tasto che la attiva (lucchetto aperto, lucchetto chiuso, casa, luna, qualsiasi tasto).
- **Tasto SOS**: `emergency` genera `rfid_emergency`, anche con tastierino bloccato. Le azioni SOS globali si gestiscono nel Menu operatore.
- **Vedere il PIN**: in modifica utente il PIN resta nascosto (`••••`) e si vede solo con il PIN admin.
- **Elimina utente** con conferma, **cambio PIN admin** dalla schermata Utenti.

## Installazione con HACS

1. Apri **HACS** → **Integrazioni** → menu a tre puntini → **Repository personalizzati**.
2. Aggiungi `https://github.com/EdisonACDC/rfid-access-control`, categoria **Integrazione**.
3. Cerca "RFID Access Control", installa e riavvia Home Assistant.

## Installazione manuale

Copia la cartella `custom_components/rfid_access_control/` in `config/custom_components/` e riavvia Home Assistant.

## Configurazione

1. **Impostazioni** → **Integrazioni** → **Aggiungi integrazione** → "RFID Access Control".
2. Inserisci l'**ID tastierino** (es. `portoncino`) e il **topic MQTT** Zigbee2MQTT (es. `zigbee2mqtt/tastierino_portoncino`).
3. Apri la card: al primo avvio chiede il **PIN admin** e il **PIN operatore**. Non esistono PIN di default.

Le **Impostazioni** dell'integrazione permettono di cambiare il topic MQTT e il ritardo del coperchio (0-60 secondi). Dopo il salvataggio il tastierino si ricarica.

## Card Lovelace

La card è registrata automaticamente. Per aggiungerla alla dashboard:

```yaml
type: custom:rfid-access-control-card
entity: sensor.rfid_users_portoncino
title: Controllo Accessi
lock_timeout: 5
```

| Parametro | Obbligatorio | Default | Descrizione |
|-----------|-------------|---------|-------------|
| `entity` | Sì | - | Sensore del tastierino (`sensor.rfid_users_<id>`) |
| `title` | No | Controllo Accessi | Titolo della card |
| `lock_timeout` | No | 5 | Minuti prima del blocco automatico della card |
| `device_id` | No | - | Non serve: la card legge il tastierino dal sensore |

Se la risorsa non viene registrata (Lovelace in modalità YAML), aggiungila a mano in **Impostazioni** → **Dashboard** → **Risorse**: `/rfid_access_control/rfid-access-control-card.js?v=1.3.0`, tipo **Modulo JavaScript**.

## Come funziona

1. Chi digita un codice sul tastierino: l'integrazione riceve il codice via MQTT.
2. Un doppio invio dello stesso codice entro 2 secondi viene ignorato. Non esegue azioni e non conta come errore.
3. Il codice viene cercato tra gli utenti e si verifica che l'accesso sia valido in quel momento (periodo, numero di accessi, utente attivo).
4. Vengono eseguite le azioni dell'utente per il tasto premuto.
5. Dopo 5 codici errati il tastierino si blocca per 60 secondi.
6. Coperchio aperto oltre il ritardo: il tastierino si blocca. Si sblocca con il PIN operatore, dalla card o sul tastierino (PIN operatore + Arma Tutto).
7. Modalità installatore: per 15, 30 o 60 minuti il tastierino funziona anche con il coperchio aperto.

## Più tastierini

- Il selettore in Home compare solo con due o più tastierini.
- **Aggiungi tastierino** (Menu operatore): legge da `zigbee2mqtt/bridge/devices` i tastierini trovati e crea la voce con il topic giusto. Se non compare, si scrivono nome e topic a mano.
- Con più tastierini i servizi chiedono `device_id`; la card lo mette da sola.

## Eventi

| Evento | Quando | Dati principali |
|--------|--------|-----------------|
| `rfid_access_granted` | Accesso riuscito | `user_id`, `user_name`, `keypad_action`, `device_id` |
| `rfid_access_denied` | Accesso negato | `reason`: `unknown_code` (codice sconosciuto o utente non valido adesso), `tamper_lock` (coperchio), `locked_out` (troppi errori); `device_id` |
| `rfid_emergency` | Tasto SOS | `device_id`, `user_id`, `user_name` (vuoti se il codice non è valido o assente) |
| `rfid_tamper_detected` | Coperchio aperto (sempre) | `device_id` |
| `rfid_tamper_locked` | Coperchio aperto oltre il ritardo | `device_id` |
| `rfid_tamper_unlocked` | Sbloccato dopo il coperchio | `device_id`, `source` |
| `rfid_installer_mode` | Modalità installatore accesa o spenta | `device_id`, `active`, `minutes` |
| `rfid_user_added` / `rfid_user_removed` | Utente aggiunto o rimosso | `user_id`, `device_id` |

## Servizi

| Servizio | Descrizione |
|----------|-------------|
| `rfid_access_control.add_user` | Aggiunge un utente (PIN o tessera, accesso temporaneo facoltativo) |
| `rfid_access_control.remove_user` | Rimuove un utente |
| `rfid_access_control.update_user` | Aggiorna un utente (PIN o tessera vuoti = invariati) |
| `rfid_access_control.add_action` | Aggiunge un'azione a un utente, con il tasto del tastierino |
| `rfid_access_control.remove_action` | Rimuove un'azione |
| `rfid_access_control.validate_access` | Verifica PIN o tessera ed esegue le azioni |
| `rfid_access_control.list_users` | Elenca gli utenti |
| `rfid_access_control.set_admin_pin` | Imposta o cambia il PIN admin (`current_pin` se già impostato) |
| `rfid_access_control.set_operator_pin` | Imposta o cambia il PIN operatore (`current_pin` se già impostato) |
| `rfid_access_control.verify_admin_pin` | Verifica il PIN admin (risponde `valid`, `locked_out`, `not_set`) |
| `rfid_access_control.verify_operator_pin` | Verifica il PIN operatore |
| `rfid_access_control.clear_tamper_lock` | Sblocca dopo il coperchio (richiede `pin` operatore) |
| `rfid_access_control.set_installer_mode` | Modalità installatore: `pin` operatore e `minutes` (0-60, 0 spegne) |
| `rfid_access_control.test_access_code` | Dice di chi è un codice, senza eseguire azioni (richiede `operator_pin`) |
| `rfid_access_control.get_user_pin` | Restituisce il PIN di un utente (richiede `admin_pin`) |
| `rfid_access_control.add_sos_action` | Aggiunge un'azione globale del tasto SOS |
| `rfid_access_control.remove_sos_action` | Rimuove un'azione globale del tasto SOS |
| `rfid_access_control.copy_user` | Copia un utente su un altro tastierino (serve il PIN admin di destinazione) |
| `rfid_access_control.discover_keypads` | Elenca i tastierini trovati in Zigbee2MQTT |

## Privacy dei PIN

I PIN (admin, operatore, utenti) non compaiono mai negli attributi del sensore. Il sensore espone solo `has_pin`, `admin_pin_set` e `operator_pin_set`. Il PIN di un utente si legge solo con `get_user_pin` e il PIN admin.

## Dalla 1.2.x

| Cosa | Ora | Cosa fare |
|------|-----|-----------|
| Card | Registrata dall'integrazione | Rimuovi la risorsa `/local/rfid-access-control-card.js` se la avevi |
| Coperchio | Blocco dopo il ritardo (3 s) | Regola il ritardo nelle impostazioni, se serve |
| Topic MQTT nelle impostazioni | Ricarica il tastierino | Nulla |
| Attributi del sensore | Nessun PIN; `mqtt_topic` aggiunto | Nulla |

## Beta

Le versioni di prova sono **pre-release GitHub** dello stesso repository, con tag come `v1.3.1-beta.1`. Per provarle, in HACS attiva "Mostra versioni beta" sul repository. La versione stabile resta sul ramo predefinito e nelle release senza `beta`.

## Licenza

MIT
