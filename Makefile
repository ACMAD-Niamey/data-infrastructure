ifneq (,$(wildcard ./ .env))
	include .env
	export
	ENV_FILE_PARAM = --env-file .env
endif

build:
	docker compose up --build -d --remove-orphans
up:
	docker compose up -d
down:
	docker compose down
logs:
	docker compose logs -f
makemigrations:
	docker compose exec web python manage.py makemigrations
migrate:
	docker compose exec web python manage.py migrate
createsuperuser:
	docker compose exec web python manage.py createsuperuser
collectstatic:
	docker compose exec web python manage.py collectstatic --noinput
shell:
	docker compose exec web python manage.py shell
connectdb:
	PGPASSWORD=${POSTGRES_PASSWORD} psql -h localhost -U ${POSTGRES_USER} -d ${POSTGRES_DB}