# Lampac Bunny — installeren op bunny.net (NL)

Lampac Bunny is een **zelfstandige Lampac-backend**. Het project is niet afhankelijk van Lampa Multilingual Edition en kan door elke geschikte client worden gebruikt. Gebruik uitsluitend mediabronnen waarvoor je toestemming hebt.

> **Status:** de broncode en offline controles zijn voorbereid. Een echte Bunny-deployment, de werking van mediabronnen, afspelen en gegevensherstel zijn **nog niet gevalideerd**. Stel de server niet onbeschermd bloot aan het internet.


## Read-only-bestandssysteem van Docker Desktop herstellen

In het aangeleverde logboek trad de fout op in de **opslag van Docker Desktop**, niet bij GitHub of NuGet: `dpkg: Input/output error`, `NuGet: Read-only file system`, daarna `metadata_v2.db: read-only file system`.

1. **Start Docker Desktop opnieuw**, zonder Factory Reset of volumes van andere projecten te wissen.
2. Voer `bash bunny/scripts/doctor.sh` uit (diagnose, verwijdert niets).
3. Controleer de vrije ruimte op uw Mac en ga naar **Docker Desktop → Settings → Resources → Advanced**. Vergroot of verplaats de virtuele schijf via Docker Desktop, niet via Finder.
4. Wanneer Docker weer werkt, kunt u eventueel `docker builder prune` interactief uitvoeren om **ongebruikte buildcaches** te verwijderen. Voer **niet** `docker system prune --volumes` uit.
5. Bouw opnieuw nadat u de repository hebt bijgewerkt:

```bash
git pull --ff-only
bash bunny/scripts/doctor.sh
bash bunny/scripts/preflight.sh
bash bunny/scripts/build-image.sh ghcr.io/vbrekher/lampac-bunny:v0.1.1 --load
```

De nieuwe `bunny/Dockerfile` bouwt een **LIGHT-image** op basis van de volledige Lampac-broncode en officiële .NET 10-images, maar bevat **geen** Chromium, GStreamer of FFmpeg. Deze modules zijn in de standaardconfiguratie uitgeschakeld. Schakel ze niet in met een JSON-override; een afzonderlijk geteste uitgebreide image is nodig. Blijft de VM na een herstart read-only, onderzoek de Docker-schijf zonder volumes zomaar te wissen.

**v0.1.1 oplossing voor de containergebruiker:** Ubuntu in de .NET 10-basisimage heeft al een groep met GID 1000. De Dockerfile gebruikt daarom de bestaande niet-rootgebruiker `app` in plaats van een conflicterende groep te maken. Voer `bash bunny/scripts/local-acceptance.sh` uit voor een lokale test die direct stopt bij een bouwfout.

**Opnieuw testen zonder hercompilatie:** na een geslaagde Docker-build maar een vroege HTTP-fout, voer `bash bunny/scripts/local-acceptance.sh --no-build` uit met `LAMPAC_ROOT_PASSWORD` ingesteld. Het script blijft tijdens het opstarten proberen en toont de containerstatus en logboeken bij een fout. Een vroege curl-fout (52) bewijst niet dat Lampac defect is.

## 1. Zelf de Docker-image bouwen

Benodigd: Git, Bash, Docker met buildx en `jq` voor de offline controle.

```bash
git clone https://github.com/vbrekher/lampac-bunny.git
cd lampac-bunny
bash bunny/scripts/preflight.sh
bash bunny/scripts/build-image.sh ghcr.io/vbrekher/lampac-bunny:v0.1.1 --load
# Publiceren na docker login ghcr.io:
bash bunny/scripts/build-image.sh ghcr.io/vbrekher/lampac-bunny:v0.1.1 --push
```

Met `--load` blijft de image lokaal; `--push` publiceert deze in de containerregistry. De image wordt gebouwd uit de .NET-broncode van deze fork. Vanwege de browser- en mediaonderdelen kan de build veel schijfruimte gebruiken.

Voor een lokale test:

```bash
export LAMPAC_ROOT_PASSWORD="$(openssl rand -hex 24)"
docker compose -f bunny/compose.yaml up --build -d
curl -fsS 'http://127.0.0.1:9118/version?type=hash'
```

Zet wachtwoorden nooit in Git of openbare logs.

## 2. Deployment in Bunny Magic Containers

Open [Bunny Dashboard](https://dash.bunny.net/) → **Magic Containers → Add App**:

1. Selecteer de gepubliceerde **linux/amd64** image `ghcr.io/vbrekher/lampac-bunny:v0.1.1`. Koppel GHCR als deze privé is.
2. Maak **één CDN-endpoint** aan met containerpoort **9118**. Het externe adres gebruikt HTTPS; binnen de container draait HTTP.
3. Voeg een persistent volume toe met pad `/lampac/database` (bijvoorbeeld 5 GB). Een tweede volume `/lampac/cache` is optioneel (bijvoorbeeld 2 GB). Een proefaccount ondersteunt slechts één volume.
4. Stel de omgevingsvariabele `LAMPAC_ROOT_PASSWORD` in op een uniek geheim van minimaal 16 tekens.
5. Gebruik **één regio, één replica en geen autoscaling**. SQLite van Lampac is geen gedeelde database.
6. Stel Startup/Readiness/Liveness HTTP-controles in: pad `/version?type=hash`, poort 9118 en voldoende opstarttijd.
7. Stel vóór openbare toegang authenticatie, snelheidslimieten en routebeperkingen in. Een CDN-endpoint is standaard publiek toegankelijk.
8. Deploy de container, controleer de logs en voer uit:

```bash
bash bunny/scripts/smoke.sh 'https://YOUR-CONTAINER-ENDPOINT'
```

Deze test controleert de service en `/online.js`, niet de echte beschikbaarheid van video.

## 3. Modules en eigen instellingen

Het startprofiel schakelt risicovolle of stateful modules uit, onder andere TorrServer, JacRed, Sync, TimeCode, GStreamer, DLNA, WebLog en SISI. De broncode blijft aanwezig; activeer modules pas na controle van beveiliging, netwerk en capaciteit.

Wijzig een lokale kopie van `bunny/config/init.conf` en encodeer deze:

```bash
base64 < bunny/config/init.conf | tr -d '\n'
```

Plaats de uitkomst in de Bunny-omgevingsvariabele `LAMPAC_BUNNY_CONFIG_B64`. De JSON moet geldig zijn en luisteren op HTTP `0.0.0.0:9118` (of `ip=any`). Ongeldige configuratie wordt geweigerd. Herstart de container om wijzigingen toe te passen. Plaats geen geheimen in het configuratiebestand.

## 4. Opslag en beperkingen

- `/lampac/database` bevat de lokale SQLite-bestanden; dit is **geen Bunny Database**. Een directe integratie met Bunny Database bestaat nog niet.
- Bunny-volumes hebben **geen automatische back-ups of replicatie**. Replicas krijgen ieder een eigen volume. Maak offline back-ups en test het herstel.
- Torrent/P2P, DLNA/multicast, specifieke netwerkpoorten en transcoding kunnen beperkt worden door Magic Containers. Ondersteuning is nog niet aangetoond.
- Voorkom een onbeveiligde open proxy. Respecteer auteursrechten, gebruiksvoorwaarden en beveiligingsregels.

Zie [Security](SECURITY.md), [Architecture](ARCHITECTURE.md), [Bunny deployment](https://bunny.net/docs/magic-containers/deploy), [Persistent Volumes](https://bunny.net/docs/magic-containers/persistent-volumes) en [Lampac-documentatie](https://docs.lampac.dev/).
