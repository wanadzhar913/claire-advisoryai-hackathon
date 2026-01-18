### Getting started:
You'll first have to clone the project and then your can start it using [`docker-compose.yaml`](/docker-compose.yaml).
```bash
git clone https://github.com/irfannaqieb/claire.git
cd claire

docker compose --env-file .env up --build
docker compose down -v # end of session
```

If you'd like to work on/contribute code a particular service, comment out the relevant service in the [`docker-compose.yaml`](/docker-compose.yaml). Then do the following:

```bash
docker compose --env-file .env up --build
cd apps/backend && python3 -m main # if you run backend outside of docker compose change POSTGRES_HOST & MINIO_ENDPOINT to localhost
```

You'll be able to access the following services locally:
- Backend API: http://localhost:8000/docs
- MinIO Portal: http://localhost:9000 (username: admin, password: admin123)

### To Do's
- [ ] Implement JWT Session & User Management
- [ ] Add datasets in [`datasets`](/datasets/banking_transactions/)
- [ ] In [`sankey.py`](/apps/backend/utils/sankey.py), need to handle edge cases where credits and debits for a period is 0.
