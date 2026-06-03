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
make-empty-migrations-observations:
	docker compose exec web python manage.py makemigrations observations --empty -n make_timescale_hypertables
make-hypertables:
	docker exec -e PGPASSWORD=$(POSTGRES_PASSWORD) -i geodatamanager_db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -h ${POSTGRES_HOST} < ./observations/sql/hypertable.sql
make-wis2-consumer:
	docker compose exec web python manage.py run_wis2_consumer
createsuperuser:
	docker compose exec web python manage.py createsuperuser
collectstatic:
	docker compose exec web python manage.py collectstatic --noinput
shell:
	docker compose exec web python manage.py shell
connectdb:
	PGPASSWORD=${POSTGRES_PASSWORD} psql -h localhost -U ${POSTGRES_USER} -d ${POSTGRES_DB}
connectdb-container:
	 docker exec -e PGPASSWORD=$(POSTGRES_PASSWORD) -it geodatamanager_db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -h ${POSTGRES_HOST} 
certificate:
	docker compose run --rm certbot
test:
	docker compose exec web python3 manage.py test --verbosity=2