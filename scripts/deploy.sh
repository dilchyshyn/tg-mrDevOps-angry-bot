#!/usr/bin/env bash
# Виконується на VPS: оновлює контейнер до вказаного образу і чекає healthcheck.
# Якщо новий контейнер не став healthy, повертає попередній образ.
# Використання: deploy.sh <image:tag>
set -euo pipefail

IMAGE="${1:?потрібен образ, наприклад ghcr.io/owner/repo:sha}"
SERVICE=mrdevops
HEALTH_TIMEOUT=240

cd ~/mrdevops

container_id() { docker compose ps -q "$SERVICE"; }

previous=""
if cid=$(container_id) && [ -n "$cid" ]; then
  previous=$(docker inspect --format '{{.Config.Image}}' "$cid")
fi
echo "Поточний образ: ${previous:-немає}"
echo "Новий образ: $IMAGE"

deploy() {
  MRDEVOPS_IMAGE="$1" docker compose up -d --remove-orphans --no-build
}

wait_healthy() {
  local deadline=$((SECONDS + HEALTH_TIMEOUT)) cid status restarts
  while [ "$SECONDS" -lt "$deadline" ]; do
    cid=$(container_id)
    if [ -z "$cid" ]; then
      sleep 10
      continue
    fi
    status=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid")
    restarts=$(docker inspect --format '{{.RestartCount}}' "$cid")
    if [ "$restarts" -gt 0 ]; then
      echo "Контейнер перезапускався ($restarts), процес падає"
      return 1
    fi
    case "$status" in
      healthy) return 0 ;;
      unhealthy) return 1 ;;
    esac
    sleep 10
  done
  echo "Не дочекались healthy за ${HEALTH_TIMEOUT} с"
  return 1
}

# Старі образи цього бота: лишаються лише поточний і попередній (для відкату).
# Чужі образи на сервері не чіпаються, бо фільтр за репозиторієм
cleanup_old_images() {
  local repo="${IMAGE%:*}" image
  docker images --format '{{.Repository}}:{{.Tag}}' "$repo" | while read -r image; do
    if [ "$image" != "$IMAGE" ] && [ "$image" != "$previous" ]; then
      docker image rm "$image" >/dev/null && echo "Видалено старий образ $image" || true
    fi
  done
}

docker pull "$IMAGE"
deploy "$IMAGE"

if wait_healthy; then
  echo "Деплой успішний"
  cleanup_old_images || echo "Не вдалось прибрати старі образи"
  docker image prune -f
  exit 0
fi

docker compose logs --tail=50 "$SERVICE" || true
if [ -n "$previous" ] && [ "$previous" != "$IMAGE" ]; then
  echo "Відкат на $previous"
  deploy "$previous"
fi
exit 1
