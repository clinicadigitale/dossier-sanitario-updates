# Clinica Digitale - Gestore licenze

Backend minimale per i piani FREE, MEDIUM e FULL di Clinica Digitale - Dossier Sanitario.

## Principi

- una sola codebase dell'applicazione;
- il piano appartiene al Dossier/account, non al dispositivo;
- FREE è il fallback quando non esiste un entitlement valido;
- MEDIUM e FULL vengono restituiti come entitlement firmati RSA;
- la chiave privata non deve mai essere inserita nell'EXE, nel sito o nel repository;
- il pannello `/admin` permette l'assegnazione manuale di un piano, compresi omaggi/tester/staff;
- prezzo di lancio: MEDIUM 1,99 EUR e FULL 2,99 EUR fino al 14/02/2027 compreso; dal 15/02/2027 prezzi standard 4,99 EUR e 9,99 EUR.

## Variabili/secret richiesti in Cloudflare

- `LICENSE_PRIVATE_KEY_PEM` secret: chiave RSA privata PKCS#8.
- `ADMIN_API_KEY` secret: token amministratore lungo e casuale.
- binding D1 `DB` collegato al database `clinica-digitale-licenze`.

## Creazione D1

Creare un database D1 denominato `clinica-digitale-licenze`, applicare `schema.sql`, quindi sostituire `INSERIRE_ID_D1` in `wrangler.jsonc` con l'ID reale del database.

## Endpoint

- `GET /health`
- `GET /v1/public/plans`
- `POST /v1/license/resolve`
- `GET /admin`
- `GET /v1/admin/entitlements`
- `POST /v1/admin/entitlements`
- `POST /v1/admin/revoke`

Gli endpoint `/v1/admin/*` richiedono `Authorization: Bearer <ADMIN_API_KEY>`.
