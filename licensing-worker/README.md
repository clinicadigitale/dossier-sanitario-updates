# Clinica Digitale - Gestore licenze

Backend minimale per i piani FREE, MEDIUM e FULL di Clinica Digitale - Dossier Sanitario.

## Principi

- una sola codebase dell'applicazione;
- il piano appartiene al Dossier/account, non al dispositivo;
- FREE è il fallback quando non esiste un entitlement valido;
- MEDIUM e FULL vengono restituiti come entitlement firmati RSA;
- la chiave privata non deve mai essere inserita nell'EXE, nel sito o nel repository;
- il pannello `/admin` permette l'assegnazione manuale di un piano, compresi omaggi/tester/staff;
- il pannello mostra statistiche tecniche anonime di utilizzo per Dossier: primo/ultimo utilizzo, avvii, installazioni, versione e stato di attività;
- la telemetria non invia documenti, diagnosi, terapie, nomi, e-mail o altri dati sanitari;
- prezzo di lancio: MEDIUM 1,99 EUR e FULL 2,99 EUR fino al 14/02/2027 compreso; dal 15/02/2027 prezzi standard 4,99 EUR e 9,99 EUR;
- per entitlement con origine `paid`, il token firmato richiede refresh dopo 6 ore e non resta valido offline oltre 24 ore;
- il backup del Dossier non è autorità di licenza: la licenza viene sempre risolta dal backend e il downgrade non cancella i dati;
- i pagamenti PayPal sono predisposti ma restano DISABILITATI finché `PAYMENT_MODEL` non viene deliberatamente impostato a `one_time` e i secret PayPal non sono configurati;
- webhook PayPal: verifica crittografica lato PayPal, idempotenza per event ID, ricontrollo server-to-server della capture, confronto importo/valuta, rollback automatico su refund/reversal e sospensione su dispute;
- nessun Client Secret o access token PayPal deve mai arrivare al browser, al Dossier, al repository o ai backup.

## Variabili/secret richiesti in Cloudflare

- `LICENSE_PRIVATE_KEY_PEM` secret: chiave RSA privata PKCS#8.
- `ADMIN_API_KEY` secret: token amministratore lungo e casuale.
- `PAYPAL_CLIENT_ID` secret: Client ID dell'app REST PayPal.
- `PAYPAL_CLIENT_SECRET` secret: Client Secret dell'app REST PayPal; solo server-side.
- `PAYPAL_WEBHOOK_ID` secret: ID del webhook registrato nell'app PayPal e usato per la verifica firma.
- binding D1 `DB` collegato al database `clinica-digitale-licenze`.

Variabili non segrete:
- `PAYPAL_ENVIRONMENT=sandbox` durante i test, `live` soltanto dopo collaudo;
- `PAYMENT_MODEL=disabled` per default. Non portare a `one_time` finché modello commerciale, checkout e test sandbox non sono approvati.

## Creazione D1

Creare un database D1 denominato `clinica-digitale-licenze`, applicare `schema.sql`, quindi sostituire `INSERIRE_ID_D1` in `wrangler.jsonc` con l'ID reale del database.

## Endpoint

- `GET /health`
- `GET /v1/public/plans`
- `POST /v1/license/resolve`
- `POST /v1/usage/ping`
- `POST /v1/payments/paypal/create-order`
- `POST /v1/payments/paypal/capture-order`
- `POST /v1/payments/paypal/webhook`
- `GET /admin`
- `GET /v1/admin/usage`
- `GET /v1/admin/entitlements`
- `POST /v1/admin/entitlements`
- `POST /v1/admin/revoke`

Gli endpoint `/v1/admin/*` richiedono `Authorization: Bearer <ADMIN_API_KEY>`.


## Hardening PayPal / OAuth

Il Client Secret PayPal resta esclusivamente nei secret Cloudflare. Il Worker ottiene access token OAuth 2.0 server-to-server e non li restituisce mai al client.

Un ordine non può scegliere liberamente il prezzo: il piano viene validato e l'importo viene calcolato dal Worker usando il listino ufficiale. Il `dossier_id` non viene inviato a PayPal: come `custom_id` viene usato un ID pagamento casuale, mentre l'associazione al Dossier rimane in D1.

Protections applicate:
- controllo coppia Dossier/installazione già registrata prima di creare un ordine;
- massimo 5 tentativi di creazione ordine in 15 minuti per Dossier;
- `PayPal-Request-Id` per idempotenza di creazione e capture;
- entitlement soltanto dopo capture `COMPLETED`, poi riletta direttamente dall'API Payments di PayPal;
- verifica esatta di importo e valuta prima dell'attivazione;
- webhook verificato tramite `/v1/notifications/verify-webhook-signature` e `PAYPAL_WEBHOOK_ID`;
- event ID PayPal memorizzato per impedire doppia elaborazione/replay;
- refund/reversal ripristinano il piano precedente soltanto se quel pagamento è ancora l'entitlement corrente;
- una licenza più recente o assegnata manualmente non viene abbassata da un vecchio rimborso;
- dispute aperta = sospensione automatica del piano pagato; riattivazione automatica soltanto per esito esplicitamente favorevole al venditore o cancellazione della contestazione e capture ancora `COMPLETED`;
- nessun payload webhook completo o dato sanitario viene archiviato nel registro eventi.

Eventi da registrare nel webhook PayPal:
`PAYMENT.CAPTURE.COMPLETED`, `PAYMENT.CAPTURE.PENDING`, `PAYMENT.CAPTURE.DENIED`,
`PAYMENT.CAPTURE.REFUNDED`, `PAYMENT.CAPTURE.REVERSED`,
`CHECKOUT.PAYMENT-APPROVAL.REVERSED`,
`CUSTOMER.DISPUTE.CREATED`, `CUSTOMER.DISPUTE.UPDATED`, `CUSTOMER.DISPUTE.RESOLVED`.

Il pannello amministrativo usa inoltre header di sicurezza e CSP restrittiva. La protezione applicativa non sostituisce MFA PayPal, aggiornamenti, controllo accessi Cloudflare e monitoraggio operativo.
