# 🐄 Questr Bot

Bot Telegram di sfide giornaliere gamificate per un gruppo di amici, ispirato all'app Questr.
Gira **senza PC acceso e senza hosting a pagamento**: usa GitHub Actions (un tick ogni 30 min).

## Come è organizzato

- **Nel gruppo, a bottoni** → pannello, profilo/mucca, **negozio e acquisti**, classifica,
  nickname, sfida del giorno, consegne con foto/video, recap e voti.
- **In chat privata col bot** → **solo** aggiunta di **sfide e penitenze**: restano segrete e
  vengono estratte **a sorteggio** (sorpresa per tutti). Qui l'**admin** può mettere in pausa.

## Cosa fa

- Ogni giorno (tranne domenica) una sfida tocca a una persona **a rotazione equa**:
  tutti fanno lo stesso numero di turni.
- La persona la fa, manda **foto/video** e tocca **✅ valida** (o risponde `/fatto`).
- Si guadagnano **XP e coin**, la mucca sale di livello, cresce lo **streak** 🔥
- A metà giornata, chi non ha consegnato riceve un **promemoria privato** (solo lui/lei).
- Con i coin si comprano **accessori per la mucca** dal negozio, nel gruppo.
- Il bot **ricorda periodicamente** di aggiungere nuove sfide/penitenze e **avvisa quando il
  repertorio è basso** (niente silenzi).
- **Domenica**: riposo, recap, **voto** sulla sfida più bella e **penitenza votata** per chi ha saltato.
- **Modalità vacanza**: l'admin mette in **pausa** sfide e promemoria quando serve.

## Chi fa cosa

- **Tutti**: giocano, comprano accessori, cambiano nickname, aggiungono sfide/penitenze in privato.
- **Admin** (chi ha fatto `/setup`): in chat privata col bot ha i bottoni **⏸️ Pausa / ▶️ Riprendi**
  (comandi `/pausa` e `/riprendi`). Gli altri non possono.

## Comandi principali

| Comando | Dove | Cosa fa |
|---|---|---|
| `/setup` | gruppo | Registra il gruppo; chi lo lancia diventa **admin** |
| `/menu` | gruppo/privato | Apre il pannello del gruppo o il menu privato |
| `/entra` · `/esci` | gruppo | Entra/esce dalla rotazione |
| `/nickname <nome>` | ovunque | Cambia il tuo soprannome |
| `/fatto` | gruppo | Valida rispondendo alla tua foto/video |
| `/pausa` · `/riprendi` | privato, **solo admin** | Ferma/riprende il gioco (vacanze) |

Sfide e penitenze si aggiungono dai bottoni **➕ / 😈** (che aprono la chat privata).

---

## Setup (una volta sola)

1. **@BotFather** → `/newbot`, copia il **token**; poi `/setprivacy` → **Disable**.
2. Crea un repository GitHub e carica tutti i file (con le cartelle `.github/workflows/` e `data/`).
3. **Settings → Secrets and variables → Actions → New secret**: `TELEGRAM_BOT_TOKEN` = il token.
4. **Actions** → abilita i workflow → **Run workflow** una volta.
5. Nel gruppo: `/setup` (tu diventi admin). Tutti: `/entra`.
6. **Ognuno prema Start sul bot in privato** (basta toccare un bottone ➕/✏️ dal pannello):
   serve per i **promemoria privati** e per aggiungere sfide segrete.
7. Aggiungete un po' di sfide e penitenze dai bottoni.

## Aggiungere persone

La persona entra nel gruppo, scrive **`/entra`**, preme **Start** sul bot in privato e sceglie un
nickname. Entra subito nella rotazione **senza sbilanciarla** (parte allineata agli altri).

---

## Privacy: pubblico o privato?

- **Il token è sempre al sicuro** nei Secrets (cifrati), mai nel codice.
- **Foto/video non vengono mai salvati** dal bot: restano su Telegram.
- Il bot **non salva il nome vero**: nickname di default `Mucca#N`, modificabile.

Con i nickname puoi tenere **il repo pubblico** (minuti Actions illimitati; per risposte più
rapide abbassa il cron a `*/10 * * * *` in `.github/workflows/questr.yml`). Se preferisci nascondere
anche nickname e testi, usa un **repo privato** (col cron a 30 min resti nel free tier).

---

## Personalizzazione (`config.py`, commentato)

Orari (sfida, promemoria, recap), XP/coin, oggetti del negozio, penitenze di default, frasi
celebrative, **soglie del repertorio** (`MIN_POOL_QUESTS`, `MIN_POOL_PENITENZE`) e ogni quanti
giorni ricordare di aggiungerne (`REMIND_ADD_EVERY_DAYS`).

## Stato

Niente database: è `data/state.json`, salvato nel repo dalle Actions dopo ogni tick. Creato da solo.
