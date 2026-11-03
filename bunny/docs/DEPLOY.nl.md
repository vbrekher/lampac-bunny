# Lampac Bunny — installeren op Bunny

## Snel beginnen

Vereist: macOS of Linux, Bash, curl, **Python 3.10+** en een Bunny-account dat Magic Containers mag aanmaken. Configuratie van Docker, GitHub, een VPS of SSH is niet nodig.

```bash
curl -fsSL https://raw.githubusercontent.com/vbrekher/lampac-bunny/main/bunny/scripts/install-bunny.sh | bash
```

Haal de **API-sleutel van het account** op via [Bunny Dashboard](https://dash.bunny.net/), bij de accountinstellingen en API. Voer deze in bij de verborgen invoer in de terminal. Het installatieprogramma stuurt de sleutel alleen naar Bunny, slaat deze nooit op en weigert omleidingen van verzoeken met de sleutel. De omgevingsvariabelen `BUNNY_API_KEY` en `BUNNYNET_API_KEY` worden ondersteund voor automatisering; zet geen letterlijke geheimen in de opdrachtgeschiedenis.

**Live-acceptatie: BLOCKED.** Op 2026-11-03 slaagden geauthenticeerde verzoeken naar de echte Bunny-API en meldde AMS beschikbare capaciteit. Het anonieme tokenverzoek aan GHCR gaf echter HTTP 401. Er zijn geen applicatie of volume aangemaakt. Uitrol, publieke HTTPS, SQLite-behoud, herstel na herstart, Lampa en afspelen zijn nog niet geverifieerd. Zie het [acceptatierapport](../../docs/acceptance/LIVE_BUNNY_ACCEPTANCE.md) en de [JSON-resultaten](../../docs/acceptance/live-bunny-results.json).

De pakketeigenaar moet openbaar downloaden inschakelen in de [GitHub-pakketinstellingen](https://github.com/users/vbrekher/packages/container/lampac-bunny/settings). Een Bunny-sleutel geeft geen toegang tot een privé-image op GHCR. Voer daarna dezelfde opdracht uit: de exacte digest en architectuur worden alsnog gecontroleerd voordat betaalde middelen worden aangemaakt.

## Automatische configuratie

Het installatieprogramma controleert `ghcr.io/vbrekher/lampac-bunny:v0.1.1`, de verwachte digest `sha256:ec518a9170c5f4b4373545851f2325f285ee0daa26af6cd4ffa5819200b12adc` en `linux/amd64`. Het legt de digest vast in de Bunny-configuratie, kiest één beschikbare Europese regio met AMS als eerste voorkeur, koppelt GHCR en maakt het volgende aan:

- Eén applicatie `lampac-bunny` met gedeelde uitvoering en zowel minimum als maximum op één replica.
- Eén permanent volume van 5 GB op `/lampac/database`.
- Interne HTTP-poort `9118` en een publiek CDN-eindpunt met HTTPS.
- Een willekeurig `LAMPAC_ROOT_PASSWORD` en controles voor opstarten, gereedheid en beschikbaarheid op `/version?type=hash`.

Bunny brengt rekenkracht, opslag en CDN-verkeer in rekening. Het installatieprogramma wacht maximaal 600 seconden op niet-lege HTTP 200-antwoorden van `/version?type=hash` en `/online.js`. Dit is een basiscontrole, geen volledige acceptatie.

## Serveradres en verbinding

De URL verschijnt in de terminal en onder **Magic Containers → lampac-bunny → Endpoints**. Voeg `https://YOUR-ENDPOINT/online.js` toe bij de plug-ininstellingen van een compatibele Lampa-client. Test catalogi en afspelen afzonderlijk met toegestane inhoud; een geslaagd API-verzoek bewijst niet dat video afspeelt.

Het gegenereerde wachtwoord en de uitrolgegevens staan in `~/.config/lampac-bunny/deployment.json`, of onder `XDG_CONFIG_HOME`, met rechten `0600`. Bewaar een beveiligde reservekopie. Publiceer dit bestand of de sleutels nooit.

## Opnieuw openen, herstellen en bijwerken

Herhaal de oorspronkelijke opdracht om de bestaande passende applicatie te vinden en de volumes te behouden. Een onvoltooide of inactieve uitrol wordt opnieuw gestart. Bij een ander image, dubbele namen of afwijkende lokale gegevens stopt het programma voor inspectie.

```bash
# Hetzelfde vastgelegde image opnieuw uitrollen; 15 minuten wachten op HTTPS.
curl -fsSL https://raw.githubusercontent.com/vbrekher/lampac-bunny/main/bunny/scripts/install-bunny.sh | bash -s -- --redeploy --timeout 900
# Regio voor een nieuwe applicatie, indien capaciteit beschikbaar is.
curl -fsSL https://raw.githubusercontent.com/vbrekher/lampac-bunny/main/bunny/scripts/install-bunny.sh | bash -s -- --region DE
```

Een lokale vergrendeling voorkomt gelijktijdige installaties op één computer. Start het aanmaken niet tegelijk vanaf meerdere computers. Controleer na een time-out bij het aanmaken eerst het dashboard. Verwijder bestaande applicaties of volumes niet om te herstellen. `--redeploy` kiest geen nieuwe versie; een image-upgrade vereist een beoordeelde versie met nieuwe tag en digest. Overschrijf de gepubliceerde tag `v0.1.1` nooit ongemerkt.

## Problemen oplossen

| Probleem | Actie |
| --- | --- |
| Bunny 401/403 | Controleer de API-sleutel van het account en de toegang tot Magic Containers |
| GHCR onbereikbaar of afwijkende digest | Controleer openbare pakkettoegang; omzeil de digestcontrole niet |
| Geen capaciteit | Probeer later opnieuw of kies een beschikbare Europese regio |
| Time-out bij opstarten of HTTPS | Controleer containerstatus, gezondheidscontroles, CDN-eindpunt en logboeken; verleng de wachttijd |
| Onderbroken installatie | Herhaal de opdracht; de bestaande applicatie en het volume worden hergebruikt |
| Afwijkende lokale gegevens | Vergelijk de beveiligde lokale gegevens met de applicatie in Bunny vóór wijzigingen |
| Docker-schijf is alleen-lezen | Voer `bash bunny/scripts/doctor.sh` uit en herstel Docker-opslag met behoud van volumes |

## Lokale ontwikkeling en configuratie

```bash
bash bunny/scripts/preflight.sh
python3 bunny/scripts/test_deploy_bunny.py
bash bunny/scripts/test-local-acceptance.sh
# Gebruik een eigen nieuwe versietag:
bash bunny/scripts/build-image.sh YOUR-REGISTRY/lampac-bunny:NEW-VERSION --load
```

`--push` publiceert na aanmelding bij het register. De lichte broncodebouw gebruikt .NET 10 en bevat geen Chromium, FFmpeg of GStreamer. Gebruik daarvoor een afzonderlijk getest image. Optionele modules zoals Sync, TimeCode, TorrServer, JacRed, WebLog en SISI zijn aanvankelijk uitgeschakeld.

Met `LAMPAC_BUNNY_CONFIG_B64` kunt u een aangepast `bunny/config/init.conf` doorgeven. Base64 is geen versleuteling. De actieve configuratie heeft voorrang op `config/base.conf` en de standaardwaarden in de code; behoud HTTP op `0.0.0.0:9118`. Het opstartscript controleert JSON en luisterinstellingen, niet de veiligheid van elke module.

## Beveiliging en gegevens

Het hoofdwachtwoord beschermt beheerfuncties, maar de beginconfiguratie biedt geen universele authenticatie voor alle API-routes. Publieke CDN-routes vereisen beoordeelde toegangsbeveiliging, routebeperkingen en aanvraaglimieten. Bescherming tegen onbeperkt proxygebruik is niet geverifieerd; deel geen onbeveiligd eindpunt.

Gebruik één replica in één regio voor SQLite. `/lampac/database` bevat lokale SQLite, niet Bunny Database. Maak consistente reservekopieën en test herstel. Verwijder nooit gebruikersgegevens voor acceptatietests. Herstart, SQLite-behoud en .NET-logcontrole vereisen een werkende uitrol. Voer destructieve tests alleen uit op een afzonderlijk wegwerpexemplaar.

Lees ook [beveiliging](SECURITY.md), [architectuur](ARCHITECTURE.md), [officiële Bunny-uitrol](https://bunny.net/docs/magic-containers/deploy), [permanente volumes](https://bunny.net/docs/magic-containers/persistent-volumes) en [Lampac-documentatie](https://docs.lampac.dev/).
