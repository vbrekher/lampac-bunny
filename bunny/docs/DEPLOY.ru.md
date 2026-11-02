# Lampac Bunny — установка на bunny.net (RU)

Это **самостоятельный сервер Lampac**, не связанный с Lampa Multilingual Edition. Он может обслуживать любой совместимый клиент. Использование сторонних источников контента регулируется их условиями и применимым законодательством.

> **Статус:** исходный код и локальные проверки подготовлены. Реальный запуск в Bunny, работа источников, медиаплееров и persistency пока не подтверждены. Не публикуйте сервер без сетевой защиты и тестов.

## 1. Сборка на Mac/Linux

Требования: Git, Docker Desktop или Docker Engine с `buildx` и Bash. Для локального самотеста также нужен `jq`.

```bash
git clone https://github.com/vbrekher/lampac-bunny.git
cd lampac-bunny
bash bunny/scripts/preflight.sh
# Собрать собственный образ из исходников ЭТОГО репозитория:
bash bunny/scripts/build-image.sh ghcr.io/vbrekher/lampac-bunny:v0.1.0 --load
# Или опубликовать образ в GHCR после docker login ghcr.io:
bash bunny/scripts/build-image.sh ghcr.io/vbrekher/lampac-bunny:v0.1.0 --push
```

`--load` сохраняет образ только локально; `--push` требует права записи в выбранный реестр. Dockerfile собирает `.NET 10` исходники самого форка. Сборка тяжёлая: для GStreamer/Chromium/FFmpeg понадобится много свободного места.

**Локальный запуск без публикации**:

```bash
export LAMPAC_ROOT_PASSWORD="$(openssl rand -hex 24)"
docker compose -f bunny/compose.yaml up --build -d
curl -fsS 'http://127.0.0.1:9118/version?type=hash'
```

Не храните `LAMPAC_ROOT_PASSWORD` в Git, скриншотах и публичных терминальных логах.

## 2. Запуск в Bunny Magic Containers

Откройте [Bunny Dashboard](https://dash.bunny.net/) → **Magic Containers → Add App**:

1. Укажите опубликованный **linux/amd64** образ `ghcr.io/vbrekher/lampac-bunny:v0.1.0` (или собственный путь). Приватный GHCR требует подключения реестра.
2. Создайте **один CDN endpoint**, укажите порт контейнера **9118**. Внешнее подключение будет HTTPS, внутри контейнера HTTP.
3. Создайте persistent volume с mount path `/lampac/database` (например 5 GB). Второй опциональный том `/lampac/cache` (например 2 GB). В trial-аккаунте доступен только один том.
4. В переменных окружения укажите `LAMPAC_ROOT_PASSWORD` с уникальным длинным значением (не менее 16 символов). Не используйте дефолтные пароли.
5. Выберите **один регион / один инстанс / без autoscaling**. Встроенная SQLite не является общей распределённой БД.
6. Настройте Startup/Readiness/Liveness HTTP GET `GET /version?type=hash`, порт 9118; во время первого старта допускайте увеличенный startup grace period.
7. Включите защиту доступа / rate limiting на публичном endpoint, запретите опасные маршруты и ограничьте доступ до реальной проверки безопасности. **Bunny CDN endpoint публичный сам по себе.**
8. Разверните контейнер, проверьте логи и публичный URL:

```bash
bash bunny/scripts/smoke.sh 'https://YOUR-CONTAINER-ENDPOINT'
```

Ожидаемые URL: `https://YOUR-CONTAINER-ENDPOINT/online.js` и `/version?type=hash`. Реальный список доступных видеосервисов этой проверкой не подтверждается.

## 3. Дополнительные модули

Стартовый пресет намеренно выключает TorrServer, JacRed, Sync, TimeCode, GStreamer, DLNA, WebLog, SISI и другие потенциально опасные либо stateful-модули. Код **сохранён** в форке; это не удаление функциональности.

Чтобы настроить больше модулей, создайте **свой JSON** (без комментариев, с `listen.ip=0.0.0.0`, `listen.port=9118`, `listen.scheme=http`):

```bash
base64 < bunny/config/init.conf | tr -d '\n'
```

После редактирования передайте одну строку как `LAMPAC_BUNNY_CONFIG_B64` через Bunny Environment Variables. **Не вставляйте в JSON ключи доступа или секреты.** Обновлённый конфиг применяется при перезапуске контейнера. При включении модулей отдельно проверьте их права доступа, ресурсы и ограничения Magic Containers.

## 4. Данные и безопасность

- `database/` хранит локальные SQLite-данные; Bunny Database **не является** прямой заменой SQLite в Lampac. Интеграции с Bunny Database пока **нет**.
- Bunny volumes привязаны к поду/узлу и **не имеют автоматического резервного копирования или репликации**. Не включайте масштабирование или multi-region при использовании локального Sync. Нужны регулярные offline-бэкапы и проверка восстановления.
- P2P, multicast/DLNA, входящие UDP/TCP и аппаратный транскодинг в Magic Containers могут работать иначе, чем на VPS. Ничего из этого пока не объявлено поддерживаемым.
- Если подключаете сторонние сервисы, используйте только разрешённые источники и собственные учётные данные. Не делайте из сервера открытый прокси.

Информация о защите: [SECURITY.md](SECURITY.md). Архитектура: [ARCHITECTURE.md](ARCHITECTURE.md).

Официальная документация: [Magic Containers](https://bunny.net/docs/magic-containers/deploy), [Persistent Volumes](https://bunny.net/docs/magic-containers/persistent-volumes), [Lampac](https://docs.lampac.dev/).
