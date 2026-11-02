# syntax=docker/dockerfile:1.7
# Standalone, source-built LIGHT profile for Bunny Magic Containers.
# Chromium / GStreamer / FFmpeg are intentionally not installed in this image.
# The safe default init.conf disables their dependent modules.
ARG SDK_IMAGE=mcr.microsoft.com/dotnet/sdk:10.0
ARG RUNTIME_IMAGE=mcr.microsoft.com/dotnet/aspnet:10.0

FROM --platform=$BUILDPLATFORM ${SDK_IMAGE} AS builder
ARG TARGETARCH=amd64
ARG LAMPAC_VERSION=bunny-preview
ARG GIT_COMMIT=unknown
WORKDIR /src
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
COPY . .
RUN test "$TARGETARCH" = "amd64" || (echo "Bunny image currently requires linux/amd64" >&2; exit 2)
RUN --mount=type=cache,target=/root/.nuget/packages,sharing=locked \
    dotnet publish Core/Core.csproj \
    --configuration Release \
    --runtime linux-x64 \
    --self-contained false \
    --output /out \
    -p:PlaywrightPlatform=linux-x64 \
    -p:LAMPAC_VERSION="$LAMPAC_VERSION" \
    -p:SourceRevisionId="$GIT_COMMIT"

FROM ${RUNTIME_IMAGE} AS runtime
LABEL org.opencontainers.image.source="https://github.com/vbrekher/lampac-bunny" \
      org.opencontainers.image.title="Lampac Bunny" \
      org.opencontainers.image.licenses="AGPL-3.0-only" \
      org.opencontainers.image.description="Lampac Bunny light profile for Bunny Magic Containers"
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_RUNNING_IN_CONTAINER=true \
    DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=false
# Only basic HTTP/JSON tooling. No Chromium, GStreamer or heavy desktop libraries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl jq \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 lampac \
    && useradd --uid 1000 --gid 1000 --no-create-home --home-dir /lampac --shell /usr/sbin/nologin lampac \
    && mkdir -p /lampac/database /lampac/cache /opt/lampac-bunny \
    && chown -R lampac:lampac /lampac /opt/lampac-bunny
WORKDIR /lampac
COPY --from=builder --chown=lampac:lampac /out/ /lampac/
COPY --chown=lampac:lampac bunny/config/init.conf /opt/lampac-bunny/init.conf
COPY --chown=lampac:lampac bunny/docker-entrypoint.sh /usr/local/bin/lampac-bunny-entrypoint
RUN chmod 0755 /usr/local/bin/lampac-bunny-entrypoint
USER lampac
EXPOSE 9118
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl --fail --silent --output /dev/null 'http://127.0.0.1:9118/version?type=hash' || exit 1
ENTRYPOINT ["/usr/local/bin/lampac-bunny-entrypoint"]
